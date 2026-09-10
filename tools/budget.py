from typing import Any
from .common import require_destination
from config.settings import settings


TIER_COST_ESTIMATES = {
    "budget": {
        "food_per_day": 35,
        "activities_per_day": 20,
        "transport_per_day": 15,
        "hotel_per_night": 80,
    },
    "moderate": {
        "food_per_day": 70,
        "activities_per_day": 50,
        "transport_per_day": 30,
        "hotel_per_night": 180,
    },
    "luxury": {
        "food_per_day": 150,
        "activities_per_day": 150,
        "transport_per_day": 80,
        "hotel_per_night": 400,
    },
}

TRAVEL_STYLE_ALIASES = {
    "cheap": "budget",
    "economical": "budget",
    "economic": "budget",
    "standard": "moderate",
    "comfortable": "moderate",
    "mid-range": "moderate",
    "midrange": "moderate",
    "upscale": "luxury",
    "luxurious": "luxury",
}


def calculate_budget(destination: str, number_of_days: int, budget: float | None = None,
                     activities_cost: float = 0, meals_per_day: int = 3,
                     attractions: list[dict[str, Any]] | None = None,
                     restaurants: list[dict[str, Any]] | None = None,
                     travel_style: str = "moderate") -> dict[str, Any]:
    destination = require_destination(destination)
    if number_of_days < 1 or number_of_days > 30:
        raise ValueError("number_of_days must be between 1 and 30")
    if budget is not None and budget < 0:
        raise ValueError("budget cannot be negative")
    if meals_per_day < 1 or meals_per_day > 10:
        raise ValueError("meals_per_day must be between 1 and 10")
    travel_style = travel_style.strip().lower()
    travel_style = TRAVEL_STYLE_ALIASES.get(travel_style, travel_style)
    if travel_style not in TIER_COST_ESTIMATES:
        raise ValueError(f"travel_style must be one of {sorted(TIER_COST_ESTIMATES)}")
    tier = TIER_COST_ESTIMATES[travel_style]

    attraction_costs = [
        item.get("estimated_cost") for item in (attractions or [])
        if isinstance(item.get("estimated_cost"), (int, float))
    ]
    activities_pricing_basis = "returned_attraction_costs" if attraction_costs else "assumed_tier"
    if attraction_costs:
        activities_cost = sum(attraction_costs)
    elif activities_cost:
        activities_pricing_basis = "provided_activity_cost"
    else:
        activities_cost = number_of_days * tier["activities_per_day"]

    restaurant_costs = [
        item.get("estimated_cost") for item in (restaurants or [])
        if isinstance(item.get("estimated_cost"), (int, float))
    ]
    food_pricing_basis = "returned_restaurant_costs" if restaurant_costs else "assumed_tier"
    meal_cost = sum(restaurant_costs) / len(restaurant_costs) if restaurant_costs else tier["food_per_day"] / meals_per_day
    hotel_nights = max(number_of_days - 1, 1)
    estimates = {
        "accommodation": round(hotel_nights * tier["hotel_per_night"], 2),
        "food": round(number_of_days * meals_per_day * meal_cost, 2),
        "transportation": round(number_of_days * tier["transport_per_day"], 2),
        "activities": round(activities_cost, 2),
        "miscellaneous": round(number_of_days * settings.budget_miscellaneous_per_day, 2),
    }
    total = round(sum(estimates.values()), 2)
    return {"destination": destination, "number_of_days": number_of_days,
            "estimates": estimates, "total_estimated_cost": total, "budget": budget,
            "within_budget": budget is None or total <= budget,
            "remaining": None if budget is None else round(budget - total, 2),
            "travel_style": travel_style,
            "pricing_basis": {
                "food": food_pricing_basis,
                "activities": activities_pricing_basis,
                "accommodation": "assumed_tier",
                "transportation": "assumed_tier",
                "miscellaneous": "configured_rate",
            },
            "assumptions": {
                "food_per_day": tier["food_per_day"],
                "activities_per_day": tier["activities_per_day"],
                "transport_per_day": tier["transport_per_day"],
                "hotel_per_night": tier["hotel_per_night"],
                "hotel_nights": hotel_nights,
                "miscellaneous_per_day": settings.budget_miscellaneous_per_day,
            }}
