"""Search the native nanoCAD BIM object library by SDK category."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.exceptions import NotSupportedError

if TYPE_CHECKING:
    from src.infrastructure.http_bridge import HttpCadBridge

CATEGORIES = frozenset({
    "opening", "metalware", "metalware_node", "concrete_profile",
    "reinforcement", "structural_surface",
})
_ENGINE_REQUIRED = "The in-process nanoCAD BIM engine is required"
_ENDPOINT_REQUIRED = "BIM library search endpoint is unavailable"


class BimLibraryUseCase:
    def __init__(self, bridge: HttpCadBridge | None) -> None:
        self._bridge = bridge

    def search_bim_library(
        self, category: str, name: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        if category not in CATEGORIES:
            raise ValueError("Unsupported BIM library category")  # noqa: TRY003
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")  # noqa: TRY003
        if name is not None and (not isinstance(name, str) or len(name) > 100):
            raise ValueError("name must be at most 100 characters")  # noqa: TRY003
        if self._bridge is None or not self._bridge.is_available:
            raise NotSupportedError(_ENGINE_REQUIRED)
        result = self._bridge.search_bim_library(category, name, limit)
        if result is None:
            raise NotSupportedError(_ENDPOINT_REQUIRED)
        if not result.get("success"):
            raise NotSupportedError(result.get("error", "BIM library query failed"))
        return result
