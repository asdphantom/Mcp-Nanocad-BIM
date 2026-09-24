"""Construction workflows for nanoCAD BIM Строительство via its running COM host.

Wall and slab helpers create DWG solids. The roof helper uses NBIM_ROOF to
create an editable native ncBuildingRoof object.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import psutil
import win32com.client


def _rect(values: list[float]) -> tuple[float, float, float, float]:
    if len(values) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError("Rectangle must contain four finite numbers [x1,y1,x2,y2]")
    x1, y1, x2, y2 = map(float, values)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Rectangle must have positive width and depth")
    return x1, y1, x2, y2


def _positive(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return float(value)


class ConstructionUseCase:
    def _document(self) -> Any:
        app = win32com.client.GetActiveObject("nanoCAD.Application")
        if Path(app.FullName).name.lower() != "ncads.exe":
            raise RuntimeError("The active nanoCAD process is not nanoCAD BIM Строительство")
        return app.ActiveDocument

    @staticmethod
    def _layer(doc: Any, name: str, color: int) -> None:
        try:
            layer = doc.Layers.Item(name)
        except Exception:
            layer = doc.Layers.Add(name)
        layer.Color = color

    @staticmethod
    def _box(doc: Any, rect: tuple[float, float, float, float], base_z: float,
             height: float, layer: str) -> Any:
        x1, y1, x2, y2 = rect
        box = doc.ModelSpace.AddBox(((x1+x2)/2, (y1+y2)/2, base_z+height/2),
                                    x2-x1, y2-y1, height)
        box.Layer = layer
        return box

    def get_construction_status(self) -> dict[str, Any]:
        doc = self._document()
        app = win32com.client.GetActiveObject("nanoCAD.Application")
        processes = [p for p in psutil.process_iter(["name", "cmdline"])
                     if (p.info["name"] or "").lower() == "ncads.exe"]
        building_loaded = any("BIMBuilding" in " ".join(p.info["cmdline"] or [])
                              for p in processes)
        return {"product": "nanoCAD BIM Строительство" if building_loaded else "nanoCAD",
                "version": app.Version, "executable": app.FullName,
                "bim_building_loaded": building_loaded,
                "document": doc.Name, "document_path": doc.FullName,
                "model_entities": doc.ModelSpace.Count,
                "geometry_mode": "DWG solids for walls/slabs; native ncBuildingRoof via NBIM_ROOF"}

    def create_wall_solid(self, x1: float, y1: float, x2: float, y2: float,
                          base_z: float, height: float,
                          layer: str = "BIM_WALL_SOLIDS") -> dict[str, Any]:
        rect = _rect([x1, y1, x2, y2])
        height = _positive(height, "height")
        if not math.isfinite(base_z):
            raise ValueError("base_z must be finite")
        doc = self._document()
        self._layer(doc, layer, 8)
        solid = self._box(doc, rect, base_z, height, layer)
        return {"handle": str(solid.Handle), "layer": layer,
                "volume_mm3": float(solid.Volume), "entity_type": solid.EntityName}

    def create_monolithic_slab(self, rectangles: list[list[float]],
                               base_z: float, thickness: float,
                               openings: list[list[float]] | None = None,
                               layer: str = "BIM_MONOLITHIC_SLAB") -> dict[str, Any]:
        if not rectangles:
            raise ValueError("At least one slab rectangle is required")
        parsed = [_rect(r) for r in rectangles]
        holes = [_rect(r) for r in (openings or [])]
        thickness = _positive(thickness, "thickness")
        if not math.isfinite(base_z):
            raise ValueError("base_z must be finite")
        doc = self._document()
        self._layer(doc, layer, 9)
        slab = self._box(doc, parsed[0], base_z, thickness, layer)
        for rect in parsed[1:]:
            other = self._box(doc, rect, base_z, thickness, layer)
            slab.Boolean(0, other)  # acUnion; nanoCAD deletes the consumed solid
        for rect in holes:
            cutter = self._box(doc, rect, base_z-1, thickness+2, layer)
            slab.Boolean(2, cutter)  # acSubtraction
        return {"handle": str(slab.Handle), "layer": layer,
                "volume_mm3": float(slab.Volume), "entity_type": slab.EntityName,
                "opening_count": len(holes)}

    def insert_construction_plan(self, path: str, z: float,
                                 layer: str = "BIM_PLAN_REFERENCE") -> dict[str, Any]:
        source = Path(path).resolve()
        if source.suffix.lower() != ".dwg" or not source.is_file():
            raise ValueError("path must point to an existing DWG file")
        if not math.isfinite(z):
            raise ValueError("z must be finite")
        doc = self._document()
        self._layer(doc, layer, 7)
        ref = doc.ModelSpace.InsertBlock((0.0, 0.0, float(z)), str(source), 1.0, 1.0, 1.0, 0.0)
        ref.Layer = layer
        return {"handle": str(ref.Handle), "source": str(source),
                "layer": layer, "elevation_mm": z}

    @staticmethod
    def _ensure_material(doc: Any, name: str) -> None:
        if not name or len(name) > 100:
            raise ValueError("material name must contain 1-100 characters")
        try:
            doc.Materials.Item(name)
        except Exception:
            material = doc.Materials.Add(name)
            material.Description = name

    def set_construction_material(self, handle: str,
                                  material: str = "Brick") -> dict[str, Any]:
        """Assign a named DWG material to an existing solid."""
        doc = self._document()
        self._ensure_material(doc, material)
        obj = doc.HandleToObject(handle)
        if obj.EntityName != "AcDb3dSolid":
            raise ValueError("handle must identify a 3D solid")
        obj.Material = material
        return {"handle": handle, "material": obj.Material,
                "entity_type": obj.EntityName}

    def complete_window_opening(self, x1: float, y1: float, x2: float, y2: float,
                                base_z: float, wall_height: float,
                                sill_height: float = 700.0,
                                window_height: float = 1400.0,
                                layer: str = "BIM_BRICK_WALLS",
                                material: str = "Brick") -> dict[str, Any]:
        """Fill a wall gap below and above the clear window opening.

        The caller supplies an existing full-height gap in a wall. The two
        returned solids leave the middle clear for the window frame/glazing.
        """
        rect = _rect([x1, y1, x2, y2])
        wall_height = _positive(wall_height, "wall_height")
        if not isinstance(sill_height, (int, float)) or not math.isfinite(sill_height) or sill_height < 0:
            raise ValueError("sill_height must be non-negative and finite")
        window_height = _positive(window_height, "window_height")
        if sill_height + window_height >= wall_height:
            raise ValueError("sill_height + window_height must be less than wall_height")
        doc = self._document()
        self._layer(doc, layer, 30)
        self._ensure_material(doc, material)
        handles = []
        if sill_height:
            sill = self._box(doc, rect, base_z, sill_height, layer)
            sill.Material = material
            handles.append(str(sill.Handle))
        top = base_z + sill_height + window_height
        lintel = self._box(doc, rect, top, wall_height-sill_height-window_height, layer)
        lintel.Material = material
        handles.append(str(lintel.Handle))
        return {"handles": handles, "material": material, "layer": layer,
                "opening_bottom_mm": base_z+sill_height,
                "opening_top_mm": top, "clear_height_mm": window_height}

    def create_native_roof(self, outline: list[list[float]], bottom_level: float,
                           angle: float = 25.0, overhang: float = 350.0,
                           thickness: float = 80.0,
                           layer: str = "BIM_NATIVE_ROOF") -> dict[str, Any]:
        """Create one editable native ncBuildingRoof from an exterior outline."""
        if not isinstance(outline, list) or len(outline) < 3:
            raise ValueError("outline needs at least three [x,y] vertices")
        points = []
        for point in outline:
            if (not isinstance(point, (list, tuple)) or len(point) != 2 or
                    not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point)):
                raise ValueError("roof vertices must be finite [x,y] pairs")
            points.append((float(point[0]), float(point[1])))
        if points[0] == points[-1]:
            points.pop()
        if len(set(points)) < 3:
            raise ValueError("outline needs three distinct vertices")
        if not isinstance(bottom_level, (int, float)) or not math.isfinite(bottom_level):
            raise ValueError("bottom_level must be finite")
        if not isinstance(angle, (int, float)) or not math.isfinite(angle) or not 0 < angle < 80:
            raise ValueError("angle must be between 0 and 80 degrees")
        if not isinstance(overhang, (int, float)) or not math.isfinite(overhang) or overhang < 0:
            raise ValueError("overhang must be finite and non-negative")
        thickness = _positive(thickness, "thickness")
        if not layer or len(layer) > 100:
            raise ValueError("layer needs 1-100 characters")
        doc = self._document()
        if str(doc.GetVariable("CMDNAMES")).strip():
            raise RuntimeError("Finish the active nanoCAD command first")
        self._layer(doc, layer, 151)
        before = {str(e.Handle) for e in doc.ModelSpace if e.EntityName == "ncBuildingRoof"}
        old_osmode = doc.GetVariable("OSMODE")
        try:
            doc.SetVariable("OSMODE", 0)
            command = "NBIM_ROOF\n" + "".join(f"{x:.6f},{y:.6f}\n" for x, y in points) + "\n"
            doc.SendCommand(command)
            for _ in range(30):
                new = [e for e in doc.ModelSpace if e.EntityName == "ncBuildingRoof"
                       and str(e.Handle) not in before]
                if len(new) == 1 and not str(doc.GetVariable("CMDNAMES")).strip():
                    break
                time.sleep(0.1)
            else:
                doc.SendCommand("\x1b\x1b")
                raise RuntimeError("NBIM_ROOF did not create exactly one roof")
            roof = new[0]
            roof.Angle = float(angle)
            roof.Overhang = float(overhang)
            roof.Thickness = thickness
            roof.BottomLevel = float(bottom_level)
            roof.Layer = layer
            doc.Regen(1)
            return {"handle": str(roof.Handle), "entity_type": roof.EntityName,
                    "layer": layer, "angle_degrees": float(roof.Angle),
                    "overhang_mm": float(roof.Overhang),
                    "thickness_mm": float(roof.Thickness),
                    "bottom_level_mm": float(roof.BottomLevel),
                    "bbox_mm": roof.GetBoundingBox()}
        finally:
            doc.SetVariable("OSMODE", old_osmode)

    def create_pitched_roof_panel(self, x1: float, x2: float, y1: float, y2: float,
                                  z1: float, z2: float, thickness: float = 60.0,
                                  layer: str = "BIM_PROFILED_ROOF",
                                  material: str = "Profiled steel sheeting") -> dict[str, Any]:
        """Create a thin roof panel whose height changes linearly along X."""
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x1,x2,y1,y2,z1,z2)):
            raise ValueError("Roof coordinates must be finite")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Roof footprint must have positive dimensions")
        thickness = _positive(thickness, "thickness")
        dx=x2-x1
        dz=z2-z1
        angle=math.atan2(dz,dx)
        sloped_length=math.hypot(dx,dz)
        center=((x1+x2)/2,(y1+y2)/2,(z1+z2)/2)
        doc=self._document()
        self._layer(doc,layer,151)
        self._ensure_material(doc,material)
        solid=doc.ModelSpace.AddBox(center,sloped_length,y2-y1,thickness)
        solid.Rotate3D(center,(center[0],center[1]+1,center[2]),-angle)
        solid.Layer=layer
        solid.Material=material
        return {"handle":str(solid.Handle),"layer":layer,"material":material,
                "pitch_degrees":math.degrees(abs(angle)),"entity_type":solid.EntityName}
