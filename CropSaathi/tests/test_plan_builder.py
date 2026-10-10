from src.plan_builder import build_plan


def prediction(
    label: str = "Corn___Common_Rust",
    crop: str = "corn",
    score: float = 0.9,
) -> dict[str, object]:
    return {"label": label, "crop": crop, "model_score": score}


def disease_guidance(
    provenance_status: str = "local_verification_required",
) -> dict[str, object]:
    return {
        "label": "Corn___Common_Rust",
        "disease_name": "Common rust",
        "crop": "corn",
        "prevention_and_crop_management": [
            "Source verification required before use."
        ],
        "when_to_seek_expert": "Seek local agricultural expert review.",
        "sources": [
            {
                "source_id": "SRC-TEST",
                "url": "https://example.invalid/source",
            }
        ],
        "provenance_status": provenance_status,
        "requires_source_verification": True,
    }


def healthy_guidance() -> dict[str, object]:
    return {
        "label": "Corn___Healthy",
        "crop": "corn",
        "healthy_result": True,
        "prevention_and_crop_management": [
            "No disease-specific advice is provided."
        ],
        "when_to_seek_expert": "Seek expert advice if concerns remain.",
        "sources": [],
    }


def test_approved_disease_plan_uses_only_returned_guidance():
    report = build_plan(
        prediction(),
        "corn",
        guidance=disease_guidance(),
    )

    assert report["status"] == "approved"
    assert report["selected_crop"] == "corn"
    assert report["prediction"] == {
        "label": "Corn___Common_Rust",
        "model_score": 0.9,
    }
    assert report["next_steps"] == [
        "Source verification required before use."
    ]
    assert report["sources"][0]["source_id"] == "SRC-TEST"
    assert report["provenance_status"] == "local_verification_required"


def test_healthy_plan_does_not_claim_disease_absence():
    report = build_plan(
        prediction("Corn___Healthy", "corn"),
        "corn",
        guidance=healthy_guidance(),
    )

    assert report["status"] == "healthy_result"
    assert "does not prove" in report["summary"]
    assert report["next_steps"] == ["No disease-specific advice is provided."]


def test_uncertain_prediction_has_no_disease_recommendations():
    report = build_plan(prediction(score=0.79), "corn")

    assert report["status"] == "uncertain"
    assert report["next_steps"]
    assert "disease-specific" in report["limitations"][-1]


def test_rejected_prediction_has_no_disease_recommendations():
    report = build_plan(prediction("Invalid", "corn", 0.99), "corn")

    assert report["status"] == "unsupported"
    assert report["next_steps"]
    assert report["sources"] == []


def test_crop_mismatch_has_no_disease_recommendations():
    report = build_plan(prediction(crop="rice"), "corn")

    assert report["status"] == "crop_mismatch"
    assert report["next_steps"]
    assert report["sources"] == []


def test_missing_prediction_is_reported_safely():
    report = build_plan(None, "corn")

    assert report["status"] == "unsupported"
    assert report["prediction"] is None
    assert report["summary"]
    assert report["next_steps"]


def test_missing_guidance_does_not_create_recommendations():
    report = build_plan(prediction(), "corn", guidance=None)

    assert report["status"] in {"approved", "guidance_unavailable"}
    if report["status"] == "approved":
        assert report["next_steps"] == [
            "Source verification required before this content is presented as established agricultural advice."
        ]
    else:
        assert report["next_steps"] == []


def test_provenance_status_is_not_upgraded():
    guidance = disease_guidance("general_reference_available")

    report = build_plan(prediction(), "corn", guidance=guidance)

    assert report["provenance_status"] == "general_reference_available"
