# CropSaathi — Project Agent Instructions

**Status:** Canonical project guidance for AI coding agents  
**Project:** CropSaathi, an agricultural AI decision-support MVP for AICON'26  
**Primary users:** Farmers and agricultural learners/advisers in Pakistan  
**Current product form:** Python + Streamlit application  
**Last refined:** 10 October 2026

This file is the project-specific source of truth for coding-agent behavior inside `CropSaathi/`. If a higher-priority system or repository instruction conflicts with this file, follow the higher-priority instruction. Where the repository's current implementation differs from this document, inspect the implementation and report the discrepancy before changing it.

---

## 1. Mission and product boundaries

CropSaathi helps a user inspect a crop-leaf image, understand a model's *possible* prediction, and see cautious, source-backed next steps.

The intended end-to-end flow is:

`Uploaded image → image validation → pretrained model prediction → decision rules → reviewed guidance → “Aaj ka Plan”`

The AI model is a core part of the product, not a decorative feature. The product is a decision-support prototype, **not** a diagnostic authority, a replacement for an agricultural extension officer, or a guarantee of crop outcome.

### Required user-facing language

- Present outputs as **“Possible issue — not a confirmed diagnosis.”**
- Explain that image-model predictions can be wrong and that lighting, image quality, crop variety, growth stage, and field conditions can affect results.
- Include a clear recommendation to consult a local agriculture extension officer or qualified agronomist, especially before consequential treatment decisions.
- Never describe the model score as a calibrated probability unless calibration has been measured and documented.
- Do not claim improved yield, reduced losses, clinical/field-grade accuracy, or other impact without a defined metric and evidence.

### Scope for the MVP

Prioritize one reliable vertical slice: validate an image, run the existing candidate model, apply transparent decision rules, retrieve reviewed guidance, and display a concise plan.

Do not add unrelated crop forecasting, irrigation scheduling, chatbots, market prices, supply-chain features, accounts, databases, or complex infrastructure unless the team explicitly approves the scope change.

---

## 2. Read project context before editing

Before making changes, inspect the relevant existing files rather than assuming this document describes the implementation perfectly. At minimum, review:

- `ContextualandMDFiles/AGENTS_1.md` as a general hackathon reference, while recognizing that this file is a project-specific override for the stack and structure.
- The CropSaathi roadmap supplied by the team.
- `README.md`, `DISCLOSURES.md`, `requirements.txt`, and `.gitignore`.
- `test_model.py` and `test_model_dynamic.py`.
- All existing modules in `src/`, JSON files in `data/`, tests in `tests/`, and documents in `docs/`.
- Current Git branch, working tree, and recent changes before any Git operation.

If a referenced file is absent, say so. Do not silently invent its contents or claim to have inspected it.

---

## 3. Stack and dependency policy

Use the current project stack unless the team explicitly approves a change:

- Python 3.x
- Streamlit for the interface
- PyTorch and Transformers for the candidate image model
- Pillow for image handling
- pytest for automated tests
- Standard-library modules where practical

Avoid adding React, Node.js, a separate web backend, a database, an LLM API, cloud infrastructure, or another model framework for this MVP unless specifically approved.

Before adding a dependency:
1. Explain why it is needed.
2. Check whether the existing stack can do the job.
3. Ask the team for approval when the addition is not clearly necessary or was not requested.
4. Update `requirements.txt` only for dependencies the project actually uses, with compatible versions or reasonable constraints.

Do not install packages, download model weights, or make network calls during a task that asks for a read-only audit or pure unit tests.

---

## 4. Existing model and label contract

The current candidate model recorded by the team is:

`wambugu71/crop_leaf_diseases_vit`

The reported model label map is:

| Index | Model label |
|---:|---|
| 0 | `Corn___Common_Rust` |
| 1 | `Corn___Gray_Leaf_Spot` |
| 2 | `Corn___Healthy` |
| 3 | `Invalid` |
| 4 | `Potato___Early_Blight` |
| 5 | `Potato___Healthy` |
| 6 | `Potato___Late_Blight` |
| 7 | `Rice___Brown_Spot` |
| 8 | `Rice___Healthy` |
| 9 | `Rice___Leaf_Blast` |
| 10 | `Wheat___Brown_Rust` |
| 11 | `Wheat___Healthy` |
| 12 | `Wheat___Yellow_Rust` |

Treat this as the **reported candidate label map**, not independent verification of the model artifact. Inspect the actual loaded model configuration, preprocessing, output order, model card, and license before relying on it or distributing the model. If any source disagrees with this table, do not silently force the table onto the model; report the discrepancy and resolve it using authoritative model metadata.

Do not discard, remap, or suppress a model class merely to force a supported-crop result. Handle the `Invalid` class explicitly and safely. Distinguish:
- unsupported or invalid input,
- an uncertain model result,
- a prediction for a crop the user did not select,
- a supported prediction that may receive guidance.

The selected crop is a user input and must not be treated as proof that the model prediction belongs to that crop.

### Model loading and runtime

- Load the model once per process/session using the project's established caching pattern; for Streamlit, use the appropriate resource cache if compatible with the current implementation.
- Keep inference code separate from UI code.
- Use the processor/image preprocessing expected by the actual model.
- Handle missing network access, missing weights, incompatible versions, malformed outputs, and inference errors with understandable messages. Do not fabricate a prediction as a fallback.
- Keep a small deterministic unit-test surface that does not download or load model weights.
- Any smoke-test scripts must preserve their existing purpose and command-line interface unless the team approves a change.

---

## 5. Module contracts

The roadmap proposes the following interfaces. Before implementing them, compare them with existing code and preserve compatible behavior. If a signature must change, explain why and update callers and tests together.

### 5.1 Image validation

`validate_image(uploaded_file) -> {"ok": bool, "reason": str, "image": PIL.Image | None}`

Expected policy from the roadmap:
- Accept JPG/JPEG, PNG, and WebP.
- Maximum upload size: 5 MB.
- Minimum dimensions: 100 × 100 pixels.
- Verify that Pillow can decode the image; do not trust the filename or declared MIME type alone.
- Convert a valid image into a consistent RGB representation for inference.
- Reject corrupt, unsupported, empty, oversized, or too-small images with a clear reason.
- Avoid reading an unbounded upload into memory where the framework permits a safe size check.
- Close file handles and image objects appropriately; do not mutate the user's original upload unexpectedly.

A technically valid image is not necessarily a leaf image. Image validation and biological/content validation are different checks. Do not claim to reliably identify leaves unless that capability is implemented and evaluated.

### 5.2 Prediction

The roadmap proposes:

`predict(image) -> {"label": str, "crop": str, "model_score": float, "top3": [{"label": str, "score": float}], "model_id": str, "status": "candidate"}`

- Keep the raw model output/score distinguishable from a calibrated confidence estimate.
- Ensure the returned crop and label are parsed consistently from verified model labels.
- Return stable, structured values and handle malformed model outputs.
- Do not invent `top3` values or return success after a failed inference.
- Keep the candidate model identity visible in the result or documentation.

### 5.3 Decision rules

The roadmap proposes:

`decide(prediction, selected_crop) -> {"decision": "usable" | "uncertain" | "unsupported" | "crop_mismatch", "reason": str, "show_guidance": bool}`

The roadmap lists these **provisional starting thresholds**:
- Score ≥ 0.80: usable candidate
- Score from 0.50 to below 0.80: uncertain
- Score below 0.50: reject as too uncertain

These are not validated universal thresholds. Do not treat them as scientifically established. Before shipping them as final policy, test them on representative, correctly labelled images and document the rationale. If that evaluation is unavailable, mark the thresholds as provisional in code comments and user-facing documentation.

Rules must be transparent and deterministic. An `Invalid` prediction or unsupported crop/class must not receive disease-specific treatment advice. A crop mismatch must not show guidance for the wrong crop. Never use a threshold alone to claim a diagnosis is correct.

### 5.4 Guidance lookup

The roadmap proposes:

`get_guidance(label) -> {label, crop, display_name, what_to_check, safe_next_steps, when_to_seek_expert, sources[{title,url}], reviewed_date} | None`

- Store structured guidance in `data/guidance.json` or the approved existing data location.
- Return `None` or a clear safe state when no reviewed entry exists; never invent missing guidance.
- Every substantive recommendation must be supported by a traceable source.
- Prefer official agricultural extension services, government agricultural departments, universities, and reputable research institutions.
- Record source title, exact URL, and review date. Verify URLs and applicability before representing a source as checked.
- Keep advice conservative and crop/condition-specific.
- Do not prescribe pesticide brands, chemical doses, application frequency, mixing instructions, or other high-consequence treatment steps without authoritative, locally applicable source support and qualified review.
- Encourage label compliance and qualified local advice for any pesticide decision.
- Clearly distinguish general observation/prevention advice from confirmed disease treatment.

### 5.5 “Aaj ka Plan”

The roadmap proposes:

`build_plan(prediction, decision, guidance) -> {"title","likely_issue","confidence","today_steps","monitor","expert_note","sources","disclaimer"}`

- The plan must be derived from the actual prediction, decision, and reviewed guidance.
- Do not create disease-specific steps when the decision disallows guidance or the guidance entry is missing.
- Use “possible issue” language rather than asserting a diagnosis.
- Include practical, non-alarmist next steps and what to monitor.
- Include the source references and the required disclaimer.
- Keep language concise and understandable for the target user. If Urdu or another language is added, preserve the meaning and uncertainty of the English source; do not translate technical claims in a way that strengthens them.

---

## 6. Evaluation and evidence standards

The team previously observed mixed predictions on synthetic test images, including some apparent matches and several wheat/rice misclassifications. Those images were smoke-test inputs, not an authentic labelled evaluation set. **Do not present those results as model accuracy.**

- Synthetic images may be used for plumbing, error handling, and UI smoke tests only. Clearly label them synthetic.
- Public dataset examples may be used only after checking dataset terms, provenance, labels, and any relevant usage restrictions.
- Do not report accuracy, precision, recall, F1, confusion matrices, or crop-specific performance without a documented labelled evaluation set and reproducible evaluation procedure.
- Use authentic, correctly labelled images for model-performance claims, with a documented source and split protocol.
- Avoid data leakage: near-duplicates, augmented copies, or images from the same original source should not cross evaluation splits in a way that inflates results.
- Report the number and source of tested images, class coverage, metric definitions, and important limitations.
- If the available sample is too small or unrepresentative, state that clearly and treat the model as a demo candidate.
- Do not tune thresholds on the final test set and then report that same set as independent evaluation.
- Keep model evaluation separate from software unit tests. Unit tests establish software behavior, not model accuracy.

The project must not imply that a model evaluated on corn, potato, rice, and wheat classes is validated for every crop, region, variety, growth stage, or field condition in Pakistan.

---

## 7. Tests and quality gates

Use pytest for deterministic tests. Tests should be fast and should not require model downloads unless the team explicitly requests an integration test.

Add or preserve tests for:
- image type, size, dimensions, corruption, and successful RGB conversion;
- score boundaries and each decision state;
- `Invalid`, unsupported labels, and crop mismatch;
- missing guidance entries and malformed guidance data;
- plan behavior when guidance is withheld;
- model-output parsing using small mocked/fake outputs;
- a small end-to-end test with a fake predictor and controlled guidance.

Tests must check both positive and negative paths. Avoid assertions that merely confirm the function ran. Do not weaken or delete a failing test just to obtain a green run; explain the underlying issue and fix or escalate it.

Before saying tests pass:
1. Run the exact command.
2. Report the command and result.
3. Separate skipped tests from passed tests.
4. State if model/network integration tests were not run.

Do not claim the app was deployed or that evaluation was completed unless that actually happened.

---

## 8. Streamlit interface and user experience

- Keep the interface focused on the single hero workflow.
- Make the expected upload formats and 5 MB limit visible.
- Ask the user to select the crop if required by the current flow, but explain that selection does not verify the model prediction.
- Show progress/loading states and readable errors for missing weights, network failure, invalid input, and inference failure.
- Display the candidate model label, possible issue, score with accurate terminology, decision state, guidance, sources, monitoring advice, and disclaimer as appropriate.
- Never show disease-specific guidance for an `Invalid`, unsupported, uncertain, or crop-mismatch result when the decision rules prohibit it.
- Avoid presenting a raw score as a percentage chance of disease.
- Provide a safe retake/retry path.
- Design for a short hackathon demo and ordinary laptop use; avoid features that delay the reliable vertical slice.
- Do not claim the app is production-ready, field-validated, or an agronomist replacement.

---

## 9. Privacy, security, licensing, and disclosures

- Never commit API keys, passwords, tokens, `.env` files, private contact details, or personal/identifiable farm data.
- Do not upload user images to a third-party service unless the team has explicitly approved the behavior and the user is informed.
- Keep virtual environments, model weights, caches, large generated files, and temporary outputs out of Git unless there is a clear, approved reason.
- Inspect `.gitignore` before adding files. Do not broadly ignore useful source, test, or documentation files.
- Verify the actual model license from the authoritative repository/license file. The team previously noticed inconsistent MIT/Apache-2.0 indications in model metadata versus model-card text; do not resolve this by guessing. Record the verified outcome and any restrictions.
- Check the licenses and terms for datasets, pretrained weights, code, fonts, images, and other third-party assets used in the project.
- Keep `DISCLOSURES.md` accurate about pre-existing code, pretrained models, datasets, AI-generated assistance, and third-party components as required by the competition.
- Do not imply that the team trained the pretrained model from scratch.
- Clearly distinguish the team's original work from existing tools, public resources, and AI-assisted work according to competition rules.

---

## 10. Repository and Git safety

The team has an original working directory and a separate fork clone. Preserve that distinction.

Known repository context at the time this file was drafted:
- Original parent repository: `D:\AICON\AICON_AGRICULTURE_MODULE`
- Fork workspace: `D:\AICON\AICON_AGRICULTURAL_MODULE_FORK`
- Fork remote: `https://github.com/muhammadsanaurrehman48/AICON_AGRICULTURE_MODULE.git`

These paths and remote settings can change. Always inspect the current workspace, `git remote -v`, branch, and status instead of assuming these values remain true.

Rules:
- Do not delete, move, or overwrite the original `CropSaathi` work to make the clone look tidy.
- Do not run destructive commands such as `git reset --hard`, `git clean -fd`, broad recursive deletion, or force-push unless the user explicitly requests the specific action after the risks are explained.
- Do not commit, push, merge, rebase, or switch branches automatically unless the user asks.
- Before editing, inspect `git status --short` and the current branch; preserve unrelated changes.
- Make focused changes, avoid unrelated formatting churn, and explain changed files.
- If the user asks for a branch, check whether it already exists before creating it.
- Do not remove a nested `.git` directory or alter repository boundaries without explicit approval.
- Treat LF/CRLF warnings on Windows as line-ending notices unless there is evidence of a real problem.
- Never say a commit or push succeeded without checking the command result and resulting Git status.

---

## 11. Development workflow: phased, approval-aware

Do not attempt to build or rewrite the entire application in one large operation.

### Phase 0 — Read-only audit
1. Inspect the repository tree, Git status, branch, and remotes.
2. Read existing scripts, modules, tests, documentation, and data.
3. Verify the candidate model's actual labels, preprocessing, model metadata, and licensing sources when network access is explicitly allowed.
4. Classify files as working implementation, partial implementation, or placeholder.
5. Compare implementation against the roadmap and report gaps, risks, and proposed small steps.
6. Make no edits, installs, downloads, commits, or pushes.

### Phase 1 — Stable core contracts
After approval:
1. Agree on config and verified label-map source of truth.
2. Implement or refine image validation.
3. Implement model-independent decision rules.
4. Implement guidance loading and schema checks.
5. Implement plan construction.
6. Add deterministic tests and run them.
7. Preserve existing smoke-test scripts and command-line behavior.

### Phase 2 — Model adapter and evaluation
After core tests are stable:
1. Implement model loading and inference adapter.
2. Test output parsing with mocked outputs.
3. Run explicit model smoke tests only when weights/dependencies are available and the user approves any required download.
4. Build a documented evaluation dataset and reproducible evaluation script.
5. Record results honestly; do not call synthetic smoke tests accuracy evaluation.

### Phase 3 — UI integration
After contracts are stable:
1. Build the Streamlit vertical slice.
2. Connect validation, prediction, decisions, guidance, and plan.
3. Add clear states for invalid image, uncertain result, unsupported class, crop mismatch, and model failure.
4. Verify all required disclaimers and source links.
5. Run unit tests and a manual smoke test.

### Phase 4 — Hackathon readiness
1. Complete README setup/run instructions.
2. Verify `requirements.txt` and `.gitignore`.
3. Complete disclosures and sources.
4. Write a five-minute demo script and submission checklist.
5. Confirm the deployed demo, if any, actually works before claiming it is available.
6. Freeze scope and avoid feature creep near the deadline.

After each phase, report:
- files changed;
- why each change was needed;
- exact test commands and outcomes;
- unresolved risks and limitations;
- any approval needed before proceeding.

---

## 12. Agent response format

For substantial tasks, finish with these headings:

1. **What I changed**
2. **Why**
3. **Tests run**
4. **Results**
5. **Limitations / risks**
6. **Next proposed step**

Be concise but specific. Mention exact file paths and commands. Distinguish verified facts from assumptions and recommendations. Do not state that a task is complete when only a plan or scaffold exists.

### Immediate task default

If the user gives no more specific task and asks the agent to start work, begin with the read-only audit in Phase 0. Do not edit files until the audit has been reported and the user has approved the next phase.
