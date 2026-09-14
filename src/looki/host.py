"""Host-specific pairing and Wi-Fi selection."""

from __future__ import annotations

import sys
from typing import ContextManager


def pair_device(address: str, *, renew: bool = False) -> None:
    if sys.platform == "darwin":
        from .macos.pairing import pair_device as pair_macos

        pair_macos(address, renew=renew)
        return
    if sys.platform == "win32":
        from .windows.pairing import pair_device as pair_windows

        pair_windows(address, renew=renew)
        return
    raise RuntimeError(f"automatic Bluetooth pairing is unsupported on {sys.platform}")


def hotspot_connection(
    ssid: str, password: str, *, interface: str | None = None
) -> ContextManager[object]:
    if sys.platform == "darwin":
        from .macos.wifi import MacOSHotspot

        return MacOSHotspot(ssid, password, interface=interface)
    if sys.platform == "win32":
        from .windows.wifi import WindowsHotspot

        return WindowsHotspot(ssid, password, interface=interface or "WLAN")
    raise RuntimeError(f"automatic Looki hotspot switching is unsupported on {sys.platform}")
