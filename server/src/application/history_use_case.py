"""Use case for tool call history and model regeneration."""

from __future__ import annotations

from typing import Any

from src.domain.history_registry import get_history_registry


class HistoryUseCase:
    """Manage tool call history for parametric model regeneration.

    Pairs with ``ParameterRegistry`` so that on replay, any ``=expr`` or
    ``*Name`` parameter values are re-resolved against current parameter values.
    """

    # ── Record ────────────────────────────────────────────────────

    def record_tool_call(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        *,
        description: str = "",
    ) -> dict[str, Any]:
        """Record a tool call for later replay.

        Returns:
            ``{"success": true, "entry_id": "...", "tool_name": "..."}``
        """
        reg = get_history_registry()
        entry_id = reg.record(tool_name, params, description=description)
        return {
            "success": True,
            "entry_id": entry_id,
            "tool_name": tool_name,
            "description": description,
        }

    # ── Query ─────────────────────────────────────────────────────

    def get_history(self) -> dict[str, Any]:
        """Return all recorded entries.

        Returns:
            ``{"success": true, "entries": [...], "count": N}``
        """
        reg = get_history_registry()
        entries = reg.get_all()
        result_entries = []
        for e in entries:
            entry_dict: dict[str, Any] = {
                "entry_id": e.entry_id,
                "tool_name": e.tool_name,
                "params": e.params,
            }
            if e.description:
                entry_dict["description"] = e.description
            result_entries.append(entry_dict)
        return {"success": True, "entries": result_entries, "count": len(result_entries)}

    # ── Delete / Clear ────────────────────────────────────────────

    def delete_entry(self, entry_id: str) -> dict[str, Any]:
        """Delete a single entry by ID.

        Returns:
            ``{"success": true, "entry_id": "..."}``
            or ``{"success": false, "error": "..."}`` if not found.
        """
        reg = get_history_registry()
        if reg.delete(entry_id):
            return {"success": True, "entry_id": entry_id}
        return {"success": False, "error": f"Entry '{entry_id}' not found"}

    def clear_history(self) -> dict[str, Any]:
        """Delete all entries.

        Returns:
            ``{"success": true}``
        """
        reg = get_history_registry()
        reg.clear()
        return {"success": True, "message": "History cleared"}

    # ── Replay ────────────────────────────────────────────────────

    async def replay_history(
        self,
        dispatcher: Any,  # Callable[[str, dict[str, Any]], Any]
    ) -> dict[str, Any]:
        """Replay all recorded calls with re-resolved parameters.

        Args:
            dispatcher: An async callable ``(tool_name, resolved_params) -> result``.

        Returns:
            ``{"success": true, "results": [...], "total": N, "ok": N, "errors": N}``
        """
        reg = get_history_registry()
        results = await reg.replay(dispatcher)
        ok_count = sum(1 for r in results if r["success"])
        error_count = sum(1 for r in results if not r["success"])
        return {
            "success": error_count == 0,
            "results": results,
            "total": len(results),
            "ok": ok_count,
            "errors": error_count,
        }
