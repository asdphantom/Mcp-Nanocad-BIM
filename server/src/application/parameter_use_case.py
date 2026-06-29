"""Use cases for parametric design parameter management."""

from __future__ import annotations

from typing import Any

from src.domain.parameter_registry import (
    get_parameter_registry,
)


class ParameterUseCase:
    """Manage named parameters for parametric design.

    Operates entirely server-side — parameter resolution happens before
    any HTTP bridge call. No .NET plugin changes needed.
    """

    # ── Parameter CRUD ────────────────────────────────────────────

    def set_parameter(self, name: str, value: str | float, description: str = "") -> dict[str, Any]:
        """Set a named parameter (literal, formula, or reference).

        Returns:
            ``{"success": true, "name": ..., "value": ...}``
        """
        reg = get_parameter_registry()
        resolved = reg.set(name, value, description)
        return {"success": True, "name": name, "value": resolved}

    def get_parameter(self, name: str) -> dict[str, Any]:
        """Get a parameter's value and metadata.

        Returns:
            ``{"name": ..., "value": ..., "formula": ..., "description": ...}``
            or ``{"error": "not found"}`` if the parameter doesn't exist.
        """
        reg = get_parameter_registry()
        val = reg.get(name)
        if val is None:
            return {"error": f"Parameter '{name}' not found", "success": False}
        result: dict[str, Any] = {"name": name, "value": val}
        formula = reg.get_formula(name)
        if formula:
            result["formula"] = formula
        desc = reg.get_description(name)
        if desc:
            result["description"] = desc
        result["success"] = True
        return result

    def list_parameters(self) -> dict[str, Any]:
        """List all parameters with values and metadata.

        Returns:
            ``{"success": true, "parameters": [...], "count": N}``
        """
        reg = get_parameter_registry()
        params = reg.list_all_with_meta()
        return {"success": True, "parameters": params, "count": len(params)}

    def delete_parameter(self, name: str) -> dict[str, Any]:
        """Delete a named parameter."""
        reg = get_parameter_registry()
        if not reg.has(name):
            return {"error": f"Parameter '{name}' not found", "success": False}
        reg.delete(name)
        return {"success": True, "name": name}

    def clear_parameters(self) -> dict[str, Any]:
        """Delete all parameters."""
        reg = get_parameter_registry()
        reg.clear()
        return {"success": True, "message": "All parameters cleared"}

    # ── Resolution ───────────────────────────────────────────────

    def evaluate_expression(self, expression: str) -> dict[str, Any]:
        """Evaluate a mathematical expression against current parameters.

        Returns:
            ``{"success": true, "expression": ..., "result": ...}``
            or ``{"error": ...}`` on failure.
        """
        from src.domain.parameter_registry import evaluate_expression

        reg = get_parameter_registry()
        try:
            result = evaluate_expression(expression, reg.list_all())
            return {"success": True, "expression": expression, "result": result}
        except Exception as e:
            return {"error": str(e), "success": False}

    def resolve_value(self, raw: str | float) -> dict[str, Any]:
        """Resolve a raw value against the parameter registry.

        Handles ``*Name`` (reference), ``=expr`` (formula), and literals.

        Returns:
            ``{"success": true, "raw": ..., "resolved": ...}``
        """
        reg = get_parameter_registry()
        try:
            resolved = reg.resolve_value(raw)
            return {"success": True, "raw": str(raw), "resolved": resolved}
        except Exception as e:
            return {"error": str(e), "success": False}

    # ── Design Table ─────────────────────────────────────────────

    def load_design_table(self, csv_data: str) -> dict[str, Any]:
        """Load a design table from CSV string.

        Returns:
            ``{"success": true, "rows": [...], "columns": [...], "count": N}``
        """
        reg = get_parameter_registry()
        try:
            rows = reg.load_design_table(csv_data)
            columns = list(rows[0].keys()) if rows else []
            return {
                "success": True,
                "rows": rows,
                "columns": columns,
                "count": len(rows),
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def apply_design_row(self, row_index: int, rows_json: list[dict[str, str]]) -> dict[str, Any]:
        """Apply a design table row as parameter values.

        Args:
            row_index: 0-based index into the rows list.
            rows_json: The rows list from ``load_design_table``.

        Returns:
            ``{"success": true, "applied_parameters": [...], "values": {...}}``
        """
        reg = get_parameter_registry()
        try:
            if row_index < 0 or row_index >= len(rows_json):
                return {"error": f"Row index {row_index} out of range", "success": False}
            row = rows_json[row_index]
            set_params = reg.apply_design_row(row)
            values = {n: reg.get(n) for n in set_params if reg.get(n) is not None}
            return {"success": True, "applied_parameters": set_params, "values": values}
        except Exception as e:
            return {"error": str(e), "success": False}

    # ── Configuration Management ─────────────────────────────────

    def save_configuration(self, name: str) -> dict[str, Any]:
        """Save all current parameter values as a named configuration.

        Returns:
            ``{"success": true, "name": "Small", "parameters": {...}}``
        """
        reg = get_parameter_registry()
        snapshot = reg.save_configuration(name)
        return {"success": True, "name": name, "parameters": snapshot}

    def load_configuration(self, name: str) -> dict[str, Any]:
        """Restore a named configuration as current parameter values.

        Returns:
            ``{"success": true, "name": "Small", "parameters": {...}}``
            or ``{"success": false, "error": "..."}`` if not found.
        """
        reg = get_parameter_registry()
        try:
            snapshot = reg.load_configuration(name)
            return {"success": True, "name": name, "parameters": snapshot}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_configurations(self) -> dict[str, Any]:
        """List all saved configurations.

        Returns:
            ``{"success": true, "configurations": {...}, "count": N}``
        """
        reg = get_parameter_registry()
        configs = reg.list_configurations()
        return {"success": True, "configurations": configs, "count": len(configs)}

    def delete_configuration(self, name: str) -> dict[str, Any]:
        """Delete a named configuration.

        Returns:
            ``{"success": true, "name": "..."}``
            or ``{"success": false, "error": "..."}`` if not found.
        """
        reg = get_parameter_registry()
        if reg.delete_configuration(name):
            return {"success": True, "name": name}
        return {"success": False, "error": f"Configuration '{name}' not found"}

    # ── Utility for bridge resolution ────────────────────────────

    def resolve_for_bridge(self, **kwargs: Any) -> dict[str, Any]:
        """Resolve any parameter-driven values in kwargs for HTTP bridge calls.

        Any string value matching ``"*Name"`` or ``"=expression"`` is resolved
        to its numeric value. Other values pass through unchanged.

        Returns:
            Resolved kwargs dict.
        """
        reg = get_parameter_registry()
        return reg.parameters_for_bridge(kwargs)
