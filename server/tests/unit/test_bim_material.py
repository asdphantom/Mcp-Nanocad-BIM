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
