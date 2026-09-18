"""Entrypoint for the travel MCP server.

    python main.py                        # Streamable HTTP on settings.mcp_host:mcp_port
    python main.py --transport stdio      # for MCP clients that spawn a subprocess

Startup lives here rather than in server.py so that importing the app has no
side effects -- tests and MCP Inspector can import `server.mcp` without
configuring logging or installing a tracer provider.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the travel MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"),
                        default="streamable-http")
    parser.add_argument("--host", default=None,
                        help="override the configured bind address")
    parser.add_argument("--port", type=int, default=None,
                        help="override the configured port")
    args = parser.parse_args(argv)

    from config import settings
    from observability import configure_logging, configure_tracing

    configure_logging(settings.log_level)
    configure_tracing(settings.otel_service_name)

    from server import mcp

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return 0

    import uvicorn

    from observability import wrap_asgi_app

    # Wrap from the outside: StarletteInstrumentor.instrument_app() injects
    # into Starlette's middleware stack and breaks MCP session routing.
    uvicorn.run(
        wrap_asgi_app(mcp.streamable_http_app()),
        host=args.host or settings.mcp_host,
        port=args.port or settings.mcp_port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
