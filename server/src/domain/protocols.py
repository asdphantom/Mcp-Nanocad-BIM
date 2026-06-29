"""Type protocols for COM objects used by the nanoCAD COM bridge."""

from __future__ import annotations

from typing import Any, Protocol


class ComApplication(Protocol):
    """Protocol for nanoCAD COM Application object."""

    ActiveDocument: Any
    Visible: bool
    ZoomExtents: Any


class ComDocument(Protocol):
    """Protocol for nanoCAD COM Document object."""

    Name: str
    FullName: str
    Saved: bool
    ActiveLayer: Any
    Layers: Any
    ModelSpace: Any
    Utility: Any
    Application: Any

    def Export(self, path: str, fmt: str) -> Any: ...
    def GetVariable(self, name: str) -> Any: ...
    def HandleToObject(self, handle: str) -> Any: ...
    def Save(self) -> Any: ...
    def SaveAs(self, path: str) -> Any: ...
    def SetVariable(self, name: str, value: Any) -> Any: ...


class ComModelSpace(Protocol):
    """Protocol for nanoCAD COM ModelSpace object."""

    Count: int

    def AddArc(self, center: Any, radius: float, sa: float, ea: float) -> Any: ...
    def AddCircle(self, center: Any, radius: float) -> Any: ...
    def AddLightWeightPolyline(self, pts: Any) -> Any: ...
    def AddLine(self, pt1: Any, pt2: Any) -> Any: ...
    def AddPoint(self, pt: Any) -> Any: ...
    def AddText(self, content: str, ins: Any, height: float) -> Any: ...
