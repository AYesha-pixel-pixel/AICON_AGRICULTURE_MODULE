from src.config import UNCERTAIN_THRESHOLD, USABLE_THRESHOLD
from src.decision_rules import decide


def prediction(
    label: str = "Corn___Common_Rust",
    crop: str = "corn",
    score: float = USABLE_THRESHOLD,
) -> dict[str, object]:
    return {"label": label, "crop": crop, "model_score": score}


def test_high_confidence_prediction_for_selected_crop_is_usable():
    result = decide(prediction(), "corn")

    assert result == {
        "decision": "usable",
        "reason": "The prediction meets the configured threshold for a possible issue.",
        "show_guidance": True,
    }


def test_score_at_usable_boundary_is_usable():
    result = decide(prediction(score=USABLE_THRESHOLD), "corn")

    assert result["decision"] == "usable"
    assert result["show_guidance"] is True


def test_score_just_below_usable_boundary_is_uncertain():
    result = decide(prediction(score=USABLE_THRESHOLD - 0.01), "corn")

    assert result["decision"] == "uncertain"
    assert result["show_guidance"] is False


def test_score_at_uncertain_boundary_is_uncertain():
    result = decide(prediction(score=UNCERTAIN_THRESHOLD), "corn")

    assert result["decision"] == "uncertain"
    assert result["show_guidance"] is False


def test_score_below_uncertain_boundary_cannot_show_guidance():
    result = decide(prediction(score=UNCERTAIN_THRESHOLD - 0.01), "corn")

    assert result["decision"] == "uncertain"
    assert "below" in result["reason"]
    assert result["show_guidance"] is False


def test_invalid_class_is_not_treated_as_a_disease():
    result = decide(prediction(label="Invalid", score=0.99), "corn")

    assert result["decision"] == "unsupported"
    assert result["show_guidance"] is False


def test_unsupported_label_is_rejected():
    result = decide(prediction(label="Potato___Early_Blight"), "corn")

    assert result["decision"] == "unsupported"
    assert result["show_guidance"] is False


def test_unsupported_selected_crop_is_rejected():
    result = decide(prediction(), "potato")

    assert result["decision"] == "unsupported"
    assert result["show_guidance"] is False


def test_crop_mismatch_does_not_show_guidance():
    result = decide(prediction(crop="rice"), "corn")

    assert result["decision"] == "crop_mismatch"
    assert result["show_guidance"] is False


def test_missing_prediction_is_rejected():
    result = decide(None, "corn")

    assert result["decision"] == "unsupported"
    assert result["show_guidance"] is False


def test_missing_prediction_fields_are_rejected():
    result = decide({"label": "Corn___Common_Rust"}, "corn")

    assert result["decision"] == "unsupported"
    assert result["show_guidance"] is False


def test_invalid_confidence_values_are_rejected():
    for score in (None, "0.9", float("nan"), float("inf"), -0.1, 1.1, True):
        result = decide(prediction(score=score), "corn")

        assert result["decision"] == "unsupported"
        assert result["show_guidance"] is False