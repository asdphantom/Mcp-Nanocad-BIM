"""Unit tests for the HistoryRegistry domain module."""

from __future__ import annotations

import pytest

from src.domain.history_registry import (
    HistoryEntry,
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


class TestHistoryRegistry:
    """Tests for HistoryRegistry CRUD and replay."""

    def test_record_returns_entry_id(self) -> None:
        reg = HistoryRegistry()
        entry_id = reg.record("create_box", {"x": 100, "y": 50, "z": 30})
        assert isinstance(entry_id, str)
        assert len(entry_id) == 12

    def test_record_stores_tool_name_and_params(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_cylinder", {"radius": 10, "height": 20})
        entries = reg.get_all()
        assert len(entries) == 1
        assert entries[0].tool_name == "create_cylinder"
        assert entries[0].params == {"radius": 10, "height": 20}

    def test_record_with_description(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 100}, description="Main box")
        assert reg.get_all()[0].description == "Main box"

    def test_record_default_params(self) -> None:
        reg = HistoryRegistry()
        eid = reg.record("create_line")
        entry = reg.get(eid)
        assert entry is not None
        assert entry.params == {}

    def test_get_all_returns_in_order(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 1})
        reg.record("create_sphere", {"radius": 5})
        reg.record("create_cylinder", {"radius": 3})
        entries = reg.get_all()
        assert len(entries) == 3
        assert entries[0].tool_name == "create_box"
        assert entries[1].tool_name == "create_sphere"
        assert entries[2].tool_name == "create_cylinder"

    def test_get_by_id(self) -> None:
        reg = HistoryRegistry()
        eid = reg.record("create_box", {"x": 100})
        entry = reg.get(eid)
        assert entry is not None
        assert entry.tool_name == "create_box"

    def test_get_nonexistent_returns_none(self) -> None:
        reg = HistoryRegistry()
        assert reg.get("nonexistent") is None

    def test_delete_existing(self) -> None:
        reg = HistoryRegistry()
        eid = reg.record("create_box", {"x": 100})
        assert reg.count() == 1
        assert reg.delete(eid) is True
        assert reg.count() == 0

    def test_delete_nonexistent(self) -> None:
        reg = HistoryRegistry()
        assert reg.delete("no-such-id") is False

    def test_clear(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 1})
        reg.record("create_sphere", {"radius": 5})
        assert reg.count() == 2
        reg.clear()
        assert reg.count() == 0

    def test_count(self) -> None:
        reg = HistoryRegistry()
        assert reg.count() == 0
        reg.record("a")
        assert reg.count() == 1
        reg.record("b")
        assert reg.count() == 2


@pytest.mark.asyncio
class TestHistoryReplay:
    """Tests for HistoryRegistry.replay()."""

    async def test_replay_empty(self) -> None:
        reg = HistoryRegistry()
        results = await reg.replay(lambda name, params: {"ok": True})
        assert results == []

    async def test_replay_single_entry(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 100, "y": 50, "z": 30})

        async def dispatcher(name: str, params: dict) -> dict:
            return {"tool": name, "params": params}

        results = await reg.replay(dispatcher)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["tool_name"] == "create_box"

    async def test_replay_resolves_parameters(self) -> None:
        """Parameter expressions are resolved before dispatch."""
        from src.domain.parameter_registry import (
            ParameterRegistry,
            set_parameter_registry,
        )

        param_reg = ParameterRegistry()
        param_reg.set("Width", 100)
        set_parameter_registry(param_reg)

        reg = HistoryRegistry()
        reg.record("create_box", {"x": "=Width * 2", "y": 50})

        async def dispatcher(name: str, params: dict) -> dict:
            return {"tool": name, "params": params, "resolved_x": params["x"]}

        results = await reg.replay(dispatcher)
        assert len(results) == 1
        assert results[0]["result"]["resolved_x"] == 200.0

    async def test_replay_handles_dispatcher_error(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 100})

        async def failing_dispatcher(name: str, params: dict) -> dict:
            msg = f"Failed: {name}"
            raise RuntimeError(msg)

        results = await reg.replay(failing_dispatcher)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Failed" in results[0]["error"]

    async def test_replay_multiple_entries(self) -> None:
        reg = HistoryRegistry()
        reg.record("create_box", {"x": 100})
        reg.record("create_sphere", {"radius": 5})
        reg.record("create_cylinder", {"radius": 3, "height": 10})

        calls: list[str] = []

        async def tracker(name: str, params: dict) -> None:
            calls.append(name)

        await reg.replay(tracker)
        assert calls == ["create_box", "create_sphere", "create_cylinder"]


class TestHistoryContextVar:
    """Tests for contextvar-based singleton access."""

    def test_get_returns_registry(self) -> None:
        reg = get_history_registry()
        assert isinstance(reg, HistoryRegistry)

    def test_get_returns_same_instance(self) -> None:
        reg1 = get_history_registry()
        reg2 = get_history_registry()
        assert reg1 is reg2

    def test_set_replaces_instance(self) -> None:
        original = get_history_registry()
        new_reg = HistoryRegistry()
        set_history_registry(new_reg)
        assert get_history_registry() is new_reg
        assert get_history_registry() is not original


class TestConcurrency:
    """Tests for thread safety of HistoryRegistry."""

    def test_concurrent_record_and_get_all(self) -> None:
        import threading

        reg = HistoryRegistry()
        errors: list[Exception] = []

        def recorder() -> None:
            try:
                for i in range(100):
                    reg.record(f"tool_{i}", {"i": i})
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    reg.get_all()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=recorder), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.count() == 100


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_record_empty_tool_name(self) -> None:
        reg = HistoryRegistry()
        entry_id = reg.record("", {"x": 1})
        assert isinstance(entry_id, str)

    def test_get_all_after_delete_count(self) -> None:
        reg = HistoryRegistry()
        reg.record("tool_a", {})
        reg.record("tool_b", {})
        reg.record("tool_c", {})
        all_entries = reg.get_all()
        reg.delete(all_entries[0].entry_id)
        assert reg.count() == 2
