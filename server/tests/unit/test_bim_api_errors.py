"""Failure boundaries shared by native BIM API use cases."""

from unittest.mock import Mock

import pytest

from src.application.bim_contour_use_case import BimContourUseCase
from src.application.bim_roof_variant_use_case import BimRoofVariantUseCase
from src.application.bim_structure_use_case import BimStructureUseCase
from src.application.bim_wall_use_case import BimWallUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.server import _TOOL_HANDLER_MAP
from src.presentation.tool_defs import TOOL_DEFS


POINTS = [[0, 0], [1000, 0], [0, 1000]]
WALL = dict(x1=0, y1=0, x2=1000, y2=0, base_z=0, height=3000, thickness=200)


@pytest.mark.parametrize(
    ("use_case", "method", "args", "bridge_method"),
    [
        (BimContourUseCase, "create_bim_slab", (POINTS, 200), "create_bim_contour"),
        (BimRoofVariantUseCase, "create_bim_dome_roof", (POINTS, 200), "create_bim_roof_variant"),
        (BimStructureUseCase, "create_bim_concrete_beam", ("P", 0, 0, 0, 100, 0, 0), "create_bim_concrete_member"),
    ],
)
def test_native_api_reports_missing_endpoint_and_sdk_failure(use_case, method, args, bridge_method):
    bridge = Mock(is_available=True)
    call = getattr(bridge, bridge_method)
    uc = use_case(bridge)
    call.return_value = None
    with pytest.raises(NotSupportedError, match="unavailable"):
        getattr(uc, method)(*args)
    call.return_value = {"success": False, "error": "SDK rejected request"}
    with pytest.raises(NotSupportedError, match="SDK rejected request"):
        getattr(uc, method)(*args)


@pytest.mark.parametrize(
    ("use_case", "method", "args", "bridge_method", "result", "message"),
    [
        (BimContourUseCase, "create_bim_slab", (POINTS, 200), "create_bim_contour", {"success": True}, "no native entity"),
        (BimStructureUseCase, "create_bim_concrete_beam", ("P", 0, 0, 0, 100, 0, 0), "create_bim_concrete_member", {"success": True, "handle": "A1", "entity_type": "AcDb3dSolid"}, "native member"),
    ],
)
def test_native_api_rejects_incomplete_or_non_native_identity(use_case, method, args, bridge_method, result, message):
    bridge = Mock(is_available=True)
    getattr(bridge, bridge_method).return_value = result
    with pytest.raises(RuntimeError, match=message):
        getattr(use_case(bridge), method)(*args)


def test_wall_missing_endpoint_and_missing_native_identity():
    bridge = Mock(is_available=True)
    uc = BimWallUseCase(bridge)
    bridge.create_bim_wall.return_value = None
    with pytest.raises(NotSupportedError, match="endpoint is unavailable"):
        uc.create_bim_wall(**WALL)
    bridge.create_bim_wall.return_value = {"success": True, "handle": "A1"}
    with pytest.raises(RuntimeError, match="native entity identity"):
        uc.create_bim_wall(**WALL)


@pytest.mark.parametrize(
    ("use_case", "method", "args"),
    [
        (BimContourUseCase, "create_bim_slab", (POINTS, 200)),
        (BimRoofVariantUseCase, "create_bim_dome_roof", (POINTS, 200)),
        (BimStructureUseCase, "get_bim_associations", ("A1",)),
    ],
)
def test_native_api_rejects_missing_or_unavailable_engine(use_case, method, args):
    for bridge in (None, Mock(is_available=False)):
        with pytest.raises(NotSupportedError, match="in-process"):
            getattr(use_case(bridge), method)(*args)


def test_structure_association_requires_native_identity():
    bridge = Mock(is_available=True)
    bridge.create_bim_association.return_value = {
        "success": True,
        "handle": "F1",
        "entity_type": "AcDb3dSolid",
    }
    with pytest.raises(RuntimeError, match="native association"):
        BimStructureUseCase(bridge).create_bim_association("A1", "A2")


@pytest.mark.parametrize(
    ("method", "args", "error"),
    [
        ("get_bim_associations", ("0",), "hexadecimal entity handle"),
        ("create_bim_concrete_beam", ("  ", 0, 0, 0, 100, 0, 0), "profile_name is required"),
        ("create_bim_concrete_beam", ("P", 0, 0, 0, float("nan"), 0, 0), "finite numbers"),
        ("create_bim_concrete_beam", ("P", 0, 0, 0, 0, 0, 0), "nonzero length"),
    ],
)
def test_structure_rejects_invalid_association_and_member_inputs(method, args, error):
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError, match=error):
        getattr(BimStructureUseCase(bridge), method)(*args)
    if method == "get_bim_associations":
        bridge.get_bim_associations.assert_not_called()
    else:
        bridge.create_bim_concrete_member.assert_not_called()


@pytest.mark.parametrize(
    ("tool", "method", "payload", "kwargs"),
    [
        ("shift_bim_wall", "shift_bim_wall", {"handle": "A1", "dx": 10, "dy": -5, "dz": 0}, {"handle": "A1", "dx": 10, "dy": -5}),
        ("get_bim_window_mark", "get_bim_window_mark", {"handle": "A2"}, {"handle": "A2"}),
        ("copy_bim_window_mark", "copy_bim_window_mark", {"source_handle": "A1", "handle": "A2"}, {"source_handle": "A1", "handle": "A2"}),
    ],
)
def test_structure_edit_tools_route_valid_payload(tool, method, payload, kwargs):
    bridge = Mock(is_available=True)
    getattr(bridge, method).return_value = {"success": True, "updated": True}
    assert getattr(BimStructureUseCase(bridge), method)(**kwargs)["success"]
    getattr(bridge, method).assert_called_once_with(payload)
    assert _TOOL_HANDLER_MAP[tool] == ("bim_structure", method)
    assert next(item for item in TOOL_DEFS if item["name"] == tool)["requires_mode"] == "full"


@pytest.mark.parametrize(
    ("method", "args", "bridge_method"),
    [
        ("shift_bim_wall", ("A1", 1, 2), "shift_bim_wall"),
        ("get_bim_window_mark", ("A1",), "get_bim_window_mark"),
        ("copy_bim_window_mark", ("A1", "A2"), "copy_bim_window_mark"),
    ],
)
def test_structure_edit_tools_propagate_sdk_errors(method, args, bridge_method):
    bridge = Mock(is_available=True)
    call = getattr(bridge, bridge_method)
    uc = BimStructureUseCase(bridge)
    call.return_value = None
    with pytest.raises(NotSupportedError, match="endpoint"):
        getattr(uc, method)(*args)
    call.return_value = {"success": False, "error": "invalid native target"}
    with pytest.raises(NotSupportedError, match="invalid native target"):
        getattr(uc, method)(*args)


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("shift_bim_wall", ("0", 1, 2)),
        ("shift_bim_wall", ("A1", float("inf"), 2)),
        ("shift_bim_wall", ("A1", True, 2)),
        ("get_bim_window_mark", ("not-hex",)),
        ("copy_bim_window_mark", ("A1", "A1")),
        ("copy_bim_window_mark", ("A1", "8000000000000000")),
    ],
)
def test_structure_edit_tools_reject_invalid_arguments_before_bridge_call(method, args):
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError):
        getattr(BimStructureUseCase(bridge), method)(*args)
    getattr(bridge, method).assert_not_called()

@pytest.mark.parametrize('method,route', [('shift_bim_wall','shift'), ('get_bim_window_mark','mark'), ('copy_bim_window_mark','copy-mark')])
def test_edit_http_routes(method, route):
    from src.infrastructure.http_bridge import HttpCadBridge
    bridge = HttpCadBridge.__new__(HttpCadBridge)
    bridge._request = Mock(return_value={'success': True})
    payload = {'handle': 'A2', 'source_handle': 'A1', 'dx': -10}
    getattr(bridge, method)(payload)
    bridge._request.assert_called_once_with('POST', '/api/bim/edit/' + route, json_body=payload)


def test_factory_separate_cached_instances():
    from src.application.use_case_factory import UseCaseFactory
    factory = UseCaseFactory(Mock())
    names = [name for name, value in vars(UseCaseFactory).items() if isinstance(value, property)]
    cases = [getattr(factory, name) for name in names]
    assert len({id(case) for case in cases}) == len(names)
    for name, case in zip(names, cases):
        assert getattr(factory, name) is case


@pytest.mark.parametrize('result', [None, {'success': False}, {'success': False, 'error': 'missing library'}])
def test_window_catalog_failure(result):
    from src.application.bim_window_use_case import BimWindowUseCase
    bridge = Mock(is_available=True)
    bridge.list_bim_windows.return_value = result
    with pytest.raises(NotSupportedError):
        BimWindowUseCase(bridge).list_bim_windows()


@pytest.mark.parametrize('result', [None, {'success': False}, {'success': True, 'handle': 'A1', 'entity_type': 'Solid'}])
def test_window_creation_requires_native_result(result):
    from src.application.bim_window_use_case import BimWindowUseCase
    bridge = Mock(is_available=True)
    bridge.create_bim_window.return_value = result
    with pytest.raises((NotSupportedError, RuntimeError)):
        BimWindowUseCase(bridge).create_bim_window('A2', 'Window')

@pytest.mark.parametrize('bridge,kwargs,error', [(None, {}, NotSupportedError), (Mock(is_available=True), {'position': float('nan')}, ValueError)])
def test_window_rejects_invalid_geometry_or_missing_engine(bridge, kwargs, error):
    from src.application.bim_window_use_case import BimWindowUseCase
    with pytest.raises(error):
        BimWindowUseCase(bridge).create_bim_window('A2', 'Window', **kwargs)
