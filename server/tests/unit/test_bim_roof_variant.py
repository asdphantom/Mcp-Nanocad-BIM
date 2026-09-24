"""Contracts for SDK native roof variants."""

from unittest.mock import Mock

import pytest

from src.application.bim_roof_variant_use_case import BimRoofVariantUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.tool_defs import TOOL_DEFS

A = [[0, 0], [1500, 0], [0, 2000]]
B = [[0, 0], [1500, 0], [1000, 2000]]


@pytest.mark.parametrize(
    ("method", "args", "kind"),
    [
        ("create_bim_dome_roof", (A, 170), "dome"),
        ("create_bim_loft_roof", (A, B, 8000), "loft"),
        ("create_bim_sweep_roof", (A, B), "sweep"),
    ],
)
def test_native_roof_variant_contract(method: str, args: tuple, kind: str) -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_roof_variant.return_value = {
        "success": True, "handle": "E70", "entity_type": "NativeRoof"
    }
    result = getattr(BimRoofVariantUseCase(bridge), method)(*args)
    assert result["handle"] == "E70"
    assert bridge.create_bim_roof_variant.call_args.args[0]["kind"] == kind
    tool = next(item for item in TOOL_DEFS if item["name"] == method)
    assert tool["requires_mode"] == "full"


def test_rejects_invalid_contour_and_engine() -> None:
    uc = BimRoofVariantUseCase(Mock(is_available=False))
    with pytest.raises(ValueError, match="three finite XY pairs"):
        uc.create_bim_dome_roof([[0, 0], [1, 1]], 170)
    with pytest.raises(NotSupportedError, match="in-process"):
        uc.create_bim_dome_roof(A, 170)


def test_endpoint_errors() -> None:
    bridge = Mock(is_available=True)
    uc = BimRoofVariantUseCase(bridge)
    bridge.create_bim_roof_variant.return_value = None
    with pytest.raises(NotSupportedError, match="endpoint is unavailable"):
        uc.create_bim_dome_roof(A, 170)
    bridge.create_bim_roof_variant.return_value = {"success": False, "error": "invalid roof"}
    with pytest.raises(NotSupportedError, match="invalid roof"):
        uc.create_bim_dome_roof(A, 170)
    bridge.create_bim_roof_variant.return_value = {"success": True}
    with pytest.raises(RuntimeError, match="no native entity"):
        uc.create_bim_dome_roof(A, 170)
