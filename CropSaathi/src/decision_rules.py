from __future__ import annotations

import math
from typing import Any

from src.config import SUPPORTED_CROPS, UNCERTAIN_THRESHOLD, USABLE_THRESHOLD


_SUPPORTED_DISEASE_LABELS = {
    "Corn___Common_Rust",
    "Corn___Gray_Leaf_Spot",
    "Rice___Brown_Spot",
    "Rice___Leaf_Blast",
    "Wheat___Brown_Rust",
    "Wheat___Yellow_Rust",
}


def _result(decision: str, reason: str) -> dict[str, Any]:
    return {
        "decision": decision,
        "reason": reason,
        "show_guidance": decision == "usable",
    }


def _normalise_crop(crop: Any) -> str | None:
    if not isinstance(crop, str):
        return None
    normalised = crop.strip().lower()
    return normalised if normalised in SUPPORTED_CROPS else None


def decide(prediction: Any, selected_crop: Any) -> dict[str, Any]:
    selected = _normalise_crop(selected_crop)
    if selected is None:
        return _result(
            "unsupported",
            "The selected crop is not supported.",
        )

    if not isinstance(prediction, dict):
        return _result(
            "unsupported",
            "The prediction is missing or has an invalid structure.",
        )

    label = prediction.get("label")
    predicted_crop = _normalise_crop(prediction.get("crop"))
    score = prediction.get("model_score")

    if not isinstance(label, str) or not label.strip():
        return _result(
            "unsupported",
            "The prediction does not contain a valid label.",
        )
    if label == "Invalid":
        return _result(
            "unsupported",
            "The model marked this image as invalid, so no disease guidance is shown.",
        )
    if label not in _SUPPORTED_DISEASE_LABELS:
        return _result(
            "unsupported",
            "The predicted label is not supported for disease guidance.",
        )
    if predicted_crop is None:
        return _result(
            "unsupported",
            "The prediction does not contain a supported crop.",
        )
    if predicted_crop != selected:
        return _result(
            "crop_mismatch",
            "The predicted crop does not match the selected crop.",
        )
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return _result(
            "unsupported",
            "The prediction score is missing or invalid.",
        )
    if not math.isfinite(score) or not 0 <= score <= 1:
        return _result(
            "unsupported",
            "The prediction score must be a finite value from 0 to 1.",
        )

    if score >= USABLE_THRESHOLD:
        return _result(
            "usable",
            "The prediction meets the configured threshold for a possible issue.",
        )
    if score >= UNCERTAIN_THRESHOLD:
        return _result(
            "uncertain",
            "The prediction is in the configured uncertain confidence range.",
        )
    return _result(
        "uncertain",
        "The prediction is below the configured minimum confidence for disease guidance.",
    )