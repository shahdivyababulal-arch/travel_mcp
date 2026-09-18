from tools.attractions import search_attractions
from tools.budget import calculate_budget


def test_local_mcp_tool_chain_returns_grounded_data():
    attractions = search_attractions("New York", 2, ["museums"])
    costs = sum(item["estimated_cost"] for item in attractions["attractions"])
    budget = calculate_budget("New York", 2, 1000, costs)
    assert budget["estimates"]["activities"] == costs
