"""Verified Bluetooth control-plane messages for Looki media transfer."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..credentials.binding import OwnerBinding
from ..protocol.lcmp import fields, uint
from ..protocol.messages import HOTSPOT_CONNECT, HTTP_FILE_SERVER
from .session import LookiSession


@dataclass(frozen=True)
class FileService:
    """Short-lived connection data supplied by Looki for one transfer session."""

    ssid: str
    password: str
    host: str
    port: int


def _string_field(payload: bytes, field_number: int) -> str | None:
    value = next(
        (value for field, wire, value in fields(payload)
         if field == field_number and wire == 2 and isinstance(value, bytes)),
        None,
    )
    return value.decode("utf-8", "strict") if value is not None else None


def _uint_field(payload: bytes, field_number: int) -> int | None:
    return next(
        (value for field, wire, value in fields(payload)
         if field == field_number and wire == 0 and isinstance(value, int)),
        None,
    )


def request_file_service(
    session: LookiSession, owner_binding: OwnerBinding, timeout: float = 30,
) -> FileService:
    """Request the verified, temporary hotspot and HTTP media service.

    The order is evidence-based: authenticate and owner-bind first, then send
    ``DeviceFileSync(start=1)`` before reporting the media page state.
    """
    session.authenticate(owner_binding=owner_binding)
    session.send(253, uint(1, 1))
    session.set_app_state(app_state_value=1, device_page_state=0)

    hotspot: tuple[str, str] | None = None
    server: tuple[str, int] | None = None
    deadline = time.monotonic() + timeout
    for received in session.receive(deadline):
        if received.wire_type != 2 or not isinstance(received.payload, bytes):
            continue
        if received.tag == HOTSPOT_CONNECT:
            ssid = _string_field(received.payload, 2)
            password = _string_field(received.payload, 3)
            if ssid and password:
                hotspot = (ssid, password)
        elif received.tag == HTTP_FILE_SERVER:
            host = _string_field(received.payload, 2)
            port = _uint_field(received.payload, 3)
            if host and port:
                server = (host, port)
        if hotspot and server:
            return FileService(*hotspot, *server)
    raise TimeoutError("Looki did not provide a temporary file service")
