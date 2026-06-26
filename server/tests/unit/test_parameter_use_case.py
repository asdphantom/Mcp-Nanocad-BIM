"""Unit tests for ParameterUseCase."""

from __future__ import annotations

import pytest

from src.application.parameter_use_case import ParameterUseCase
from src.domain.parameter_registry import get_parameter_registry, set_parameter_registry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset the contextvar-backed registry before each test."""
    from src.domain.parameter_registry import ParameterRegistry

    set_parameter_registry(ParameterRegistry())
    yield
    set_parameter_registry(None)


class TestParameterUseCase:
    """Tests for ParameterUseCase methods."""

    def _make_uc(self) -> ParameterUseCase:
        return ParameterUseCase()

    def test_set_parameter_literal(self) -> None:
        uc = self._make_uc()
        result = uc.set_parameter("Width", 100)
        assert result["success"] is True
        assert result["name"] == "Width"
        assert result["value"] == 100.0

    def test_set_parameter_formula(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        result = uc.set_parameter("PanelWidth", "=Width - 10")
        assert result["success"] is True
        assert result["value"] == 90.0

    def test_get_parameter_found(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100, "Overall width")
        result = uc.get_parameter("Width")
        assert result["success"] is True
        assert result["value"] == 100.0
        assert result["name"] == "Width"

    def test_get_parameter_not_found(self) -> None:
        uc = self._make_uc()
        result = uc.get_parameter("NonExistent")
        assert "error" in result
        assert result["success"] is not True

    def test_list_parameters_empty(self) -> None:
        uc = self._make_uc()
        result = uc.list_parameters()
        assert result["success"] is True
        assert result["count"] == 0
        assert result["parameters"] == []

    def test_list_parameters_with_values(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        uc.set_parameter("Height", 50)
        result = uc.list_parameters()
        assert result["count"] == 2
        names = {p["name"] for p in result["parameters"]}
        assert names == {"Width", "Height"}

    def test_delete_parameter(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        result = uc.delete_parameter("Width")
        assert result["success"] is True
        # Verify it's gone
        assert uc.get_parameter("Width")["success"] is not True

    def test_delete_nonexistent(self) -> None:
        uc = self._make_uc()
        result = uc.delete_parameter("NoSuch")
        assert result["success"] is False

    def test_clear_parameters(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("A", 1)
        uc.set_parameter("B", 2)
        uc.clear_parameters()
        assert uc.list_parameters()["count"] == 0

    def test_evaluate_expression(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        result = uc.evaluate_expression("Width * 2 + 10")
        assert result["success"] is True
        assert result["result"] == 210.0

    def test_evaluate_expression_unknown_param(self) -> None:
        uc = self._make_uc()
        result = uc.evaluate_expression("Foo * 2")
        assert result["success"] is False
        assert "error" in result

    def test_resolve_value_literal(self) -> None:
        uc = self._make_uc()
        result = uc.resolve_value("42")
        assert result["success"] is True
        assert result["resolved"] == 42.0

    def test_resolve_value_reference(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Thickness", 5)
        result = uc.resolve_value("*Thickness")
        assert result["success"] is True
        assert result["resolved"] == 5.0

    def test_resolve_value_formula(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        result = uc.resolve_value("=Width * 2")
        assert result["success"] is True
        assert result["resolved"] == 200.0

    def test_resolve_for_bridge(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Height", 50)
        resolved = uc.resolve_for_bridge(
            height="=Height * 2", width=100, name="test"
        )
        assert resolved["height"] == 100.0
        assert resolved["width"] == 100
        assert resolved["name"] == "test"

    def test_load_design_table(self) -> None:
        uc = self._make_uc()
        csv_data = "Width,Height\n100,50\n200,80\n"
        result = uc.load_design_table(csv_data)
        assert result["success"] is True
        assert result["count"] == 2
        assert result["columns"] == ["Width", "Height"]

    def test_load_design_table_empty(self) -> None:
        uc = self._make_uc()
        result = uc.load_design_table("Width\n")
        assert result["success"] is True
        assert result["count"] == 0

    def test_apply_design_row_valid(self) -> None:
        uc = self._make_uc()
        rows = [{"Width": "200", "Height": "80"}, {"Width": "300", "Height": "100"}]
        result = uc.apply_design_row(0, rows)
        assert result["success"] is True
        assert "Width" in result["applied_parameters"]
        assert result["values"]["Width"] == 200.0

    def test_apply_design_row_second_row(self) -> None:
        uc = self._make_uc()
        rows = [{"Width": "200"}, {"Width": "300"}]
        result = uc.apply_design_row(1, rows)
        assert result["success"] is True
        assert result["values"]["Width"] == 300.0

    def test_apply_design_row_out_of_bounds(self) -> None:
        uc = self._make_uc()
        result = uc.apply_design_row(5, [{"Width": "100"}])
        assert result["success"] is False
        assert "out of range" in result.get("error", "")


class TestConfigurationUseCase:
    """Tests for configuration save/load/list/delete via use case."""

    def _make_uc(self) -> ParameterUseCase:
        return ParameterUseCase()

    def test_save_configuration(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        uc.set_parameter("Height", 50)
        result = uc.save_configuration("Small")
        assert result["success"] is True
        assert result["name"] == "Small"
        assert result["parameters"]["Width"] == 100.0
        assert result["parameters"]["Height"] == 50.0

    def test_save_empty_configuration(self) -> None:
        uc = self._make_uc()
        result = uc.save_configuration("Empty")
        assert result["success"] is True
        assert result["parameters"] == {}

    def test_list_configurations(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        uc.save_configuration("Small")
        uc.set_parameter("Width", 200)
        uc.save_configuration("Large")
        result = uc.list_configurations()
        assert result["success"] is True
        assert result["count"] == 2
        assert "Small" in result["configurations"]
        assert "Large" in result["configurations"]

    def test_list_empty(self) -> None:
        uc = self._make_uc()
        result = uc.list_configurations()
        assert result["count"] == 0
        assert result["configurations"] == {}

    def test_load_configuration(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        uc.set_parameter("Height", 50)
        uc.save_configuration("Original")
        uc.set_parameter("Width", 999)
        result = uc.load_configuration("Original")
        assert result["success"] is True
        assert result["name"] == "Original"
        # Verify Width is restored
        get_result = uc.get_parameter("Width")
        assert get_result["value"] == 100.0

    def test_load_nonexistent(self) -> None:
        uc = self._make_uc()
        result = uc.load_configuration("NoSuch")
        assert result["success"] is False

    def test_delete_existing(self) -> None:
        uc = self._make_uc()
        uc.set_parameter("Width", 100)
        uc.save_configuration("Small")
        result = uc.delete_configuration("Small")
        assert result["success"] is True
        # Verify gone
        assert uc.list_configurations()["count"] == 0

    def test_delete_nonexistent(self) -> None:
        uc = self._make_uc()
        result = uc.delete_configuration("NoSuch")
        assert result["success"] is False
