"""macOS Bluetooth and Wi-Fi adapters."""

from .pairing import pair_device
from .wifi import MacOSHotspot

__all__ = ["MacOSHotspot", "pair_device"]
