from typing import Any
from .common import geoapify_places, load, require_destination
from config import settings


INTEREST_CATEGORIES = {
    "museum": "entertainment.museum",
    "museums": "entertainment.museum",
    "art": "entertainment.culture",
    "culture": "entertainment.culture",
    "history": "entertainment.culture",
    "walking": "tourism.sights",
    "landmarks": "tourism.sights",
    "landmark": "tourism.sights",
    "outdoors": "leisure.park",
    "parks": "leisure.park",
    "park": "leisure.park",
}


def _categories_for_interests(interests: list[str] | None) -> tuple[str, set[str]]:
    wanted = {item.strip().lower() for item in (interests or []) if item.strip()}
    categories = {INTEREST_CATEGORIES[item] for item in wanted if item in INTEREST_CATEGORIES}
    if not categories:
        categories = {"entertainment.museum", "entertainment.culture",
                      "tourism.sights", "leisure.park"}
    return ",".join(sorted(categories)), wanted


def search_attractions(destination: str, number_of_days: int = 1,
                       interests: list[str] | None = None,
                       activity_type: str | None = None) -> dict[str, Any]:
    destination = require_destination(destination)
    if number_of_days < 1 or number_of_days > 30:
        raise ValueError("number_of_days must be between 1 and 30")
    if settings.travel_data_source.lower() != "local":
        categories_query, wanted = _categories_for_interests(interests)
        elements = geoapify_places(destination, categories_query)
        rows = []
        for item in elements[:30]:
            props = item.get("properties", {})
            categories = props.get("categories", [])
            matched_category = next(
                (category for category in categories
                 if category in categories_query.split(",")),
                categories[-1] if categories else "attraction",
            )
            category = matched_category.split(".")[-1]
            name = props.get("name")
            searchable = f"{name} {' '.join(categories)}".lower()
            if not name or (wanted and not any(
                    word in searchable or word.rstrip("s") in searchable for word in wanted)):
                continue
            rows.append({"destination": destination, "name": name,
                         "description": f"{category.title()} in {destination}",
                         "category": category, "interests": [category],
                         "estimated_cost": None, "duration_hours": 2,
                         "location": props.get("formatted") or props.get("street", destination)})
        return {"destination": destination, "attractions": rows, "count": len(rows)}
    wanted = {item.lower() for item in (interests or [])}
    rows = [row for row in load("attractions.json")
            if row["destination"].lower() == destination.lower()
            and (not wanted or wanted.intersection(map(str.lower, row["interests"])))
            and (not activity_type or row["category"].lower() == activity_type.lower())]
    return {"destination": destination, "attractions": rows, "count": len(rows)}
