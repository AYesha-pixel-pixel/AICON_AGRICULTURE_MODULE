from __future__ import annotations

import math
from typing import Any

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

from src.config import MODEL_ID


class ModelServiceError(RuntimeError):
    """Base error for model loading and inference failures."""


class ModelLoadError(ModelServiceError):
    """Raised when the configured model or processor cannot be loaded."""


class ModelInferenceError(ModelServiceError):
    """Raised when an image cannot be classified."""


def _label_for_index(id2label: Any, index: int) -> str:
    if not isinstance(id2label, dict):
        raise ModelInferenceError("The loaded model has no valid label mapping.")

    label = id2label.get(index, id2label.get(str(index)))
    if not isinstance(label, str) or not label.strip():
        raise ModelInferenceError(
            f"The loaded model has no label for output class {index}."
        )
    return label


def _crop_for_label(label: str) -> str | None:
    if label == "Invalid":
        return None
    parts = label.split("___", 1)
    if len(parts) != 2 or not parts[0]:
        return None
    return parts[0].lower()


class ModelService:
    """Reusable image-classification service for the configured candidate model.

    Loading is performed once when the service is constructed. Calls to
    :meth:`predict` reuse the loaded processor and model.
    """

    def __init__(
        self,
        model_id: str = MODEL_ID,
        *,
        processor: Any | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_id = model_id
        if (processor is None) != (model is None):
            raise ModelLoadError(
                "A processor and model must be provided together for injection."
            )

        if processor is not None and model is not None:
            self.processor = processor
            self.model = model
            return

        try:
            self.processor = AutoImageProcessor.from_pretrained(model_id)
            self.model = AutoModelForImageClassification.from_pretrained(model_id)
            self.model.eval()
        except Exception as error:
            raise ModelLoadError(
                f"Could not load model '{model_id}': {error}"
            ) from error

    def predict(self, image: Image.Image, top_k: int = 3) -> dict[str, Any]:
        """Return the candidate model's ranked prediction for a validated image."""
        if not isinstance(image, Image.Image):
            raise ModelInferenceError("Prediction requires a PIL image.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ModelInferenceError("top_k must be a positive integer.")

        try:
            inputs = self.processor(image.convert("RGB"), return_tensors="pt")
            with torch.no_grad():
                outputs = self.model(**inputs)
            logits = getattr(outputs, "logits", None)
            if logits is None:
                raise ModelInferenceError("The model returned no classification logits.")

            logits = torch.as_tensor(logits)
            if logits.ndim != 2 or logits.shape[0] != 1 or logits.shape[1] < 1:
                raise ModelInferenceError(
                    "The model returned malformed classification logits."
                )

            scores = torch.softmax(logits[0], dim=0)
            limit = min(top_k, scores.shape[0])
            values, indices = torch.topk(scores, k=limit)
            id2label = getattr(getattr(self.model, "config", None), "id2label", None)

            top_predictions = []
            for value, index in zip(values.tolist(), indices.tolist()):
                score = float(value)
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise ModelInferenceError(
                        "The model returned an invalid confidence score."
                    )
                label = _label_for_index(id2label, int(index))
                top_predictions.append({"label": label, "score": score})

            best = top_predictions[0]
            return {
                "label": best["label"],
                "crop": _crop_for_label(best["label"]),
                "model_score": best["score"],
                "top3": top_predictions,
                "model_id": self.model_id,
                "status": "candidate",
            }
        except ModelServiceError:
            raise
        except Exception as error:
            raise ModelInferenceError(
                f"Model inference failed for '{self.model_id}': {error}"
            ) from error


def load_model(model_id: str = MODEL_ID) -> ModelService:
    """Load and return one reusable service for the configured model."""
    return ModelService(model_id=model_id)