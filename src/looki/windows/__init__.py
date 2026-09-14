"""Windows-specific pairing and Wi-Fi helpers."""

from .pairing import pair_device
from .wifi import WindowsHotspot

__all__ = ["WindowsHotspot", "pair_device"]
