"""Load server.yaml and expose it as `settings`.

Mirrors the agent repos' config module deliberately: one declarative file per
service, environment variables override any configured value so Cloud Run can
supply deploy-time values without a second config source.

This server no longer shares a config module with the travel agent. That
coupling is what kept the MCP server pinned to the agent's dependency set --
it imported `config`, which imports the agent's whole settings surface. The
settings here are only the ones the tools actually read.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG_FILE = "server.yaml"


def _parse(text: str, origin: str) -> dict[str, Any]:
    """Parse YAML or JSON by extension.

    safe_load is used deliberately -- plain load would construct arbitrary
    objects from config. JSON is still accepted so an override can be either.
    """
    if origin.endswith((".yaml", ".yml")):
        import yaml

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{origin} must contain a mapping at the top level")
    return data


def _load_from_gcs(uri: str) -> dict[str, Any]:
    """Read a config object from gs://bucket/object.

    Raises rather than falling back to defaults: an unreadable bucket would
    otherwise start the server on local defaults and fail later in a way that
    looks like a tool bug rather than a config problem.
    """
    from google.cloud import storage  # imported lazily; only needed for gs://

    bucket_name, _, blob_name = uri[len("gs://"):].partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"malformed GCS config URI: {uri}")
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise FileNotFoundError(f"config object not found: {uri}")
    return _parse(blob.download_as_text(), uri)


def load_config() -> dict[str, Any]:
    location = os.getenv("MCP_CONFIG_PATH", DEFAULT_CONFIG_FILE)
    if location.startswith("gs://"):
        return _load_from_gcs(location)
    path = Path(location)
    if not path.is_absolute():
        # Resolve against this file, not the cwd, so the server works no
        # matter which directory it is launched from.
        path = Path(__file__).resolve().parent / path
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    return _parse(path.read_text(encoding="utf-8"), path.name)


CONFIG = load_config()


def value(section: str, key: str, env_var: str, default: Any) -> Any:
    """Resolve a setting: environment variable, then config, then default."""
    section_data = CONFIG.get(section, {})
    configured = section_data.get(key) if isinstance(section_data, dict) else None
    return os.getenv(env_var, configured if configured is not None else default)


def _top(key: str, env_var: str, default: Any) -> Any:
    configured = CONFIG.get(key)
    return os.getenv(env_var, configured if configured is not None else default)


@dataclass(frozen=True)
class Settings:
    # Identity
    name: str = str(_top("name", "MCP_NAME", "local-travel-tools"))

    # Bind address. Defaults to loopback so a local run is not exposed; the
    # container overrides MCP_HOST to 0.0.0.0 because Cloud Run routes to the
    # published port from outside the container's network namespace.
    mcp_host: str = str(value("server", "host", "MCP_HOST", "127.0.0.1"))
    mcp_port: int = int(value("server", "port", "MCP_PORT", 8001))

    # Logging and data
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/travel-mcp.jsonl")
    travel_data_source: str = str(value("data", "travel_data_source",
                                        "TRAVEL_DATA_SOURCE", "real"))
    http_user_agent: str = os.getenv(
        "HTTP_USER_AGENT", "local-travel-mcp/1.0 (local development)")
    geoapify_api_key: str = os.getenv("GEOAPIFY_API_KEY", "")

    # Observability
    otel_enabled: bool = str(_top("otel_enabled", "OTEL_ENABLED", "true")).lower() in {"1", "true", "yes"}
    otel_service_name: str = str(value("observability", "service_name",
                                       "OTEL_SERVICE_NAME", "travel-mcp"))
    otel_exporter_otlp_endpoint: str = str(value(
        "observability", "otlp_endpoint",
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"))

    # Budget fallback, used when providers return no prices. The per-tier
    # estimates live in tools/budget.py as constants; only this one is
    # configurable, because it is the one with no market rate to look up.
    budget_miscellaneous_per_day: float = float(value(
        "budget", "miscellaneous_per_day", "BUDGET_MISCELLANEOUS_PER_DAY", 15))


settings = Settings()
