# Gemini agricultural advisory

CropSaathi can optionally generate a structured agricultural advisory after
the local image pipeline has produced an analysis. Gemini is not required for
`/analyze`; image analysis continues to work when the advisory provider is
unconfigured or unavailable.

## Configuration

Set these environment variables in the existing virtual environment or local
process configuration:

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "gemini-2.5-flash"
```

`GEMINI_API_KEY` is required only for approved disease advisories.
`GEMINI_MODEL` defaults to `gemini-2.5-flash`. Never commit a key; `.env` is
excluded by `.gitignore`.

The required dependency is `google-genai`. No live Gemini request is made by
the automated tests.

## API flow

1. Call `POST /analyze` with the image and selected crop.
2. Read the server-generated `analysis_id` from the response.
3. Call `POST /advisory` with that ID and optional context:

```json
{
  "analysis_id": "server-generated-id",
  "province": "Punjab",
  "district": "Lahore",
  "crop_growth_stage": "unknown",
  "farmer_observed_symptoms": "unknown",
  "soil_test_results": "not available",
  "irrigation_context": "recent irrigation",
  "recent_weather_context": "unknown"
}
```

The server does not accept a client-supplied prediction. References are kept
in a bounded in-memory store for development only; they expire when the
process restarts or when the store exceeds its capacity. Do not use this
store as durable production storage.

Advisory statuses are:

- `available`: a healthy response or validated Gemini response is available.
- `blocked_by_uncertainty`: the existing decision rules did not approve a
  disease-specific advisory; Gemini is not called.
- `unavailable`: represented by HTTP 503 when the key, SDK, or provider is
  unavailable. Existing image analysis remains independent.

Grounding and citations are conservative. `grounding_used` is true only when
provider grounding metadata and returned sources are both present. Without
that metadata, sources are removed and the response warns that source
verification was unavailable. Raw model scores remain raw scores, not
calibrated probabilities. The advisory is preliminary and not a confirmed
field diagnosis.

Optional context is limited to agricultural information needed for the
advisory. Do not submit unnecessary personal data or exact GPS coordinates.
