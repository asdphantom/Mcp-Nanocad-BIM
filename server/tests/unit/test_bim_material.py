from unittest.mock import Mock
import pytest
from src.application.bim_material_use_case import BimMaterialUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.server import _TOOL_HANDLER_MAP
from src.presentation.tool_defs import TOOL_DEFS
from src.infrastructure.http_bridge import HttpCadBridge

@pytest.mark.parametrize('name,scope', [('list_bim_library_materials','library'),('list_bim_project_materials','project'),('list_bim_used_materials','used')])
def test_reads_dispatch_to_correct_catalog(name,scope):
    bridge=Mock(is_available=True)
    bridge.list_bim_materials.return_value={'success':True,'materials':[]}
    getattr(BimMaterialUseCase(bridge),name)(name='бетон',limit=5)
    bridge.list_bim_materials.assert_called_once_with(scope,'бетон',5)

@pytest.mark.parametrize('handle,material', [('0','БТ-001'),('bad!','БТ-001'),('8000000000000000','БТ-001'),('A1',''),('A1','x\n')])
def test_invalid_assignment_never_writes(handle,material):
    bridge=Mock(is_available=True)
    with pytest.raises(ValueError):BimMaterialUseCase(bridge).assign_bim_material(handle,material)
    bridge.assign_bim_material.assert_not_called()

@pytest.mark.parametrize('limit',[True,0,501,1.5])
def test_invalid_limits_never_read(limit):
    bridge=Mock(is_available=True)
    with pytest.raises(ValueError):BimMaterialUseCase(bridge).list_bim_project_materials(limit=limit)
    bridge.list_bim_materials.assert_not_called()

def test_material_not_in_project_fails_without_com_fallback():
    bridge=Mock(is_available=True)
    bridge.assign_bim_material.return_value={'success':False,'error':'Add this material to the project first'}
    with pytest.raises(NotSupportedError):BimMaterialUseCase(bridge).assign_bim_material('A1','БТ-001')
    with pytest.raises(NotSupportedError):BimMaterialUseCase(None).list_bim_project_materials()

def test_write_payload_and_tool_routing():
    bridge=Mock(is_available=True)
    bridge.add_bim_project_material.return_value={'success':True,'added':False}
    bridge.assign_bim_material.return_value={'success':True,'material_id':'БТ-001'}
    uc=BimMaterialUseCase(bridge)
    assert not uc.add_bim_project_material('БТ-001')['added']
    uc.assign_bim_material('A1','БТ-001')
    bridge.assign_bim_material.assert_called_once_with({'handle':'A1','material_id':'БТ-001'})
    names={'list_bim_library_materials','list_bim_project_materials','list_bim_used_materials','add_bim_project_material','assign_bim_material'}
    assert names <= {d['name'] for d in TOOL_DEFS}
    for name in names:assert _TOOL_HANDLER_MAP[name]==('bim_material',name)

def test_bridge_preserves_filter_and_payload():
    bridge=HttpCadBridge.__new__(HttpCadBridge)
    bridge._request=Mock(return_value={'success':True})
    bridge.list_bim_materials('project','a&b',5)
    assert 'name=a%26b' in bridge._request.call_args.args[1]
    bridge.assign_bim_material({'handle':'A1','material_id':'БТ-001'})
    bridge._request.assert_called_with('POST','/api/bim/materials/assign',json_body={'handle':'A1','material_id':'БТ-001'})


@pytest.mark.parametrize('name', [1, 'x' * 101])
def test_invalid_name_never_reads(name):
    bridge = Mock(is_available=True)
    with pytest.raises(ValueError):
        BimMaterialUseCase(bridge).list_bim_library_materials(name=name)
    bridge.list_bim_materials.assert_not_called()


@pytest.mark.parametrize('material_id', ['', '   ', 'x' * 101, 'x\x00y', None, 7])
def test_invalid_material_id_never_writes(material_id):
    bridge = Mock(is_available=True)
    uc = BimMaterialUseCase(bridge)
    with pytest.raises(ValueError):
        uc.add_bim_project_material(material_id)
    with pytest.raises(ValueError):
        uc.assign_bim_material('A1', material_id)
    bridge.add_bim_project_material.assert_not_called()
    bridge.assign_bim_material.assert_not_called()


def test_assignment_rejects_non_string_and_overflow_handles():
    bridge = Mock(is_available=True)
    for handle in (None, 10, '8000000000000000'):
        with pytest.raises(ValueError):
            BimMaterialUseCase(bridge).assign_bim_material(handle, 'БТ-001')
    bridge.assign_bim_material.assert_not_called()


def test_material_add_payload_and_shared_call_error_boundaries():
    bridge = Mock(is_available=True)
    bridge.add_bim_project_material.return_value = {'success': True, 'added': True}
    assert BimMaterialUseCase(bridge).add_bim_project_material('БТ-001')['added']
    bridge.add_bim_project_material.assert_called_once_with({'material_id': 'БТ-001'})

    bridge.list_bim_materials.return_value = None
    with pytest.raises(NotSupportedError, match='endpoint'):
        BimMaterialUseCase(bridge).list_bim_library_materials()
    bridge.list_bim_materials.return_value = {'success': False}
    with pytest.raises(NotSupportedError, match='operation failed'):
        BimMaterialUseCase(bridge).list_bim_project_materials()


def test_material_factory_caches_use_case_and_uses_repository_bridge():
    from src.application.use_case_factory import UseCaseFactory

    bridge = Mock(is_available=True)
    factory = UseCaseFactory(Mock(_http=bridge))
    assert factory.bim_material is factory.bim_material
    factory.bim_material.list_bim_used_materials()
    bridge.list_bim_materials.assert_called_once_with('used', None, 50)


@pytest.mark.parametrize('property_name', [
    'bim_library', 'bim_roof_variant', 'bim_contour', 'bim_window',
    'bim_wall', 'bim_material', 'bim_structure',
])
def test_factory_caches_native_bim_use_cases(property_name):
    from src.application.use_case_factory import UseCaseFactory

    bridge = Mock(is_available=True)
    factory = UseCaseFactory(Mock(_http=bridge))
    use_case = getattr(factory, property_name)
    assert getattr(factory, property_name) is use_case
    assert use_case._bridge is bridge
