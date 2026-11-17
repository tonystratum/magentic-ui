# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.3", "httpx>=0.28", "websockets>=17"]
# ///
"""MCP server: lets Claude hand browser tasks to Fara via a running MagenticLite backend.

Claude -> this server -> MagenticLite REST + websocket (:8081) -> Fara -> Chromium in the VM.
Run: uv run --script fara_mcp.py   (MagenticLite must already be running; see DESIGN.md)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import websockets
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.stdio import stdio_server

BASE = os.environ.get("FARA_UI_URL", "http://127.0.0.1:8081").rstrip("/")
USER_ID = "guestuser@gmail.com"  # frontend's DEFAULT_USER_ID, so runs show in the UI
WS_PROTOCOL_TAG = "magui.auth.bearer"
LOG = Path(__file__).resolve().parent / "runs" / "fara.jsonl"
DONE = {"complete", "error", "stopped", "disconnected"}
CHANNEL = "notifications/claude/channel"

mcp = MCPServer(
    "fara",
    instructions=(
        'When loaded as a channel, Fara reports back on its own: a <channel source="fara" '
        'session_id=".." status=".."> event arrives when a task finishes (complete/error/stopped/'
        "disconnected) or when Fara asks a question (awaiting_input). The body is the same report "
        "fara_status returns. Relay Fara's questions to the user and answer with fara_respond; "
        "do not poll fara_status while waiting for these events."
    ),
)
_token: str | None = None
_outbound: Any = None  # connection-scoped channel to Claude Code, captured on the first tool call


@dataclass
class Run:
    session_id: int
    run_id: int
    task: str = ""
    ws: Any = None
    status: str = "created"
    steps: list[str] = field(default_factory=list)
    seen: int = 0
    answer: str | None = None
    pending: dict[str, Any] | None = None
    error: str | None = None
    started: float = 0.0
    changed: asyncio.Event = field(default_factory=asyncio.Event)


RUNS: dict[int, Run] = {}


async def _get_token(refresh: bool = False) -> str:
    """The backend embeds a per-process token in index.html."""
    global _token
    if _token is None or refresh:
        async with httpx.AsyncClient() as c:
            html = (await c.get(BASE + "/")).text
        m = re.search(r'__MAGUI_TOKEN__="([^"]+)"', html)
        if not m:
            raise RuntimeError(f"No session token at {BASE}/ - is MagenticLite running?")
        _token = m.group(1)
    return _token


async def _api(method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    for refresh in (False, True):
        headers = {"Authorization": f"Bearer {await _get_token(refresh)}"}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.request(method, f"{BASE}/api{path}", json=body, headers=headers)
        if r.status_code != 401:
            r.raise_for_status()
            return r.json()
    raise RuntimeError("Backend rejected the session token")


def _text(data: dict[str, Any]) -> str:
    content = data.get("content", [])
    if isinstance(content, str):  # user echoes and some system messages carry a plain string
        return content
    return "\n".join(c["text"] for c in content if isinstance(c, dict) and c.get("type") == "text")


def _log(run: Run) -> None:
    LOG.parent.mkdir(exist_ok=True)
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": run.session_id,
        "task": run.task,
        "status": run.status,
        "seconds": round(time.time() - run.started, 1),
        "steps": run.steps,
        "answer": run.answer,
        "error": run.error,
    }
    with LOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _report(run: Run) -> str:
    """Status, steps not yet reported, pending question, answer; marks the steps as reported."""
    out = [f"session {run.session_id}: {run.status} ({len(run.steps)} steps, {time.time() - run.started:.0f}s)"]
    new = run.steps[run.seen:]
    run.seen = len(run.steps)
    if new:
        out += ["steps:"] + new
    if run.pending:
        p = run.pending
        out.append(f"FARA ASKS ({p.get('input_type', 'text_input')}): {p.get('content', '')}")
        if p.get("tool"):
            out.append(f"  action: {p['tool']} {json.dumps(p.get('tool_args'))}")
    if run.answer:
        out.append(f"answer: {run.answer}")
    if run.error:
        out.append(f"error: {run.error}")
    return "\n".join(out)


async def _send_channel(params: dict[str, Any]) -> None:
    try:
        await _outbound.notify(CHANNEL, params)
    except Exception as e:
        print(f"fara_mcp: channel push failed ({e!r})", file=sys.stderr)


def _push(run: Run) -> None:
    """Report to Claude Code unprompted. Dropped silently by Claude Code unless loaded as a channel."""
    if _outbound is not None:
        params = {"content": _report(run), "meta": {"session_id": str(run.session_id), "status": run.status}}
        asyncio.create_task(_send_channel(params))


def _set_status(run: Run, status: str) -> None:
    was_done = run.status in DONE
    run.status = status
    if status in DONE and not was_done and run.task:
        _log(run)
        _push(run)
    run.changed.set()


def _handle(run: Run, msg: dict[str, Any]) -> None:
    kind = msg.get("type")
    if kind == "system":
        if msg.get("content") and msg.get("status") in ("error", "stopped"):
            run.error = msg["content"]
        _set_status(run, msg.get("status", run.status))
    elif kind == "input_request":
        run.pending = {k: msg[k] for k in ("input_type", "content", "tool", "tool_args", "reason") if k in msg}
        _set_status(run, "awaiting_input")
        _push(run)
    elif kind == "message":
        data = msg.get("data", {})
        mtype = data.get("metadata", {}).get("type")
        text = _text(data)
        if mtype == "tool_call":
            run.steps.append(text)
        elif mtype == "browser_screenshot" and text:
            run.steps.append(f"  -> {text}")
        elif mtype == "error":
            run.steps.append(f"  !! {text}")
        elif mtype == "final_answer":
            run.answer = text
        run.changed.set()


async def _listen(run: Run) -> None:
    try:
        async for raw in run.ws:
            try:
                _handle(run, json.loads(raw))
            except Exception as e:  # one odd message must not drop the connection
                print(f"fara_mcp: skipped message ({e!r}): {str(raw)[:200]}", file=sys.stderr)
    except websockets.ConnectionClosed:
        pass
    finally:
        run.ws = None
        if run.status not in DONE:
            _set_status(run, "disconnected")


async def _connect(run: Run) -> None:
    url = BASE.replace("http", "ws", 1) + f"/api/ws/runs/{run.run_id}"
    run.ws = await websockets.connect(
        url, subprotocols=[WS_PROTOCOL_TAG, await _get_token()], max_size=None
    )
    asyncio.create_task(_listen(run))


@mcp.tool()
async def fara_start(ctx: Context, task: str, session_id: int | None = None) -> str:
    """Give Fara (a small local browser agent) one web task; returns immediately.

    Fara sees screenshots and clicks/types in a sandboxed Chromium.
    Pass session_id to continue in the same browser session (follow-up task);
    omit it for a fresh session. Several sessions may run in parallel (5 browser slots).
    If this server is loaded as a channel, the result arrives as a <channel source="fara"> event;
    otherwise poll with fara_status(session_id, wait_seconds=...).
    """
    global _outbound
    # The SDK exposes no public handle for unsolicited notifications outside a request.
    _outbound = ctx.session._connection.outbound
    if session_id is None:
        sess = await _api("POST", "/sessions/", {"user_id": USER_ID, "name": task[:80]})
        session_id = sess["data"]["id"]
    run = RUNS.get(session_id)
    if run and run.status in ("active", "awaiting_input", "paused", "starting"):
        return f"session {session_id} is busy (status {run.status}); use fara_status / fara_respond / fara_stop"
    if run is None:
        r = await _api("POST", "/runs/", {"session_id": session_id, "user_id": USER_ID})
        run = RUNS[session_id] = Run(session_id=session_id, run_id=int(r["data"]["run_id"]))
    if run.ws is None:
        await _connect(run)
    run.task, run.answer, run.pending, run.error = task, None, None, None
    run.steps, run.seen, run.started = [], 0, time.time()
    run.status = "starting"
    await run.ws.send(json.dumps({"type": "start", "task": json.dumps({"content": task}), "settings_config": {}}))
    return f"started session_id={session_id} (run {run.run_id}); UI: {BASE}"


@mcp.tool()
async def fara_status(session_id: int | None = None, wait_seconds: int = 0) -> str:
    """Report a Fara session: status, new steps since the last call, pending question, answer.

    wait_seconds (max 300) blocks until the task finishes or Fara asks for input.
    Without session_id, lists all sessions this server knows.
    Statuses: starting, active, awaiting_input (answer via fara_respond), complete, error, stopped, disconnected.
    """
    if session_id is None:
        if not RUNS:
            return "no sessions"
        return "\n".join(f"session {r.session_id}: {r.status} - {r.task[:80]}" for r in RUNS.values())
    run = RUNS.get(session_id)
    if run is None:
        return f"unknown session {session_id}"
    deadline = time.time() + min(max(wait_seconds, 0), 300)
    # Wake on the question itself: the backend sends status awaiting_input before the input_request.
    while run.status not in DONE and run.pending is None and time.time() < deadline:
        run.changed.clear()
        try:
            await asyncio.wait_for(run.changed.wait(), deadline - time.time())
        except asyncio.TimeoutError:
            break
    return _report(run)


@mcp.tool()
async def fara_respond(session_id: int, response: str) -> str:
    """Answer Fara's pending question (status awaiting_input).

    For critical points (login, purchase, submit) Fara waits for the user's decision:
    relay the user's answer, do not decide on their behalf.
    input_type approval: 'approve' or 'deny'. continuation: 'continue' or 'stop'.
    text_input: any text, e.g. 'Yes, proceed' or an instruction.
    """
    run = RUNS.get(session_id)
    if run is None or run.ws is None:
        return f"session {session_id} is not connected"
    if run.pending is None:
        return f"session {session_id} has no pending question (status {run.status}); check fara_status first"
    kind = run.pending.get("input_type", "text_input")
    r = response.strip().lower()
    if kind == "approval" and r in ("approve", "deny"):
        msg = {"type": "approval_response", "decision": r, "source": "user"}
    elif kind == "continuation" and r in ("continue", "stop"):
        msg = {"type": "continuation_response", "decision": r}
    else:
        msg = {"type": "input_response", "response": response}
    await run.ws.send(json.dumps(msg))
    run.pending = None
    run.status = "active"
    return f"sent {msg['type']} to session {session_id}"


@mcp.tool()
async def fara_stop(session_id: int) -> str:
    """Stop a running Fara task. The session can take a new fara_start afterwards."""
    run = RUNS.get(session_id)
    if run is None or run.ws is None:
        return f"session {session_id} is not connected"
    await run.ws.send(json.dumps({"type": "stop", "reason": "Stopped by Claude"}))
    return f"stop sent to session {session_id}"


async def _main() -> None:
    # mcp.run() offers no way to add experimental capabilities; declare claude/channel here.
    server = mcp._lowlevel_server
    async with stdio_server() as (read, write):
        await server.run(
            read, write, server.create_initialization_options(experimental_capabilities={"claude/channel": {}})
        )


if __name__ == "__main__":
    asyncio.run(_main())
