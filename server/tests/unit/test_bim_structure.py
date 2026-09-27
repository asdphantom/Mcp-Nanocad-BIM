"""Contracts for native nBIM associations and concrete members."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.application.bim_structure_use_case import BimStructureUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.server import _TOOL_HANDLER_MAP
from src.presentation.tool_defs import TOOL_DEFS


def test_association_creation_and_lookup() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_association.return_value = {
        "success": True,
        "handle": "F1",
        "entity_type": "ObjectAssociation",
    }
    bridge.get_bim_associations.return_value = {
        "success": True,
        "entity_handle": "E55",
        "slave_associations": [],
    }
    use_case = BimStructureUseCase(bridge)
    assert use_case.create_bim_association("E55", "E67")["handle"] == "F1"
    bridge.create_bim_association.assert_called_once_with(
        {"master_handle": "E55", "slave_handle": "E67"},
    )
    assert use_case.get_bim_associations("E55")["slave_associations"] == []
    bridge.get_bim_associations.assert_called_once_with("E55")


@pytest.mark.parametrize(
    ("master", "slave"),
    [("", "E67"), ("E55", "bad!"), ("E55", "e55"), ("0", "E67")],
)
def test_association_rejects_invalid_targets(master: str, slave: str) -> None:
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError, match="Association"):
        BimStructureUseCase(bridge).create_bim_association(master, slave)
    bridge.create_bim_association.assert_not_called()


@pytest.mark.parametrize(
    ("kind", "method", "expected"),
    [
        ("beam", "create_bim_concrete_beam", "ConcreteBeam"),
        ("column", "create_bim_concrete_column", "ConcreteColumn"),
    ],
)
def test_concrete_members_use_exact_library_profile(kind: str, method: str, expected: str) -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_concrete_member.return_value = {
        "success": True,
        "handle": "F2",
        "entity_type": expected,
    }
    coordinates = (0, 0, 0, 0, 0, 3000)
    result = getattr(BimStructureUseCase(bridge), method)("Прямоугольный", *coordinates)
    assert result["entity_type"] == expected
    assert bridge.create_bim_concrete_member.call_args.args[0] == {
        "kind": kind,
        "profile_name": "Прямоугольный",
        "x1": 0,
        "y1": 0,
        "z1": 0,
        "x2": 0,
        "y2": 0,
        "z2": 3000,
    }


def test_concrete_column_rejects_slanted_axis() -> None:
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError, match="vertical"):
        BimStructureUseCase(bridge).create_bim_concrete_column("Профиль", 0, 0, 0, 1, 0, 3000)
    bridge.create_bim_concrete_member.assert_not_called()


def test_sdk_failure_and_non_native_result() -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_concrete_member.return_value = {"success": False, "error": "missing profile"}
    with pytest.raises(NotSupportedError, match="missing profile"):
        BimStructureUseCase(bridge).create_bim_concrete_beam("missing", 0, 0, 0, 1000, 0, 0)
    bridge.create_bim_concrete_member.return_value = {
        "success": True,
        "handle": "A1",
        "entity_type": "AcDb3dSolid",
    }
    with pytest.raises(RuntimeError, match="native member"):
        BimStructureUseCase(bridge).create_bim_concrete_beam("Profile", 0, 0, 0, 1000, 0, 0)


def test_new_tools_are_full_mode_and_routed() -> None:
    names = {
        "create_bim_association",
        "get_bim_associations",
        "create_bim_concrete_beam",
        "create_bim_concrete_column",
    }
    tools = {tool["name"]: tool for tool in TOOL_DEFS}
    for name in names:
        assert tools[name]["requires_mode"] == "full"
        assert _TOOL_HANDLER_MAP[name][0] == "bim_structure"
