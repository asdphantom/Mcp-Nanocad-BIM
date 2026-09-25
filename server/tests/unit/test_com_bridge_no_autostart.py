from __future__ import annotations

from unittest.mock import patch

import pywintypes

from src.infrastructure.com_bridge import NanoCadComBridge


def test_connect_does_not_launch_nanocad_when_it_is_closed() -> None:
    bridge = NanoCadComBridge()
    with (
        patch(
            "src.infrastructure.com_bridge.win32com.client.GetObject",
            side_effect=pywintypes.com_error(-2147221021, "not running", None, None),
        ),
        patch("src.infrastructure.com_bridge.win32com.client.Dispatch") as dispatch,
    ):
        assert bridge.connect() is False
    dispatch.assert_not_called()
    assert bridge.is_connected is False

def test_explicit_start_tool_targets_bim_building() -> None:
    from unittest.mock import MagicMock

    from src.presentation import server as srv

    srv._routing_cache = None
    with (
        patch.object(srv, "get_factory", return_value=None),
        patch("pathlib.Path.is_file", return_value=True),
        patch("psutil.process_iter", return_value=[]),
        patch("subprocess.Popen", return_value=MagicMock(pid=1234)) as popen,
    ):
        routing = srv._build_routing()
        popen.assert_not_called()
        assert routing["start_nanocad"]() == {"status": "started", "pid": 1234}
    assert popen.call_args.args[0][0].endswith("nanoCAD BIM Строительство x64 26.0\\BIMSP.exe")