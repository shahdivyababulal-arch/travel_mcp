from types import SimpleNamespace
from unittest.mock import patch

from tools.restaurants import search_restaurants


def test_live_restaurant_filter_prefers_cuisine_metadata():
    live_settings = SimpleNamespace(travel_data_source="real")
    with patch("tools.restaurants.settings", live_settings), \
            patch("tools.restaurants.geoapify_places", return_value=[
        {"properties": {"name": "Unknown Cafe", "street": "Main Street"}},
        {"properties": {"name": "Italian Bistro", "cuisine": "Italian"}},
    ]):
        result = search_restaurants("New York", cuisine="Italian")
    assert [item["name"] for item in result["restaurants"]] == ["Italian Bistro"]
    assert result["restaurants"][0]["estimated_cost"] is None
    assert result["restaurants"][0]["match_status"] == "verified"


def test_live_restaurant_filter_falls_back_when_metadata_is_missing():
    live_settings = SimpleNamespace(travel_data_source="real")
    with patch("tools.restaurants.settings", live_settings), \
            patch("tools.restaurants.geoapify_places", return_value=[
        {"properties": {"name": "Unknown Cafe", "street": "Main Street"}},
    ]):
        result = search_restaurants("Boston", cuisine="Italian")
    assert result["restaurants"] == []
    assert result["nearby_unverified"][0]["cuisine"] is None
    assert result["nearby_unverified"][0]["match_status"] == "unverified"
    assert "No restaurants were verified" in result["note"]


def test_generic_food_request_is_not_treated_as_cuisine_filter():
    local_settings = SimpleNamespace(travel_data_source="local")
    with patch("tools.restaurants.settings", local_settings):
        result = search_restaurants("New York", cuisine="good food")
    assert result["count"] == 4
