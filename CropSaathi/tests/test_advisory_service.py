from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.advisory_service import (
    AdvisoryContext,
    AdvisoryProviderError,
    AdvisoryService,
    AdvisoryUnavailableError,
)


def context(status: str = "usable", label: str = "Corn___Common_Rust"):
    return AdvisoryContext(
        selected_crop="corn",
        predicted_label=label,
        raw_model_score=0.95,
        decision_status=status,
        decision_reason="meets threshold",
        report_summary="Possible issue.",
        report_warnings=["Verify locally."],
    )


def provider_payload():
    return {
        "status": "available",
        "model": "ignored",
        "summary": "Review the possible issue with local expertise.",
        "what_the_result_means": "The image result is preliminary.",
        "immediate_actions": ["Inspect more leaves."],
        "information_needed": ["Growth stage"],
        "management_options": ["Use locally verified options only."],
        "fertilizer_guidance": ["No quantity without a soil test."],
        "when_to_seek_expert_help": ["Contact an agronomist if it spreads."],
        "sources": [{"title": "Verified source", "url": "https://example.test/source"}],
        "warnings": ["Not a confirmed diagnosis."],
        "grounding_used": True,
    }


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        return self.response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


def test_missing_key_fails_only_when_advisory_is_requested(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(AdvisoryUnavailableError):
        AdvisoryService().advise(context())


def test_successful_response_is_structured_and_grounding_is_preserved():
    response = SimpleNamespace(
        text=json.dumps(provider_payload()),
        grounding_metadata={
            "web_search_queries": ["corn disease"],
            "sources": [
                {
                    "title": "Verified source",
                    "url": "https://example.test/source",
                    "source_type": "grounding",
                }
            ],
        },
    )
    service = AdvisoryService(
        client=FakeClient(response),
        model="gemini-2.5-flash",
    )

    result = service.advise(context())

    assert result.status == "available"
    assert result.grounding_used is True
    assert result.sources[0].url == "https://example.test/source"


def test_uncertain_result_is_blocked_before_provider_call():
    client = FakeClient(SimpleNamespace(text=json.dumps(provider_payload())))

    result = AdvisoryService(client=client).advise(context("uncertain"))

    assert result.status == "blocked_by_uncertainty"
    assert client.models.calls == 0
    assert result.sources == []


def test_crop_mismatch_is_blocked_before_provider_call():
    client = FakeClient(SimpleNamespace(text=json.dumps(provider_payload())))
    advisory_context = context("crop_mismatch")

    result = AdvisoryService(client=client).advise(advisory_context)

    assert result.status == "blocked_by_uncertainty"
    assert client.models.calls == 0


def test_healthy_result_does_not_claim_disease_absence_or_call_provider():
    client = FakeClient(SimpleNamespace(text=json.dumps(provider_payload())))

    result = AdvisoryService(client=client).advise(
        context("usable", "Corn___Healthy")
    )

    assert result.status == "available"
    assert "not proof" in result.summary
    assert client.models.calls == 0


def test_malformed_provider_output_is_rejected():
    service = AdvisoryService(
        client=FakeClient(SimpleNamespace(text="not json"))
    )

    with pytest.raises(AdvisoryProviderError):
        service.advise(context())


def test_provider_failure_is_sanitized():
    class FailingModels:
        def generate_content(self, **kwargs):
            raise TimeoutError("secret provider details")

    service = AdvisoryService(client=SimpleNamespace(models=FailingModels()))

    with pytest.raises(AdvisoryProviderError, match="request failed"):
        service.advise(context())


def test_missing_soil_data_does_not_create_fertilizer_quantities():
    response = SimpleNamespace(
        text=json.dumps(provider_payload()),
        grounding_metadata=None,
    )
    result = AdvisoryService(client=FakeClient(response)).advise(context())

    assert all(
        not any(char.isdigit() for char in item)
        for item in result.fertilizer_guidance
    )
    assert result.grounding_used is False
    assert result.sources == []


def test_model_authored_sources_are_discarded_without_grounding_metadata():
    response = SimpleNamespace(
        text=json.dumps(provider_payload()),
        grounding_metadata={"web_search_queries": ["corn disease"]},
    )

    result = AdvisoryService(client=FakeClient(response)).advise(context())

    assert result.grounding_used is False
    assert result.sources == []
