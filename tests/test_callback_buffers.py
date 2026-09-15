from __future__ import annotations

import unittest

from looki.transport.buffers import copy_callback_bytes


class MisleadingVarList:
    """Reproduce the PyObjC failure where slicing did not copy native bytes."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __getitem__(self, item: slice) -> bytes:
        return bytes(len(self.payload[item]))

    def as_buffer(self, length: int) -> memoryview:
        return memoryview(self.payload)[:length]


class CallbackBufferTest(unittest.TestCase):
    def test_varlist_uses_bounded_native_buffer(self) -> None:
        data = MisleadingVarList(b"\x01\x02\x03\x04")
        self.assertEqual(copy_callback_bytes(data, 3), b"\x01\x02\x03")

    def test_python_buffer_fallback(self) -> None:
        self.assertEqual(copy_callback_bytes(b"abcdef", 4), b"abcd")


if __name__ == "__main__":
    unittest.main()
