from __future__ import annotations

import logging
import os
import threading
import uuid
from collections import OrderedDict
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.advisory_service import (
    AdvisoryContext,
    AdvisoryProviderError,
    AdvisoryResponse,
    AdvisoryService,
    AdvisoryUnavailableError,
    build_blocked_response,
)
from src.config import (
    MAX_UPLOAD_MB,
    MODEL_ID,
    SUPPORTED_CROPS,
)
from src.decision_rules import decide
from src.guidance import get_guidance
from src.image_validation import validate_image
from src.model_service import (
    ModelInferenceError,
    ModelLoadError,
    ModelService,
    ModelServiceError,
    load_model,
)
from src.plan_builder import build_plan
from src.weather_service import WeatherServiceError, get_weather


LOGGER = logging.getLogger(__name__)
API_VERSION = "1.0"
APPLICATION_NAME = "CropSaathi"

app = FastAPI(
    title=APPLICATION_NAME,
    version=API_VERSION,
    description=(
        "Preliminary crop-leaf image decision support. Results are not "
        "confirmed field diagnoses."
    ),
)

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_model_lock = threading.Lock()
_model_service: ModelService | None = None
_advisory_service: AdvisoryService | None = None
_analysis_lock = threading.Lock()
_analysis_references: OrderedDict[str, dict[str, Any]] = OrderedDict()
_MAX_ANALYSIS_REFERENCES = 128


class HealthResponse(BaseModel):
    status: str
    application: str
    api_version: str
    process_running: bool
    model_ready: bool | None = Field(
        default=None,
        description="Null means that model readiness has not been checked.",
    )


class RootResponse(BaseModel):
    application: str
    api_version: str
    message: str
    docs_url: str
    health_url: str


class CropOption(BaseModel):
    id: str
    label: str


class CropsResponse(BaseModel):
    crops: list[CropOption]


class WeatherResponse(BaseModel):
    source: str
    location: dict[str, float]
    timezone: str
    units: dict[str, str]
    current: dict[str, Any]
    hourly_forecast: list[dict[str, Any]]
    rain_alerts: list[dict[str, Any]]


class TopPrediction(BaseModel):
    label: str
    score: float


class PredictionResponse(BaseModel):
    label: str
    crop: str | None = None
    model_score: float
    top3: list[TopPrediction] = Field(default_factory=list)
    model_id: str
    status: str


class DecisionResponse(BaseModel):
    decision: str
    reason: str
    show_guidance: bool


class AnalyzeResponse(BaseModel):
    request_id: str
    analysis_id: str | None = None
    selected_crop: str
    prediction: PredictionResponse
    decision: DecisionResponse
    report: dict[str, Any]
    model_id: str


class AdvisoryRequest(BaseModel):
    analysis_id: str = Field(min_length=1, max_length=100)
    province: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    crop_growth_stage: str | None = Field(default=None, max_length=200)
    farmer_observed_symptoms: str | None = Field(default=None, max_length=2000)
    soil_test_results: str | None = Field(default=None, max_length=2000)
    irrigation_context: str | None = Field(default=None, max_length=1000)
    recent_weather_context: str | None = Field(default=None, max_length=1000)


def get_advisory_service() -> AdvisoryService:
    global _advisory_service
    if _advisory_service is None:
        _advisory_service = AdvisoryService()
    return _advisory_service


def _store_analysis(
    prediction: dict[str, Any],
    decision: dict[str, Any],
    report: dict[str, Any],
) -> str:
    analysis_id = str(uuid.uuid4())
    with _analysis_lock:
        _analysis_references[analysis_id] = {
            "prediction": dict(prediction),
            "decision": dict(decision),
            "report": report,
        }
        while len(_analysis_references) > _MAX_ANALYSIS_REFERENCES:
            _analysis_references.popitem(last=False)
    return analysis_id


def _get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _analysis_lock:
        return _analysis_references.get(analysis_id)


def get_model_service() -> ModelService:
    """Return one lazily loaded service, safe against duplicate concurrent loads."""
    global _model_service
    if _model_service is not None:
        return _model_service
    with _model_lock:
        if _model_service is None:
            _model_service = load_model()
    return _model_service


def _request_id() -> str:
    return str(uuid.uuid4())


def _crop_label(crop: str) -> str:
    return crop.replace("_", " ").title()


def _validation_error(reason: str) -> HTTPException:
    status_code = 413 if "exceeds" in reason.lower() else 400
    return HTTPException(status_code=status_code, detail=reason)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report API process status without loading or probing the model."""
    return HealthResponse(
        status="ok",
        application=APPLICATION_NAME,
        api_version=API_VERSION,
        process_running=True,
        model_ready=None,
    )


@app.get("/", response_model=RootResponse, tags=["system"])
def root() -> RootResponse:
    """Provide a lightweight landing response for the API base URL."""
    return RootResponse(
        application=APPLICATION_NAME,
        api_version=API_VERSION,
        message="CropSaathi API is running. Use /docs for interactive documentation.",
        docs_url="/docs",
        health_url="/health",
    )


@app.get("/crops", response_model=CropsResponse, tags=["configuration"])
def crops() -> CropsResponse:
    """Return only crops configured as selectable by the application."""
    return CropsResponse(
        crops=[CropOption(id=crop, label=_crop_label(crop)) for crop in SUPPORTED_CROPS]
    )


@app.get(
    "/api/weather",
    response_model=WeatherResponse,
    tags=["weather"],
    responses={502: {"description": "Weather provider unavailable or returned invalid data."}},
)
def weather(
    latitude: float = Query(
        33.6844,
        ge=-90,
        le=90,
        description="Farm latitude in decimal degrees.",
    ),
    longitude: float = Query(
        73.0479,
        ge=-180,
        le=180,
        description="Farm longitude in decimal degrees.",
    ),
) -> WeatherResponse:
    """Return normalized Open-Meteo conditions and application rain alerts."""
    try:
        return WeatherResponse.model_validate(get_weather(latitude, longitude))
    except WeatherServiceError:
        LOGGER.exception("Weather provider failed for %.5f, %.5f", latitude, longitude)
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve weather data. Please try again.",
        ) from None


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=200,
    tags=["analysis"],
    responses={
        400: {"description": "Invalid or corrupt image upload."},
        413: {"description": "Image exceeds the configured upload limit."},
        422: {"description": "Missing fields or unsupported selected crop."},
        503: {"description": "Model is unavailable or inference cannot run."},
        500: {"description": "Unexpected internal server error."},
    },
)
def analyze(
    image: UploadFile = File(..., description="JPG, JPEG, PNG, or WebP image."),
    selected_crop: str = Form(..., description="Configured crop identifier."),
) -> AnalyzeResponse:
    """Validate and analyze one image using the existing local pipeline."""
    request_id = _request_id()
    if selected_crop.strip().lower() not in SUPPORTED_CROPS:
        raise HTTPException(
            status_code=422,
            detail="The selected crop is not supported.",
        )

    if (
        isinstance(image.size, int)
        and image.size > MAX_UPLOAD_MB * 1024 * 1024
    ):
        raise _validation_error(
            f"Image exceeds the {MAX_UPLOAD_MB} MB upload limit."
        )

    try:
        uploaded_data = image.file
        validation = validate_image(uploaded_data)
    except Exception:
        LOGGER.exception("Image validation failed unexpectedly for request %s", request_id)
        raise HTTPException(
            status_code=400,
            detail="The uploaded image could not be validated.",
        ) from None
    finally:
        image.file.close()

    if not validation["ok"]:
        raise _validation_error(validation["reason"])
    validated_image = validation["image"]
    if validated_image is None:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image could not be prepared for analysis.",
        )

    normalized_crop = selected_crop.strip().lower()
    try:
        service = get_model_service()
        prediction = service.predict(validated_image)
    except ModelLoadError:
        LOGGER.exception("Model loading failed for request %s", request_id)
        raise HTTPException(
            status_code=503,
            detail="The analysis model is currently unavailable.",
        ) from None
    except ModelInferenceError:
        LOGGER.exception("Model inference failed for request %s", request_id)
        raise HTTPException(
            status_code=503,
            detail="The image inference service is currently unavailable.",
        ) from None
    except ModelServiceError:
        LOGGER.exception("Model service failed for request %s", request_id)
        raise HTTPException(
            status_code=503,
            detail="The analysis service is currently unavailable.",
        ) from None
    except Exception:
        LOGGER.exception("Unexpected analysis failure for request %s", request_id)
        raise HTTPException(
            status_code=500,
            detail="The analysis could not be completed.",
        ) from None

    decision = decide(prediction, normalized_crop)
    guidance = get_guidance(prediction, normalized_crop)
    report = build_plan(prediction, normalized_crop, guidance=guidance)
    analysis_id = _store_analysis(prediction, decision, report)

    return AnalyzeResponse(
        request_id=request_id,
        analysis_id=analysis_id,
        selected_crop=normalized_crop,
        prediction=PredictionResponse.model_validate(prediction),
        decision=DecisionResponse.model_validate(decision),
        report=report,
        model_id=str(prediction.get("model_id", MODEL_ID)),
    )


@app.post(
    "/advisory",
    response_model=AdvisoryResponse,
    tags=["advisory"],
    responses={
        404: {"description": "Analysis reference was not found."},
        503: {"description": "Gemini advisory service is unavailable."},
    },
)
def advisory(request: AdvisoryRequest) -> AdvisoryResponse:
    """Generate an optional advisory from a server-produced analysis."""
    stored = _get_analysis(request.analysis_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="The analysis reference was not found or has expired.",
        )

    prediction = stored["prediction"]
    decision = stored["decision"]
    report = stored["report"]
    try:
        context = AdvisoryContext(
            selected_crop=report["selected_crop"],
            predicted_label=prediction["label"],
            raw_model_score=prediction["model_score"],
            decision_status=decision["decision"],
            decision_reason=decision["reason"],
            report_summary=report["summary"],
            report_warnings=report["warnings"],
            report_knowledge=report.get("knowledge"),
            provenance_status=report.get("provenance_status"),
            province=request.province,
            district=request.district,
            crop_growth_stage=request.crop_growth_stage,
            farmer_observed_symptoms=request.farmer_observed_symptoms,
            soil_test_results=request.soil_test_results,
            irrigation_context=request.irrigation_context,
            recent_weather_context=request.recent_weather_context,
        )
        if context.decision_status != "usable":
            return build_blocked_response(context)
        return get_advisory_service().advise(context)
    except AdvisoryUnavailableError:
        LOGGER.exception("Advisory service unavailable for %s", request.analysis_id)
        raise HTTPException(
            status_code=503,
            detail="The agricultural advisory service is currently unavailable.",
        ) from None
    except AdvisoryProviderError:
        LOGGER.exception("Advisory provider failed for %s", request.analysis_id)
        raise HTTPException(
            status_code=503,
            detail="The agricultural advisory could not be generated.",
        ) from None


__all__ = ["app", "get_model_service", "get_advisory_service"]
