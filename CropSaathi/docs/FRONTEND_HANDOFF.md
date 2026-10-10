# CropSaathi frontend API handoff

## Local server

Run the single canonical backend from `CropSaathi`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Base URL: `http://127.0.0.1:8000`

Swagger: `http://127.0.0.1:8000/docs`

The frontend should use `/api/weather` on this same server. It should not
start `backend/main.py` as a second port-8000 application.

## Routes

### `GET /crops`

Returns selectable crops:

```json
{
  "crops": [
    {"id": "rice", "label": "Rice"},
    {"id": "wheat", "label": "Wheat"},
    {"id": "corn", "label": "Corn"}
  ]
}
```

### `POST /analyze`

Send `multipart/form-data` with:

- `image`: JPG, JPEG, PNG, or WebP; maximum 5 MB; minimum 100 x 100 pixels.
- `selected_crop`: one of `rice`, `wheat`, or `corn`.

The response includes `request_id`, `analysis_id`, `selected_crop`,
`prediction`, `decision`, `report`, and `model_id`. `analysis_id` is required
for a later advisory request. Raw `model_score` values are not calibrated
probabilities.

The client must represent these decision values distinctly:

- `usable`: possible supported disease result; still preliminary.
- `uncertain`: do not show disease-specific guidance.
- `unsupported`: invalid or unsupported model result; do not show disease
  guidance.
- `crop_mismatch`: predicted crop differs from the selected crop; do not show
  disease guidance.

### `GET /api/weather`

Query parameters:

- `latitude`: optional decimal number from `-90` to `90`; default `33.6844`.
- `longitude`: optional decimal number from `-180` to `180`; default `73.0479`.

The response contains:

- `source`: normally `Open-Meteo`.
- `location`: requested coordinates.
- `timezone`: `Asia/Karachi`.
- `units`: metric units.
- `current`: current provider fields and a WMO description.
- `hourly_forecast`: up to the next 24 available future hourly entries.
- `rain_alerts`: application-rule alerts carrying the matching forecast
  timestamp, probability, rainfall, severity, and reasons.

Rain rules are transparent application thresholds, not validated agronomic
laws:

- probability `>= 70%` adds a high-probability reason;
- rainfall `>= 2.0 mm` adds a significant-rainfall reason and makes severity
  `high`;
- high probability without that rainfall threshold is `moderate`.

Invalid coordinates return `422`. Open-Meteo timeout, HTTP, rate-limit, or
malformed-data failures return `502`. The UI should show weather as
unavailable and offer retry; it must not fabricate forecast values.

### `POST /advisory`

Send JSON containing a server-generated `analysis_id` from `/analyze` and
optional context fields such as province, district, growth stage, symptoms,
soil results, irrigation, and recent weather context.

The endpoint rejects unknown analysis references with `404`. Non-usable
analysis decisions return `blocked_by_uncertainty` without calling Gemini.
Missing Gemini configuration or provider failures return `503`.

## Recommended screen flow

1. Load `/crops` and let the farmer select a crop.
2. Upload an image and call `/analyze`.
3. Display the preliminary decision, report, warnings, limitations, and
   sources.
4. Request `/api/weather` when the farmer supplies or confirms coordinates;
   show the source, timestamp, and location with the forecast.
5. Offer `/advisory` using the returned `analysis_id` only when appropriate.
6. Provide retry paths for image validation, model unavailability, weather
   unavailability, and advisory unavailability.

Do not present a model result as a confirmed diagnosis, a raw score as a
probability, weather alerts as guaranteed events, or unverified knowledge as
verified agronomic fact. Do not duplicate inference, thresholds, crop
mapping, or guidance rules in the frontend.

## CORS and configuration

The canonical API allows only `http://localhost:5173` and
`http://127.0.0.1:5173` by default, without credentials. Override the
comma-separated allowlist with `CORS_ORIGINS` for an approved deployment
origin; never use wildcard origins with credentials. The frontend should make
its API base URL configurable (for example, `VITE_API_BASE_URL`) rather than
hard-coding production infrastructure.
