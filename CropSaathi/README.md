# CropSaathi

A Pakistan-focused agricultural AI decision-support MVP.

## Planned workflow
1. Upload a crop-leaf image.
2. Run pretrained-model inference.
3. Handle uncertain predictions and unsupported crops.
4. Present source-backed agricultural guidance.
5. Generate an actionable "Aaj ka Plan".

## Development status
Early development. Model predictions are experimental and are not confirmed diagnoses.

Synthetic images are for smoke testing only, not accuracy evaluation.

## FastAPI backend

From the `CropSaathi` directory, activate the existing virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the declared dependencies if needed, then start the API:

```powershell
python -m uvicorn api:app --reload
```

The API landing response is available at `http://127.0.0.1:8000/`.
Interactive Swagger documentation is available at
`http://127.0.0.1:8000/docs`.

Endpoints:

- `GET /` confirms that the API process is running and links to `/docs` and
  `/health`. It does not load the ML model or contact Gemini.
- `GET /health` reports that the API process is running. It does not load or
  validate the ML model, so `model_ready` is `null` until a deliberate
  readiness check is added.
- `GET /crops` returns the configured selectable crop identifiers and labels.
- `GET /api/weather` accepts optional `latitude` and `longitude` query
  parameters and returns normalized Open-Meteo current conditions, a
  forward-looking hourly forecast, and application rain alerts. It defaults
  to Islamabad coordinates for backward compatibility. Provider failures
  return HTTP 502; invalid coordinates return HTTP 422.
- `POST /analyze` accepts multipart fields `image` and required
  `selected_crop`. It returns the existing prediction, decision, and report
  structures, including provenance and knowledge fields where available.

Run the automated tests from `CropSaathi` with:

```powershell
python -m pytest tests/ -q
```

Example manual request:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/analyze" `
  -F "selected_crop=corn" `
  -F "image=@samples/test_leaf.png"
```

Scores are raw model scores, not calibrated probabilities. Image results are
preliminary decision support and not confirmed field diagnoses. The candidate
model may be unavailable when weights are not cached, and agricultural
guidance remains subject to source and local expert verification.

## Model evaluation

The repository does not contain a labelled evaluation dataset. Use the
manifest-driven evaluator only with a locally supplied, explicitly labelled
dataset:

```powershell
python evaluate_model.py --manifest path\to\manifest.csv --split evaluation
```

See [docs/MODEL_EVALUATION.md](docs/MODEL_EVALUATION.md) for the manifest
schema, held-out split rules, output files, and limitations. Raw model scores
are not calibrated probabilities.

## Optional Gemini advisory

The optional advisory endpoint is documented in
[docs/ADVISORY.md](docs/ADVISORY.md). Set `GEMINI_API_KEY` only when using
`POST /advisory`; `/analyze` remains functional without Gemini.

For a local Vite frontend, the API allows `http://localhost:5173` and
`http://127.0.0.1:5173` by default. Set `CORS_ORIGINS` to a comma-separated
explicit origin allowlist for another approved frontend origin.

## Frontend handoff

The exact frontend-facing route and response contract is documented in
[docs/FRONTEND_HANDOFF.md](docs/FRONTEND_HANDOFF.md). The React client should
consume the canonical API on port `8000`; it should not call the separate
weather module or duplicate model and decision logic.
