from __future__ import annotations

import math
from typing import Any

from src.decision_rules import decide
from src.guidance import get_guidance


_DISCLAIMER = (
    "Possible issue — not a confirmed diagnosis. Model predictions can be "
    "wrong; consult a local agriculture extension officer or qualified "
    "agronomist before consequential decisions."
)


def _normalise_crop(selected_crop: Any) -> str | None:
    if not isinstance(selected_crop, str):
        return None
    crop = selected_crop.strip().lower()
    return crop or None


def _prediction_details(prediction: Any) -> dict[str, Any] | None:
    if not isinstance(prediction, dict):
        return None

    label = prediction.get("label")
    score = prediction.get("model_score")
    if (
        not isinstance(label, str)
        or not label.strip()
        or isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0 <= score <= 1
    ):
        return None
    return {"label": label, "model_score": float(score)}


def _base_report(
    prediction: Any,
    selected_crop: Any,
) -> dict[str, Any]:
    return {
        "status": "rejected",
        "selected_crop": _normalise_crop(selected_crop),
        "prediction": _prediction_details(prediction),
        "summary": "",
        "next_steps": [],
        "sources": [],
        "warnings": [_DISCLAIMER],
        "limitations": [
            "This report is decision support, not a confirmed diagnosis.",
        ],
    }


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def build_plan(
    prediction: Any,
    selected_crop: Any,
    guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, render-ready Aaj ka Plan report.

    The decision and default guidance are obtained from the existing
    ``decide`` and ``get_guidance`` interfaces. An optional ``guidance`` value
    is provided for callers that already performed the lookup or for offline
    tests; it is copied into the report without upgrading its provenance.
    """
    report = _base_report(prediction, selected_crop)
    decision = decide(prediction, selected_crop)
    supplied_guidance = guidance if guidance is not None else get_guidance(
        prediction,
        selected_crop,
    )

    if isinstance(supplied_guidance, dict) and supplied_guidance.get(
        "healthy_result"
    ) is True:
        report["status"] = "healthy_result"
        report["summary"] = (
            "The model result is consistent with a healthy result for the "
            "selected crop, but this does not prove that the plant is "
            "disease-free."
        )
        report["next_steps"] = _safe_list(
            supplied_guidance.get("prevention_and_crop_management")
        )
        report["sources"] = _safe_list(supplied_guidance.get("sources"))
        report["warnings"].append(
            supplied_guidance.get("when_to_seek_expert", "")
        )
        report["limitations"].append(
            "The model result may be wrong or may not reflect all field conditions."
        )
        return report

    if decision.get("decision") == "usable" and decision.get("show_guidance"):
        if not isinstance(supplied_guidance, dict):
            report["status"] = "guidance_unavailable"
            report["summary"] = (
                "The model produced a possible issue, but no reviewed guidance "
                "entry is available."
            )
            report["warnings"].append(
                "No disease-specific recommendations are available."
            )
            return report

        report["status"] = "approved"
        report["summary"] = (
            f"Possible issue: {supplied_guidance.get('disease_name', prediction.get('label'))}. "
            "This is not a confirmed diagnosis."
        )
        report["next_steps"] = _safe_list(
            supplied_guidance.get("prevention_and_crop_management")
        )
        report["sources"] = _safe_list(supplied_guidance.get("sources"))
        provenance_status = supplied_guidance.get("provenance_status")
        if provenance_status is not None:
            report["provenance_status"] = provenance_status
        if supplied_guidance.get("requires_source_verification") is True:
            report["warnings"].append(
                "Agricultural guidance still requires source and local expert verification."
            )
        report["warnings"].append(
            supplied_guidance.get("when_to_seek_expert", "")
        )
        return report

    decision_name = decision.get("decision", "unsupported")
    report["status"] = decision_name
    report["summary"] = decision.get(
        "reason",
        "No disease-specific plan can be generated from this result.",
    )
    report["next_steps"] = [
        "Do not make disease-specific treatment decisions from this result.",
        "Verify the image and prediction with a local agriculture expert if concerns remain.",
    ]
    report["limitations"].append(
        "No disease-specific recommendations are provided for this result."
    )
    return report
