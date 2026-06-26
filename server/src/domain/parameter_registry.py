"""Parameter registry and expression evaluator for parametric design.

Maintains a named parameter dictionary with optional expressions.
Expressions can reference other parameters and are evaluated in dependency order.
Uses Python's ``ast`` module for safe expression evaluation (no ``eval``).
"""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Mapping
from typing import Any, Set

# ── Expression Evaluator ─────────────────────────────────────────────────────


from src.domain.exceptions import NanocadError  # noqa: E402


class ExpressionError(NanocadError):
    """Raised when a parameter expression cannot be evaluated."""


_ALLOWED_OPS: dict[type[ast.AST], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate_ast(node: ast.AST, context: Mapping[str, float]) -> float:
    """Safely evaluate a parsed AST node using only allowed operations."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ExpressionError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.Name):
        name = node.id
        if name in context:
            return context[name]
        raise ExpressionError(f"Unknown parameter: {name}")
    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ExpressionError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_evaluate_ast(node.operand, context))
    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left, context)
        right = _evaluate_ast(node.right, context)
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ExpressionError(f"Unsupported binary operator: {type(node.op).__name__}")
        return op(left, right)
    if isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else ""
        args = [_evaluate_ast(a, context) for a in node.args]
        if func_name == "min" and len(args) >= 2:
            return float(min(args))
        if func_name == "max" and len(args) >= 2:
            return float(max(args))
        if func_name == "round" and len(args) >= 1:
            return float(round(args[0]))
        if func_name == "sqrt" and len(args) == 1:
            import math
            return float(math.sqrt(args[0]))
        if func_name == "abs" and len(args) == 1:
            return float(abs(args[0]))
        raise ExpressionError(f"Unsupported function: {func_name}")
    raise ExpressionError(f"Unsupported expression: {ast.dump(node)}")


def evaluate_expression(expression: str, context: Mapping[str, float]) -> float:
    """Evaluate a mathematical expression string against a parameter context.

    Args:
        expression: A mathematical expression like ``Width*2 + 10``.
        context: Parameter name → value mapping.

    Returns:
        The computed float value.

    Raises:
        ExpressionError: On parse errors, unknown parameters, or unsafe operations.
    """
    cleaned = expression.strip()
    if not cleaned:
        raise ExpressionError("Empty expression")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"Syntax error in expression: {e}") from e
    return _evaluate_ast(tree.body, context)


# ── Parameter Registry ───────────────────────────────────────────────────────


_PARAM_RE = re.compile(r"^\*(\w+)$")
_FORMULA_RE = re.compile(r"^=(.+)$")


class ParameterRegistry:
    """Thread-safe named parameter registry for parametric design.

    Parameters can be:
      - Literal values (float)
      - Formulas starting with ``=``: ``=Width * 2``
      - References starting with ``*``: ``*Thickness`` (resolves to parameter value)

    The registry maintains dependency order for formula resolution.
    """

    def __init__(self) -> None:
        self._values: dict[str, float] = {}
        self._formulas: dict[str, str] = {}
        self._descriptions: dict[str, str] = {}
        self._configurations: dict[str, dict[str, float]] = {}

    # ── Query ─────────────────────────────────────────────────────

    def get(self, name: str) -> float | None:
        """Get the resolved value of a named parameter.

        Tries to resolve formulas on-the-fly if the value isn't cached.
        Returns ``None`` if the parameter doesn't exist.
        Raises ``ExpressionError`` on resolution errors (circular deps, etc.).
        """
        if name in self._values:
            return self._values[name]
        if name in self._formulas:
            return self.resolve(name)
        return None

    def get_formula(self, name: str) -> str | None:
        """Get the raw formula string of a named parameter."""
        return self._formulas.get(name)

    def get_description(self, name: str) -> str | None:
        """Get the description of a named parameter."""
        return self._descriptions.get(name)

    def list_all(self) -> dict[str, float]:
        """Return all parameters with their resolved values."""
        result: dict[str, float] = {}
        all_names = set(self._values.keys()) | set(self._formulas.keys())
        for name in all_names:
            val = self.get(name)
            if val is not None:
                result[name] = val
        return result

    def list_all_with_meta(self) -> list[dict[str, Any]]:
        """Return all parameters with metadata (value, formula, description)."""
        result: list[dict[str, Any]] = []
        all_names = set(self._values.keys()) | set(self._formulas.keys())
        for name in sorted(all_names):
            entry: dict[str, Any] = {"name": name}
            val = self.get(name)
            if val is not None:
                entry["value"] = val
            else:
                entry["value"] = None
            if name in self._formulas:
                entry["formula"] = self._formulas[name]
            if name in self._descriptions:
                entry["description"] = self._descriptions[name]
            result.append(entry)
        return result

    def has(self, name: str) -> bool:
        """Check if a parameter exists (in values or formulas)."""
        return name in self._values or name in self._formulas

    # ── Mutation ──────────────────────────────────────────────────

    def set(self, name: str, raw: str | float, description: str = "") -> float:
        """Set a parameter from a raw value (numeric, formula, or reference).

        Args:
            name: Parameter name (e.g. ``Width``).
            raw: Numeric value, formula (``=Width*2``), or reference (``*Thickness``).
            description: Optional human-readable description.

        Returns:
            The resolved numeric value.

        Raises:
            ExpressionError: On circular or broken dependencies.
        """
        if isinstance(raw, (int, float)):
            self._values[name] = float(raw)
            self._formulas.pop(name, None)
        elif isinstance(raw, str):
            formula_match = _FORMULA_RE.match(raw)
            ref_match = _PARAM_RE.match(raw)
            if formula_match:
                expr = formula_match.group(1)
                self._formulas[name] = expr
            elif ref_match:
                ref_name = ref_match.group(1)
                self._formulas[name] = f"*{ref_name}"
            else:
                # Try to parse as direct number
                try:
                    self._values[name] = float(raw)
                    self._formulas.pop(name, None)
                except ValueError:
                    raise ExpressionError(f"Cannot parse parameter value: {raw}") from None
        else:
            raise ExpressionError(f"Unsupported parameter type: {type(raw).__name__}")

        if description:
            self._descriptions[name] = description

        # Resolve immediately if possible; keep formula for later if deps missing
        if name in self._formulas:
            try:
                val = self.resolve(name)
                self._values[name] = val
                return val
            except ExpressionError:
                self._values.pop(name, None)
                return float("nan")
        return self.resolve(name)

    def delete(self, name: str) -> None:
        """Remove a parameter and its formula."""
        self._values.pop(name, None)
        self._formulas.pop(name, None)
        self._descriptions.pop(name, None)

    def clear(self) -> None:
        """Remove all parameters."""
        self._values.clear()
        self._formulas.clear()
        self._descriptions.clear()

    # ── Resolution ────────────────────────────────────────────────

    def resolve(self, name: str) -> float:
        """Resolve a named parameter to its computed float value.

        Handles topologically-ordered formula chains.
        """
        visited: set[str] = set()
        return self._resolve_with_cycle_check(name, visited)

    def resolve_value(self, raw: str | float) -> float:
        """Resolve a raw value that may be a formula, reference, or literal.

        Examples:
          ``100``        → 100
          ``"*Width"``   → self._values["Width"]
          ``"=Width*2"`` → evaluate_expression("Width*2", self._values)
        """
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            ref_match = _PARAM_RE.match(raw)
            formula_match = _FORMULA_RE.match(raw)
            if ref_match:
                ref_name = ref_match.group(1)
                val = self.get(ref_name)
                if val is None:
                    raise ExpressionError(f"Unknown parameter reference: {ref_name}")
                return val
            if formula_match:
                expr = formula_match.group(1)
                return evaluate_expression(expr, dict(self._values))
            try:
                return float(raw)
            except ValueError:
                raise ExpressionError(f"Cannot resolve value: {raw}") from None
        raise ExpressionError(f"Unsupported type: {type(raw).__name__}")

    @staticmethod
    def _extract_names(expression: str) -> list[str]:
        """Extract all ``ast.Name`` identifiers from an expression string.

        Used to detect cycle candidates before evaluation.
        """
        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError:
            return []
        return [
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        ]

    def _resolve_with_cycle_check(self, name: str, visited: Set[str]) -> float:
        if name in visited:
            raise ExpressionError(f"Circular dependency for parameter: {name}")
        if name in self._formulas:
            expr = self._formulas[name]
            ref_match = _PARAM_RE.match(expr if expr.startswith("*") else "")
            if ref_match:
                ref_name = ref_match.group(1)
                visited.add(name)
                val = self._resolve_with_cycle_check(ref_name, visited)
                self._values[name] = val
                return val
            # Evaluate the formula expression
            visited.add(name)
            # Pre-check for cycle candidates: any referenced param that is
            # already in visited indicates a cycle
            ref_names = self._extract_names(expr)
            for ref_name in ref_names:
                if ref_name in visited:
                    raise ExpressionError(
                        f"Circular dependency for parameter: {name}"
                    )
            # Build context with cached values + recursively resolved formulas
            context: dict[str, float] = dict(self._values)
            for pname in self._formulas:
                if pname not in context and pname not in visited:
                    try:
                        context[pname] = self._resolve_with_cycle_check(
                            pname, visited
                        )
                    except ExpressionError as exc:
                        # Re-raise cycle detection errors; skip unresolvable ones
                        if "Circular" in str(exc):
                            raise
                        pass
            val = evaluate_expression(expr, context)
            self._values[name] = val
            return val
        if name in self._values:
            return self._values[name]
        raise ExpressionError(f"Unknown parameter: {name}")

    # ── Design Table ──────────────────────────────────────────────

    def load_design_table(self, csv_data: str) -> list[dict[str, str]]:
        """Load a design table from CSV string.

        First row = header (parameter names).
        Subsequent rows = configurations.

        Returns:
            List of rows, each as ``{param_name: value_string}``.
        """
        import csv
        import io

        reader = csv.DictReader(io.StringIO(csv_data))
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items() if k})
        return rows

    def apply_design_row(self, row: dict[str, str], append_prefix: str = "") -> list[str]:
        """Apply a design table row as parameter values.

        Args:
            row: ``{param_name: value_string}`` from ``load_design_table``.
            append_prefix: Optional prefix for parameter names (e.g. ``"V1_"``).

        Returns:
            List of parameter names that were set.
        """
        set_params: list[str] = []
        for name, value_str in row.items():
            full_name = f"{append_prefix}{name}" if append_prefix else name
            try:
                num_val = float(value_str)
                self.set(full_name, num_val)
                set_params.append(full_name)
            except ValueError:
                pass  # Non-numeric values are not stored
        return set_params

    def parameters_for_bridge(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Resolve any formula/reference values in kwargs for HTTP bridge.

        Any string value matching ``"*Name"`` or ``"=expression"`` is resolved
        to its numeric value. Other values pass through unchanged.
        """
        resolved: dict[str, Any] = {}
        for key, val in kwargs.items():
            if isinstance(val, str) and (val.startswith("*") or val.startswith("=")):
                resolved[key] = self.resolve_value(val)
            else:
                resolved[key] = val
        return resolved

    # ── Configuration Management (named parameter snapshots) ───────

    def save_configuration(self, name: str) -> dict[str, float]:
        """Save all current parameter resolved values as a named configuration.

        Args:
            name: Configuration name (e.g. ``"Small"``, ``"Large"``).

        Returns:
            The snapshot dict of ``{param_name: resolved_value}``.

        Raises:
            ExpressionError: If a parameter cannot be resolved.
        """
        snapshot: dict[str, float] = {}
        all_names = set(self._values.keys()) | set(self._formulas.keys())
        for pname in all_names:
            val = self.get(pname)
            if val is not None:
                snapshot[pname] = val
        self._configurations[name] = snapshot
        return snapshot

    def load_configuration(self, name: str) -> dict[str, float]:
        """Restore a named configuration as current parameter values.

        Sets all parameters stored in the config as plain numbers (no formulas).
        Parameters not in the config are left unchanged.

        Args:
            name: Configuration name.

        Returns:
            The restored snapshot dict.

        Raises:
            ExpressionError: If the configuration does not exist.
        """
        snapshot = self._configurations.get(name)
        if snapshot is None:
            raise ExpressionError(f"Configuration not found: {name}")
        # Clear current values/formulas and restore from snapshot
        self._values.clear()
        self._formulas.clear()
        self._values.update(snapshot)
        return snapshot

    def list_configurations(self) -> dict[str, dict[str, float]]:
        """Return all saved configurations.

        Returns:
            ``{config_name: {param_name: value, ...}, ...}``
        """
        return dict(self._configurations)

    def get_configuration(self, name: str) -> dict[str, float] | None:
        """Get a single configuration snapshot by name.

        Returns:
            The snapshot dict or ``None`` if not found.
        """
        return self._configurations.get(name)

    def delete_configuration(self, name: str) -> bool:
        """Delete a named configuration.

        Returns:
            ``True`` if the config was found and removed.
        """
        if name in self._configurations:
            del self._configurations[name]
            return True
        return False


# ── Module-level singleton ────────────────────────────────────────────────────

_param_registry: ParameterRegistry | None = None


def get_parameter_registry() -> ParameterRegistry:
    """Get the process-wide parameter registry (created lazily)."""
    global _param_registry
    if _param_registry is None:
        _param_registry = ParameterRegistry()
    return _param_registry


def set_parameter_registry(reg: ParameterRegistry | None) -> None:
    """Set or clear the parameter registry (for testing/reset)."""
    global _param_registry
    _param_registry = reg
