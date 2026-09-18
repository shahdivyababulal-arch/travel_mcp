"""Deterministic checks for MCP tool schemas, validation, and failure handling."""
import os
from typing import Callable

os.environ["TRAVEL_DATA_SOURCE"] = "local"

from tools.attractions import search_attractions
from tools.budget import calculate_budget
from tools.itinerary import create_itinerary
from tools.restaurants import search_restaurants
from tools.weather import get_weather


def _check(name: str, assertion: Callable[[], None]) -> tuple[str, bool, str]:
    try:
        assertion()
    except Exception as error:
        return name, False, str(error)
    return name, True, ""


def run() -> int:
    checks = [
        ("attractions_schema", lambda: _assert_attractions()),
        ("weather_schema", lambda: _assert_weather()),
        ("restaurants_schema", lambda: _assert_restaurants()),
        ("budget_math", lambda: _assert_budget()),
        ("itinerary_missing_cost", lambda: _assert_itinerary_missing_cost()),
        ("invalid_days_rejected", lambda: _assert_invalid_days()),
    ]
    passed = 0
    for name, ok, error in (_check(*check) for check in checks):
        print(f"- {name}: {'PASS' if ok else 'FAIL'}{f' ({error})' if error else ''}")
        passed += ok
    print(f"Result: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


def _assert_attractions() -> None:
    result = search_attractions("New York", 2, ["museums"])
    assert isinstance(result["attractions"], list)
    assert all({"name", "category", "estimated_cost"} <= item.keys()
               for item in result["attractions"])


def _assert_weather() -> None:
    result = get_weather("New York", 2)
    assert len(result["weather"]) == 2
    assert {"date", "condition"} <= result["weather"][0].keys()


def _assert_restaurants() -> None:
    result = search_restaurants("New York", cuisine="Italian")
    assert isinstance(result["restaurants"], list)
    assert all(item["cuisine"].lower() == "italian" for item in result["restaurants"])


def _assert_budget() -> None:
    result = calculate_budget("New York", 2, 500, activities_cost=10)
    assert result["total_estimated_cost"] == 480
    assert result["remaining"] == 20


def _assert_itinerary_missing_cost() -> None:
    result = create_itinerary("New York", 1, [{"name": "Museum"}], [{"name": "Cafe"}])
    assert result["days"][0]["schedule"][1]["estimated_cost"] == 25


def _assert_invalid_days() -> None:
    try:
        get_weather("New York", 0)
    except ValueError:
        return
    raise AssertionError("invalid number_of_days was accepted")


if __name__ == "__main__":
    raise SystemExit(run())
