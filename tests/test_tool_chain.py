from tool_chain import plan_trip


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
