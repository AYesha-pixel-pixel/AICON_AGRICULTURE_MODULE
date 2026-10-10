from __future__ import annotations

from typing import Any

import streamlit as st

from src.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, MODEL_ID, SUPPORTED_CROPS
from src.decision_rules import decide
from src.guidance import get_guidance
from src.image_validation import validate_image
from src.model_service import ModelLoadError, ModelServiceError, load_model
from src.plan_builder import build_plan


@st.cache_resource(show_spinner=False)
def get_model_service():
    """Load the candidate model once per Streamlit process/session cache."""
    return load_model()


def _display_sources(sources: Any) -> None:
    if not isinstance(sources, list) or not sources:
        return

    st.subheader("Sources")
    for source in sources:
        if not isinstance(source, dict):
            continue
        title = source.get("title") or source.get("source_id") or "Source"
        organization = source.get("organization")
        provenance_status = source.get("provenance_status")
        url = source.get("url")
        details = [str(title)]
        if isinstance(organization, str) and organization:
            details.append(organization)
        if isinstance(provenance_status, str) and provenance_status:
            details.append(f"provenance: `{provenance_status}`")
        if isinstance(url, str) and url:
            st.markdown(f"- [{details[0]}]({url}) — {'; '.join(details[1:])}")
        else:
            st.markdown(f"- {'; '.join(details)}")


def _display_knowledge(knowledge: Any) -> None:
    if not isinstance(knowledge, dict):
        return

    st.subheader("Evidence-aware agricultural information")
    evidence_status = knowledge.get("evidence_status")
    if isinstance(evidence_status, str):
        st.caption(f"Overall evidence status: `{evidence_status}`")
    evidence_note = knowledge.get("evidence_note")
    if isinstance(evidence_note, str) and evidence_note:
        st.info(evidence_note)

    field_titles = {
        "symptoms": "Symptoms",
        "possible_lookalikes": "Possible Lookalikes",
        "favourable_conditions": "Favourable Conditions",
        "prevention": "Prevention",
        "immediate_safe_actions": "Immediate Safe Actions",
        "when_to_contact_expert": "When to Contact an Agricultural Expert",
    }
    for field_name, title in field_titles.items():
        field = knowledge.get(field_name)
        if not isinstance(field, dict):
            continue
        items = field.get("items")
        if not isinstance(items, list) or not items:
            continue
        st.markdown(f"**{title}**")
        for item in items:
            if isinstance(item, str) and item:
                st.write(f"- {item}")
        status = field.get("provenance_status")
        if isinstance(status, str):
            st.caption(f"Field evidence status: `{status}`")


def _display_report(
    report: dict[str, Any],
    prediction: dict[str, Any],
) -> None:
    status = report.get("status", "unknown")
    status_labels = {
        "approved": ("Supported disease prediction", st.warning),
        "healthy_result": ("Healthy model result", st.success),
        "uncertain": ("Uncertain prediction", st.warning),
        "crop_mismatch": ("Crop mismatch", st.warning),
        "unsupported": ("Unsupported result", st.warning),
        "guidance_unavailable": ("Guidance unavailable", st.warning),
        "rejected": ("Analysis unavailable", st.error),
    }
    status_text, status_renderer = status_labels.get(
        status,
        ("Analysis result", st.info),
    )
    status_renderer(status_text)

    report_prediction = report.get("prediction")
    label = (
        report_prediction.get("label")
        if isinstance(report_prediction, dict)
        else prediction.get("label")
    )
    score = (
        report_prediction.get("model_score")
        if isinstance(report_prediction, dict)
        else prediction.get("model_score")
    )
    selected_crop = report.get("selected_crop")
    dashboard_columns = st.columns(3)
    with dashboard_columns[0]:
        st.metric("Selected crop", str(selected_crop).title())
    with dashboard_columns[1]:
        st.metric("Decision status", status_text)
    with dashboard_columns[2]:
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            st.metric("Model score", f"{score:.4f}")
        else:
            st.metric("Model score", "Unavailable")
    if isinstance(label, str) and label:
        st.write(f"**Predicted label:** `{label}`")
    st.caption(
        "The model score is a raw model score, not a calibrated probability "
        "or a confirmed field diagnosis."
    )

    summary = report.get("summary")
    if isinstance(summary, str) and summary:
        st.subheader("Summary")
        st.write(summary)

    next_steps = report.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        st.subheader("Recommended Next Steps")
        for step in next_steps:
            if isinstance(step, str) and step:
                st.write(f"- {step}")

    warnings = report.get("warnings")
    if isinstance(warnings, list) and any(
        isinstance(warning, str) and warning for warning in warnings
    ):
        st.subheader("Warnings")
        for warning in warnings:
            if isinstance(warning, str) and warning:
                st.warning(warning)

    provenance_status = report.get("provenance_status")
    if isinstance(provenance_status, str):
        st.caption(f"Guidance provenance: `{provenance_status}`")

    _display_sources(report.get("sources"))
    _display_knowledge(report.get("knowledge"))

    limitations = report.get("limitations")
    if isinstance(limitations, list) and limitations:
        with st.expander("Limitations"):
            for limitation in limitations:
                if isinstance(limitation, str) and limitation:
                    st.write(f"- {limitation}")

    top_predictions = prediction.get("top3")
    with st.expander("Technical details"):
        model_label = prediction.get("label")
        model_id = prediction.get("model_id")
        if isinstance(model_label, str) and model_label:
            st.write(f"**Model label:** `{model_label}`")
        if isinstance(model_id, str) and model_id:
            st.write(f"**Model ID:** `{model_id}`")
        if isinstance(top_predictions, list) and top_predictions:
            st.write("**Top predictions:**")
            for candidate in top_predictions:
                if not isinstance(candidate, dict):
                    continue
                candidate_label = candidate.get("label")
                candidate_score = candidate.get("score")
                if (
                    isinstance(candidate_label, str)
                    and isinstance(candidate_score, (int, float))
                    and not isinstance(candidate_score, bool)
                ):
                    st.write(f"- `{candidate_label}` — raw score `{candidate_score:.4f}`")


def main() -> None:
    st.set_page_config(
        page_title="CropSaathi",
        page_icon="🌾",
        layout="centered",
    )
    st.title("CropSaathi")
    st.write("Agricultural image decision support for a possible crop issue.")
    st.caption(
        "Preliminary image-based prediction only — not a confirmed field "
        "diagnosis or a replacement for local agricultural expertise."
    )

    selected_crop = st.selectbox(
        "Select the crop shown in the image",
        options=SUPPORTED_CROPS,
        format_func=str.title,
    )
    allowed_types = sorted(ALLOWED_EXTENSIONS)
    uploaded_file = st.file_uploader(
        f"Upload a crop image ({', '.join(allowed_types)}; up to {MAX_UPLOAD_MB} MB)",
        type=allowed_types,
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded image", use_container_width=True)

    if not st.button("Analyze", type="primary"):
        return
    if uploaded_file is None:
        st.error("Please upload an image before selecting Analyze.")
        return

    validation = validate_image(uploaded_file)
    if not validation["ok"]:
        st.error(validation["reason"])
        return

    image = validation["image"]
    if image is None:
        st.error("The image could not be prepared for analysis.")
        return

    try:
        with st.spinner(f"Loading {MODEL_ID} and analyzing the image..."):
            service = get_model_service()
            prediction = service.predict(image)
    except ModelLoadError as error:
        st.error(
            "The candidate model could not be loaded. Check that its weights "
            f"are available and try again. Details: {error}"
        )
        return
    except ModelServiceError as error:
        st.error(f"The image analysis failed safely. Details: {error}")
        return

    decision = decide(prediction, selected_crop)
    guidance = get_guidance(prediction, selected_crop)
    report = build_plan(prediction, selected_crop, guidance=guidance)
    report["decision"] = decision
    _display_report(report, prediction)


if __name__ == "__main__":
    main()
