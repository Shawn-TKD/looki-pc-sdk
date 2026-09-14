"""Classic Bluetooth RFCOMM stream backed by Apple's IOBluetooth framework."""

from __future__ import annotations

import queue
import time

try:
    import objc
    from Foundation import NSDate, NSDefaultRunLoopMode, NSObject, NSRunLoop
    from IOBluetooth import IOBluetoothDevice
except ImportError as error:  # pragma: no cover - imported only on macOS
    raise RuntimeError(
        "macOS RFCOMM requires the 'macos' extra: pip install -e '.[macos]'"
    ) from error


class _RFCOMMDelegate(NSObject):
    def initWithOwner_(self, owner: "MacOSRFCOMMTransport") -> "_RFCOMMDelegate":
        self = objc.super(_RFCOMMDelegate, self).init()
        if self is not None:
            self.owner = owner
        return self

    def rfcommChannelData_data_length_(self, _channel: object, data: object, length: int) -> None:
        self.owner._incoming.put(bytes(data[:length]))

    def rfcommChannelClosed_(self, _channel: object) -> None:
        self.owner._closed = True


class MacOSRFCOMMTransport:
    """Socket-like adapter around ``IOBluetoothRFCOMMChannel``.

    IOBluetooth delivers incoming bytes through an Objective-C delegate. ``recv``
    pumps the current run loop while presenting the blocking stream interface used
    by the platform-neutral LCMP session.
    """

    def __init__(self, address: str, channel_id: int, timeout: float) -> None:
        self._timeout: float | None = timeout
        self._incoming: queue.Queue[bytes] = queue.Queue()
        self._buffer = bytearray()
        self._closed = False
        self._delegate = _RFCOMMDelegate.alloc().initWithOwner_(self)
        self._device = IOBluetoothDevice.deviceWithAddressString_(address.replace(":", "-"))
        if self._device is None:
            raise ConnectionError(f"macOS could not create a Bluetooth device for {address}")

        status, opened_channel = self._device.openRFCOMMChannelSync_withChannelID_delegate_(
            None, channel_id, self._delegate
        )
        if status != 0 or opened_channel is None:
            raise ConnectionError(
                f"macOS could not open Looki RFCOMM channel {channel_id} (IOReturn {status})"
            )
        self._channel = opened_channel

    def settimeout(self, timeout: float | None) -> None:
        self._timeout = timeout

    def sendall(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionError("Looki RFCOMM channel is closed")
        mtu = max(1, min(int(self._channel.getMTU()), 65535))
        for offset in range(0, len(data), mtu):
            chunk = data[offset : offset + mtu]
            status = self._channel.writeSync_length_(chunk, len(chunk))
            if status != 0:
                raise OSError(status, f"macOS RFCOMM write failed with IOReturn {status}")

    def recv(self, size: int) -> bytes:
        if size <= 0:
            return b""
        deadline = None if self._timeout is None else time.monotonic() + self._timeout
        while not self._buffer:
            if self._closed:
                return b""
            try:
                self._buffer.extend(self._incoming.get_nowait())
                continue
            except queue.Empty:
                pass
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("macOS RFCOMM receive timed out")
            interval = 0.05
            if deadline is not None:
                interval = min(interval, max(0.001, deadline - time.monotonic()))
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode, NSDate.dateWithTimeIntervalSinceNow_(interval)
            )

        result = bytes(self._buffer[:size])
        del self._buffer[:size]
        return result

    def close(self) -> None:
        if not self._closed:
            self._channel.closeChannel()
            self._closed = True
