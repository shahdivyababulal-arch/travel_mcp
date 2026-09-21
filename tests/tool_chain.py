"""Deterministic composition of the five tools, used for testing.

This is `plan_trip`, moved here from the travel agent. It mirrors the
tool-selection policy the model is prompted to follow -- gather attractions,
optionally restaurants and weather, price it, then schedule it -- and calls
the tool functions directly, with no model and no MCP round trip.

It lives under tests/ because testing is all it is for -- nothing the server
serves imports it. It came across from the travel agent with the tools,
since every line of it is tool code.

What it is good for: proving the tools compose into a coherent itinerary
with grounded costs, fast and offline. What it is not: an end-to-end test.
The model's actual tool choices are covered by the agent's golden and
trajectory evals, which do run the model.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.attractions import search_attractions
from tools.budget import calculate_budget
from tools.itinerary import create_itinerary
from tools.restaurants import search_restaurants
from tools.weather import get_weather

logger = logging.getLogger("travel.tool_chain")


def plan_trip(destination: str, number_of_days: int, interests: list[str] | None = None,
              cuisine: str | None = None, budget: float | None = None,
              include_weather: bool = False, travel_style: str = "moderate") -> dict[str, Any]:
    """Run the full tool chain and return every intermediate result."""
    interests = interests or []
    logger.info("tool_chain_started", extra={"fields": {
        "destination": destination, "number_of_days": number_of_days}})
    attractions = search_attractions(destination, number_of_days, interests)
    restaurants = search_restaurants(destination, cuisine=cuisine) if cuisine else {"restaurants": []}
    weather = get_weather(destination, number_of_days) if include_weather else {"weather": []}
    activity_cost = sum(
        item["estimated_cost"] for item in attractions["attractions"]
        if isinstance(item.get("estimated_cost"), (int, float))
    )
    budget_result = calculate_budget(
        destination, number_of_days, budget, activity_cost,
        attractions=attractions["attractions"],
        restaurants=restaurants["restaurants"],
        travel_style=travel_style,
    ) if budget is not None else None
    itinerary = create_itinerary(destination, number_of_days, attractions["attractions"],
                                 restaurants["restaurants"], weather["weather"],
                                 budget_result, interests)
    logger.info("tool_chain_completed", extra={"fields": {"destination": destination}})
    return {"attractions": attractions, "restaurants": restaurants, "weather": weather,
            "budget": budget_result, "itinerary": itinerary}
