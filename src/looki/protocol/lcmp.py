"""The length-prefixed protobuf envelope observed on Looki RFCOMM channel 3."""

from __future__ import annotations

import struct
from collections.abc import Iterable


MAX_MESSAGE_BYTES = 1024 * 1024


def _varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("LCMP varints must be unsigned")
    encoded = bytearray()
    while value > 0x7F:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def uint(field_number: int, value: int) -> bytes:
    """Encode an unsigned protobuf varint field."""
    return _varint(field_number << 3) + _varint(value)


def message(field_number: int, payload: bytes = b"") -> bytes:
    """Encode a length-delimited protobuf field."""
    return _varint((field_number << 3) | 2) + _varint(len(payload)) + payload


def frame(payload: bytes) -> bytes:
    """Add Looki's four-byte big-endian LCMP record length."""
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("LCMP payload exceeds the verified safety limit")
    return struct.pack(">I", len(payload)) + payload


def fields(payload: bytes) -> list[tuple[int, int, int | bytes]]:
    """Decode the protobuf wire types used by verified Looki messages."""
    def read_varint(position: int) -> tuple[int, int]:
        value = 0
        for shift in range(0, 70, 7):
            if position >= len(payload):
                raise ValueError("truncated protobuf varint")
            current = payload[position]
            position += 1
            value |= (current & 0x7F) << shift
            if current < 0x80:
                return value, position
        raise ValueError("protobuf varint exceeds ten bytes")

    position = 0
    decoded: list[tuple[int, int, int | bytes]] = []
    while position < len(payload):
        tag, position = read_varint(position)
        field_number, wire_type = tag >> 3, tag & 7
        if field_number == 0:
            raise ValueError("protobuf field number zero")
        if wire_type == 0:
            value, position = read_varint(position)
        elif wire_type == 2:
            length, position = read_varint(position)
            end = position + length
            if end > len(payload):
                raise ValueError("truncated protobuf bytes field")
            value = payload[position:end]
            position = end
        elif wire_type in (1, 5):
            length = 8 if wire_type == 1 else 4
            end = position + length
            if end > len(payload):
                raise ValueError("truncated protobuf fixed-width field")
            value = payload[position:end]
            position = end
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type}")
        decoded.append((field_number, wire_type, value))
    return decoded


class Framer:
    """Incrementally split a RFCOMM byte stream into LCMP records."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, chunk: bytes) -> Iterable[bytes]:
        self.buffer.extend(chunk)
        records: list[bytes] = []
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], "big")
            if length > MAX_MESSAGE_BYTES:
                raise ValueError("unexpected LCMP message length")
            if len(self.buffer) < length + 4:
                break
            records.append(bytes(self.buffer[4:length + 4]))
            del self.buffer[:length + 4]
        return records
