# CLAUDE.md

Fork of microsoft/magentic-ui (MagenticLite 0.2.x). This fork adds Claude Code orchestration of the Fara browser agent through `fara_mcp.py`, and a backend relay for the live browser view (noVNC) so the UI works behind a tunnel. `DESIGN.md` is the source of truth for the flow, the backend protocol, environment facts and the Fara capability profile. Update it when any of those change.

## Layout

- `fara_mcp.py` — the MCP server this fork adds (PEP 723 script, run with `uv run --script`).
- Upstream code under `src/`, `frontend/` and `docs/` is unchanged except for the noVNC relay: `src/magentic_ui/backend/web/routes/ws.py` (`/api/ws/novnc/{port}`), `frontend/src/lib/utils.ts` (`buildNovncUrl`) and `frontend/src/components/browser/BrowserViewer.tsx` (`wsProtocols`). Keep further changes out of upstream code unless unavoidable, so rebasing stays easy.
- `.venv` — the fork installed editable (`uv sync`). The frontend is built into `src/magentic_ui/backend/web/ui/` (gitignored) with `cd frontend && pnpm install --frozen-lockfile && pnpm build`; rebuild after frontend changes.
- `config.yaml` (gitignored) — `web_surfer` → llama.cpp `:8001` (Fara1.5-4B), `agent_mode: websurfer_only`.
- `runs/fara.jsonl` (gitignored) — one line per finished Fara task, appended by `fara_mcp.py`.

## Running

1. llama.cpp serving Fara on `:8001` (`curl -s localhost:8001/v1/models`).
2. MagenticLite backend from this checkout, kept running in its own terminal: `.venv/bin/magentic-ui --port 8081 --config config.yaml`. Restart it after backend or frontend changes.
3. Claude Code in this directory. Add `--dangerously-load-development-channels server:fara` so Fara's results arrive as `<channel source="fara">` events instead of having to be polled.

Remote access: `cloudflared tunnel --url http://localhost:8081 --http-host-header localhost` (without the Host override the backend answers 400). The tunnel URL grants full control, since the page carries the session token.

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
