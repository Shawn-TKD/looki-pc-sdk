"""Shareable host diagnostics that never inspect device credentials or media."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import socket
import sys
from pathlib import Path


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def host_diagnostics() -> dict[str, object]:
    """Return non-sensitive information needed to diagnose host integration."""
    result: dict[str, object] = {
        "sdk_platform": sys.platform,
        "os_release": platform.release(),
        "machine": (
            platform.machine()
            or os.environ.get("PROCESSOR_ARCHITECTURE")
            or platform.architecture()[0]
        ),
        "python": platform.python_version(),
    }

    if sys.platform == "darwin":
        modules = {
            name: _module_available(name)
            for name in ("objc", "Foundation", "IOBluetooth")
        }
        networksetup = Path("/usr/sbin/networksetup").is_file()
        ipconfig = Path("/usr/sbin/ipconfig").is_file()
        wifi_interface: str | None = None
        wifi_error: str | None = None
        if networksetup:
            try:
                from .macos.wifi import _wifi_interface

                wifi_interface = _wifi_interface()
            except RuntimeError as error:
                wifi_error = str(error)
        result.update(
            {
                "bluetooth_backend": "IOBluetooth/PyObjC",
                "pyobjc_modules": modules,
                "networksetup": networksetup,
                "ipconfig": ipconfig,
                "wifi_interface": wifi_interface,
                "wifi_detection_error": wifi_error,
                "static_ready": all(modules.values()) and networksetup and ipconfig,
                "permission_note": (
                    "Bluetooth permission is checked by macOS when a real device connection starts"
                ),
            }
        )
    elif sys.platform == "win32":
        rfcomm_socket = all(
            hasattr(socket, name)
            for name in ("AF_BLUETOOTH", "BTPROTO_RFCOMM")
        )
        result.update(
            {
                "bluetooth_backend": "Winsock RFCOMM",
                "rfcomm_socket": rfcomm_socket,
                "netsh": shutil.which("netsh") is not None,
                "static_ready": rfcomm_socket and shutil.which("netsh") is not None,
            }
        )
    else:
        result.update(
            {
                "bluetooth_backend": None,
                "static_ready": False,
                "unsupported_reason": "automatic pairing and hotspot switching are not implemented",
            }
        )
    return result
