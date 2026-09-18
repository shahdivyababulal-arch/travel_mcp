# travel-mcp

MCP tool server for the travel planner. Exposes five tools over Streamable
HTTP: `search_attractions`, `search_restaurants`, `get_weather`,
`calculate_budget`, `create_itinerary`.

Consumed by [`travel_agent`](../travel_agent) through ADK's `McpToolset`. This
repository has no dependency on the agent, on ADK, or on any model SDK -- it
answers tool calls and nothing else.

## Layout

| Path | What it is |
|---|---|
| `main.py` | Process entrypoint: logging, tracing, transport selection |
| `server.py` | FastMCP app and tool registrations (import-safe, no side effects) |
| `tools/` | The tool implementations |
| `data/` | JSON fixtures used when `TRAVEL_DATA_SOURCE=local` |
| `config.py` | Loads `server.yaml`; env vars override every value |
| `observability.py` | JSON logging and OpenTelemetry bootstrap |

## Running locally

```bash
uv sync
uv run python main.py
```

Serves Streamable HTTP on `http://127.0.0.1:8001/mcp`. Set
`TRAVEL_DATA_SOURCE=local` to use the bundled fixtures instead of live
Geoapify and Open-Meteo lookups; `real` needs `GEOAPIFY_API_KEY`.

For a client that spawns the server as a subprocess:

```bash
uv run python main.py --transport stdio
```

## Inspecting the tools

See [docs/INSPECTOR.md](docs/INSPECTOR.md) for driving the server with MCP
Inspector, which is the fastest way to check a tool's JSON Schema after
changing its signature.

## Deployment

Deploys to Cloud Run as a private service; only the travel agent's runtime
service account holds `roles/run.invoker` on it. The agent authenticates with
a Google-signed ID token whose audience is this service's URL.

Provisioning and deploy scripts live in
[`travel_agent/scripts`](../travel_agent/scripts).
