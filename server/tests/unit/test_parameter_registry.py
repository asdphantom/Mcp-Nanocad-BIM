"""Unit tests for parameter_registry domain module."""

from __future__ import annotations

import pytest

from src.domain.parameter_registry import (
    ExpressionError,
    ParameterRegistry,
    evaluate_expression,
)


class TestExpressionEvaluator:
    """Tests for the safe expression evaluator."""

    def test_literal_number(self) -> None:
        assert evaluate_expression("42", {}) == 42.0

    def test_simple_addition(self) -> None:
        assert evaluate_expression("Width + 10", {"Width": 100}) == 110.0

    def test_multiplication(self) -> None:
        assert evaluate_expression("Width * 2", {"Width": 50}) == 100.0

    def test_complex_expression(self) -> None:
        ctx = {"Width": 100, "Height": 50, "Thickness": 5}
        result = evaluate_expression("(Width - Thickness*2) * (Height - Thickness*2)", ctx)
        assert result == (100 - 10) * (50 - 10) == 3600.0

    def test_division(self) -> None:
        assert evaluate_expression("Width / 2", {"Width": 100}) == 50.0

    def test_power(self) -> None:
        assert evaluate_expression("2 ** 3", {}) == 8.0

    def test_negative(self) -> None:
        assert evaluate_expression("-Width", {"Width": 10}) == -10.0

    def test_min_function(self) -> None:
        ctx = {"A": 10, "B": 20}
        assert evaluate_expression("min(A, B)", ctx) == 10.0

    def test_max_function(self) -> None:
        ctx = {"A": 10, "B": 20}
        assert evaluate_expression("max(A, B)", ctx) == 20.0

    def test_round_function(self) -> None:
        assert evaluate_expression("round(3.7)", {}) == 4.0

    def test_abs_function(self) -> None:
        assert evaluate_expression("abs(-5)", {}) == 5.0

    def test_unknown_parameter_raises_error(self) -> None:
        with pytest.raises(ExpressionError, match="Unknown parameter"):
            evaluate_expression("Foo", {})

    def test_unsupported_operator_raises_error(self) -> None:
        with pytest.raises(ExpressionError, match="Unsupported expression"):
            evaluate_expression("1 and 0", {})

    def test_empty_expression_raises_error(self) -> None:
        with pytest.raises(ExpressionError, match="Empty expression"):
            evaluate_expression("", {})

    def test_syntax_error_raises_error(self) -> None:
        with pytest.raises(ExpressionError, match="Syntax error"):
            evaluate_expression("2 +* 3", {})


class TestParameterRegistry:
    """Tests for the ParameterRegistry class."""

    def test_set_and_get_literal(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        assert reg.get("Width") == 100.0

    def test_set_and_get_string_number(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", "50")
        assert reg.get("Width") == 50.0

    def test_set_formula(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("PanelWidth", "=Width - 10")
        assert reg.get("PanelWidth") == 90.0

    def test_set_reference(self) -> None:
        reg = ParameterRegistry()
        reg.set("Thickness", 5)
        reg.set("WallThickness", "*Thickness")
        assert reg.get("WallThickness") == 5.0

    def test_chained_formulas(self) -> None:
        reg = ParameterRegistry()
        reg.set("A", 10)
        reg.set("B", "=A * 2")
        reg.set("C", "=B + 5")
        assert reg.get("C") == 25.0

    def test_circular_dependency_raises_error(self) -> None:
        reg = ParameterRegistry()
        reg.set("A", "=B + 1")
        reg.set("B", "=A + 1")
        with pytest.raises(ExpressionError, match="Circular"):
            reg.get("A")

    def test_delete_parameter(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        assert reg.has("Width")
        reg.delete("Width")
        assert not reg.has("Width")
        assert reg.get("Width") is None

    def test_clear_all(self) -> None:
        reg = ParameterRegistry()
        reg.set("A", 1)
        reg.set("B", 2)
        reg.clear()
        assert reg.list_all() == {}

    def test_list_all(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("Height", 50)
        assert reg.list_all() == {"Width": 100.0, "Height": 50.0}

    def test_list_all_with_meta(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100, "Overall width")
        reg.set("Height", "=Width * 0.5")
        meta = reg.list_all_with_meta()
        assert len(meta) == 2
        width_entry = next(m for m in meta if m["name"] == "Width")
        assert width_entry["value"] == 100.0
        assert width_entry["description"] == "Overall width"

    def test_description(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100, "Overall width of the panel")
        assert reg.get_description("Width") == "Overall width of the panel"

    def test_get_formula(self) -> None:
        reg = ParameterRegistry()
        reg.set("Height", "=Width * 0.5")
        assert reg.get_formula("Height") == "Width * 0.5"

    def test_resolve_value_literal(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        assert reg.resolve_value(50) == 50.0
        assert reg.resolve_value("50") == 50.0

    def test_resolve_value_reference(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        assert reg.resolve_value("*Width") == 100.0

    def test_resolve_value_formula(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        assert reg.resolve_value("=Width * 2") == 200.0

    def test_resolve_value_unknown_reference(self) -> None:
        reg = ParameterRegistry()
        with pytest.raises(ExpressionError, match="Unknown parameter reference"):
            reg.resolve_value("*Foo")

    def test_resolve_value_invalid_string(self) -> None:
        reg = ParameterRegistry()
        with pytest.raises(ExpressionError, match="Cannot resolve"):
            reg.resolve_value("not-a-number")

    def test_parameters_for_bridge_resolves_formulas(self) -> None:
        reg = ParameterRegistry()
        reg.set("Height", 50)
        kwargs = {"height": "=Height * 2", "width": 100, "name": "test"}
        resolved = reg.parameters_for_bridge(kwargs)
        assert resolved["height"] == 100.0
        assert resolved["width"] == 100
        assert resolved["name"] == "test"

    def test_parameters_for_bridge_resolves_references(self) -> None:
        reg = ParameterRegistry()
        reg.set("Thickness", 5)
        kwargs = {"thickness": "*Thickness"}
        resolved = reg.parameters_for_bridge(kwargs)
        assert resolved["thickness"] == 5.0

    def test_parameters_for_bridge_passes_numbers(self) -> None:
        reg = ParameterRegistry()
        reg.set("H", 10)
        kwargs = {"height": 30, "depth": 40.5}
        resolved = reg.parameters_for_bridge(kwargs)
        assert resolved["height"] == 30
        assert resolved["depth"] == 40.5


class TestDesignTable:
    """Tests for design table CSV loading and application."""

    def test_load_design_table(self) -> None:
        reg = ParameterRegistry()
        csv_data = "Width,Height,Thickness\n100,50,5\n200,80,8\n"
        rows = reg.load_design_table(csv_data)
        assert len(rows) == 2
        assert rows[0] == {"Width": "100", "Height": "50", "Thickness": "5"}
        assert rows[1] == {"Width": "200", "Height": "80", "Thickness": "8"}

    def test_load_design_table_empty_columns(self) -> None:
        reg = ParameterRegistry()
        csv_data = "Width,Height\n100,50\n"
        rows = reg.load_design_table(csv_data)
        assert len(rows) == 1
        assert rows[0]["Width"] == "100"
        assert rows[0]["Height"] == "50"

    def test_load_design_table_single_row(self) -> None:
        reg = ParameterRegistry()
        csv_data = "Width\n100\n"
        rows = reg.load_design_table(csv_data)
        assert len(rows) == 1
        assert rows[0]["Width"] == "100"

    def test_apply_design_row(self) -> None:
        reg = ParameterRegistry()
        row = {"Width": "200", "Height": "80"}
        set_params = reg.apply_design_row(row)
        assert set(set_params) == {"Width", "Height"}
        assert reg.get("Width") == 200.0
        assert reg.get("Height") == 80.0

    def test_apply_design_row_with_prefix(self) -> None:
        reg = ParameterRegistry()
        row = {"Width": "150"}
        set_params = reg.apply_design_row(row, append_prefix="V1_")
        assert "V1_Width" in set_params
        assert reg.get("V1_Width") == 150.0

    def test_apply_design_row_text_value(self) -> None:
        """Non-numeric values are skipped (registry only handles numbers)."""
        reg = ParameterRegistry()
        row = {"Width": "100", "Description": "Panel A"}
        set_params = reg.apply_design_row(row)
        assert "Width" in set_params
        # Description was not stored (non-numeric)
        assert not reg.has("Description")


class TestConfigurationManagement:
    """Tests for named configuration save/load/delete."""

    def test_save_empty(self) -> None:
        reg = ParameterRegistry()
        snap = reg.save_configuration("Empty")
        assert snap == {}
        assert reg.list_configurations() == {"Empty": {}}

    def test_save_and_list(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("Height", 50)
        reg.save_configuration("Small")
        configs = reg.list_configurations()
        assert "Small" in configs
        assert configs["Small"]["Width"] == 100.0
        assert configs["Small"]["Height"] == 50.0

    def test_save_multiple(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.save_configuration("Small")
        reg.set("Width", 200)
        reg.save_configuration("Large")
        configs = reg.list_configurations()
        assert len(configs) == 2
        assert configs["Small"]["Width"] == 100.0
        assert configs["Large"]["Width"] == 200.0

    def test_save_resolves_formulas(self) -> None:
        """Saved configurations store resolved values, not formulas."""
        reg = ParameterRegistry()
        reg.set("A", 10)
        reg.set("B", "=A * 2")
        snap = reg.save_configuration("Test")
        assert snap["B"] == 20.0  # resolved value

    def test_load_replaces_all_params(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("Height", 50)
        reg.save_configuration("Original")
        # Change params
        reg.set("Width", 999)
        reg.set("Height", 999)
        # Load back
        reg.load_configuration("Original")
        assert reg.get("Width") == 100.0
        assert reg.get("Height") == 50.0

    def test_load_clears_old_params(self) -> None:
        """load_configuration replaces all params, not just config ones."""
        reg = ParameterRegistry()
        reg.set("A", 1)
        reg.save_configuration("Cfg")
        reg.set("Extra", 999)
        reg.load_configuration("Cfg")
        # 'Extra' should be gone
        assert reg.has("Extra") is False

    def test_load_clears_formulas(self) -> None:
        reg = ParameterRegistry()
        reg.set("A", "=B + 1")
        reg.set("B", 5)
        reg.save_configuration("Cfg")
        # After load, A and B are plain values, not formulas
        reg.load_configuration("Cfg")
        assert reg.get_formula("A") is None
        assert reg.get_formula("B") is None
        assert reg.get("A") == 6.0

    def test_load_nonexistent_raises(self) -> None:
        reg = ParameterRegistry()
        with pytest.raises(ExpressionError, match="Configuration not found"):
            reg.load_configuration("NoSuch")

    def test_get_configuration_found(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.save_configuration("Small")
        cfg = reg.get_configuration("Small")
        assert cfg is not None
        assert cfg["Width"] == 100.0

    def test_get_configuration_not_found(self) -> None:
        reg = ParameterRegistry()
        assert reg.get_configuration("NoSuch") is None

    def test_delete_existing(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.save_configuration("Small")
        assert reg.delete_configuration("Small") is True
        assert reg.list_configurations() == {}

    def test_delete_nonexistent(self) -> None:
        reg = ParameterRegistry()
        assert reg.delete_configuration("NoSuch") is False

    def test_complex_scenario(self) -> None:
        """Save multiple configs, modify params, switch between them."""
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("Height", 50)
        reg.save_configuration("Small")
        reg.set("Width", 200)
        reg.set("Height", 80)
        reg.save_configuration("Medium")
        reg.set("Width", 300)
        reg.set("Height", 120)
        reg.save_configuration("Large")

        # Switch back to Small
        reg.load_configuration("Small")
        assert reg.get("Width") == 100.0
        assert reg.get("Height") == 50.0

        # Switch back to Large
        reg.load_configuration("Large")
        assert reg.get("Width") == 300.0
        assert reg.get("Height") == 120.0

        assert len(reg.list_configurations()) == 3


class TestConcurrency:
    """Tests for thread safety of ParameterRegistry."""

    def test_concurrent_set_and_list(self) -> None:
        import threading

        reg = ParameterRegistry()
        errors: list[Exception] = []

        def setter() -> None:
            try:
                for i in range(100):
                    reg.set(f"K{i}", i)
            except Exception as e:
                errors.append(e)

        def lister() -> None:
            try:
                for _ in range(100):
                    reg.list_all()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=setter), threading.Thread(target=lister)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_set_and_delete(self) -> None:
        import threading

        reg = ParameterRegistry()
        for i in range(50):
            reg.set(f"Del{i}", i)
        errors: list[Exception] = []

        def setter() -> None:
            try:
                for i in range(50):
                    reg.set(f"New{i}", i)
            except Exception as e:
                errors.append(e)

        def deleter() -> None:
            try:
                for i in range(50):
                    reg.delete(f"Del{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=setter), threading.Thread(target=deleter)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_get_nonexistent_returns_none(self) -> None:
        reg = ParameterRegistry()
        assert reg.get("nonexistent") is None

    def test_delete_nonexistent_no_error(self) -> None:
        reg = ParameterRegistry()
        reg.delete("nonexistent")

    def test_load_design_table_empty_csv(self) -> None:
        reg = ParameterRegistry()
        reg.load_design_table("")

    def test_load_design_table_single_column(self) -> None:
        reg = ParameterRegistry()
        reg.load_design_table("Width\n")

    def test_set_empty_key_raises_error(self) -> None:
        reg = ParameterRegistry()
        with pytest.raises(ExpressionError, match="Cannot parse"):
            reg.set("", "abc")

    def test_list_all_with_meta_all_entries(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.set("Height", "=Width * 0.5")
        meta = reg.list_all_with_meta()
        assert len(meta) == 2
        for entry in meta:
            assert "name" in entry
            assert "value" in entry

    def test_save_configuration_overwrite(self) -> None:
        reg = ParameterRegistry()
        reg.set("Width", 100)
        reg.save_configuration("Config")
        reg.set("Width", 200)
        reg.save_configuration("Config")
        reg.set("Width", 300)
        reg.load_configuration("Config")
        assert reg.get("Width") == 200.0
