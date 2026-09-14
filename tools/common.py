import json
import logging
import time
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import settings
from observability.span_data import summarize

DATA_DIR = Path(__file__).parent.parent / "data"


def load(name: str) -> list[dict[str, Any]]:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def require_destination(destination: str) -> str:
    value = destination.strip()
    if not value:
        raise ValueError("destination is required")
    return value


def get_json(url: str, params: dict[str, Any]) -> Any:
    logger = logging.getLogger("travel.api")
    started = time.perf_counter()
    safe_params = {key: "[redacted]" if "key" in key.lower() or "token" in key.lower()
                   else value for key, value in params.items()}
    request = Request(
        f"{url}?{urlencode(params, doseq=True)}",
        headers={"User-Agent": settings.http_user_agent, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            try:
                result = json.load(response)
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "api_response_received",
                    extra={"fields": {
                        "provider": request.host,
                        "endpoint": url,
                        "status_code": response.status,
                        "duration_ms": duration_ms,
                        "request_params": safe_params,
                        "response": summarize(result),
                    }},
                )
                try:
                    from opentelemetry import trace
                    span = trace.get_current_span()
                    span.set_attribute("api.provider", request.host)
                    span.set_attribute("api.endpoint", url)
                    span.set_attribute("api.status_code", response.status)
                    span.set_attribute("api.duration_ms", duration_ms)
                    span.set_attribute("api.response", summarize(result))
                except ImportError:
                    pass
                return result
            except JSONDecodeError as error:
                raise RuntimeError(
                    f"public data service returned invalid JSON for {url}"
                ) from error
    except (HTTPError, URLError, TimeoutError) as error:
        logger.error(
            "api_request_failed",
            extra={"fields": {
                "provider": request.host,
                "endpoint": url,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "request_params": safe_params,
                "error_type": type(error).__name__,
                "error": str(error),
            }},
        )
        raise RuntimeError(f"public data service unavailable: {error}") from error


def geocode(destination: str) -> tuple[float, float]:
    if not settings.geoapify_api_key:
        raise RuntimeError("GEOAPIFY_API_KEY is required when TRAVEL_DATA_SOURCE=real")
    result = get_json("https://api.geoapify.com/v1/geocode/search", {
        "text": destination, "limit": 1, "type": "city",
        "apiKey": settings.geoapify_api_key,
    })
    features = result.get("features", [])
    if not features:
        raise ValueError(f"destination not found: {destination}")
    coordinates = features[0]["geometry"]["coordinates"]
    return float(coordinates[1]), float(coordinates[0])


def geoapify_places(destination: str, categories: str, limit: int = 20) -> list[dict[str, Any]]:
    latitude, longitude = geocode(destination)
    result = get_json("https://api.geoapify.com/v2/places", {
        "categories": categories,
        "filter": f"circle:{longitude},{latitude},15000",
        "bias": f"proximity:{longitude},{latitude}",
        "limit": limit,
        "apiKey": settings.geoapify_api_key,
    })
    return result.get("features", [])
