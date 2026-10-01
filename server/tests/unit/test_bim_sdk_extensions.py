"""Contracts for native SDK grid, slab contour and window mark operations."""

from unittest.mock import Mock

import pytest

from src.application.bim_sdk_use_case import BimSdkUseCase
from src.application.use_case_factory import UseCaseFactory
from src.domain.exceptions import NotSupportedError
from src.infrastructure.http_bridge import HttpCadBridge
from src.presentation.server import _TOOL_HANDLER_MAP
from src.presentation.tool_defs import TOOL_DEFS


TRIANGLE = [[0, 0], [4, 0], [0, 3]]


def bridge_with_success():
    bridge = Mock(is_available=True)
    bridge.bim_sdk_operation.return_value = {"success": True, "handle": "A1"}
    return bridge


def test_grid_catalog_limit_and_bridge_operation():
    bridge = bridge_with_success()
    assert BimSdkUseCase(bridge).list_bim_coordinate_grids(7)["success"]
    bridge.bim_sdk_operation.assert_called_once_with("grid-list", {"limit": 7})


@pytest.mark.parametrize("limit", [True, False, 0, 501, 1.5, "5"])
def test_grid_catalog_rejects_invalid_limits(limit):
    bridge = bridge_with_success()
    with pytest.raises(ValueError, match="limit"):
        BimSdkUseCase(bridge).list_bim_coordinate_grids(limit)
    bridge.bim_sdk_operation.assert_not_called()


@pytest.mark.parametrize(
    ("method", "circular"),
    [("create_bim_rectangular_grid", False), ("create_bim_circular_grid", True)],
)
def test_grid_creation_sorts_axes_and_sends_complete_native_payload(method, circular):
    bridge = bridge_with_success()
    x = [20, 10] if circular else [20, 0, 10]
    args = ("Grid A", x, [30, 0], [3000, 0])
    result = getattr(BimSdkUseCase(bridge), method)(*args)
    assert result["handle"] == "A1"
    bridge.bim_sdk_operation.assert_called_once_with(
        "grid-create",
        {
            "circular": circular,
            "name": "Grid A",
            "x": [10, 20] if circular else [0, 10, 20],
            "y": [0, 30],
            "z": [0, 3000],
            "origin": [0, 0, 0],
            "direction": [1, 0, 0],
        },
    )


def test_rectangular_grid_keeps_custom_origin_and_direction():
    bridge = bridge_with_success()
    BimSdkUseCase(bridge).create_bim_rectangular_grid(
        "G", [0], [0], [0], origin=[5, 6, 7], direction=[0, 2, 0]
    )
    assert bridge.bim_sdk_operation.call_args.args == (
        "grid-create",
        {
            "circular": False,
            "name": "G",
            "x": [0],
            "y": [0],
            "z": [0],
            "origin": [5, 6, 7],
            "direction": [0, 2, 0],
        },
    )


@pytest.mark.parametrize(
    ("args", "method", "match"),
    [
        ((" ", [1], [1], [1]), "create_bim_rectangular_grid", "grid name"),
        (("x" * 101, [1], [1], [1]), "create_bim_rectangular_grid", "grid name"),
        (("G", [], [1], [1]), "create_bim_rectangular_grid", "numeric array"),
        (("G", [1, 1], [1], [1]), "create_bim_rectangular_grid", "distinct"),
        (("G", [float("nan")], [1], [1]), "create_bim_rectangular_grid", "finite numeric"),
        (("G", [True], [1], [1]), "create_bim_rectangular_grid", "finite numeric"),
        (("G", list(range(101)), [1], [1]), "create_bim_rectangular_grid", "numeric array"),
        (("G", [0], [0], [0], [0, 0]), "create_bim_rectangular_grid", "numeric array"),
        (("G", [0], [0], [0], [0, 0, 0], [0, 0]), "create_bim_rectangular_grid", "numeric array"),
        (("G", [0], [0], [0], [0, 0, float("inf")]), "create_bim_rectangular_grid", "finite numeric"),
        (("G", [0], [0], [0], [0, 0, 0], [0, 0, 1]), "create_bim_rectangular_grid", "horizontal"),
        (("G", [0], [0], [0], [0, 0, 0], [0, 0, 0]), "create_bim_rectangular_grid", "horizontal"),
        (("G", [0], [0], [0]), "create_bim_circular_grid", "radii"),
        (("G", [1], [360], [0]), "create_bim_circular_grid", "angles"),
        (("G", [1], [-1], [0]), "create_bim_circular_grid", "angles"),
    ],
)
def test_grid_creation_rejects_invalid_inputs_before_bridge(args, method, match):
    bridge = bridge_with_success()
    with pytest.raises(ValueError, match=match):
        getattr(BimSdkUseCase(bridge), method)(*args)
    bridge.bim_sdk_operation.assert_not_called()


@pytest.mark.parametrize(
    ("method", "args", "operation", "payload"),
    [
        ("redistribute_bim_grid_axes", ("A1",), "grid-distribute", {"handle": "A1", "axis": "x"}),
        ("redistribute_bim_grid_axes", ("A1", "z"), "grid-distribute", {"handle": "A1", "axis": "z"}),
        ("assign_bim_coordinate_grid", ("A1", "B2"), "grid-assign", {"handle": "A1", "grid_handle": "B2"}),
        ("clear_bim_coordinate_grid", ("A1",), "grid-clear", {"handle": "A1"}),
        ("new_bim_window_mark", ("A1",), "window-new-mark", {"handle": "A1", "prefix": "WIN"}),
        ("new_bim_window_mark", ("A1", "DOOR"), "window-new-mark", {"handle": "A1", "prefix": "DOOR"}),
    ],
)
def test_handle_operations_send_expected_payload(method, args, operation, payload):
    bridge = bridge_with_success()
    assert getattr(BimSdkUseCase(bridge), method)(*args)["success"]
    bridge.bim_sdk_operation.assert_called_once_with(operation, payload)


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("redistribute_bim_grid_axes", ("A1", "q")),
        ("redistribute_bim_grid_axes", ("0", "x")),
        ("assign_bim_coordinate_grid", ("A1", "A1")),
        ("assign_bim_coordinate_grid", ("A1", "8000000000000000")),
        ("clear_bim_coordinate_grid", ("bad!",)),
        ("new_bim_window_mark", ("A1", "")),
        ("new_bim_window_mark", ("A1", "x" * 33)),
        ("new_bim_window_mark", ("A1", "x\n")),
    ],
)
def test_handle_operations_reject_invalid_inputs(method, args):
    bridge = bridge_with_success()
    with pytest.raises(ValueError):
        getattr(BimSdkUseCase(bridge), method)(*args)
    bridge.bim_sdk_operation.assert_not_called()


@pytest.mark.parametrize(
    ("method", "operation"),
    [
        ("add_bim_slab_contour", "slab-add"),
        ("cut_bim_slab_contour", "slab-cut"),
        ("update_bim_slab_contour", "slab-update"),
    ],
)
def test_slab_contour_operations_send_valid_vertices(method, operation):
    bridge = bridge_with_success()
    assert getattr(BimSdkUseCase(bridge), method)("A1", TRIANGLE)["success"]
    bridge.bim_sdk_operation.assert_called_once_with(
        operation, {"handle": "A1", "points": TRIANGLE}
    )


def test_slab_contour_accepts_a_concave_outline():
    bridge = bridge_with_success()
    outline = [[0, 0], [4, 0], [4, 4], [2, 2], [0, 4]]
    BimSdkUseCase(bridge).update_bim_slab_contour("A1", outline)
    bridge.bim_sdk_operation.assert_called_once_with(
        "slab-update", {"handle": "A1", "points": outline}
    )


@pytest.mark.parametrize(
    ("handle", "points", "match"),
    [
        ("0", TRIANGLE, "signed-64-bit"),
        ("A1", [[0, 0], [1, 1]], "3 to 200"),
        ("A1", [[0, 0], [1, 0], [0, True]], "finite numeric"),
        ("A1", [[0, 0], [2, 0], [2, 0], [0, 2]], "distinct"),
        ("A1", [[0, 0], [1, 0], [2, 0]], "nonzero area"),
        ("A1", [[0, 0], [3, 3], [0, 3], [2, 0]], "self-intersect"),
        ("A1", [[0, 0], [2, 0], [1, 0], [1, 2]], "self-intersect"),
    ],
)
def test_slab_contours_reject_invalid_or_self_intersecting_polygons(handle, points, match):
    bridge = bridge_with_success()
    with pytest.raises(ValueError, match=match):
        BimSdkUseCase(bridge).add_bim_slab_contour(handle, points)
    bridge.bim_sdk_operation.assert_not_called()


@pytest.mark.parametrize(
    ("result", "error"),
    [(None, "endpoint is unavailable"), ({"success": False}, "operation failed")],
)
def test_sdk_errors_are_propagated(result, error):
    bridge = bridge_with_success()
    bridge.bim_sdk_operation.return_value = result
    with pytest.raises(NotSupportedError, match=error):
        BimSdkUseCase(bridge).list_bim_coordinate_grids()


@pytest.mark.parametrize("bridge", [None, Mock(is_available=False)])
def test_sdk_operations_require_in_process_engine(bridge):
    with pytest.raises(NotSupportedError, match="in-process"):
        BimSdkUseCase(bridge).list_bim_coordinate_grids()


def test_bim_sdk_factory_caches_use_case_with_configured_bridge():
    bridge = bridge_with_success()
    factory = UseCaseFactory(Mock(_http=bridge))
    assert factory.bim_sdk is factory.bim_sdk
    assert factory.bim_sdk._bridge is bridge


def test_sdk_operations_have_full_mode_tool_routes():
    names = {
        "list_bim_coordinate_grids",
        "create_bim_rectangular_grid",
        "create_bim_circular_grid",
        "redistribute_bim_grid_axes",
        "assign_bim_coordinate_grid",
        "clear_bim_coordinate_grid",
        "add_bim_slab_contour",
        "cut_bim_slab_contour",
        "update_bim_slab_contour",
        "new_bim_window_mark",
    }
    tools = {tool["name"]: tool for tool in TOOL_DEFS}
    for name in names:
        assert _TOOL_HANDLER_MAP[name] == ("bim_sdk", name)
        assert tools[name]["requires_mode"] == "full"


def test_bridge_posts_each_sdk_operation_to_operation_endpoint():
    bridge = HttpCadBridge.__new__(HttpCadBridge)
    bridge._request = Mock(return_value={"success": True})
    payload = {"handle": "A1", "axis": "x"}
    bridge.bim_sdk_operation("grid-distribute", payload)
    bridge._request.assert_called_once_with(
        "POST", "/api/bim/sdk/grid-distribute", json_body=payload
    )
