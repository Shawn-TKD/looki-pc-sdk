"""Helpers for copying byte buffers supplied by platform bridges."""

from __future__ import annotations


def copy_callback_bytes(data: object, length: int) -> bytes:
    """Copy exactly ``length`` bytes before the native callback returns.

    PyObjC represents an unbounded C array as ``objc.varlist``. Its slice
    conversion is not a reliable byte copy; ``as_buffer`` is the supported
    bounded view for this case.
    """
    as_buffer = getattr(data, "as_buffer", None)
    if as_buffer is not None:
        return bytes(as_buffer(length))
    return bytes(memoryview(data)[:length])
