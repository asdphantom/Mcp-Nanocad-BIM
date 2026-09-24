"""Native BIM wall request boundary; never substitutes plain DWG geometry."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge


_ENGINE_REQUIRED = "The in-process nanoCAD engine is required for native BIM walls"
_PLUGIN_REQUIRED = "BIM wall endpoint is unavailable; rebuild and load the .NET plugin"


class BimWallUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    def create_bim_wall(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        base_z: float,
        height: float,
        thickness: float,
        wall_type: str | None = None,
        level: str | None = None,
    ) -> dict[str, Any]:
        values = (x1, y1, x2, y2, base_z, height, thickness)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            for value in values
        ):
            raise ValueError("BIM wall coordinates and dimensions must be finite numbers")  # noqa: TRY003
        if (x1, y1) == (x2, y2) or height <= 0 or thickness <= 0:
            raise ValueError("BIM wall needs distinct endpoints and positive height/thickness")  # noqa: TRY003
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.create_bim_wall(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "base_z": base_z,
                "height": height,
                "thickness": thickness,
                "wall_type": wall_type,
                "level": level,
            }
        )
        if result is None:
            raise NotSupportedError(_PLUGIN_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "Native BIM wall creation failed"))
        if not result.get("handle") or result.get("entity_type") != "LinearBuildingWall":
            raise RuntimeError("BIM wall endpoint returned no native entity identity")  # noqa: TRY003
        return result
