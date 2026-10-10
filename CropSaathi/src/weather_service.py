from __future__ import annotations

from datetime import datetime
import math
from typing import Any
from zoneinfo import ZoneInfo

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PAKISTAN_TZ = ZoneInfo("Asia/Karachi")
WEATHER_TIMEOUT_SECONDS = 10
RAIN_PROBABILITY_THRESHOLD = 70
RAIN_AMOUNT_THRESHOLD_MM = 2.0

_WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherServiceError(ValueError):
    """Raised when the upstream weather response cannot be safely used."""


def _description(code: Any) -> str:
    return _WEATHER_DESCRIPTIONS.get(code, "Weather conditions unavailable")


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _required_hourly_arrays(hourly: dict[str, Any]) -> tuple[list[Any], ...]:
    fields = (
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation_probability",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
    )
    arrays = tuple(hourly.get(field) for field in fields)
    if any(not isinstance(values, list) for values in arrays):
        raise WeatherServiceError("Open-Meteo returned incomplete hourly data.")
    if not arrays[0]:
        raise WeatherServiceError("Open-Meteo returned no hourly forecast data.")
    if len({len(values) for values in arrays}) != 1:
        raise WeatherServiceError("Open-Meteo returned inconsistent hourly data.")
    return arrays


def _parse_forecast_time(timestamp: Any) -> datetime:
    if not isinstance(timestamp, str):
        raise WeatherServiceError("Open-Meteo returned an invalid forecast timestamp.")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise WeatherServiceError(
            "Open-Meteo returned an invalid forecast timestamp."
        ) from error
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(PAKISTAN_TZ).replace(tzinfo=None)
    return parsed


def generate_rain_alerts(hourly_forecast: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply transparent application thresholds to normalized forecast rows."""
    alerts = []
    for forecast in hourly_forecast:
        probability = forecast.get("rain_probability_percent")
        rainfall = forecast.get("precipitation_mm")
        reasons = []
        if probability is not None and probability >= RAIN_PROBABILITY_THRESHOLD:
            reasons.append("High rain probability")
        if rainfall is not None and rainfall >= RAIN_AMOUNT_THRESHOLD_MM:
            reasons.append("Significant expected rainfall")
        if not reasons:
            continue
        alerts.append(
            {
                "time": forecast["time"],
                "rain_probability_percent": probability,
                "precipitation_mm": rainfall,
                "severity": (
                    "high"
                    if rainfall is not None and rainfall >= RAIN_AMOUNT_THRESHOLD_MM
                    else "moderate"
                ),
                "message": " and ".join(reasons),
            }
        )
    return alerts


def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or not math.isfinite(latitude)
        or not -90 <= latitude <= 90
        or isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
        or not math.isfinite(longitude)
        or not -180 <= longitude <= 180
    ):
        raise WeatherServiceError("Weather coordinates are outside the supported ranges.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Karachi",
        "forecast_hours": 24,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "cloud_cover",
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ],
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=WEATHER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise WeatherServiceError(
            "Unable to retrieve usable weather data from Open-Meteo."
        ) from error

    if not isinstance(data, dict):
        raise WeatherServiceError("Open-Meteo returned an invalid response.")
    current = data.get("current")
    hourly = data.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise WeatherServiceError("Open-Meteo returned incomplete weather data.")

    (
        timestamps,
        temperatures,
        humidities,
        probabilities,
        rainfall,
        codes,
        wind_speeds,
    ) = _required_hourly_arrays(hourly)

    current_code = current.get("weather_code")
    current_weather = {
        "time": current.get("time"),
        "temperature_c": _number(current.get("temperature_2m")),
        "feels_like_c": _number(current.get("apparent_temperature")),
        "humidity_percent": _number(current.get("relative_humidity_2m")),
        "precipitation_mm": _number(current.get("precipitation")),
        "rain_mm": _number(current.get("rain")),
        "wind_speed_kmh": _number(current.get("wind_speed_10m")),
        "wind_direction_degrees": _number(current.get("wind_direction_10m")),
        "cloud_cover_percent": _number(current.get("cloud_cover")),
        "weather_code": current_code,
        "description": _description(current_code),
    }

    current_hour = datetime.now(PAKISTAN_TZ).replace(
        minute=0, second=0, microsecond=0, tzinfo=None
    )
    hourly_forecast = []
    for values in zip(
        timestamps,
        temperatures,
        humidities,
        probabilities,
        rainfall,
        codes,
        wind_speeds,
    ):
        timestamp, temperature, humidity, probability, amount, code, wind_speed = values
        forecast_time = _parse_forecast_time(timestamp)
        if forecast_time < current_hour:
            continue
        hourly_forecast.append(
            {
                "time": timestamp,
                "temperature_c": _number(temperature),
                "humidity_percent": _number(humidity),
                "rain_probability_percent": _number(probability),
                "precipitation_mm": _number(amount),
                "wind_speed_kmh": _number(wind_speed),
                "weather_code": code,
                "description": _description(code),
            }
        )

    if not hourly_forecast:
        raise WeatherServiceError("Open-Meteo returned no future forecast entries.")

    hourly_forecast = hourly_forecast[:24]
    return {
        "source": "Open-Meteo",
        "location": {"latitude": latitude, "longitude": longitude},
        "timezone": data.get("timezone", "Asia/Karachi"),
        "units": {
            "temperature": "°C",
            "precipitation": "mm per hour",
            "wind_speed": "km/h",
            "probability": "%",
        },
        "current": current_weather,
        "hourly_forecast": hourly_forecast,
        "rain_alerts": generate_rain_alerts(hourly_forecast),
    }
