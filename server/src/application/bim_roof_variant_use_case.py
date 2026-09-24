"""Native dome, loft and sweep roof factories in ncBIM SDK 26."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge

_ENGINE_REQUIRED = "The in-process nanoCAD BIM engine is required"
_ENDPOINT_REQUIRED = "BIM roof variant endpoint is unavailable"


class BimRoofVariantUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    @staticmethod
    def _valid_contour(points: list[list[float]]) -> bool:
        return len(points) >= 3 and all(
            len(point) == 2 and all(
                isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)
                for v in point
            )
            for point in points
        )

    def _create(
        self,
        kind: str,
        contour_a: list[list[float]],
        contour_b: list[list[float]] | None = None,
        *,
        base_z: float = 0,
        thickness: float = 0,
        height: float = 0,
    ) -> dict[str, Any]:
        if not self._valid_contour(contour_a) or (
            kind != "dome" and not self._valid_contour(contour_b or [])
        ):
            raise ValueError("Each roof contour needs at least three finite XY pairs")  # noqa: TRY003
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.create_bim_roof_variant(
            {
                "kind": kind,
                "contour_a": contour_a,
                "contour_b": contour_b or [],
                "base_z": base_z,
                "thickness": thickness,
                "height": height,
            }
        )
        if result is None:
            raise NotSupportedError(_ENDPOINT_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "BIM roof creation failed"))
        if not result.get("handle"):
            raise RuntimeError("BIM roof endpoint returned no native entity")  # noqa: TRY003
        return result

    def create_bim_dome_roof(
        self, contour: list[list[float]], thickness: float, base_z: float = 0
    ) -> dict[str, Any]:
        return self._create("dome", contour, base_z=base_z, thickness=thickness)

    def create_bim_loft_roof(
        self, contour_a: list[list[float]], contour_b: list[list[float]],
        height: float, base_z: float = 0,
    ) -> dict[str, Any]:
        return self._create("loft", contour_a, contour_b, height=height, base_z=base_z)

    def create_bim_sweep_roof(
        self, contour_a: list[list[float]], contour_b: list[list[float]],
        base_z: float = 0,
    ) -> dict[str, Any]:
        return self._create("sweep", contour_a, contour_b, base_z=base_z)
