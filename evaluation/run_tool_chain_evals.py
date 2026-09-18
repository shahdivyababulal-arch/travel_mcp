"""Fixture-backed checks that the five tools compose into a grounded plan.

Not end-to-end despite the name it used to carry: there is no model and no
MCP round trip here. The agent's golden and trajectory evals cover those.
"""
import os

os.environ["TRAVEL_DATA_SOURCE"] = "local"

from tool_chain import plan_trip


def run() -> int:
    result = plan_trip(
        "New York", 3, ["museums", "walking"], "Italian", 1000, include_weather=True
    )
    itinerary = result["itinerary"]
    budget = result["budget"]
    checks = {
        "three itinerary days": len(itinerary["days"]) == 3,
        "three weather rows": len(result["weather"]["weather"]) == 3,
        "budget is calculated": budget is not None and budget["total_estimated_cost"] == 870,
        "budget is respected": budget is not None and budget["within_budget"],
        "itinerary uses returned attractions": all(
            day["schedule"][0]["activity"]
            in {item["name"] for item in result["attractions"]["attractions"]}
            for day in itinerary["days"]
        ),
        "restaurant costs are grounded": all(
            isinstance(item["estimated_cost"], (int, float))
            for item in result["restaurants"]["restaurants"]
        ),
    }
    passed = sum(checks.values())
    for name, ok in checks.items():
        print(f"- {name}: {'PASS' if ok else 'FAIL'}")
    print(f"Result: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(run())
