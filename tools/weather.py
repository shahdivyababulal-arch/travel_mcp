from typing import Any
from datetime import date
from .common import geocode, get_json, load, require_destination
from config.settings import settings


def get_weather(destination: str, number_of_days: int = 1,
                travel_dates: list[str] | None = None) -> dict[str, Any]:
    destination = require_destination(destination)
    if number_of_days < 1 or number_of_days > 30:
        raise ValueError("number_of_days must be between 1 and 30")
    dates = travel_dates or [f"day-{index}" for index in range(1, number_of_days + 1)]
    if travel_dates:
        try:
            requested_dates = [date.fromisoformat(value) for value in dates[:number_of_days]]
        except ValueError as error:
            raise ValueError("travel_dates must use YYYY-MM-DD format") from error
        if len(travel_dates) != number_of_days or requested_dates != sorted(requested_dates):
            raise ValueError("travel_dates must contain one ordered date per day")
    if settings.travel_data_source.lower() == "local":
        rows = [row for row in load("weather.json") if row["destination"].lower() == destination.lower()]
        if not rows:
            raise ValueError(f"no local weather data for {destination}")
        by_date = {row["date"]: row for row in rows}
        return {"destination": destination,
                "weather": [by_date.get(date, by_date["default"]) | {"date": date}
                            for date in dates[:number_of_days]]}
    latitude, longitude = geocode(destination)
    params = {
        "latitude": latitude, "longitude": longitude,
        "daily": "temperature_2m_max,weather_code,precipitation_probability_max",
        "temperature_unit": "fahrenheit", "timezone": "auto",
    }
    if travel_dates:
        params["start_date"] = dates[0]
        params["end_date"] = dates[number_of_days - 1]
    else:
        params["forecast_days"] = number_of_days
    forecast = get_json("https://api.open-meteo.com/v1/forecast", params)
    daily = forecast.get("daily", {})
    by_date = {
        daily["time"][i]: {"date": daily["time"][i],
                           "temperature_f": daily["temperature_2m_max"][i],
                           "condition": weather_code_name(daily["weather_code"][i]),
                           "precipitation_probability": daily["precipitation_probability_max"][i]}
        for i in range(len(daily.get("time", [])))
    }
    weather = [by_date[value] for value in dates[:number_of_days] if value in by_date]
    return {"destination": destination, "weather": weather}


def weather_code_name(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorms"
    return "Mixed conditions"
