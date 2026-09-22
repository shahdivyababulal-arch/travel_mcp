"""Structured logging and OpenTelemetry bootstrap for the travel MCP server.

One file rather than a package: this is the subset of the travel agent's
observability that a tool server actually needs. The agent's ADK plugin and
groundedness heuristic score *model output*, which this process never sees, so
carrying them here would have meant importing google-adk into a server whose
only job is to answer tool calls.

Context propagation is inbound-only here. `wrap_asgi_app` extracts the W3C
`traceparent` the agent's MCP client injects, so tool spans join the caller's
trace instead of starting their own. There is no outbound httpx instrumentation
because the provider calls in tools/common.py go through urllib and set their
own span attributes.

Cloud Trace is the only export backend. Set `OTEL_ENABLED=false` to run with
tracing off; there is no second backend to select between.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from config import settings

_SPAN_ATTRIBUTE_LIMIT = 4000


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        try:
            from opentelemetry import trace
            context = trace.get_current_span().get_span_context()
            if context.is_valid:
                payload["otel_trace_id"] = format(context.trace_id, "032x")
                payload["otel_span_id"] = format(context.span_id, "016x")
        except ImportError:
            pass
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    # MCP stdio reserves stdout exclusively for JSON-RPC messages.
    formatter = JsonFormatter()
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    for existing_handler in root.handlers:
        existing_handler.close()
    root.handlers.clear()
    root.addHandler(stderr_handler)
    root.addHandler(file_handler)
    root.setLevel(level.upper())


def event(logger: logging.Logger, name: str, **fields: Any) -> None:
    logger.info(name, extra={"fields": fields})


def wrap_asgi_app(app: Any) -> Any:
    """Wrap an already-built ASGI app (FastMCP's) for trace extraction.

    Wraps from the outside instead of using StarletteInstrumentor.
    instrument_app(), which injects into Starlette's middleware stack and
    breaks MCP streamable-HTTP session routing (POST /mcp -> 404). Wrapping
    externally leaves Starlette's own stack untouched.
    """
    if not settings.otel_enabled:
        return app
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    return OpenTelemetryMiddleware(app, exclude_spans=["send", "receive"])


def configure_tracing(service_name: str | None = None) -> None:
    """Export this server's spans to Cloud Trace.

    Requires application default credentials: in Cloud Run that is the
    runtime service account, and locally `gcloud auth application-default
    login`. Without them, run with `OTEL_ENABLED=false`.
    """
    if not settings.otel_enabled:
        return

    import os

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Sampling must be parent-based so the entry agent's decision propagates to
    # every downstream service; independent samplers produce half-traces.
    os.environ.setdefault("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
    os.environ.setdefault("OTEL_TRACES_SAMPLER_ARG", "1.0")

    # Unlike the agents, nothing installs a provider before this runs -- there
    # is no ADK here -- so there is no existing one to merge into.
    provider = TracerProvider(resource=Resource.create({
        "service.name": service_name or settings.otel_service_name,
    }))
    # Tracing must never prevent the service from starting. The Cloud Trace
    # exporter resolves application default credentials in its constructor, so
    # on a machine without ADC -- a CI runner, a developer who has not run
    # `gcloud auth application-default login` -- this raises
    # DefaultCredentialsError. The OTLP exporter it replaced constructed
    # happily and only failed later, at export time, so losing traces used to
    # be survivable and is again.
    try:
        exporter = CloudTraceSpanExporter()
    except Exception as error:
        logging.getLogger(__name__).warning(
            "tracing disabled: cannot create the Cloud Trace exporter (%s: %s). "
            "Run `gcloud auth application-default login`, or set "
            "OTEL_ENABLED=false to silence this.",
            type(error).__name__, error)
        return

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def summarize(value: Any, limit: int = _SPAN_ATTRIBUTE_LIMIT) -> str:
    """Serialize tool data without allowing large payloads into telemetry.

    Bounded because span attributes are not a data store: an unbounded tool
    result bloats every trace and can be dropped by the exporter.
    """
    serialized = json.dumps(value, default=str, sort_keys=True)
    if len(serialized) <= limit:
        return serialized
    return serialized[:limit] + "... [truncated]"
