"""Active controls verified from isolated official-App HCI traffic.

Callers must authenticate the session before invoking a control.  These methods
only send a protocol request; status and resulting media should be checked by
the caller through the normal state/media interfaces.
"""

from __future__ import annotations

from enum import IntEnum

from ..protocol.lcmp import uint
from ..protocol.messages import DEVICE_FUNCTION_COMMAND, LOOKI_PRIVACY_LIGHT_UPDATE, device_function
from .session import LookiSession


class DeviceFunction(IntEnum):
    DIARY_RECORD = 1
    VIDEO_RECORD = 2
    AUDIO_RECORD = 3
    PHOTO = 4


class FunctionState(IntEnum):
    STOP = 1
    START_OR_TRIGGER = 2


class LookiControls:
    """Small, explicit control surface for the Looki L1 v1 session."""

    def __init__(self, session: LookiSession) -> None:
        self._session = session

    def capture_photo(self) -> None:
        self._function(DeviceFunction.PHOTO, FunctionState.START_OR_TRIGGER)

    def start_audio_recording(self) -> None:
        self._function(DeviceFunction.AUDIO_RECORD, FunctionState.START_OR_TRIGGER)

    def stop_audio_recording(self) -> None:
        self._function(DeviceFunction.AUDIO_RECORD, FunctionState.STOP)

    def start_video_recording(self) -> None:
        self._function(DeviceFunction.VIDEO_RECORD, FunctionState.START_OR_TRIGGER)

    def stop_video_recording(self) -> None:
        self._function(DeviceFunction.VIDEO_RECORD, FunctionState.STOP)

    def start_diary_recording(self) -> None:
        self._function(DeviceFunction.DIARY_RECORD, FunctionState.START_OR_TRIGGER)

    def stop_diary_recording(self) -> None:
        self._function(DeviceFunction.DIARY_RECORD, FunctionState.STOP)

    def set_privacy_light(self, enabled: bool) -> None:
        self._session.send(LOOKI_PRIVACY_LIGHT_UPDATE, uint(1, int(enabled)))

    def _function(self, action: DeviceFunction, state: FunctionState) -> None:
        self._session.send(DEVICE_FUNCTION_COMMAND, device_function(action=int(action), state=int(state)))
