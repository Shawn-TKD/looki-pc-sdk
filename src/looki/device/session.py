"""A stateful RFCOMM/LCMP connection to one paired Looki device."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Iterator

from ..credentials.binding import OwnerBinding
from ..protocol.lcmp import Framer, fields, frame, message, uint
from ..protocol.messages import ACK, DEVICE_AUTH_REQUEST, app_state, challenge_response


RFCOMM_CHANNEL = 3


@dataclass(frozen=True)
class ReceivedMessage:
    """One outer LCMP protobuf field received from the device."""

    tag: int
    wire_type: int
    payload: int | bytes


class LookiSession:
    """Own one authenticated RFCOMM session.

    Pair the device with Windows before opening this session.  ``authenticate``
    always answers the fresh device challenge; it never replays an old one.
    """

    def __init__(self, address: str, channel: int = RFCOMM_CHANNEL, timeout: float = 30) -> None:
        self.address = address
        self.channel = channel
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._framer = Framer()
        self._sequence = 1
        self._authenticated = False

    def __enter__(self) -> "LookiSession":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        try:
            # Windows-specific options.  An already paired device may reject
            # them on some stacks, so the connection itself remains decisive.
            sock.setsockopt(3, -2147483647, 1)  # SO_BTH_AUTHENTICATE
            sock.setsockopt(3, 2, 1)  # SO_BTH_ENCRYPT
        except OSError:
            pass
        sock.settimeout(10)
        try:
            sock.connect((self.address, self.channel))
        except Exception:
            sock.close()
            raise
        self._socket = sock

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def send(self, tag: int, payload: bytes = b"") -> None:
        """Send one outer message with an automatically assigned sequence."""
        if self._socket is None:
            raise RuntimeError("LookiSession is not connected")
        body = uint(1, self._sequence) + message(tag, payload)
        self._sequence += 1
        self._socket.sendall(frame(body))

    def _send_ack(self, sequence: int) -> None:
        if self._socket is None:
            raise RuntimeError("LookiSession is not connected")
        self._socket.sendall(frame(uint(ACK, sequence)))

    def receive(self, deadline: float) -> Iterator[ReceivedMessage]:
        """Yield protocol messages until the monotonic deadline expires."""
        if self._socket is None:
            raise RuntimeError("LookiSession is not connected")
        while time.monotonic() < deadline:
            self._socket.settimeout(min(0.5, max(0.05, deadline - time.monotonic())))
            try:
                chunk = self._socket.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("Looki closed the RFCOMM session")
            for body in self._framer.feed(chunk):
                for tag, wire_type, payload in fields(body):
                    if tag == 1 and wire_type == 0 and isinstance(payload, int):
                        self._send_ack(payload)
                    else:
                        yield ReceivedMessage(tag, wire_type, payload)

    def authenticate(
        self,
        *,
        owner_binding: OwnerBinding | None = None,
        app_state_value: tuple[int, int] | None = None,
    ) -> None:
        """Answer the current challenge and optionally provide owner context."""
        if self._authenticated:
            return
        deadline = time.monotonic() + self.timeout
        for received in self.receive(deadline):
            if received.tag != DEVICE_AUTH_REQUEST or received.wire_type != 2:
                continue
            if not isinstance(received.payload, bytes):
                raise RuntimeError("Looki authentication request is malformed")
            challenge = next(
                (value for field, wire, value in fields(received.payload)
                 if field == 1 and wire == 2 and isinstance(value, bytes)),
                None,
            )
            if challenge is None:
                raise RuntimeError("Looki authentication challenge is missing")
            self.send(201, message(1, challenge))
            if owner_binding is not None:
                for tag, payload in owner_binding.messages():
                    self.send(tag, payload)
            if app_state_value is not None:
                state, page = app_state_value
                self.send(99, uint(1, state) + uint(2, page))
            self._authenticated = True
            return
        raise TimeoutError("Looki did not send a device authentication challenge")

    def set_app_state(self, *, app_state_value: int, device_page_state: int) -> None:
        self.send(99, uint(1, app_state_value) + uint(2, device_page_state))
