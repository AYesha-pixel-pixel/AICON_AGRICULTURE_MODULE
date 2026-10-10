from __future__ import annotations

from copy import deepcopy
from typing import Any


_FIELD_VERIFICATION_NOTE = (
    "No disease-specific claim for this field has been verified in the "
    "project source registry. Local agricultural review is required."
)

_EXPERT_REVIEW_NOTE = (
    "Ask a local agricultural expert to verify the image and field conditions "
    "before taking disease-specific action."
)

_SOURCE_BY_LABEL = {
    "Wheat___Brown_Rust": ["SRC-005"],
    "Wheat___Yellow_Rust": ["SRC-005"],
}

_SUPPORTED_LABELS = {
    "Corn___Common_Rust": ("Common rust", "corn"),
    "Corn___Gray_Leaf_Spot": ("Gray leaf spot", "corn"),
    "Rice___Brown_Spot": ("Brown spot", "rice"),
    "Rice___Leaf_Blast": ("Leaf blast", "rice"),
    "Wheat___Brown_Rust": ("Brown rust", "wheat"),
    "Wheat___Yellow_Rust": ("Yellow rust", "wheat"),
}


def _field(items: list[str], source_ids: list[str]) -> dict[str, Any]:
    return {
        "items": list(items),
        "provenance_status": "local_verification_required",
        "sources": list(source_ids),
    }


def _entry(label: str, disease_name: str, crop: str) -> dict[str, Any]:
    source_ids = _SOURCE_BY_LABEL.get(label, [])
    return {
        "label": label,
        "disease_name": disease_name,
        "crop": crop,
        "evidence_status": "local_verification_required",
        "symptoms": _field([_FIELD_VERIFICATION_NOTE], source_ids),
        "possible_lookalikes": _field([_FIELD_VERIFICATION_NOTE], source_ids),
        "favourable_conditions": _field([_FIELD_VERIFICATION_NOTE], source_ids),
        "prevention": _field([_FIELD_VERIFICATION_NOTE], source_ids),
        "immediate_safe_actions": _field([_FIELD_VERIFICATION_NOTE], source_ids),
        "when_to_contact_expert": _field([_EXPERT_REVIEW_NOTE], source_ids),
        "evidence_note": (
            "The source registry currently verifies only institutional "
            "diagnostic/advisory context for these entries, not the "
            "disease-specific claims above."
        ),
    }


_KNOWLEDGE_BASE = {
    label: _entry(label, disease_name, crop)
    for label, (disease_name, crop) in _SUPPORTED_LABELS.items()
}


def get_disease_knowledge(label: Any) -> dict[str, Any] | None:
    """Return a defensive copy of structured evidence-aware disease knowledge."""
    if not isinstance(label, str):
        return None
    entry = _KNOWLEDGE_BASE.get(label)
    return deepcopy(entry) if entry is not None else None
