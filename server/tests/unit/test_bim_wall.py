"""Native BIM wall contract: validates inputs and never reports DWG solids."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.application.bim_wall_use_case import BimWallUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.tool_defs import TOOL_DEFS

ARGS = {"x1": 0, "y1": 0, "x2": 6000, "y2": 0, "base_z": 0, "height": 3300, "thickness": 300}


def test_create_bim_wall_routes_native_payload() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_wall.return_value = {
        "success": True,
        "handle": "A1",
        "entity_type": "LinearBuildingWall",
    }
    assert BimWallUseCase(bridge).create_bim_wall(**ARGS)["handle"] == "A1"
    bridge.create_bim_wall.assert_called_once_with(
        {
            **ARGS,
            "wall_type": None,
            "level": None,
        }
    )


def test_create_bim_wall_never_accepts_unverified_entity() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_wall.return_value = {
        "success": True,
        "handle": "A1",
        "entity_type": "AcDb3dSolid",
    }
    with pytest.raises(RuntimeError, match="native entity identity"):
        BimWallUseCase(bridge).create_bim_wall(**ARGS)


def test_create_bim_wall_reports_sdk_error() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_wall.return_value = {
        "success": False,
        "error": "nBIM API is unavailable",
    }
    with pytest.raises(NotSupportedError, match="nBIM API"):
        BimWallUseCase(bridge).create_bim_wall(**ARGS)


@pytest.mark.parametrize(
    "change",
    [
        {"x2": 0, "y2": 0},
        {"height": 0},
        {"thickness": -1},
        {"x1": float("nan")},
    ],
)
def test_create_bim_wall_rejects_bad_geometry(change: dict) -> None:
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError, match="BIM wall"):
        BimWallUseCase(bridge).create_bim_wall(**(ARGS | change))
    bridge.create_bim_wall.assert_not_called()


def test_create_bim_wall_requires_engine() -> None:
    bridge = Mock(is_available=False)
    with pytest.raises(NotSupportedError, match="in-process"):
        BimWallUseCase(bridge).create_bim_wall(**ARGS)


def test_create_bim_wall_is_full_mode_only() -> None:
    tool = next(item for item in TOOL_DEFS if item["name"] == "create_bim_wall")
    assert tool["requires_mode"] == "full"
    assert "thickness" in tool["required"]
