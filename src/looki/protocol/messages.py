"""Names and small parsers for LCMP messages verified from Looki L1 traffic."""

from __future__ import annotations

from collections import defaultdict

from .lcmp import fields, message, uint


ACK = 2
APP_STATE_SYNC = 99
HOTSPOT_CONNECT = 103
DEVICE_AUTH_REQUEST = 200
DEVICE_AUTH_RESULT = 201
AUTH_RESULT_SYNC = 202
DEVICE_FILE_SYNC = 253
HTTP_FILE_SERVER = 256
DEVICE_FUNCTION_COMMAND = 257
LOOKI_PRIVACY_LIGHT_UPDATE = 245


def grouped_fields(payload: bytes) -> dict[int, list[int | bytes]]:
    grouped: dict[int, list[int | bytes]] = defaultdict(list)
    for number, _, value in fields(payload):
        grouped[number].append(value)
    return dict(grouped)


def read_utf8(payload: bytes, field_number: int) -> str | None:
    values = grouped_fields(payload).get(field_number, [])
    if values and isinstance(values[0], bytes):
        return values[0].decode("utf-8", "strict")
    return None


def read_uint(payload: bytes, field_number: int) -> int | None:
    values = grouped_fields(payload).get(field_number, [])
    return values[0] if values and isinstance(values[0], int) else None


def challenge_response(challenge: bytes) -> bytes:
    """Build the verified current-session DeviceAuthResult message."""
    return message(DEVICE_AUTH_RESULT, message(1, challenge))


def app_state(*, app_state: int, device_page_state: int) -> bytes:
    return message(APP_STATE_SYNC, uint(1, app_state) + uint(2, device_page_state))


def start_file_sync() -> bytes:
    """Start the verified file service: start=1, upload_state=0, hotspot_type=0."""
    return message(DEVICE_FILE_SYNC, uint(1, 1))


def device_function(*, action: int, state: int) -> bytes:
    """Encode the verified v1 DeviceFunctionCmd payload."""
    return uint(1, action) + uint(2, state)
