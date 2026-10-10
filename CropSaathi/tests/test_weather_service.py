from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import requests

import src.weather_service as weather


def _payload(*, timestamps=None, probabilities=None, rainfall=None):
    timestamps = timestamps or [
        (datetime.now(weather.PAKISTAN_TZ) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:00"
        ),
        (datetime.now(weather.PAKISTAN_TZ) + timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:00"
        ),
    ]
    probabilities = probabilities or [70, 10]
    rainfall = rainfall or [2.0, 0.0]
    return {
        "timezone": "Asia/Karachi",
        "current": {
            "time": timestamps[0],
            "temperature_2m": 30,
            "relative_humidity_2m": 60,
            "weather_code": 999,
        },
        "hourly": {
            "time": timestamps,
            "temperature_2m": [30, 29],
            "relative_humidity_2m": [60, 61],
            "precipitation_probability": probabilities,
            "precipitation": rainfall,
            "weather_code": [999, 0],
            "wind_speed_10m": [10, 8],
        },
    }


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_get_weather_normalizes_future_forecast_and_unknown_code(monkeypatch):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(_payload()),
    )

    result = weather.get_weather(33.6844, 73.0479)

    assert result["source"] == "Open-Meteo"
    assert result["location"] == {"latitude": 33.6844, "longitude": 73.0479}
    assert result["timezone"] == "Asia/Karachi"
    assert result["current"]["description"] == "Weather conditions unavailable"
    assert len(result["hourly_forecast"]) == 2
    assert result["hourly_forecast"][0]["description"] == "Weather conditions unavailable"
    assert result["rain_alerts"][0]["time"] == result["hourly_forecast"][0]["time"]


def test_get_weather_filters_past_forecast_entries(monkeypatch):
    now = datetime.now(weather.PAKISTAN_TZ)
    timestamps = [
        (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:00"),
        (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00"),
    ]
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(_payload(timestamps=timestamps)),
    )

    result = weather.get_weather(0, 0)

    assert [item["time"] for item in result["hourly_forecast"]] == [timestamps[1]]


@pytest.mark.parametrize(
    ("probability", "rainfall", "expected"),
    [
        (69, 0, False),
        (70, 0, True),
        (71, 0, True),
        (0, 1.9, False),
        (0, 2.0, True),
        (0, 2.1, True),
    ],
)
def test_rain_alert_boundaries(probability, rainfall, expected):
    alerts = weather.generate_rain_alerts(
        [
            {
                "time": "2026-10-10T12:00",
                "rain_probability_percent": probability,
                "precipitation_mm": rainfall,
            }
        ]
    )

    assert bool(alerts) is expected


def test_rain_alert_combines_reasons_and_severity():
    alerts = weather.generate_rain_alerts(
        [
            {
                "time": "2026-10-10T12:00",
                "rain_probability_percent": 70,
                "precipitation_mm": 2.0,
            }
        ]
    )

    assert alerts[0]["severity"] == "high"
    assert "High rain probability" in alerts[0]["message"]
    assert "Significant expected rainfall" in alerts[0]["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {"current": {}, "hourly": {}},
        {
            **_payload(),
            "hourly": {
                **_payload()["hourly"],
                "wind_speed_10m": [1],
            },
        },
    ],
)
def test_get_weather_rejects_incomplete_or_inconsistent_payload(monkeypatch, payload):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    with pytest.raises(weather.WeatherServiceError):
        weather.get_weather(0, 0)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 0), (-91, 0), (0, 181), (0, -181), (float("nan"), 0)],
)
def test_get_weather_rejects_invalid_coordinates(latitude, longitude):
    with pytest.raises(weather.WeatherServiceError, match="coordinates"):
        weather.get_weather(latitude, longitude)


@pytest.mark.parametrize("error", [requests.Timeout("timed out"), requests.HTTPError("429")])
def test_get_weather_sanitizes_upstream_failures(monkeypatch, error):
    monkeypatch.setattr(
        weather.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(error=error),
    )

    with pytest.raises(weather.WeatherServiceError, match="Unable to retrieve"):
        weather.get_weather(0, 0)
