"""Native nBIM associations and concrete structural members."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge


_HANDLE = re.compile(r"[0-9a-fA-F]+\Z")
_ENGINE_REQUIRED = "The in-process nanoCAD BIM engine is required"
_PLUGIN_REQUIRED = "Native BIM structure endpoint is unavailable; rebuild the plugin"


class BimStructureUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    def _call(self, method: str, *args: Any) -> dict[str, Any]:
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result: dict[str, Any] | None = getattr(self._bridge, method)(*args)
        if result is None:
            raise NotSupportedError(_PLUGIN_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "Native BIM operation failed"))
        return result

    @staticmethod
    def _handle(value: str) -> bool:
        return isinstance(value, str) and bool(_HANDLE.fullmatch(value)) and int(value, 16) > 0

    def create_bim_association(self, master_handle: str, slave_handle: str) -> dict[str, Any]:
        if not self._handle(master_handle) or not self._handle(slave_handle):
            raise ValueError("Association requires hexadecimal entity handles")  # noqa: TRY003
        if int(master_handle, 16) == int(slave_handle, 16):
            raise ValueError("Association targets must be different entities")  # noqa: TRY003
        result = self._call(
            "create_bim_association",
            {"master_handle": master_handle, "slave_handle": slave_handle},
        )
        if not result.get("handle") or result.get("entity_type") != "ObjectAssociation":
            raise RuntimeError("BIM association endpoint returned no native association")  # noqa: TRY003
        return result

    def get_bim_associations(self, entity_handle: str) -> dict[str, Any]:
        if not self._handle(entity_handle):
            raise ValueError("A hexadecimal entity handle is required")  # noqa: TRY003
        return self._call("get_bim_associations", entity_handle)

    def _concrete_member(
        self,
        kind: str,
        profile_name: str,
        x1: float,
        y1: float,
        z1: float,
        x2: float,
        y2: float,
        z2: float,
    ) -> dict[str, Any]:
        values = (x1, y1, z1, x2, y2, z2)
        if not profile_name or not profile_name.strip():
            raise ValueError("Concrete profile_name is required")  # noqa: TRY003
        if any(
            isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v)
            for v in values
        ):
            raise ValueError("Concrete member coordinates must be finite numbers")  # noqa: TRY003
        if (x1, y1, z1) == (x2, y2, z2):
            raise ValueError("Concrete member axis must have nonzero length")  # noqa: TRY003
        if kind == "column" and (x1 != x2 or y1 != y2 or z2 <= z1):
            raise ValueError("Concrete column must have a vertical, upward axis")  # noqa: TRY003
        result = self._call(
            "create_bim_concrete_member",
            {
                "kind": kind,
                "profile_name": profile_name,
                "x1": x1,
                "y1": y1,
                "z1": z1,
                "x2": x2,
                "y2": y2,
                "z2": z2,
            },
        )
        expected = "ConcreteBeam" if kind == "beam" else "ConcreteColumn"
        if not result.get("handle") or result.get("entity_type") != expected:
            raise RuntimeError("BIM concrete endpoint returned no native member")  # noqa: TRY003
        return result

    def create_bim_concrete_beam(
        self,
        profile_name: str,
        x1: float,
        y1: float,
        z1: float,
        x2: float,
        y2: float,
        z2: float,
    ) -> dict[str, Any]:
        return self._concrete_member("beam", profile_name, x1, y1, z1, x2, y2, z2)

    def create_bim_concrete_column(
        self,
        profile_name: str,
        x1: float,
        y1: float,
        z1: float,
        x2: float,
        y2: float,
        z2: float,
    ) -> dict[str, Any]:
        return self._concrete_member("column", profile_name, x1, y1, z1, x2, y2, z2)
