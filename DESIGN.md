# Claude × Fara — Design

Status 2026-11-17. Claude orchestrates; Fara1.5-4B (local) browses through MagenticLite 0.2.2.

## Flow

```
user ──tasks, approvals──▶ Claude ──task text──▶ fara_mcp.py ──REST + websocket──▶ MagenticLite :8081
                             ▲  │                                                     │ Fara loop
                             │  │                                                     ▼
                             │  │                                    Chromium in Quicksand VM ◀── llama.cpp :8001
                             │  │
                             └──────── answer, status, step trace, Fara's questions ◀────────────────┘
```

1. **Claude manages:** splits work into browser tasks, writes each task for Fara, relays Fara's questions to the user. MagenticLite's own orchestrator is off (`agent_mode: websurfer_only`).
2. **Fara sees and acts:** Fara1.5-4B on llama.cpp `:8001`, driven by MagenticLite's Fara loop: screenshot in, one action out (visit_url, left_click, type, scroll, …) in a sandboxed Chromium inside the Quicksand VM.
3. **Claude receives the trace only:** Fara's step trace and answer; no screenshots or page text.

## Components

- `config.yaml` (gitignored) — `web_surfer` → `http://localhost:8001/v1`, model `./Fara1.5-4B-Q4_K_L.gguf`, `model_info.vision: true`, `agent_mode: websurfer_only`, `sandbox.type: quicksand`.
- `fara_mcp.py` — stdio MCP server (PEP 723 script, `mcp` 2.x `MCPServer`). Talks to the running backend as the web UI does; runs appear in the UI under the default user.
  - `fara_start(task, session_id?)` — new session, or a follow-up in an existing one (same browser state). Returns at once.
  - `fara_status(session_id?, wait_seconds≤300)` — status, steps new since the last call, Fara's pending question, answer. Without id: all sessions.
  - `fara_respond(session_id, response)` — answers a pending question; `approve`/`deny` and `continue`/`stop` map to the structured replies. Refused when no question is pending.
  - `fara_stop(session_id)`.
  - Appends each finished task (task, status, seconds, steps, answer, error) to `runs/fara.jsonl` (gitignored).
  - **Reports back unprompted** (Claude Code channel, research preview): declares `experimental: {"claude/channel": {}}` and sends `notifications/claude/channel` with the fara_status report as `content` and `meta {session_id, status}` when a task ends or Fara asks a question. Claude sees `<channel source="fara" session_id=".." status="..">`. Without the channel flag Claude Code drops these silently and polling with `fara_status` still works.
  - The Python SDK (mcp 2.3) has no public API for this: the capability goes through `mcp._lowlevel_server.create_initialization_options(experimental_capabilities=…)`, and pushes use `ctx.session._connection.outbound`, captured on the first `fara_start`.
- Registered in Claude Code (local scope, `~/.claude.json`): `claude mcp add fara -- uv run --script <repo>/fara_mcp.py`.
- Launch with push enabled (interactive only; custom channels are not on the allowlist): `claude --dangerously-load-development-channels server:fara`.

## Backend protocol (as used)

- REST under `/api`, auth `Authorization: Bearer <token>`; token is per server process, embedded in `index.html` as `window.__MAGUI_TOKEN__` (MCP refetches on 401).
- `POST /api/sessions/ {user_id, name}` → session id; `POST /api/runs/ {session_id, user_id}` → run id (one run per session, reused by follow-ups).
- Websocket `/api/ws/runs/{run_id}`, subprotocols `["magui.auth.bearer", token]`. Send `{"type":"start","task":"{\"content\":…}","settings_config":{}}`, `input_response`, `approval_response`, `continuation_response`, `stop`.
- Receive `system` (status: active / awaiting_input / complete / error / stopped), `input_request`, `message` with `metadata.type` tool_call / browser_screenshot / final_answer / error.
- `awaiting_input` arrives **before** the `input_request` that carries the question; the MCP waits for the question.
- Websocket closed → 60 s grace, then the backend stops the run. If the MCP process exits, its running tasks stop.

## Environment facts (measured 2026-11-17)

- llama.cpp: `Fara1.5-4B-Q4_K_L.gguf`, multimodal, `n_ctx` 65536, **1 slot**. Honors `chat_template_kwargs.enable_thinking=false`, which the Fara loop always sends; without it the output goes to `reasoning_content` and `content` is empty.
- MagenticLite 0.2.2 from PyPI in `.venv`; start: `.venv/bin/magentic-ui --port 8081 --config config.yaml`. First start downloads the Quicksand Ubuntu image (308 MB). VM: 6 G RAM, 3 CPUs, 5 browser slots. `/dev/kvm` is accessible.
- Parallel sessions run, but llama.cpp has 1 slot, so model calls queue: 3 concurrent tasks worked, each slower.
- Fara's start page is Bing.
- `mcp` 2.x renamed FastMCP → `MCPServer` (`mcp.server.mcpserver`); the client API is unchanged.

## Setup (new machine)

```
uv venv --python=3.12 --seed .venv && uv pip install --python .venv "magentic_ui>=0.2.0"
# config.yaml as above; llama.cpp serving Fara on :8001
curl -s localhost:8001/v1/models
.venv/bin/magentic-ui --port 8081 --config config.yaml      # keep running
claude mcp add fara -- uv run --script $PWD/fara_mcp.py
```

## Fara capability profile (Fara1.5-4B Q4_K_L, 7 task runs, 2026-11-17, trace only)

Reliable so far:
- direct navigation when given a URL: first action every time (5/5);
- labelled form fields (click, then type): saucedemo login 2/2;
- button targets by label (Add to cart, cart icon, Checkout, Continue): 2/2 checkout runs;
- asks for missing form data instead of inventing it (2/2), and obeys "stop before <button>" (1/1);
- follow-up in the same session continues from the current page (1/1);
- reading an infobox field (Wikipedia "Designed by") 1/1; fast single-page answers in 15–20 s.

Unmeasured / to watch:
- login with given credentials was **not** flagged as a critical point; Fara asked only for missing data. Critical-point behaviour still untested on purchases and real submits.
- multi-page tasks: 9–15 actions in 84–123 s with 3 sessions sharing 1 llama.cpp slot.

## Open

- First 3 log entries are from a parser bug fixed during setup (2 `disconnected` at 0 s; the session-3 `complete` entry carries the previous task's steps).
- Untested: `approval` and `continuation` input types, max-rounds behaviour, file upload, secrets in tasks (they currently appear in the task text, the trace and the log).
- MagenticLite orchestrator (`agent_mode: all`) not used; would need a second model.
