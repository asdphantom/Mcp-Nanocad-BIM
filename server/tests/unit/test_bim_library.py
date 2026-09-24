"""Native ncBIM library search contract."""

from unittest.mock import Mock

import pytest

from src.application.bim_library_use_case import BimLibraryUseCase
from src.domain.exceptions import NotSupportedError
from src.presentation.tool_defs import TOOL_DEFS


def test_search_known_sdk_category() -> None:
    bridge = Mock(is_available=True)
    bridge.search_bim_library.return_value = {
        "success": True,
        "category": "metalware",
        "objects": [{"name": "profile", "guid": "0000"}],
    }
    uc = BimLibraryUseCase(bridge)
    result = uc.search_bim_library("metalware", "profile", 20)
    assert result["objects"][0]["name"] == "profile"
    bridge.search_bim_library.assert_called_once_with("metalware", "profile", 20)
    tool = next(item for item in TOOL_DEFS if item["name"] == "search_bim_library")
    assert tool["requires_mode"] == "full"


def test_rejects_invalid_category_and_limit() -> None:
    uc = BimLibraryUseCase(Mock(is_available=True))
    with pytest.raises(ValueError, match="category"):
        uc.search_bim_library("anything")
    with pytest.raises(ValueError, match="limit"):
        uc.search_bim_library("opening", limit=0)
    with pytest.raises(ValueError, match="name"):
        uc.search_bim_library("opening", name="x" * 101)


def test_requires_engine_and_propagates_sdk_failure() -> None:
    with pytest.raises(NotSupportedError, match="in-process"):
        BimLibraryUseCase(Mock(is_available=False)).search_bim_library("opening")
    bridge = Mock(is_available=True)
    bridge.search_bim_library.return_value = None
    with pytest.raises(NotSupportedError, match="endpoint is unavailable"):
        BimLibraryUseCase(bridge).search_bim_library("opening")
    bridge.search_bim_library.return_value = {"success": False, "error": "library offline"}
    with pytest.raises(NotSupportedError, match="library offline"):
        BimLibraryUseCase(bridge).search_bim_library("opening")
