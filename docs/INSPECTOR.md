# MCP Inspector

Interactive debugging for the travel MCP server. Complements
`evaluation/run_mcp_evals.py`: that suite is the automated regression gate,
Inspector is the human-driven exploration tool. Requires Node (`npx`).

Two server profiles are defined in `inspector.json`:

| Profile | Transport | Data | Use for |
| --- | --- | --- | --- |
| `travel-mcp-http` | Streamable HTTP -> `:8001` | whatever the running server uses | Default. The exact transport and process ADK talks to. |
| `travel-mcp-stdio-fixtures` | stdio (spawned) | bundled fixtures | Isolated runs on deterministic data without touching `:8001`. |

`travel-mcp-http` attaches to the already-running server, so start it first:

```powershell
python main.py mcp
```

`TRAVEL_DATA_SOURCE` is read by the **server** process, not by Inspector. To
inspect fixture behaviour either restart `:8001` in local mode or use the stdio
profile, which sets it for the process it spawns.

## UI mode

```powershell
npx @modelcontextprotocol/inspector --config mcp_server\inspector.json --server travel-mcp-http
```

Binds UI on `6274` and proxy on `6277`. Recent versions print a
pre-authenticated URL containing a session token -- open that link rather than
a bare `localhost:6274`, and do not set `DANGEROUSLY_OMIT_AUTH`.

Because the server wraps its ASGI app with `OpenTelemetryMiddleware`, calls made
from Inspector emit spans and appear in Cloud Trace under
`travel-mcp-server`.

## CLI mode

Scriptable, no browser. List tools:

```powershell
npx @modelcontextprotocol/inspector --cli --config mcp_server\inspector.json --server travel-mcp-http --method tools/list
```

Call one tool:

```powershell
npx @modelcontextprotocol/inspector --cli --config mcp_server\inspector.json --server travel-mcp-http --method tools/call --tool-name calculate_budget --tool-arg destination="New York" --tool-arg number_of_days=2 --tool-arg budget=3000 --tool-arg travel_style=luxury
```

Each `--tool-arg` is a separate `key=value`. The response includes `isError`,
which is what distinguishes a tool failure from an empty result.

## What it is useful for here

* **Reading the schema the model actually receives.** `tools/list` returns the
  JSON Schema FastMCP generated from the type hints -- the same text the LLM
  sees. Missing constraints and enums show up immediately.
* **Seeing what a failure looks like to the model.** Call a tool with arguments
  that raise and read the raw error payload. A vague message here is a
  server-side cause of ungrounded agent answers.
* **Reproducing eval failures without LLM cost.** ADK live evals are slow,
  nondeterministic, and billed; Inspector reproduces the tool-level half of a
  failure in one deterministic call.

Once a defect is understood here, encode it as an assertion in
`evaluation/run_mcp_evals.py` so it stays fixed.
