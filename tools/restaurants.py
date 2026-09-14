from typing import Any
from .common import geoapify_places, load, require_destination
from config import settings


GENERIC_FOOD_REQUESTS = {
    "food", "good food", "great food", "best food", "good restaurants",
    "best restaurants", "varied cuisine", "variety", "where should i eat",
}


def _normalize_cuisine(cuisine: str | None) -> str | None:
    if not cuisine:
        return None
    normalized = cuisine.strip().lower()
    if normalized in GENERIC_FOOD_REQUESTS:
        return None
    return cuisine.strip() or None


def _cuisine_from_properties(properties: dict[str, Any]) -> str:
    for key in ("catering cuisine", "catering.cuisine", "cuisine"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            cuisines = [str(item).strip() for item in value if str(item).strip()]
            if cuisines:
                return ", ".join(cuisines)
    return ""


def search_restaurants(destination: str, cuisine: str | None = None,
                       price_range: str | None = None, meal_type: str | None = None,
                       dietary_preferences: list[str] | None = None) -> dict[str, Any]:
    destination = require_destination(destination)
    cuisine = _normalize_cuisine(cuisine)
    valid_prices = {"budget", "moderate", "premium"}
    if price_range and price_range.lower() not in valid_prices:
        raise ValueError(f"price_range must be one of {sorted(valid_prices)}")
    if settings.travel_data_source.lower() != "local":
        elements = geoapify_places(destination, "catering.restaurant")
        rows = []
        unverified_rows = []
        for item in elements[:40]:
            props = item.get("properties", {})
            name = props.get("name")
            tagged_cuisine = _cuisine_from_properties(props)
            if not name:
                continue
            row = {"destination": destination, "name": name,
                   "cuisine": tagged_cuisine or None,
                   "price_range": price_range or "unknown",
                   "meal_types": ["lunch", "dinner"], "dietary": [],
                   "estimated_cost": None, "neighborhood": props.get("street", destination),
                   "match_status": "verified" if tagged_cuisine else "unverified"}
            if not cuisine:
                rows.append(row)
            elif tagged_cuisine and cuisine.lower() in tagged_cuisine.lower():
                rows.append(row)
            elif not tagged_cuisine:
                unverified_rows.append(row)
        note = None
        if cuisine and not rows:
            note = f"No restaurants were verified as {cuisine} by the data provider."
        result = {"destination": destination, "restaurants": rows, "count": len(rows)}
        if note:
            result["note"] = note
        if cuisine and unverified_rows:
            result["nearby_unverified"] = unverified_rows
        return result
    dietary = {item.lower() for item in (dietary_preferences or [])}
    rows = [row for row in load("restaurants.json")
            if row["destination"].lower() == destination.lower()
            and (not cuisine or row["cuisine"].lower() == cuisine.lower())
            and (not price_range or row["price_range"].lower() == price_range.lower())
            and (not meal_type or meal_type.lower() in [m.lower() for m in row["meal_types"]])
            and (not dietary or dietary.intersection(map(str.lower, row["dietary"])))]
    return {"destination": destination, "restaurants": rows, "count": len(rows)}
