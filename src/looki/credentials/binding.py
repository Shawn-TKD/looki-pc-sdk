"""In-memory owner-binding support for the exploratory SDK.

Portable bundles are intentionally simple so one owner can move a device between
their Windows and macOS computers. They are bearer credentials and must be kept
outside Git and transferred through an encrypted channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from ..protocol.lcmp import Framer, fields


USER_INFO_SYNC = 205
LOGIN_STATE_SYNC = 276
PORTABLE_MAGIC = b"LOOKI-BINDING\x01"


@dataclass(frozen=True)
class OwnerBinding:
    """The two observed application-level authorization messages for one owner."""

    user_info_sync: bytes
    login_state_sync: bytes

    def messages(self) -> tuple[tuple[int, bytes], tuple[int, bytes]]:
        return (
            (USER_INFO_SYNC, self.user_info_sync),
            (LOGIN_STATE_SYNC, self.login_state_sync),
        )

    def save_portable(self, path: Path) -> None:
        """Save a device-owner bundle for private transfer between computers."""
        payload = (
            PORTABLE_MAGIC
            + struct.pack(">II", len(self.user_info_sync), len(self.login_state_sync))
            + self.user_info_sync
            + self.login_state_sync
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    @classmethod
    def load_portable(cls, path: Path) -> "OwnerBinding":
        """Load a private bundle previously created by ``save_portable``."""
        data = path.read_bytes()
        if not data.startswith(PORTABLE_MAGIC) or len(data) < len(PORTABLE_MAGIC) + 8:
            raise ValueError("not a Looki owner-binding bundle")
        position = len(PORTABLE_MAGIC)
        user_length, login_length = struct.unpack(">II", data[position:position + 8])
        position += 8
        user_end = position + user_length
        login_end = user_end + login_length
        if login_end != len(data):
            raise ValueError("truncated or trailing owner-binding data")
        return cls(data[position:user_end], data[user_end:login_end])


def owner_binding_from_framed_capture(path: Path) -> OwnerBinding:
    """Read an existing local capture without exposing its credential values.

    This is a migration aid for the user-owned experimental device only.  It is
    intentionally unsuitable for distribution as an enrollment mechanism.
    """
    wanted: dict[int, bytes] = {}
    framer = Framer()
    for body in framer.feed(path.read_bytes()):
        for tag, wire, value in fields(body):
            if tag in (USER_INFO_SYNC, LOGIN_STATE_SYNC) and wire == 2 and isinstance(value, bytes):
                wanted.setdefault(tag, value)
    if set(wanted) != {USER_INFO_SYNC, LOGIN_STATE_SYNC}:
        raise RuntimeError("The local capture does not contain the required owner-binding messages")
    return OwnerBinding(
        user_info_sync=wanted[USER_INFO_SYNC],
        login_state_sync=wanted[LOGIN_STATE_SYNC],
    )
