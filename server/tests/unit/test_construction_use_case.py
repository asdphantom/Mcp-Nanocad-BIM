"""Checks existing construction helpers that share the BIM MCP tool registry."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.application.construction_use_case import ConstructionUseCase

if TYPE_CHECKING:
    from pathlib import Path


def test_wall_solid_reports_its_actual_dwg_type() -> None:
    uc = ConstructionUseCase()
    doc = MagicMock()
    solid = MagicMock(Handle="A1", Volume=12.0, EntityName="AcDb3dSolid")
    doc.ModelSpace.AddBox.return_value = solid
    with patch.object(uc, "_document", return_value=doc):
        result = uc.create_wall_solid(0, 0, 6000, 300, 0, 3300)
    assert result["entity_type"] == "AcDb3dSolid"
    assert result["handle"] == "A1"
    doc.ModelSpace.AddBox.assert_called_once()


def test_monolithic_slab_unions_and_subtracts() -> None:
    uc = ConstructionUseCase()
    doc = MagicMock()
    slab = MagicMock(Handle="S1", Volume=100.0, EntityName="AcDb3dSolid")
    doc.ModelSpace.AddBox.side_effect = [slab, MagicMock(), MagicMock()]
    with patch.object(uc, "_document", return_value=doc):
        result = uc.create_monolithic_slab(
            [[0, 0, 1000, 1000], [1000, 0, 2000, 1000]],
            3000,
            200,
            [[500, 500, 700, 700]],
        )
    assert result["opening_count"] == 1
    assert [call.args[0] for call in slab.Boolean.call_args_list] == [0, 2]


def test_insert_plan_uses_existing_dwg(tmp_path: Path) -> None:
    uc = ConstructionUseCase()
    dwg = tmp_path / "plan.dwg"
    dwg.write_bytes(b"test")
    doc = MagicMock()
    ref = MagicMock(Handle="B1")
    doc.ModelSpace.InsertBlock.return_value = ref
    with patch.object(uc, "_document", return_value=doc):
        result = uc.insert_construction_plan(str(dwg), 3300)
    assert result["handle"] == "B1"
    assert result["elevation_mm"] == 3300


def test_window_opening_creates_sill_and_lintel() -> None:
    uc = ConstructionUseCase()
    doc = MagicMock()
    sill = MagicMock(Handle="S")
    lintel = MagicMock(Handle="L")
    with (
        patch.object(uc, "_document", return_value=doc),
        patch.object(uc, "_ensure_material"),
        patch.object(uc, "_box", side_effect=[sill, lintel]),
    ):
        result = uc.complete_window_opening(
            0,
            0,
            1000,
            300,
            base_z=0,
            wall_height=3300,
            sill_height=700,
            window_height=1400,
        )
    assert result["handles"] == ["S", "L"]
    assert result["opening_bottom_mm"] == 700
    assert result["opening_top_mm"] == 2100


def test_pitched_panel_reports_solid_geometry() -> None:
    uc = ConstructionUseCase()
    doc = MagicMock()
    solid = MagicMock(Handle="R1", EntityName="AcDb3dSolid")
    doc.ModelSpace.AddBox.return_value = solid
    with (
        patch.object(uc, "_document", return_value=doc),
        patch.object(uc, "_ensure_material"),
    ):
        result = uc.create_pitched_roof_panel(0, 3000, 0, 4000, 3000, 4000)
    assert result["entity_type"] == "AcDb3dSolid"
    assert result["pitch_degrees"] > 0
    solid.Rotate3D.assert_called_once()


def test_construction_status_identifies_loaded_bim_module() -> None:
    uc = ConstructionUseCase()
    doc = MagicMock(Name="test.dwg", FullName="C:\\test.dwg")
    doc.ModelSpace.Count = 2
    app = MagicMock(Version="26.0", FullName="C:\\Program Files\\nCadS.exe")
    process = MagicMock()
    process.info = {"name": "nCadS.exe", "cmdline": ["-r", "BIMBuilding"]}
    with (
        patch.object(uc, "_document", return_value=doc),
        patch(
            "src.application.construction_use_case.win32com.client.GetActiveObject",
            return_value=app,
        ),
        patch("src.application.construction_use_case.psutil.process_iter", return_value=[process]),
    ):
        result = uc.get_construction_status()
    assert result["bim_building_loaded"] is True
    assert result["model_entities"] == 2


def test_construction_rejects_invalid_slabs_and_openings() -> None:
    uc = ConstructionUseCase()
    with pytest.raises(ValueError, match="At least one slab"):
        uc.create_monolithic_slab([], 0, 200)
    with pytest.raises(ValueError, match="sill_height"):
        uc.complete_window_opening(0, 0, 100, 100, 0, 3000, 2000, 1500)
