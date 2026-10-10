from __future__ import annotations

import json
import os
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AdvisoryError(RuntimeError):
    """Base error for advisory service failures."""


class AdvisoryUnavailableError(AdvisoryError):
    """Raised when Gemini cannot be used for an advisory request."""


class AdvisoryProviderError(AdvisoryError):
    """Raised when Gemini returns an unusable response."""


class AdvisorySource(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2000)
    source_type: str | None = Field(default=None, max_length=100)


class AdvisoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "unavailable", "blocked_by_uncertainty"]
    model: str
    summary: str
    what_the_result_means: str
    immediate_actions: list[str]
    information_needed: list[str]
    management_options: list[str]
    fertilizer_guidance: list[str]
    when_to_seek_expert_help: list[str]
    sources: list[AdvisorySource]
    warnings: list[str]
    grounding_used: bool


class AdvisoryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_crop: str
    predicted_label: str
    raw_model_score: float
    decision_status: str
    decision_reason: str
    report_summary: str
    report_warnings: list[str] = Field(default_factory=list)
    report_knowledge: dict[str, Any] | None = None
    provenance_status: str | None = None
    province: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    crop_growth_stage: str | None = Field(default=None, max_length=200)
    farmer_observed_symptoms: str | None = Field(default=None, max_length=2000)
    soil_test_results: str | None = Field(default=None, max_length=2000)
    irrigation_context: str | None = Field(default=None, max_length=1000)
    recent_weather_context: str | None = Field(default=None, max_length=1000)


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["available"]},
        "model": {"type": "string"},
        "summary": {"type": "string"},
        "what_the_result_means": {"type": "string"},
        "immediate_actions": {"type": "array", "items": {"type": "string"}},
        "information_needed": {"type": "array", "items": {"type": "string"}},
        "management_options": {"type": "array", "items": {"type": "string"}},
        "fertilizer_guidance": {"type": "array", "items": {"type": "string"}},
        "when_to_seek_expert_help": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "source_type": {"type": "string"},
                },
                "required": ["title", "url"],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
        "grounding_used": {"type": "boolean"},
    },
    "required": [
        "status",
        "model",
        "summary",
        "what_the_result_means",
        "immediate_actions",
        "information_needed",
        "management_options",
        "fertilizer_guidance",
        "when_to_seek_expert_help",
        "sources",
        "warnings",
        "grounding_used",
    ],
}


def _optional_text(value: str | None) -> str:
    return value if value is not None else "Unknown; do not infer this information."


def build_blocked_response(context: AdvisoryContext) -> AdvisoryResponse:
    return AdvisoryResponse(
        status="blocked_by_uncertainty",
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        summary="The result is inconclusive, so no disease-specific advisory was generated.",
        what_the_result_means=context.decision_reason,
        immediate_actions=[
            "Review the image quality and capture a clearer image in good lighting.",
            "Compare the plant with observations from a local agricultural expert.",
        ],
        information_needed=[
            "A clearer image and direct field observations may be needed.",
        ],
        management_options=[],
        fertilizer_guidance=[
            "No fertilizer quantity or schedule is recommended from an inconclusive result."
        ],
        when_to_seek_expert_help=[
            "Contact a local agriculture extension officer or qualified agronomist "
            "if symptoms or crop loss concerns continue."
        ],
        sources=[],
        warnings=[
            "This image-based result is preliminary and not a confirmed field diagnosis.",
            "Disease-specific Gemini advice was blocked by the existing decision rules.",
        ],
        grounding_used=False,
    )


def _healthy_response(context: AdvisoryContext) -> AdvisoryResponse:
    return AdvisoryResponse(
        status="available",
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        summary="The model result is consistent with a healthy result, but this is not proof that the plant is disease-free.",
        what_the_result_means=(
            "Image classification can miss disease or other field problems. "
            "Continue observing the crop and compare concerns with local advice."
        ),
        immediate_actions=[
            "Continue routine field observation for new or changing symptoms.",
        ],
        information_needed=[
            "Observed symptoms, crop growth stage, and local field conditions if concerns remain."
        ],
        management_options=[],
        fertilizer_guidance=[
            "No fertilizer quantity or schedule is recommended without crop stage, "
            "location, soil test results, and local recommendations."
        ],
        when_to_seek_expert_help=[
            "Seek local agricultural advice if symptoms or concerns remain despite the healthy result."
        ],
        sources=[],
        warnings=[
            "A healthy model result is not proof that the plant is disease-free.",
        ],
        grounding_used=False,
    )


class AdvisoryService:
    """Injectable Gemini advisory boundary with validated structured output."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str | None = None,
        grounding_enabled: bool = False,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.grounding_enabled = grounding_enabled
        self._client = client
        self._client_factory = client_factory

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AdvisoryUnavailableError(
                "Gemini advisory is unavailable because GEMINI_API_KEY is not configured."
            )
        try:
            if self._client_factory is not None:
                self._client = self._client_factory(api_key)
            else:
                from google import genai

                self._client = genai.Client(api_key=api_key)
        except ImportError as error:
            raise AdvisoryUnavailableError(
                "Gemini advisory is unavailable because the provider SDK is not installed."
            ) from error
        except Exception as error:
            raise AdvisoryUnavailableError(
                "Gemini advisory is unavailable because the provider SDK could not be initialized."
            ) from error
        return self._client

    def advise(self, context: AdvisoryContext) -> AdvisoryResponse:
        if context.decision_status != "usable":
            return build_blocked_response(context)
        if context.predicted_label.endswith("___Healthy"):
            return _healthy_response(context)

        client = self._get_client()
        prompt = self._prompt(context)
        try:
            config: dict[str, Any] = {
                "response_mime_type": "application/json",
                "response_schema": _RESPONSE_SCHEMA,
            }
            if self.grounding_enabled:
                try:
                    from google.genai import types

                    config["tools"] = [
                        types.Tool(google_search=types.GoogleSearch())
                    ]
                except ImportError as error:
                    raise AdvisoryUnavailableError(
                        "Gemini Search grounding is unavailable in the installed SDK."
                    ) from error
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            payload = self._response_payload(response)
            advisory = AdvisoryResponse.model_validate(payload)
            if advisory.status != "available":
                raise AdvisoryProviderError("Gemini returned an invalid advisory status.")
            advisory.model = self.model
            grounded_sources = self._grounded_sources(response)
            advisory.grounding_used = bool(grounded_sources)
            advisory.sources = grounded_sources
            if not grounded_sources:
                advisory.warnings.append(
                    "Provider grounding metadata was not available; sources were not treated as verified."
                )
            return advisory
        except AdvisoryError:
            raise
        except ValidationError as error:
            raise AdvisoryProviderError(
                "Gemini returned a response that did not match the advisory schema."
            ) from error
        except Exception as error:
            raise AdvisoryProviderError(
                "The Gemini advisory request failed."
            ) from error

    def _prompt(self, context: AdvisoryContext) -> str:
        payload = context.model_dump(exclude_none=True)
        return (
            "Create a cautious agricultural advisory from this server-produced "
            "CropSaathi result. Treat all unknown fields as unknown. The result "
            "is preliminary, not a confirmed field diagnosis. Use only evidence "
            "you can support. Do not provide pesticide names, chemical doses, "
            "spray schedules, fertilizer quantities, or guaranteed outcomes. "
            "Separate immediate safe observations/actions, preventive options, "
            "expert-verification treatment options, and fertilizer information "
            "needed. Return JSON matching the requested schema. "
            f"Server analysis context: {json.dumps(payload, ensure_ascii=False)}"
        )

    @staticmethod
    def _response_payload(response: Any) -> Any:
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise AdvisoryProviderError("Gemini returned an empty advisory response.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise AdvisoryProviderError(
                "Gemini returned malformed advisory JSON."
            ) from error

    @staticmethod
    def _grounded_sources(response: Any) -> list[AdvisorySource]:
        metadata = getattr(response, "grounding_metadata", None)
        if metadata is None:
            metadata = getattr(response, "groundingMetadata", None)
        if metadata is None:
            candidates = getattr(response, "candidates", None)
            if isinstance(candidates, list) and candidates:
                metadata = getattr(candidates[0], "grounding_metadata", None)
                if metadata is None:
                    metadata = getattr(candidates[0], "groundingMetadata", None)
        raw_sources: list[dict[str, Any]] = []
        if isinstance(metadata, dict):
            sources = metadata.get("sources")
            if isinstance(sources, list):
                raw_sources.extend(
                    source for source in sources if isinstance(source, dict)
                )
        else:
            chunks = getattr(metadata, "grounding_chunks", None)
            if chunks is None:
                chunks = getattr(metadata, "groundingChunks", None)
            if isinstance(chunks, list):
                for chunk in chunks:
                    web = getattr(chunk, "web", None)
                    if web is None:
                        web = getattr(chunk, "retrieved_context", None)
                    title = getattr(web, "title", None)
                    url = getattr(web, "uri", None)
                    if isinstance(title, str) and isinstance(url, str):
                        raw_sources.append({"title": title, "url": url})
        sources = []
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                continue
            try:
                sources.append(AdvisorySource.model_validate(raw_source))
            except ValidationError:
                continue
        return sources
