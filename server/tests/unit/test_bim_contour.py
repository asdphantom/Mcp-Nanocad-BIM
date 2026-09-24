"""Contracts for native SDK contour based architecture objects."""

from unittest.mock import Mock

import pytest

from src.application.bim_contour_use_case import BimContourUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.tool_defs import TOOL_DEFS

POINTS = [[0, 0], [6000, 0], [6000, 4000], [0, 4000]]


@pytest.mark.parametrize(
    ("method", "expected_kind", "kwargs"),
    [
        ("create_bim_slab", "slab", {"thickness": 200}),
        ("create_bim_roof", "roof", {"thickness": 200}),
        ("create_bim_space", "space", {"height": 3000}),
    ],
)
def test_native_contour_contract(method: str, expected_kind: str, kwargs: dict) -> None:
    bridge = Mock(is_available=True)
    bridge.create_bim_contour.return_value = {
        "success": True, "handle": "EA", "entity_type": "NativeBimEntity"
    }
    result = getattr(BimContourUseCase(bridge), method)(POINTS, **kwargs)
    assert result["handle"] == "EA"
    payload = bridge.create_bim_contour.call_args.args[0]
    assert payload["kind"] == expected_kind
    assert payload["points"] == POINTS
    tool = next(item for item in TOOL_DEFS if item["name"] == method)
    assert tool["requires_mode"] == "full"


def test_rejects_invalid_contour_and_unavailable_engine() -> None:
    uc = BimContourUseCase(Mock(is_available=False))
    with pytest.raises(ValueError, match="three finite XY pairs"):
        uc.create_bim_slab([[0, 0], [1, 1]], 200)
    with pytest.raises(NotSupportedError, match="in-process"):
        uc.create_bim_slab(POINTS, 200)


def test_native_endpoint_failure_is_reported() -> None:
    bridge = Mock(is_available=True)
    uc = BimContourUseCase(bridge)
    bridge.create_bim_contour.return_value = None
    with pytest.raises(NotSupportedError, match="endpoint is unavailable"):
        uc.create_bim_slab(POINTS, 200)
    bridge.create_bim_contour.return_value = {"success": False, "error": "bad contour"}
    with pytest.raises(NotSupportedError, match="bad contour"):
        uc.create_bim_roof(POINTS, 200)
    bridge.create_bim_contour.return_value = {"success": True}
    with pytest.raises(RuntimeError, match="no native entity"):
        uc.create_bim_space(POINTS, 3000)


def test_rejects_malformed_coordinates() -> None:
    uc = BimContourUseCase(Mock(is_available=True))
    with pytest.raises(ValueError, match="finite XY pairs"):
        uc.create_bim_slab([[0, 0], [100, float("nan")], [0, 100]], 200)
