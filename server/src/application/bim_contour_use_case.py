"""Native contour based architecture objects in nanoCAD BIM SDK 26."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge


_ENGINE_REQUIRED = "The in-process nanoCAD BIM engine is required"
_ENDPOINT_REQUIRED = "Native BIM contour endpoint is unavailable"


class BimContourUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    def _create(
        self,
        kind: str,
        points: list[list[float]],
        *,
        base_z: float = 0,
        height: float = 0,
        thickness: float = 0,
        angle: float = 45,
        overhang: float = 150,
        name: str | None = None,
        number: str | None = None,
    ) -> dict[str, Any]:
        if len(points) < 3 or any(
            len(point) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                for value in point
            )
            for point in points
        ):
            raise ValueError("points must be at least three finite XY pairs")  # noqa: TRY003
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.create_bim_contour(
            {
                "kind": kind,
                "points": points,
                "base_z": base_z,
                "height": height,
                "thickness": thickness,
                "angle": angle,
                "overhang": overhang,
                "name": name,
                "number": number,
            }
        )
        if result is None:
            raise NotSupportedError(_ENDPOINT_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "Native BIM creation failed"))
        if not result.get("handle"):
            raise RuntimeError("BIM contour endpoint returned no native entity")  # noqa: TRY003
        return result

    def create_bim_slab(
        self, points: list[list[float]], thickness: float, base_z: float = 0
    ) -> dict[str, Any]:
        return self._create("slab", points, thickness=thickness, base_z=base_z)

    def create_bim_roof(
        self,
        points: list[list[float]],
        thickness: float,
        base_z: float = 0,
        angle: float = 45,
        overhang: float = 150,
    ) -> dict[str, Any]:
        return self._create(
            "roof", points, thickness=thickness, base_z=base_z,
            angle=angle, overhang=overhang,
        )

    def create_bim_space(
        self,
        points: list[list[float]],
        height: float,
        name: str | None = None,
        number: str | None = None,
    ) -> dict[str, Any]:
        return self._create("space", points, height=height, name=name, number=number)
