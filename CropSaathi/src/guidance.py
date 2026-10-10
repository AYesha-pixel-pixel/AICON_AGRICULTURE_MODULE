from __future__ import annotations

import math
from typing import Any

from src.decision_rules import decide


_SOURCE_VERIFICATION_NOTE = (
    "Source verification required before this content is presented as "
    "established agricultural advice."
)

_DISEASE_GUIDANCE: dict[str, dict[str, Any]] = {
    "Corn___Common_Rust": {
        "label": "Corn___Common_Rust",
        "disease_name": "Common rust",
        "crop": "corn",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
    "Corn___Gray_Leaf_Spot": {
        "label": "Corn___Gray_Leaf_Spot",
        "disease_name": "Gray leaf spot",
        "crop": "corn",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
    "Rice___Brown_Spot": {
        "label": "Rice___Brown_Spot",
        "disease_name": "Brown spot",
        "crop": "rice",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
    "Rice___Leaf_Blast": {
        "label": "Rice___Leaf_Blast",
        "disease_name": "Leaf blast",
        "crop": "rice",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
    "Wheat___Brown_Rust": {
        "label": "Wheat___Brown_Rust",
        "disease_name": "Brown rust",
        "crop": "wheat",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
    "Wheat___Yellow_Rust": {
        "label": "Wheat___Yellow_Rust",
        "disease_name": "Yellow rust",
        "crop": "wheat",
        "observable_symptoms": [_SOURCE_VERIFICATION_NOTE],
        "prevention_and_crop_management": [_SOURCE_VERIFICATION_NOTE],
        "when_to_seek_expert": (
            "Seek a local agricultural expert to verify the possible issue "
            "before making treatment decisions."
        ),
        "sources": [],
        "requires_source_verification": True,
    },
}

_HEALTHY_LABELS = {
    "corn": "Corn___Healthy",
    "rice": "Rice___Healthy",
    "wheat": "Wheat___Healthy",
}


def _healthy_response(label: str, crop: str) -> dict[str, Any]:
    return {
        "label": label,
        "disease_name": None,
        "crop": crop,
        "observable_symptoms": [],
        "prevention_and_crop_management": [
            "No disease-specific advice is provided from a healthy model result."
        ],
        "when_to_seek_expert": (
            "A healthy model result is not proof that the plant is disease-free. "
            "Seek local agricultural advice if symptoms or concerns remain."
        ),
        "sources": [],
        "requires_source_verification": False,
        "healthy_result": True,
    }


def _has_valid_score(prediction: dict[str, Any]) -> bool:
    score = prediction.get("model_score")
    return (
        not isinstance(score, bool)
        and isinstance(score, (int, float))
        and math.isfinite(score)
        and 0 <= score <= 1
    )


def get_guidance(
    prediction: Any,
    selected_crop: Any,
) -> dict[str, Any] | None:
    """Return reviewed-status guidance only for an approved model decision.

    Disease entries are deliberately withheld unless ``decide`` approves the
    prediction. The current repository has no verified agricultural sources,
    so disease entries remain marked for source verification.
    """
    if not isinstance(prediction, dict):
        return None
    if not isinstance(selected_crop, str):
        return None

    decision = decide(prediction, selected_crop)
    label = prediction.get("label")
    crop = selected_crop.strip().lower()

    if label in _HEALTHY_LABELS.values():
        if _HEALTHY_LABELS.get(crop) != label:
            return None
        if (
            not _has_valid_score(prediction)
            or not decision
            or not isinstance(decision.get("show_guidance"), bool)
        ):
            return None
        return _healthy_response(label, crop)

    if not decision.get("show_guidance"):
        return None
    if label not in _DISEASE_GUIDANCE:
        return None
    if _DISEASE_GUIDANCE[label]["crop"] != crop:
        return None

    return dict(_DISEASE_GUIDANCE[label])