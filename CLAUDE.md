# CLAUDE.md

Fork of microsoft/magentic-ui (MagenticLite 0.2.x). This fork adds one thing: Claude Code orchestrates the Fara browser agent through `fara_mcp.py`. `DESIGN.md` is the source of truth for the flow, the backend protocol, environment facts and the Fara capability profile. Update it when any of those change.

## Layout

- `fara_mcp.py` — the MCP server this fork adds (PEP 723 script, run with `uv run --script`). The upstream code under `src/`, `frontend/` and `docs/` is unchanged. Keep it that way unless a change is unavoidable, so rebasing on upstream stays easy.
- `config.yaml` (gitignored) — `web_surfer` → llama.cpp `:8001` (Fara1.5-4B), `agent_mode: websurfer_only`.
- `runs/fara.jsonl` (gitignored) — one line per finished Fara task, appended by `fara_mcp.py`.

## Running

1. llama.cpp serving Fara on `:8001` (`curl -s localhost:8001/v1/models`).
2. MagenticLite backend, kept running in its own terminal: `magentic-ui --port 8081 --config config.yaml`.
3. Claude Code in this directory. Add `--dangerously-load-development-channels server:fara` so Fara's results arrive as `<channel source="fara">` events instead of having to be polled.

The MCP server is registered with local scope: `claude mcp add fara -- uv run --script $PWD/fara_mcp.py`.

## Using Fara

- A click on a github.com/trending repo link once hung the backend for 6+ minutes (llama.cpp idle); giving the repo URL directly worked.
- Use `session_id` for follow-ups that need the same browser state.
- If Fara asks a question at a critical point (login, purchase, submit), relay it to the user and send their answer with `fara_respond`. Never answer it on the user's behalf.
- Claude receives Fara's step trace and answer only (no screenshots).
- Parallel sessions share llama.cpp's single slot, so they queue at the model.

## Working on fara_mcp.py

- Use the latest package versions, with no upper bounds. Port code to new major APIs instead of pinning (mcp 2.x: `mcp.server.mcpserver.MCPServer`).
- Channel push uses two private SDK attributes (`mcp._lowlevel_server`, `ctx.session._connection.outbound`). Re-check both after upgrading `mcp`.
- Verify changes end to end against the running backend with a stdio client in a scratch directory (start a task, check the status/push and the log line). There are no unit tests for `fara_mcp.py`.
- Upstream checks for `src/`: `poe check` (ruff format, ruff lint, pyright, pytest).
