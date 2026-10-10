import pytest

from src.guidance import get_guidance


DISEASE_CASES = [
    ("Corn___Common_Rust", "corn"),
    ("Corn___Gray_Leaf_Spot", "corn"),
    ("Rice___Brown_Spot", "rice"),
    ("Rice___Leaf_Blast", "rice"),
    ("Wheat___Brown_Rust", "wheat"),
    ("Wheat___Yellow_Rust", "wheat"),
]


def prediction(label: str, crop: str, score: float = 0.9) -> dict[str, object]:
    return {"label": label, "crop": crop, "model_score": score}


@pytest.mark.parametrize(("label", "crop"), DISEASE_CASES)
def test_each_supported_disease_has_structured_guidance(label, crop):
    result = get_guidance(prediction(label, crop), crop)

    assert result is not None
    assert result["label"] == label
    assert result["crop"] == crop
    assert result["disease_name"]
    assert result["observable_symptoms"]
    assert result["prevention_and_crop_management"]
    assert result["when_to_seek_expert"]
    assert result["provenance_status"] == "local_verification_required"
    assert all(
        source["provenance_status"] == "local_verification_required"
        for source in result["sources"]
    )
    assert result["requires_source_verification"] is True


@pytest.mark.parametrize(
    ("label", "crop"),
    [
        ("Corn___Healthy", "corn"),
        ("Rice___Healthy", "rice"),
        ("Wheat___Healthy", "wheat"),
    ],
)
def test_healthy_result_is_not_presented_as_proof_of_no_disease(label, crop):
    result = get_guidance(prediction(label, crop), crop)

    assert result is not None
    assert result["healthy_result"] is True
    assert result["disease_name"] is None
    assert result["sources"] == []
    assert result["provenance_status"] == "not_applicable"
    assert "not proof" in result["when_to_seek_expert"]


@pytest.mark.parametrize(
    "prediction_data",
    [
        None,
        {},
        {"label": "Corn___Common_Rust"},
        {"label": "Corn___Common_Rust", "crop": "corn"},
        {"label": "Corn___Common_Rust", "crop": "corn", "model_score": "high"},
    ],
)
def test_missing_or_malformed_data_returns_no_guidance(prediction_data):
    assert get_guidance(prediction_data, "corn") is None


@pytest.mark.parametrize(
    ("prediction_data", "selected_crop"),
    [
        (prediction("Invalid", "corn", 0.99), "corn"),
        (prediction("Potato___Early_Blight", "potato", 0.99), "potato"),
        (prediction("Corn___Common_Rust", "rice", 0.99), "rice"),
        (prediction("Corn___Common_Rust", "corn", 0.79), "corn"),
        (prediction("Unknown___Disease", "corn", 0.99), "corn"),
    ],
)
def test_denied_decisions_never_return_disease_guidance(
    prediction_data,
    selected_crop,
):
    assert get_guidance(prediction_data, selected_crop) is None


def test_healthy_result_requires_matching_selected_crop():
    assert get_guidance(prediction("Corn___Healthy", "corn"), "rice") is None


def test_malformed_healthy_result_returns_no_guidance():
    assert get_guidance({"label": "Corn___Healthy", "crop": "corn"}, "corn") is None