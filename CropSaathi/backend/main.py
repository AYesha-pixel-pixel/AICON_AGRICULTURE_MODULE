
from fastapi import FastAPI, HTTPException, Query
import requests

app = FastAPI(title="CropSaathi Weather API")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@app.get("/")
def home():
    return {"message": "CropSaathi weather backend is running"}


def generate_rain_alerts(hourly):
    alerts = []

    times = hourly.get("time", [])
    probabilities = hourly.get("precipitation_probability", [])
    precipitation = hourly.get("precipitation", [])

    for i, time in enumerate(times):
        probability = (
            probabilities[i]
            if i < len(probabilities)
            else None
        )
        rainfall = (
            precipitation[i]
            if i < len(precipitation)
            else None
        )

        reasons = []

        if probability is not None and probability >= 70:
            reasons.append("High rain probability")

        if rainfall is not None and rainfall >= 2:
            reasons.append("Significant expected rainfall")

        if reasons:
            alerts.append({
                "time": time,
                "rain_probability_percent": probability,
                "precipitation_mm": rainfall,
                "severity": (
                    "high"
                    if rainfall is not None and rainfall >= 2
                    else "moderate"
                ),
                "message": " and ".join(reasons),
            })

    return alerts

@app.get("/api/weather")
def get_weather(
    latitude: float = Query(33.6844, ge=-90, le=90),
    longitude: float = Query(73.0479, ge=-180, le=180),
):
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
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ],
    }

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "source": "Open-Meteo",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "timezone": data.get("timezone", "Asia/Karachi"),
            "current": data["current"],
            "hourly": data["hourly"],
            "rain_alerts": generate_rain_alerts(data["hourly"]),
        }

    except (requests.RequestException, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve weather data. Please try again.",
        ) from exc
