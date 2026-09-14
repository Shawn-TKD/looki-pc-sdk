"""A stateful RFCOMM/LCMP connection to one paired Looki device."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterator

from ..credentials.binding import OwnerBinding
from ..protocol.lcmp import Framer, fields, frame, message, uint
from ..protocol.messages import ACK, AUTH_RESULT_SYNC, DEVICE_AUTH_REQUEST
from ..transport import ByteTransport, open_rfcomm


RFCOMM_CHANNEL = 3


@dataclass(frozen=True)
class ReceivedMessage:
    """One outer LCMP protobuf field received from the device."""

    tag: int
    wire_type: int
    payload: int | bytes


class LookiSession:
    """Own one authenticated RFCOMM session.

    Pair the device with the host OS before opening this session.  ``authenticate``
    always answers the fresh device challenge; it never replays an old one.
    """

    def __init__(
        self,
        address: str,
        channel: int = RFCOMM_CHANNEL,
        timeout: float = 30,
        *,
        transport_factory: Callable[[str, int, float], ByteTransport] = open_rfcomm,
        trace: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.address = address
        self.channel = channel
        self.timeout = timeout
        self._transport: ByteTransport | None = None
        self._transport_factory = transport_factory
        self._trace = trace
        self._framer = Framer()
        self._sequence = 1
        self._authenticated = False

    def __enter__(self) -> "LookiSession":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def connect(self) -> None:
        if self._transport is not None:
            return
        self._emit("transport.opening", channel=self.channel)
        self._transport = self._transport_factory(self.address, self.channel, 10)
        self._emit("transport.connected", channel=self.channel)

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._emit("transport.closed")

    def _emit(self, event: str, **details: object) -> None:
        if self._trace is not None:
            self._trace({"event": event, **details})

    def send(self, tag: int, payload: bytes = b"") -> None:
        """Send one outer message with an automatically assigned sequence."""
        if self._transport is None:
            raise RuntimeError("LookiSession is not connected")
        body = uint(1, self._sequence) + message(tag, payload)
        self._emit("lcmp.send", sequence=self._sequence, tag=tag, payload_length=len(payload))
        self._sequence += 1
        self._transport.sendall(frame(body))

    def _send_ack(self, sequence: int) -> None:
        if self._transport is None:
            raise RuntimeError("LookiSession is not connected")
        self._emit("lcmp.ack.send", sequence=sequence)
        self._transport.sendall(frame(uint(ACK, sequence)))

    def receive(self, deadline: float) -> Iterator[ReceivedMessage]:
        """Yield protocol messages until the monotonic deadline expires."""
        if self._transport is None:
            raise RuntimeError("LookiSession is not connected")
        while time.monotonic() < deadline:
            self._transport.settimeout(min(0.5, max(0.05, deadline - time.monotonic())))
            try:
                chunk = self._transport.recv(65536)
            except TimeoutError:
                continue
            if not chunk:
                raise ConnectionError("Looki closed the RFCOMM session")
            self._emit("transport.received", bytes=len(chunk))
            for body in self._framer.feed(chunk):
                self._emit("lcmp.frame.received", bytes=len(body))
                for tag, wire_type, payload in fields(body):
                    if tag == 1 and wire_type == 0 and isinstance(payload, int):
                        self._send_ack(payload)
                    else:
                        self._emit(
                            "lcmp.message.received",
                            tag=tag,
                            wire_type=wire_type,
                            payload_length=len(payload) if isinstance(payload, bytes) else None,
                            value=payload if isinstance(payload, int) else None,
                        )
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
        challenge_answered = False
        for received in self.receive(deadline):
            if received.tag == DEVICE_AUTH_REQUEST and received.wire_type == 2:
                if not isinstance(received.payload, bytes):
                    raise RuntimeError("Looki authentication request is malformed")
                challenge = next(
                    (value for field, wire, value in fields(received.payload)
                     if field == 1 and wire == 2 and isinstance(value, bytes)),
                    None,
                )
                if challenge is None:
                    raise RuntimeError("Looki authentication challenge is missing")
                self._emit("auth.challenge.received", bytes=len(challenge))
                self.send(201, message(1, challenge))
                challenge_answered = True
                continue

            if challenge_answered and received.tag == AUTH_RESULT_SYNC and received.wire_type == 2:
                if not isinstance(received.payload, bytes):
                    raise RuntimeError("Looki authentication result is malformed")
                result = next(
                    (value for field, wire, value in fields(received.payload)
                     if field == 1 and wire == 0 and isinstance(value, int)),
                    0,
                )
                self._emit("auth.challenge.accepted", result=result)
                if result != 0:
                    raise PermissionError(f"Looki rejected the connection challenge (result {result})")
                if owner_binding is not None:
                    for tag, payload in owner_binding.messages():
                        self.send(tag, payload)
                    self._emit("auth.owner_binding.sent", messages=2)
                if app_state_value is not None:
                    state, page = app_state_value
                    self.send(99, uint(1, state) + uint(2, page))
                self._authenticated = True
                return
        if challenge_answered:
            raise TimeoutError("Looki did not acknowledge the connection challenge")
        raise TimeoutError("Looki did not send a device authentication challenge")

    def set_app_state(self, *, app_state_value: int, device_page_state: int) -> None:
        self.send(99, uint(1, app_state_value) + uint(2, device_page_state))
