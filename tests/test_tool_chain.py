"""The five tools composed into one plan.

Absorbs what used to be `evaluation/run_tool_chain_evals.py`. That script
asserted the same things with its own PASS/FAIL printing and exit code, and
needed its own CI step; as tests they run in the suite CI already executes.
"""

from tests.tool_chain import plan_trip


def test_full_trip_orchestration():
    result = plan_trip("New York", 3, ["museums", "walking"], "Italian", 1000, True)
    assert len(result["itinerary"]["days"]) == 3
    assert result["restaurants"]["count"] > 0
    assert len(result["weather"]["weather"]) == 3


def test_attraction_only_does_not_call_unneeded_data():
    result = plan_trip("New York", 1, ["museums"])
    assert result["restaurants"]["restaurants"] == []
    assert result["weather"]["weather"] == []
    assert result["budget"] is None


def test_budget_is_calculated_and_respected():
    """The exact total pins the fixtures and the tier arithmetic together."""
    result = plan_trip("New York", 3, ["museums", "walking"], "Italian", 1000,
                       include_weather=True)
    budget = result["budget"]
    assert budget is not None
    assert budget["total_estimated_cost"] == 870
    assert budget["within_budget"] is True


def test_the_itinerary_only_schedules_attractions_the_tools_returned():
    """The grounding invariant: no day may feature an invented venue."""
    result = plan_trip("New York", 3, ["museums", "walking"], "Italian", 1000,
                       include_weather=True)
    returned = {item["name"] for item in result["attractions"]["attractions"]}
    for day in result["itinerary"]["days"]:
        assert day["schedule"][0]["activity"] in returned


def test_restaurant_costs_are_grounded():
    result = plan_trip("New York", 3, ["museums", "walking"], "Italian", 1000,
                       include_weather=True)
    for item in result["restaurants"]["restaurants"]:
        assert isinstance(item["estimated_cost"], (int, float))
