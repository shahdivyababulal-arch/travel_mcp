import pytest

from server import mcp
from tools.attractions import search_attractions
from tools.budget import calculate_budget
from tools.itinerary import create_itinerary
from tools.restaurants import search_restaurants
from tools.weather import get_weather


def test_attractions_filter_by_interest():
    result = search_attractions("New York", 3, ["museums"])
    assert result["count"] == 2
    assert all(item["category"] == "museum" for item in result["attractions"])


def test_attractions_validate_days():
    with pytest.raises(ValueError):
        search_attractions("New York", 0)


def test_weather_has_requested_days():
    result = get_weather("New York", 3)
    assert len(result["weather"]) == 3
    assert "precipitation_probability" in result["weather"][0]


def test_weather_honors_requested_dates():
    result = get_weather("New York", 2, ["2025-01-10", "2025-01-11"])
    assert [item["date"] for item in result["weather"]] == ["2025-01-10", "2025-01-11"]


def test_weather_rejects_unordered_dates():
    with pytest.raises(ValueError):
        get_weather("New York", 2, ["2025-01-11", "2025-01-10"])


def test_restaurants_filter_cuisine_and_price():
    result = search_restaurants("New York", cuisine="Italian", price_range="budget")
    assert [item["name"] for item in result["restaurants"]] == ["Mercato"]


def test_budget_compares_against_limit():
    result = calculate_budget("New York", 2, budget=600)
    assert result["total_estimated_cost"] > 0
    assert result["within_budget"] is True


def test_budget_uses_returned_item_costs():
    result = calculate_budget(
        "New York",
        2,
        attractions=[{"estimated_cost": 30}, {"estimated_cost": 10}],
        restaurants=[{"estimated_cost": 20}, {"estimated_cost": 40}],
    )
    assert result["estimates"]["activities"] == 40
    assert result["estimates"]["food"] == 180


def test_budget_normalizes_natural_language_travel_style():
    result = calculate_budget("Boston", 3, travel_style="comfortable")
    assert result["travel_style"] == "moderate"
    assert result["assumptions"]["hotel_per_night"] == 180


def test_itinerary_is_day_by_day():
    result = create_itinerary("New York", 2, [{"name": "Museum", "estimated_cost": 10}],
                               [{"name": "Cafe", "estimated_cost": 20}])
    assert len(result["days"]) == 2
    assert result["days"][0]["schedule"][0]["activity"] == "Museum"


def test_server_registers_five_tools():
    names = set(mcp._tool_manager._tools)
    assert names == {"search_attractions", "get_weather", "search_restaurants",
                     "calculate_budget", "create_itinerary"}
