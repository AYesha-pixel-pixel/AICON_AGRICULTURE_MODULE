from types import SimpleNamespace

import pytest
import torch
from PIL import Image

from src.model_service import ModelInferenceError, ModelLoadError, ModelService


class FakeProcessor:
    def __init__(self):
        self.calls = []

    def __call__(self, image, return_tensors):
        self.calls.append((image, return_tensors))
        return {"pixel_values": torch.zeros((1, 3, 224, 224))}


class FakeModel:
    def __init__(self, logits, labels):
        self.config = SimpleNamespace(id2label=labels)
        self.logits = logits
        self.calls = 0

    def eval(self):
        return self

    def __call__(self, **inputs):
        self.calls += 1
        return SimpleNamespace(logits=self.logits)


def make_service(logits=None, labels=None):
    processor = FakeProcessor()
    model = FakeModel(
        logits if logits is not None else torch.tensor([[4.0, 1.0, 0.0]]),
        labels
        if labels is not None
        else {
            0: "Corn___Common_Rust",
            1: "Corn___Gray_Leaf_Spot",
            2: "Invalid",
        },
    )
    return (
        ModelService(model_id="test/model", processor=processor, model=model),
        processor,
        model,
    )


def test_prediction_has_decision_rules_compatible_shape():
    service, processor, model = make_service()

    result = service.predict(Image.new("RGBA", (100, 100)), top_k=2)

    assert result["label"] == "Corn___Common_Rust"
    assert result["crop"] == "corn"
    assert 0 <= result["model_score"] <= 1
    assert result["top3"][0]["label"] == "Corn___Common_Rust"
    assert len(result["top3"]) == 2
    assert result["model_id"] == "test/model"
    assert result["status"] == "candidate"
    assert processor.calls[0][0].mode == "RGB"
    assert model.calls == 1


def test_label_mapping_supports_string_class_indices():
    service, _, _ = make_service(
        logits=torch.tensor([[0.0, 3.0]]),
        labels={"0": "Invalid", "1": "Rice___Leaf_Blast"},
    )

    result = service.predict(Image.new("RGB", (100, 100)))

    assert result["label"] == "Rice___Leaf_Blast"
    assert result["crop"] == "rice"


def test_invalid_model_output_raises_inference_error():
    service, _, _ = make_service(logits=torch.tensor([[1.0]]), labels={})

    with pytest.raises(ModelInferenceError, match="no label"):
        service.predict(Image.new("RGB", (100, 100)))


def test_model_without_logits_raises_inference_error():
    processor = FakeProcessor()

    class NoLogitsModel:
        config = SimpleNamespace(id2label={0: "Invalid"})

        def eval(self):
            return self

        def __call__(self, **inputs):
            return SimpleNamespace()

    service = ModelService(
        model_id="test/model",
        processor=processor,
        model=NoLogitsModel(),
    )

    with pytest.raises(ModelInferenceError, match="no classification logits"):
        service.predict(Image.new("RGB", (100, 100)))


def test_inference_exception_is_reported():
    processor = FakeProcessor()

    class FailingModel(FakeModel):
        def __call__(self, **inputs):
            raise RuntimeError("fake inference failure")

    service = ModelService(
        model_id="test/model",
        processor=processor,
        model=FailingModel(torch.tensor([[1.0]]), {0: "Invalid"}),
    )

    with pytest.raises(ModelInferenceError, match="fake inference failure"):
        service.predict(Image.new("RGB", (100, 100)))


def test_model_and_processor_must_be_injected_together():
    with pytest.raises(ModelLoadError, match="provided together"):
        ModelService(processor=FakeProcessor())


def test_invalid_image_and_top_k_are_rejected():
    service, _, _ = make_service()

    with pytest.raises(ModelInferenceError, match="PIL image"):
        service.predict("not an image")
    with pytest.raises(ModelInferenceError, match="positive integer"):
        service.predict(Image.new("RGB", (100, 100)), top_k=0)
