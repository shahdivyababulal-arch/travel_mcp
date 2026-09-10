from typing import Any
from .common import require_destination


def create_itinerary(destination: str, number_of_days: int,
                     attractions: list[dict[str, Any]] | None = None,
                     restaurants: list[dict[str, Any]] | None = None,
                     weather: list[dict[str, Any]] | None = None,
                     budget: dict[str, Any] | None = None,
                     preferences: list[str] | None = None) -> dict[str, Any]:
    destination = require_destination(destination)
    if number_of_days < 1 or number_of_days > 30:
        raise ValueError("number_of_days must be between 1 and 30")
    attractions, restaurants, weather = attractions or [], restaurants or [], weather or []
    days = []
    for index in range(number_of_days):
        attraction = attractions[index % len(attractions)] if attractions else None
        restaurant = restaurants[index % len(restaurants)] if restaurants else None
        forecast = weather[index % len(weather)] if weather else None
        attraction_cost = attraction.get("estimated_cost") if attraction else 0
        restaurant_cost = restaurant.get("estimated_cost") if restaurant else 25
        attraction_cost = attraction_cost if isinstance(attraction_cost, (int, float)) else 0
        restaurant_cost = restaurant_cost if isinstance(restaurant_cost, (int, float)) else 25
        days.append({"day": index + 1, "weather": forecast,
                     "schedule": [
                        {"time": "Morning", "activity": attraction["name"] if attraction else "Explore the neighborhood",
                          "estimated_cost": attraction_cost},
                        {"time": "Evening", "restaurant": restaurant["name"] if restaurant else "Choose a local restaurant",
                          "estimated_cost": restaurant_cost}
                     ]})
    return {"destination": destination, "number_of_days": number_of_days,
            "preferences": preferences or [], "days": days, "budget_summary": budget}
