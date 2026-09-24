"""Place native BIM windows chosen from the nanoCAD object library."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge


_ENGINE_REQUIRED = "The in-process nanoCAD BIM engine is required for library windows"
_PLUGIN_REQUIRED = "BIM window endpoint is unavailable; rebuild and load the .NET plugin"


class BimWindowUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    def list_bim_windows(self) -> dict[str, Any]:
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.list_bim_windows()
        if result is None:
            raise NotSupportedError(_PLUGIN_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "BIM library query failed"))
        return result

    def create_bim_window(
        self,
        wall_handle: str,
        library_name: str,
        position: float | None = None,
        sill_height: float = 700,
        opening_depth: float = 120,
    ) -> dict[str, Any]:
        if not wall_handle or not library_name:
            raise ValueError("wall_handle and library_name are required")  # noqa: TRY003
        values = (sill_height, opening_depth)
        if position is not None:
            values += (position,)
        if (
            any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                for value in values
            )
            or sill_height < 0
            or opening_depth <= 0
        ):
            raise ValueError("Window dimensions must be finite and positive")  # noqa: TRY003
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.create_bim_window(
            {
                "wall_handle": wall_handle,
                "library_name": library_name,
                "position": position,
                "sill_height": sill_height,
                "opening_depth": opening_depth,
            }
        )
        if result is None:
            raise NotSupportedError(_PLUGIN_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "Native BIM window insertion failed"))
        if not result.get("handle") or result.get("entity_type") != "BuildingOpening":
            raise RuntimeError("BIM window endpoint returned no native opening")  # noqa: TRY003
        return result
