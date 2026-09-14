"""Temporary macOS Wi-Fi association for Looki's HTTP media service."""

from __future__ import annotations

import re
import subprocess
import time


NETWORKSETUP = "/usr/sbin/networksetup"
IPCONFIG = "/usr/sbin/ipconfig"


def _run(arguments: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    output = subprocess.PIPE if capture else subprocess.DEVNULL
    return subprocess.run(
        arguments,
        check=False,
        text=True,
        stdout=output,
        stderr=subprocess.PIPE,
    )


def _wifi_interface() -> str:
    result = _run([NETWORKSETUP, "-listallhardwareports"], capture=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "macOS could not list network interfaces")
    blocks = re.split(r"\n\s*\n", result.stdout)
    for block in blocks:
        if re.search(r"Hardware Port:\s*(Wi-Fi|AirPort)\s*$", block, re.MULTILINE):
            match = re.search(r"Device:\s*(\S+)", block)
            if match:
                return match.group(1)
    raise RuntimeError("macOS has no active Wi-Fi hardware port")


def _current_ssid(interface: str) -> str | None:
    result = _run([NETWORKSETUP, "-getairportnetwork", interface], capture=True)
    if result.returncode or ":" not in result.stdout:
        return None
    value = result.stdout.split(":", 1)[1].strip()
    return value or None


def _has_ipv4(interface: str) -> bool:
    result = _run([IPCONFIG, "getifaddr", interface], capture=True)
    address = result.stdout.strip()
    return result.returncode == 0 and bool(address) and not address.startswith("169.254.")


class MacOSHotspot:
    """Join one Looki hotspot and restore the previous Wi-Fi on exit."""

    def __init__(self, ssid: str, password: str, *, interface: str | None = None) -> None:
        self.ssid = ssid
        self.password = password
        self.interface = interface or _wifi_interface()
        self.restore_ssid: str | None = None
        self.join_attempted = False

    def __enter__(self) -> "MacOSHotspot":
        self.restore_ssid = _current_ssid(self.interface)
        self.join_attempted = True
        result = _run(
            [NETWORKSETUP, "-setairportnetwork", self.interface, self.ssid, self.password]
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "macOS could not join the Looki hotspot")
        for _ in range(20):
            if _current_ssid(self.interface) == self.ssid:
                break
            time.sleep(1)
        else:
            self._cleanup()
            raise TimeoutError("macOS did not associate with the Looki hotspot")
        for _ in range(10):
            if _has_ipv4(self.interface):
                return self
            time.sleep(1)
        self._cleanup()
        raise TimeoutError("Looki hotspot did not provide an IPv4 address")

    def __exit__(self, *_: object) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self.join_attempted:
            _run([NETWORKSETUP, "-removepreferredwirelessnetwork", self.interface, self.ssid])
            self.join_attempted = False
        if self.restore_ssid and self.restore_ssid != self.ssid:
            _run([NETWORKSETUP, "-setairportnetwork", self.interface, self.restore_ssid])
