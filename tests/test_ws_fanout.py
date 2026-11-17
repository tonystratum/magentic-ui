"""Several clients (UI tab + fara_mcp) on one run: all get frames, last one out starts the grace period."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from magentic_ui.backend.web.managers.connection import WebSocketManager


def _manager() -> WebSocketManager:
    mgr = WebSocketManager.__new__(WebSocketManager)
    mgr._connections = {}
    mgr._closed_connections = set()
    mgr._grace_tasks = {}
    mgr._team_managers = {}
    mgr._start_grace_period = MagicMock()
    return mgr


def _ws() -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_fanout_and_grace_only_after_last_client() -> None:
    mgr = _manager()
    mcp, ui = _ws(), _ws()
    await mgr.connect(mcp, 1)
    await mgr.connect(ui, 1)

    await mgr._send_message(1, {"type": "system", "status": "active"})
    mcp.send_json.assert_awaited_once()
    ui.send_json.assert_awaited_once()

    await mgr.disconnect(1, ws=ui)  # closing the UI tab
    mgr._start_grace_period.assert_not_called()
    assert 1 in mgr.active_connections

    await mgr._send_message(1, {"type": "system", "status": "complete"})
    assert mcp.send_json.await_count == 2

    await mgr.disconnect(1, ws=mcp)
    mgr._start_grace_period.assert_called_once_with(1)
    assert 1 not in mgr.active_connections


@pytest.mark.asyncio
async def test_failed_send_drops_only_that_client() -> None:
    mgr = _manager()
    good, bad = _ws(), _ws()
    bad.send_json.side_effect = RuntimeError("gone")
    await mgr.connect(good, 1)
    await mgr.connect(bad, 1)

    await mgr._send_message(1, {"type": "message"})
    assert mgr._connections[1] == [good]
    assert 1 not in mgr._closed_connections
