from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import api
from src.model_service import ModelInferenceError, ModelLoadError


def make_image(image_format: str = "PNG", size: tuple[int, int] = (100, 100)) -> bytes:
    image = Image.new("RGB", size, color="green")
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def prediction(
    label: str = "Corn___Common_Rust",
    crop: str | None = "corn",
    score: float = 0.95,
) -> dict[str, object]:
    return {
        "label": label,
        "crop": crop,
        "model_score": score,
        "top3": [{"label": label, "score": score}],
        "model_id": "test/model",
        "status": "candidate",
    }


class FakeService:
    def __init__(self, result: dict[str, object] | None = None, error=None):
        self.result = result or prediction()
        self.error = error
        self.calls = 0

    def predict(self, image):
        self.calls += 1
        if self.error is not None:
            raise self.error("test failure")
        return self.result


@pytest.fixture
def client():
    return TestClient(api.app)


@pytest.fixture(autouse=True)
def reset_model_service():
    api._model_service = None
    api._advisory_service = None
    api._analysis_references.clear()
    yield
    api._model_service = None
    api._advisory_service = None
    api._analysis_references.clear()


def test_health_does_not_load_model(client, monkeypatch):
    def fail_load():
        raise AssertionError("health must not load the model")

    monkeypatch.setattr(api, "load_model", fail_load)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["process_running"] is True
    assert response.json()["model_ready"] is None


def test_root_returns_api_entrypoint_without_loading_model(client, monkeypatch):
    def fail_load():
        raise AssertionError("root must not load the model")

    monkeypatch.setattr(api, "load_model", fail_load)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "CropSaathi",
        "api_version": "1.0",
        "message": (
            "CropSaathi API is running. Use /docs for interactive documentation."
        ),
        "docs_url": "/docs",
        "health_url": "/health",
    }


def test_cors_allows_only_configured_local_frontend_origin(client):
    allowed = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    denied = client.get(
        "/health",
        headers={"Origin": "https://untrusted.example"},
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_crops_match_configured_options(client):
    response = client.get("/crops")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["crops"]] == [
        "rice",
        "wheat",
        "corn",
    ]


def test_weather_route_returns_normalized_provider_data(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "get_weather",
        lambda latitude, longitude: {
            "source": "Open-Meteo",
            "location": {"latitude": latitude, "longitude": longitude},
            "timezone": "Asia/Karachi",
            "units": {"temperature": "°C"},
            "current": {"weather_code": 0},
            "hourly_forecast": [],
            "rain_alerts": [],
        },
    )

    response = client.get(
        "/api/weather",
        params={"latitude": 31.5204, "longitude": 74.3587},
    )

    assert response.status_code == 200
    assert response.json()["location"] == {
        "latitude": 31.5204,
        "longitude": 74.3587,
    }


def test_weather_route_maps_provider_failure_to_502(client, monkeypatch):
    from src.weather_service import WeatherServiceError

    def fail_weather(latitude, longitude):
        raise WeatherServiceError("provider details")

    monkeypatch.setattr(api, "get_weather", fail_weather)

    response = client.get("/api/weather")

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to retrieve weather data. Please try again."


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [("91", "73"), ("-91", "73"), ("33", "181"), ("33", "-181")],
)
def test_weather_route_rejects_invalid_coordinates(client, latitude, longitude):
    response = client.get(
        "/api/weather",
        params={"latitude": latitude, "longitude": longitude},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("files", "data", "status_code"),
    [
        (None, {"selected_crop": "corn"}, 422),
        ({"image": ("leaf.png", b"", "image/png")}, {"selected_crop": "corn"}, 400),
        ({"image": ("leaf.png", b"not image", "image/png")}, {"selected_crop": "corn"}, 400),
        ({"image": ("leaf.gif", make_image("GIF"), "image/gif")}, {"selected_crop": "corn"}, 400),
        (
            {"image": ("leaf.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
            {"selected_crop": "corn"},
            413,
        ),
        ({"image": ("leaf.png", make_image())}, {"selected_crop": "potato"}, 422),
    ],
)
def test_invalid_requests_are_rejected(client, files, data, status_code):
    response = client.post("/analyze", files=files, data=data)

    assert response.status_code == status_code


@pytest.mark.parametrize(
    "model_prediction",
    [
        prediction(),
        prediction("Corn___Healthy", "corn"),
        prediction(score=0.79),
        prediction(crop="rice"),
        prediction("Invalid", None, 0.99),
    ],
)
def test_analysis_returns_pipeline_result_for_supported_inputs(
    client,
    monkeypatch,
    model_prediction,
):
    service = FakeService(model_prediction)
    monkeypatch.setattr(api, "load_model", lambda: service)

    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["prediction"]["label"] == model_prediction["label"]
    assert payload["decision"]["show_guidance"] is (
        model_prediction["label"] == "Corn___Common_Rust"
        and model_prediction["model_score"] >= 0.8
        and model_prediction["crop"] == "corn"
    )
    assert isinstance(payload["report"], dict)


def test_denied_decision_has_no_disease_guidance(client, monkeypatch):
    service = FakeService(prediction(score=0.79))
    monkeypatch.setattr(api, "load_model", lambda: service)

    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )

    assert response.status_code == 200
    assert response.json()["report"]["sources"] == []
    assert response.json()["report"]["knowledge"] is None


@pytest.mark.parametrize("error", [ModelLoadError, ModelInferenceError])
def test_model_errors_are_service_unavailable(client, monkeypatch, error):
    monkeypatch.setattr(api, "load_model", lambda: FakeService(error=error))

    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )

    assert response.status_code == 503
    assert "currently" in response.json()["detail"]


def test_model_service_is_reused_across_requests(client, monkeypatch):
    service = FakeService()
    loads = 0

    def load_once():
        nonlocal loads
        loads += 1
        return service

    monkeypatch.setattr(api, "load_model", load_once)
    for _ in range(2):
        response = client.post(
            "/analyze",
            files={"image": ("leaf.png", make_image(), "image/png")},
            data={"selected_crop": "corn"},
        )
        assert response.status_code == 200

    assert loads == 1
    assert service.calls == 2


def test_success_response_is_json_serializable(client, monkeypatch):
    monkeypatch.setattr(api, "load_model", lambda: FakeService())

    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )

    assert response.headers["content-type"].startswith("application/json")
    response.json()


def test_advisory_requires_server_generated_analysis_reference(client):
    response = client.post(
        "/advisory",
        json={"analysis_id": "client-invented"},
    )

    assert response.status_code == 404


def test_uncertain_advisory_is_blocked_without_gemini_call(client, monkeypatch):
    service = FakeService(prediction(score=0.79))
    monkeypatch.setattr(api, "load_model", lambda: service)
    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )
    analysis_id = response.json()["analysis_id"]

    class FailingAdvisory:
        def advise(self, context):
            raise AssertionError("Gemini must not be called for uncertainty")

    monkeypatch.setattr(api, "get_advisory_service", lambda: FailingAdvisory())
    advisory_response = client.post(
        "/advisory",
        json={"analysis_id": analysis_id},
    )

    assert advisory_response.status_code == 200
    assert advisory_response.json()["status"] == "blocked_by_uncertainty"


def test_advisory_provider_unavailability_does_not_break_analysis(
    client,
    monkeypatch,
):
    service = FakeService()
    monkeypatch.setattr(api, "load_model", lambda: service)
    response = client.post(
        "/analyze",
        files={"image": ("leaf.png", make_image(), "image/png")},
        data={"selected_crop": "corn"},
    )
    analysis_id = response.json()["analysis_id"]

    from src.advisory_service import AdvisoryUnavailableError

    class UnavailableAdvisory:
        def advise(self, context):
            raise AdvisoryUnavailableError("not configured")

    monkeypatch.setattr(api, "get_advisory_service", lambda: UnavailableAdvisory())
    advisory_response = client.post(
        "/advisory",
        json={"analysis_id": analysis_id},
    )

    assert advisory_response.status_code == 503
    assert response.status_code == 200
