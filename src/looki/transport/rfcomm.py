"""Select the host implementation for a Classic Bluetooth RFCOMM stream."""

from __future__ import annotations

import socket
import sys
from typing import Protocol


class ByteTransport(Protocol):
    """The small stream surface required by :class:`LookiSession`."""

    def settimeout(self, timeout: float | None) -> None: ...
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


def open_rfcomm(address: str, channel: int, timeout: float) -> ByteTransport:
    """Open RFCOMM using the native implementation for the current host."""
    if sys.platform == "darwin":
        from ..macos.rfcomm import MacOSRFCOMMTransport

        return MacOSRFCOMMTransport(address, channel, timeout)

    if not hasattr(socket, "AF_BLUETOOTH"):
        raise RuntimeError(f"Classic Bluetooth RFCOMM is unsupported on {sys.platform}")

    transport = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    if sys.platform == "win32":
        try:
            transport.setsockopt(3, -2147483647, 1)  # SO_BTH_AUTHENTICATE
            transport.setsockopt(3, 2, 1)  # SO_BTH_ENCRYPT
        except OSError:
            pass
    transport.settimeout(timeout)
    try:
        transport.connect((address, channel))
    except Exception:
        transport.close()
        raise
    return transport
