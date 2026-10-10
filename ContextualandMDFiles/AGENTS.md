# CropSaathi — Project Instructions for Codex

> Keep this file at the repository root as `AGENTS.md`. Read it before changing code. It is the single source of truth for product scope and implementation priorities.

## 1. Product mission

Build **CropSaathi**, a Pakistan-focused crop-health decision-support MVP for the AICON'26 Build With AI hackathon.

**Core flow:** crop photo → real pretrained-model inference → uncertainty and safety checks → Pakistan-relevant, source-backed next step → optional weather context.

Help a farmer investigate a *possible* crop-health issue. Do not present a model output as a confirmed diagnosis or replace an agricultural extension officer.

## 2. Scope lock

### P0 — must work before visual polish
1. Upload and preview a leaf image.
2. Validate file type, size, and image readability.
3. Load one verified pretrained model and run actual inference.
4. Apply the model's exact documented preprocessing and correct class-label mapping.
5. Show predicted class and call the score a **model score**, not a calibrated probability.
6. Handle unsupported labels, selected-crop mismatch, weak/uncertain outputs, invalid images, and inference failures.
7. Map supported results to a small, reviewed Pakistan-relevant guidance file.
8. Show a clear next step: **Retake photo / Monitor and recheck / Consult local agricultural expert**.
9. Include source/provenance, limitations, setup instructions, and a reliable demo sample in the README.
10. Test the entire path from upload to action card.

### P1 — only after P0 passes
- Weather context for a user-selected Pakistani district using Open-Meteo. Weather must be shown separately; do not claim it predicts disease without a validated method.
- Session-only report history.
- Urdu/Roman Urdu presentation, if time permits.

### Out of scope for the four-hour MVP
- Marketplace, payments, user accounts, complex database, yield prediction, irrigation recommendations, training a model from scratch, voice assistant, or live market-price claims.
- Do not add a generic chatbot. Do not recommend pesticide brands or doses.
- Do not add a separate frontend/backend framework unless the existing repository requires it and there is time to test it.

**Priority rule:** a working end-to-end AI flow beats a large feature list or a polished but nonfunctional UI.

## 3. Stack and framework rule

- Inspect the repository before changing anything.
- If a working framework already exists, keep it unless a specific technical blocker justifies a change.
- For a new four-hour Python-first build, prefer **Python + Streamlit + Pillow + the selected model's required runtime** for the lowest integration overhead.
- Use Git for version control.
- Add dependencies only when required by the selected model or a working feature.
- Do not silently migrate to React, add FastAPI, Docker, authentication, or a database.

## 4. Model choice and verification

Model candidates to investigate, not blindly trust:

- Multi-crop ViT: https://huggingface.co/wambugu71/crop_leaf_diseases_vit
- Cotton DenseNet-121: https://huggingface.co/FarmGuard/cotton-densenet121
- Dataset reference only if needed for permitted testing: https://github.com/spMohanty/PlantVillage-Dataset

Choose **one crop and one model** first. Do not assume a model supports every crop. Prefer wheat only if the chosen model's wheat classes and inference work are verified; otherwise choose a crop the model reliably supports and explain the choice.

Before integration:
1. Inspect the current model card, files, inference example, intended use, and actual LICENSE file.
2. Confirm runtime/framework, input dimensions, RGB/BGR expectation, resizing, normalization, output shape, and label order.
3. Install and run a minimal inference test on the target machine.
4. Test a few lawful sample images and inspect whether predictions are plausible.
5. Record the exact model ID, URL, license, labels, runtime, and limitations in `README.md` and `DISCLOSURES.md`.

If model loading fails, diagnose the actual error before switching models. Never silently replace the model or fake its output. Do not download a full training dataset merely to use a pretrained model.

## 5. Prediction, uncertainty, and safety

- Treat model outputs as candidate classifications, not confirmed diagnoses.
- A maximum softmax value is not automatically a calibrated probability of correctness.
- Do not claim field accuracy from controlled-dataset accuracy.
- Do not invent or reorder class labels. If mapping cannot be verified, stop and fix it.
- Do not filter scores to the selected crop in a way that forces a crop-specific answer. Detect mismatch and return an uncertainty state.
- Use a conservative configurable threshold only as an engineering fallback, not as a scientifically validated threshold unless evaluated.
- On unclear images, unsupported class, crop mismatch, weak output, or errors, explain the limitation and request another clear image or local expert help.
- Advice must be vendor-neutral, conservative, locally relevant, and backed by a reviewed source. Do not produce pesticide dosages or brand recommendations.
- Keep weather contextual. Do not infer disease risk from weather unless a validated crop-specific rule is implemented and sourced.

## 6. Architecture and code quality

Keep the first version small and modular. Suggested structure (adapt to the repository rather than forcing a restructure):

```text
CropSaathi/
  AGENTS.md
  README.md
  DISCLOSURES.md
  requirements.txt
  app.py
  src/
    model_service.py
    image_validation.py
    decision_rules.py
    guidance.py
  data/
    guidance.json
  tests/
    test_decision_rules.py
  samples/
    README.md
```

- `model_service.py`: model loading, preprocessing, inference, label mapping. Load the model once, not on every UI rerun.
- `image_validation.py`: safe image opening, format/size checks, readable errors.
- `decision_rules.py`: deterministic uncertainty, supported-class, and crop-mismatch handling.
- `guidance.py`: retrieve reviewed guidance from `data/guidance.json`; never let free-form model text invent treatment advice.
- `app.py`: UI and orchestration only; keep model and decision logic testable outside the UI.
- Keep functions small, names clear, and errors actionable. Add type hints where useful.
- Use relative paths rooted at the project directory, not fragile current-working-directory assumptions.
- Keep secrets in `.env`; commit `.env.example` only. Do not commit `.env`, virtual environments, model caches, large private uploads, or `__pycache__`.
- Do not fabricate sample inference results. Any mock mode must be explicitly labelled and separate from the real inference path.

## 7. Tests and completion criteria

Before declaring the MVP functional, verify:
- App starts from documented commands.
- Model loads once and a supported sample image runs through real inference.
- Label mapping matches the model source.
- Valid image upload and preview work.
- Invalid file, oversized file, unreadable image, model error, unsupported label, low score, and crop mismatch produce safe messages instead of crashes.
- Guidance is only shown for a supported mapped class and includes its source.
- The UI clearly distinguishes model output from verified guidance.
- No button or control falsely claims an action succeeded.
- README includes setup, model download/loading instructions, supported labels, tests, limitations, and demo steps.

Use a small test set only when its source and labels are known. Report exact sample counts and results; do not describe a tiny demo check as a representative field evaluation.

## 8. Build order

1. Inspect files, Python version, framework, hardware, and Git status. Do not overwrite existing work.
2. Verify model licence, runtime, labels, and inference with a minimal script.
3. Implement image validation and the model service.
4. Implement deterministic decision rules and source-backed guidance.
5. Test the end-to-end backend/core flow with a few sample images.
6. Connect the simplest usable UI.
7. Add design tokens and apply `DESIGN.md` only after the real flow works.
8. Add optional weather only after core tests pass.
9. Freeze features, test the demo path, update README and disclosures, rehearse the five-minute presentation.

After each stage, run the relevant tests and report: files changed, command run, result, known issues, and the next smallest step. Do not claim a test passed unless it was actually run.

## 9. Design file relationship

`DESIGN.md` is a visual reference, not permission to build every described feature. Preserve its botanical/editorial visual direction and accessibility guidance, but implement only the screens and interactions required by the P0 flow. Avoid parallax and elaborate animation until the core product is stable. If the app is Streamlit, do not pretend React Motion is integrated; use native controls and restrained CSS where appropriate.

## 10. Hackathon integrity

Use permitted public models, datasets, libraries, and APIs. Check licences and attribute sources. Disclose external models, datasets, APIs, and significant pre-existing code. Do not fabricate accuracy, impact, sources, or team contributions. Follow the official event rulebook and organizer announcements if they supersede this file.

## Final rule

**One crop, one verified model, one real inference path, one safe action card. Build that first.**
