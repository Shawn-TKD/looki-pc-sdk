"""Pair Looki through Apple's public IOBluetooth API."""

from __future__ import annotations

import time

try:
    import objc
    from Foundation import NSDate, NSDefaultRunLoopMode, NSObject, NSRunLoop
    from IOBluetooth import IOBluetoothDevice, IOBluetoothDevicePair
except ImportError as error:  # pragma: no cover - imported only on macOS
    raise RuntimeError(
        "macOS pairing requires the 'macos' extra: pip install -e '.[macos]'"
    ) from error


class _PairingDelegate(NSObject):
    def init(self) -> "_PairingDelegate":
        self = objc.super(_PairingDelegate, self).init()
        if self is not None:
            self.finished = False
            self.status = None
        return self

    def devicePairingUserConfirmationRequest_numericValue_(
        self, sender: object, _numeric_value: int
    ) -> None:
        sender.replyUserConfirmation_(True)

    def devicePairingFinished_error_(self, _sender: object, error: int) -> None:
        self.status = int(error)
        self.finished = True


def pair_device(address: str, *, renew: bool = False, timeout: float = 60) -> None:
    """Pair one exact Bluetooth address and accept its Just Works confirmation."""
    device = IOBluetoothDevice.deviceWithAddressString_(address.replace(":", "-"))
    if device is None:
        raise ConnectionError(f"macOS could not create a Bluetooth device for {address}")
    if renew and device.isPaired():
        raise RuntimeError(
            "macOS cannot renew this bond through the public API; forget Looki in "
            "System Settings > Bluetooth, then run pair again"
        )
    if device.isPaired():
        return

    delegate = _PairingDelegate.alloc().init()
    pairing = IOBluetoothDevicePair.pairWithDevice_(device)
    pairing.setDelegate_(delegate)
    status = pairing.start()
    if status != 0:
        raise OSError(status, f"macOS could not start Bluetooth pairing (IOReturn {status})")

    deadline = time.monotonic() + timeout
    while not delegate.finished and time.monotonic() < deadline:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode, NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )
    if not delegate.finished:
        pairing.stop()
        raise TimeoutError("macOS Bluetooth pairing did not finish")
    if delegate.status != 0:
        raise OSError(delegate.status, f"macOS Bluetooth pairing failed (IOReturn {delegate.status})")
