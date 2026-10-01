"""Contracts for BuildingRoofUI slope creation and contour edits."""

from unittest.mock import Mock

import pytest

from src.application.bim_roof_edit_use_case import BimRoofEditUseCase
from src.application.use_case_factory import UseCaseFactory
from src.domain.exceptions import NotSupportedError
from src.infrastructure.http_bridge import HttpCadBridge
from src.presentation.server import _TOOL_HANDLER_MAP
from src.presentation.tool_defs import TOOL_DEFS


OUTLINE = [[0, 0], [4, 0], [4, 4], [2, 2], [0, 4]]
START = [0, 0, 3000]
END = [4000, 0, 3000]


def make_bridge(result=None):
    bridge = Mock(is_available=True)
    bridge.bim_roof_operation.return_value = {"success": True, "handle": "A1"} if result is None else result
    return bridge


def slope(**changes):
    return {"start": START, "end": END, "points": OUTLINE, **changes}


def test_create_one_roof_slope_applies_defaults_and_wraps_batch_payload():
    bridge = make_bridge()
    result = BimRoofEditUseCase(bridge).create_bim_roof_slope(START, END, OUTLINE)
    assert result["handle"] == "A1"
    bridge.bim_roof_operation.assert_called_once_with(
        "create-slopes",
        {"slopes": [slope(angle=45, thickness=150)]},
    )


def test_create_many_roof_slopes_normalizes_defaults_and_is_atomic_on_invalid_member():
    bridge = make_bridge()
    batch = [slope(thickness=180), slope(angle=30)]
    BimRoofEditUseCase(bridge).create_bim_roof_slopes(batch)
    bridge.bim_roof_operation.assert_called_once_with(
        "create-slopes",
        {"slopes": [slope(angle=45, thickness=180), slope(angle=30, thickness=150)]},
    )

    bridge.reset_mock()
    with pytest.raises(ValueError, match="horizontal"):
        BimRoofEditUseCase(bridge).create_bim_roof_slopes(
            [slope(), slope(end=[4000, 0, 3100])]
        )
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize("slopes", [[], [slope()] * 33, None, "bad"])
def test_slope_batch_rejects_invalid_count_or_container(slopes):
    bridge = make_bridge()
    with pytest.raises(ValueError, match="1 to 32"):
        BimRoofEditUseCase(bridge).create_bim_roof_slopes(slopes)
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize(
    "item",
    [
        None,
        {"start": START, "end": END},
        slope(unexpected=True),
    ],
)
def test_slope_batch_rejects_malformed_definitions(item):
    bridge = make_bridge()
    with pytest.raises(ValueError, match="slope definition"):
        BimRoofEditUseCase(bridge).create_bim_roof_slopes([item])
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize(
    ("start", "end", "points", "angle", "thickness", "message"),
    [
        ([0, 0], END, OUTLINE, 45, 150, "bounded numeric array"),
        ([0, 0, float("nan")], END, OUTLINE, 45, 150, "finite numeric"),
        (START, [0, 0, 3000], OUTLINE, 45, 150, "baseline"),
        (START, (0, 0, 3000), OUTLINE, 45, 150, "baseline"),
        (START, [4000, 0, 3001], OUTLINE, 45, 150, "baseline"),
        (START, END, OUTLINE, 0, 150, "angle"),
        (START, END, OUTLINE, 90, 150, "angle"),
        (START, END, OUTLINE, 45, 0, "thickness"),
        (START, END, [[0, 0], [2, 2], [0, 2], [1, 0]], 45, 150, "self-intersect"),
    ],
)
def test_slope_creation_rejects_invalid_geometry(start, end, points, angle, thickness, message):
    bridge = make_bridge()
    with pytest.raises(ValueError, match=message):
        BimRoofEditUseCase(bridge).create_bim_roof_slope(start, end, points, angle, thickness)
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize(
    ("method", "operation"),
    [
        ("add_bim_roof_contour", "roof-add"),
        ("cut_bim_roof_contour", "roof-cut"),
        ("update_bim_roof_contour", "roof-update"),
    ],
)
def test_roof_contour_edits_send_valid_xy_outline(method, operation):
    bridge = make_bridge()
    getattr(BimRoofEditUseCase(bridge), method)("A1", OUTLINE)
    bridge.bim_roof_operation.assert_called_once_with(
        operation, {"handle": "A1", "points": OUTLINE}
    )


@pytest.mark.parametrize(
    ("method", "operation"),
    [
        ("add_bim_roof_slope_contour", "slope-add"),
        ("cut_bim_roof_slope_contour", "slope-cut"),
        ("update_bim_roof_slope_contour", "slope-update"),
    ],
)
def test_slope_contour_edits_validate_xyz_and_project_to_simple_xy(method, operation):
    bridge = make_bridge()
    points = [[0, 0, 100], [4, 0, 200], [4, 4, 300], [2, 2, 400], [0, 4, 500]]
    getattr(BimRoofEditUseCase(bridge), method)("A1", points)
    bridge.bim_roof_operation.assert_called_once_with(
        operation, {"handle": "A1", "points": points}
    )


@pytest.mark.parametrize(
    ("method", "points"),
    [
        ("add_bim_roof_contour", [[0, 0], [1, 1]]),
        ("add_bim_roof_contour", [[0, 0], [2, 2], [0, 2], [1, 0]]),
        ("add_bim_roof_slope_contour", [[0, 0, 1], [1, 1, 1]]),
        ("add_bim_roof_slope_contour", [[0, 0, 1], [2, 2, 1], [0, 2, 1], [1, 0, 1]]),
        ("add_bim_roof_slope_contour", [[0, 0, 1], [1, 0, 2], [0, 1, float("inf")]]),
    ],
)
def test_roof_contours_reject_invalid_vertices_before_bridge_call(method, points):
    bridge = make_bridge()
    with pytest.raises(ValueError):
        getattr(BimRoofEditUseCase(bridge), method)("A1", points)
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize("handle", ["0", "bad!", "8000000000000000"])
def test_roof_contours_reject_invalid_entity_handles(handle):
    bridge = make_bridge()
    with pytest.raises(ValueError, match="signed-64-bit"):
        BimRoofEditUseCase(bridge).add_bim_roof_contour(handle, OUTLINE)
    bridge.bim_roof_operation.assert_not_called()


@pytest.mark.parametrize(
    ("result", "message"),
    [(None, "endpoint is unavailable"), ({"success": False, "error": "native slope failed"}, "native slope failed")],
)
def test_roof_edit_reports_unavailable_endpoint_and_sdk_failure(result, message):
    bridge = make_bridge()
    bridge.bim_roof_operation.return_value = result
    with pytest.raises(NotSupportedError, match=message):
        BimRoofEditUseCase(bridge).create_bim_roof_slope(START, END, OUTLINE)


@pytest.mark.parametrize("bridge", [None, Mock(is_available=False)])
def test_roof_edit_requires_in_process_engine(bridge):
    with pytest.raises(NotSupportedError, match="in-process"):
        BimRoofEditUseCase(bridge).create_bim_roof_slope(START, END, OUTLINE)


def test_roof_edit_factory_caches_use_case_with_repository_bridge():
    bridge = make_bridge()
    factory = UseCaseFactory(Mock(_http=bridge))
    assert factory.bim_roof_edit is factory.bim_roof_edit
    assert factory.bim_roof_edit._bridge is bridge


def test_roof_edit_tools_are_registered_and_routed_to_domain():
    names = {
        "create_bim_roof_slope",
        "create_bim_roof_slopes",
        "add_bim_roof_contour",
        "cut_bim_roof_contour",
        "update_bim_roof_contour",
        "add_bim_roof_slope_contour",
        "cut_bim_roof_slope_contour",
        "update_bim_roof_slope_contour",
    }
    tools = {item["name"]: item for item in TOOL_DEFS}
    for name in names:
        assert name in tools
        assert _TOOL_HANDLER_MAP[name] == ("bim_roof_edit", name)


def test_bridge_posts_roof_operations_to_sdk_operation_endpoint():
    bridge = HttpCadBridge.__new__(HttpCadBridge)
    bridge._request = Mock(return_value={"success": True})
    payload = {"slopes": [slope(angle=45, thickness=150)]}
    bridge.bim_roof_operation("create-slopes", payload)
    bridge._request.assert_called_once_with(
        "POST", "/api/bim/roof-edit/create-slopes", json_body=payload
    )
