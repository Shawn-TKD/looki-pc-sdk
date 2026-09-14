"""Read-only Looki status queries observed in a normal working session."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..protocol.lcmp import fields
from .session import LookiSession


@dataclass(frozen=True)
class Query:
    request_tag: int
    reply_tag: int
    name: str


DEFAULT_QUERIES = (
    Query(19, 20, "battery"),
    Query(204, 203, "device_info"),
    Query(49, 50, "media_count"),
    Query(45, 46, "storage"),
    Query(234, 235, "recording"),
)


def _describe(reply_tag: int, payload: bytes) -> dict[str, int | str]:
    if reply_tag == 203:
        return {
            str(field): value.decode("utf-8", "replace")
            for field, wire, value in fields(payload)
            if wire == 2 and field in (1, 5, 6, 8) and isinstance(value, bytes)
        }
    return {
        str(field): value
        for field, wire, value in fields(payload)
        if wire == 0 and isinstance(value, int)
    }


def read_status(session: LookiSession, timeout: float = 20) -> dict[str, dict[str, int | str]]:
    """Read verified, non-mutating status values from an authenticated session."""
    pending = list(DEFAULT_QUERIES)
    replies = {query.reply_tag: query for query in DEFAULT_QUERIES}
    result: dict[str, dict[str, int | str]] = {}
    for query in pending:
        session.send(query.request_tag)
        time.sleep(0.2)
    deadline = time.monotonic() + timeout
    for received in session.receive(deadline):
        query = replies.get(received.tag)
        if query is not None and received.wire_type == 2 and isinstance(received.payload, bytes):
            result[query.name] = _describe(query.reply_tag, received.payload)
        if len(result) == len(DEFAULT_QUERIES):
            return result
    return result
