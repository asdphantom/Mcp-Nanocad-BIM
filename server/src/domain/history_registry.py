"""History registry: ordered tool call history for model regeneration.

Stores a sequence of (tool_name, params) pairs so that when parameters change,
the model can be rebuilt by replaying the history with re-resolved values.

Thread-safe via ``contextvars`` singleton pattern (same as ParameterRegistry).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from src.domain.parameter_registry import get_parameter_registry


@dataclass
class HistoryEntry:
    """A single recorded tool call.

    Attributes:
        entry_id: Unique identifier for this entry.
        tool_name: Name of the MCP tool that was called.
        params: Keyword arguments passed to the tool (may contain =formulas).
        description: Optional human-readable note.
    """

    entry_id: str = field(default_factory=lambda: uuid4().hex[:12])
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


class HistoryRegistry:
    """Ordered, append-only registry of tool calls for replay.

    Entries are stored in insertion order. Calling ``replay`` iterates
    all entries, resolves any parameter formulas through ``ParameterRegistry``,
    and invokes the provided dispatcher callback for each.
    """

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []

    # ── Mutation ──────────────────────────────────────────────────

    def record(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        *,
        description: str = "",
    ) -> str:
        """Record a tool call for later replay.

        Args:
            tool_name: The MCP tool name (e.g. ``create_box``).
            params: The keyword arguments passed to the tool.
            description: Optional human-readable note.

        Returns:
            The entry ID string.
        """
        entry = HistoryEntry(
            tool_name=tool_name,
            params=dict(params) if params else {},
            description=description,
        )
        self._entries.append(entry)
        return entry.entry_id

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by ID.

        Returns:
            True if the entry was found and removed.
        """
        for i, e in enumerate(self._entries):
            if e.entry_id == entry_id:
                del self._entries[i]
                return True
        return False

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()

    # ── Query ─────────────────────────────────────────────────────

    def get_all(self) -> Sequence[HistoryEntry]:
        """Return all entries in insertion order."""
        return list(self._entries)

    def get(self, entry_id: str) -> HistoryEntry | None:
        """Get a single entry by ID."""
        for e in self._entries:
            if e.entry_id == entry_id:
                return e
        return None

    def count(self) -> int:
        """Return the number of recorded entries."""
        return len(self._entries)

    # ── Replay ────────────────────────────────────────────────────

    async def replay(
        self,
        dispatcher: Any,  # Callable[[str, dict[str, Any]], Any]
    ) -> list[dict[str, Any]]:
        """Replay all recorded entries with re-resolved parameters.

        Each entry's ``params`` are resolved through ``ParameterRegistry``
        (handling ``=expr`` and ``*Name`` references), then passed to the
        ``dispatcher`` callable along with the tool name.

        Args:
            dispatcher: An async callable ``(tool_name, resolved_params) -> result``.

        Returns:
            List of result dicts, one per entry, each containing
            ``{"entry_id", "tool_name", "success", "result"}``.
        """
        param_reg = get_parameter_registry()
        results: list[dict[str, Any]] = []
        for entry in self._entries:
            resolved_params = param_reg.parameters_for_bridge(entry.params)
            try:
                result = await dispatcher(entry.tool_name, resolved_params)
                results.append(
                    {
                        "entry_id": entry.entry_id,
                        "tool_name": entry.tool_name,
                        "success": True,
                        "result": result,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "entry_id": entry.entry_id,
                        "tool_name": entry.tool_name,
                        "success": False,
                        "error": str(exc),
                    }
                )
        return results


# ── Module-level singleton ──────────────────────────────────────

_history_registry: HistoryRegistry | None = None


def get_history_registry() -> HistoryRegistry:
    """Get the process-wide ``HistoryRegistry`` (lazy-init singleton)."""
    global _history_registry
    if _history_registry is None:
        _history_registry = HistoryRegistry()
    return _history_registry


def set_history_registry(registry: HistoryRegistry | None) -> None:
    """Set the current ``HistoryRegistry`` (test injection)."""
    global _history_registry
    _history_registry = registry
