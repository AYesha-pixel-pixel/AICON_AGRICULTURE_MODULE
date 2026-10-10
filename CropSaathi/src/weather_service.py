import requests
from datetime import datetime
from zoneinfo import ZoneInfo

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PAKISTAN_TZ = ZoneInfo("Asia/Karachi")


def get_weather(latitude, longitude):
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

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    if not current or not hourly.get("time"):
        raise ValueError("Open-Meteo returned incomplete weather data")

    weather_descriptions = {
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

    code = current.get("weather_code")

    current_weather = {
        "time": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_degrees": current.get("wind_direction_10m"),
        "cloud_cover_percent": current.get("cloud_cover"),
        "weather_code": code,
        "description": weather_descriptions.get(
            code, "Weather conditions unavailable"
        ),
    }

    now = datetime.now(PAKISTAN_TZ).replace(tzinfo=None)
    hourly_forecast = []

    for i, timestamp in enumerate(hourly["time"]):
        forecast_time = datetime.fromisoformat(timestamp)

        # Include the current hour if it is still listed by the API.
        if forecast_time < now.replace(minute=0, second=0, microsecond=0):
            continue

        hourly_forecast.append({
            "time": timestamp,
            "temperature_c": hourly["temperature_2m"][i],
            "humidity_percent": hourly["relative_humidity_2m"][i],
            "rain_probability_percent":
                hourly["precipitation_probability"][i],
            "precipitation_mm": hourly["precipitation"][i],
            "wind_speed_kmh": hourly["wind_speed_10m"][i],
            "weather_code": hourly["weather_code"][i],
            "description": weather_descriptions.get(
                hourly["weather_code"][i],
                "Conditions unavailable",
            ),
        })

    return {
        "source": "Open-Meteo",
        "timezone": "Asia/Karachi",
        "units": {
            "temperature": "°C",
            "precipitation": "mm per hour",
            "wind_speed": "km/h",
            "probability": "%",
        },
        "current": current_weather,
        "hourly_forecast": hourly_forecast[:24],
    }
