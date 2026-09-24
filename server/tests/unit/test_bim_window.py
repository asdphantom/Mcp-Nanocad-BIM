"""Library BIM window contract through the in-process .NET endpoint."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.application.bim_window_use_case import BimWindowUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.tool_defs import TOOL_DEFS


def test_catalog_and_native_insertion() -> None:
    bridge = Mock(is_available=True)
    bridge.list_bim_windows.return_value = {
        "success": True,
        "windows": [{"name": "Окно двухстворчатое с форточкой"}],
    }
    bridge.create_bim_window.return_value = {
        "success": True,
        "handle": "E59",
        "entity_type": "BuildingOpening",
    }
    uc = BimWindowUseCase(bridge)
    assert uc.list_bim_windows()["windows"]
    result = uc.create_bim_window("E55", "Окно двухстворчатое с форточкой")
    assert result["entity_type"] == "BuildingOpening"
    bridge.create_bim_window.assert_called_once_with(
        {
            "wall_handle": "E55",
            "library_name": "Окно двухстворчатое с форточкой",
            "position": None,
            "sill_height": 700,
            "opening_depth": 120,
        }
    )


def test_rejects_non_native_result() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_window.return_value = {
        "success": True,
        "handle": "A1",
        "entity_type": "AcDb3dSolid",
    }
    with pytest.raises(RuntimeError, match="native opening"):
        BimWindowUseCase(bridge).create_bim_window("E55", "Window")


def test_requires_engine_and_valid_parameters() -> None:
    uc = BimWindowUseCase(Mock(is_available=False))
    with pytest.raises(NotSupportedError, match="in-process"):
        uc.list_bim_windows()
    with pytest.raises(ValueError, match="wall_handle"):
        uc.create_bim_window("", "Window")
    with pytest.raises(ValueError, match="Window dimensions"):
        uc.create_bim_window("E55", "Window", sill_height=-1)


def test_window_tools_require_full_mode() -> None:
    for name in ("list_bim_windows", "create_bim_window"):
        tool = next(item for item in TOOL_DEFS if item["name"] == name)
        assert tool["requires_mode"] == "full"
