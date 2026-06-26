"""Unit tests for HistoryUseCase."""

from __future__ import annotations

import pytest

from src.application.history_use_case import HistoryUseCase
from src.domain.history_registry import (
    HistoryRegistry,
    get_history_registry,
    set_history_registry,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset the contextvar-backed registry before each test."""
    set_history_registry(HistoryRegistry())
    yield
    set_history_registry(None)


class TestRecord:
    """Tests for recording tool calls."""

    def _make_uc(self) -> HistoryUseCase:
        return HistoryUseCase()

    def test_record_simple(self) -> None:
        uc = self._make_uc()
        result = uc.record_tool_call("create_box", {"x": 100, "y": 50, "z": 30})
        assert result["success"] is True
        assert result["tool_name"] == "create_box"
        assert "entry_id" in result

    def test_record_with_description(self) -> None:
        uc = self._make_uc()
        result = uc.record_tool_call(
            "create_box", {"x": 100}, description="Main enclosure"
        )
        assert result["description"] == "Main enclosure"

    def test_record_no_params(self) -> None:
        uc = self._make_uc()
        result = uc.record_tool_call("zoom_extents")
        assert result["success"] is True

    def test_multiple_records(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": 100})
        uc.record_tool_call("create_sphere", {"radius": 5})
        hist = uc.get_history()
        assert hist["count"] == 2


class TestQuery:
    """Tests for querying history."""

    def _make_uc(self) -> HistoryUseCase:
        return HistoryUseCase()

    def test_get_history_empty(self) -> None:
        uc = self._make_uc()
        result = uc.get_history()
        assert result["success"] is True
        assert result["count"] == 0
        assert result["entries"] == []

    def test_get_history_with_entries(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": 100})
        uc.record_tool_call("create_line", {"x1": 0, "y1": 0, "x2": 10, "y2": 10})
        result = uc.get_history()
        assert result["count"] == 2
        assert result["entries"][0]["tool_name"] == "create_box"
        assert result["entries"][1]["tool_name"] == "create_line"

    def test_get_history_shows_params(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": 100, "y": 50})
        entry = uc.get_history()["entries"][0]
        assert entry["params"] == {"x": 100, "y": 50}


class TestDeleteClear:
    """Tests for deleting and clearing history."""

    def _make_uc(self) -> HistoryUseCase:
        return HistoryUseCase()

    def test_delete_entry_found(self) -> None:
        uc = self._make_uc()
        rec = uc.record_tool_call("create_box", {"x": 100})
        eid = rec["entry_id"]
        result = uc.delete_entry(eid)
        assert result["success"] is True
        assert uc.get_history()["count"] == 0

    def test_delete_entry_not_found(self) -> None:
        uc = self._make_uc()
        result = uc.delete_entry("no-such-id")
        assert result["success"] is False

    def test_clear_history(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": 1})
        uc.record_tool_call("create_sphere", {"radius": 5})
        result = uc.clear_history()
        assert result["success"] is True
        assert uc.get_history()["count"] == 0


@pytest.mark.asyncio
class TestReplay:
    """Tests for replay_history."""

    def _make_uc(self) -> HistoryUseCase:
        return HistoryUseCase()

    async def test_replay_empty(self) -> None:
        uc = self._make_uc()
        result = await uc.replay_history(lambda name, params: {"ok": True})
        assert result["success"] is True
        assert result["total"] == 0

    async def test_replay_single_entry(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": 100, "y": 50})

        async def dispatcher(name: str, params: dict) -> dict:
            return {"tool": name, "params": params}

        result = await uc.replay_history(dispatcher)
        assert result["total"] == 1
        assert result["ok"] == 1
        assert result["errors"] == 0
        assert result["results"][0]["tool_name"] == "create_box"

    async def test_replay_with_parameter_resolution(self) -> None:
        from src.domain.parameter_registry import (
            ParameterRegistry,
            set_parameter_registry,
        )

        param_reg = ParameterRegistry()
        param_reg.set("Width", 200)
        set_parameter_registry(param_reg)

        uc = self._make_uc()
        uc.record_tool_call("create_box", {"x": "=Width / 2", "y": 50})
        uc.record_tool_call("create_cylinder", {"radius": "=Width * 0.1"})

        calls: list[tuple[str, dict]] = []

        async def tracker(name: str, params: dict) -> None:
            calls.append((name, params))

        result = await uc.replay_history(tracker)
        assert result["total"] == 2
        assert result["ok"] == 2
        assert calls[0][1]["x"] == 100.0
        assert calls[1][1]["radius"] == 20.0

    async def test_replay_with_errors(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("good_tool", {"a": 1})
        uc.record_tool_call("bad_tool", {"b": 2})

        called: list[str] = []

        async def dispatcher(name: str, params: dict) -> None:
            if name == "bad_tool":
                msg = f"Failed on {name}"
                raise RuntimeError(msg)
            called.append(name)

        result = await uc.replay_history(dispatcher)
        assert result["total"] == 2
        assert result["ok"] == 1
        assert result["errors"] == 1
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False

    async def test_replay_maintains_order(self) -> None:
        uc = self._make_uc()
        uc.record_tool_call("first", {"order": 1})
        uc.record_tool_call("second", {"order": 2})
        uc.record_tool_call("third", {"order": 3})

        tool_order: list[str] = []

        async def tracker(name: str, params: dict) -> None:
            tool_order.append(name)

        await uc.replay_history(tracker)
        assert tool_order == ["first", "second", "third"]
