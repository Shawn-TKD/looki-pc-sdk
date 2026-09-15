"""Pair one Looki through Windows Classic Bluetooth Dedicated Bonding."""

from __future__ import annotations

import ctypes as c
from ctypes import wintypes as w


ERROR_NOT_FOUND = 1168
NUMERIC_COMPARISON = 3
NO_INPUT_NO_OUTPUT = 3
DEDICATED_BONDING = 2


class SystemTime(c.Structure):
    _fields_ = [("values", w.WORD * 8)]


class Device(c.Structure):
    _fields_ = [
        ("size", w.DWORD),
        ("address", c.c_ulonglong),
        ("connected", w.BOOL),
        ("remembered", w.BOOL),
        ("authenticated", w.BOOL),
        ("last_seen", SystemTime),
        ("last_used", SystemTime),
        ("name", w.WCHAR * 248),
    ]


class Params(c.Structure):
    _fields_ = [
        ("device", Device),
        ("method", c.c_int),
        ("io", c.c_int),
        ("requirements", c.c_int),
        ("numeric", w.ULONG),
    ]


class AuthData(c.Union):
    _fields_ = [("numeric", w.ULONG), ("storage", c.c_ubyte * 32)]


class Response(c.Structure):
    _fields_ = [
        ("address", c.c_ulonglong),
        ("method", c.c_int),
        ("data", AuthData),
        ("negative", c.c_ubyte),
    ]


def parse_address(address: str) -> int:
    compact = address.replace(":", "").replace("-", "")
    if len(compact) != 12:
        raise ValueError("Bluetooth address must contain 12 hexadecimal digits")
    return int(compact, 16)


def pair_device(address: str, *, renew: bool = False) -> None:
    """Establish the Classic bond needed by Looki's RFCOMM control channel."""
    target = parse_address(address)
    # The pairing entry points are exported by bthprops.cpl on Windows. Loading
    # BluetoothAPIs.dll works for some discovery helpers but does not expose
    # BluetoothAuthenticateDeviceEx on current Windows 11 builds.
    api = c.WinDLL("bthprops.cpl")
    callback_type = c.WINFUNCTYPE(w.BOOL, c.c_void_p, c.POINTER(Params))

    api.BluetoothGetDeviceInfo.argtypes = [w.HANDLE, c.POINTER(Device)]
    api.BluetoothRegisterForAuthenticationEx.argtypes = [
        c.POINTER(Device), c.POINTER(w.HANDLE), callback_type, c.c_void_p,
    ]
    api.BluetoothSendAuthenticationResponseEx.argtypes = [w.HANDLE, c.POINTER(Response)]
    api.BluetoothAuthenticateDeviceEx.argtypes = [
        w.HWND, w.HANDLE, c.POINTER(Device), c.c_void_p, c.c_int,
    ]
    api.BluetoothUnregisterAuthentication.argtypes = [w.HANDLE]

    if renew:
        api.BluetoothRemoveDevice.argtypes = [c.POINTER(c.c_ulonglong)]
        target_address = c.c_ulonglong(target)
        status = api.BluetoothRemoveDevice(c.byref(target_address))
        if status not in (0, ERROR_NOT_FOUND):
            raise OSError(status, c.FormatError(status))

    device = Device(size=c.sizeof(Device), address=target)
    api.BluetoothGetDeviceInfo(None, c.byref(device))

    @callback_type
    def callback(_context: c.c_void_p, pointer: c.POINTER(Params)) -> bool:
        request = pointer.contents
        accepted = (
            request.device.address == target
            and request.method == NUMERIC_COMPARISON
            and request.io == NO_INPUT_NO_OUTPUT
        )
        response = Response(
            address=request.device.address,
            method=request.method,
            negative=not accepted,
        )
        response.data.numeric = request.numeric
        api.BluetoothSendAuthenticationResponseEx(None, c.byref(response))
        return True

    registration = w.HANDLE()
    status = api.BluetoothRegisterForAuthenticationEx(
        c.byref(device), c.byref(registration), callback, None,
    )
    if status:
        raise OSError(status, c.FormatError(status))
    try:
        status = api.BluetoothAuthenticateDeviceEx(
            None, None, c.byref(device), None, DEDICATED_BONDING,
        )
        if status:
            raise OSError(status, c.FormatError(status))
    finally:
        api.BluetoothUnregisterAuthentication(registration)
