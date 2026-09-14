"""Temporary Windows Wi-Fi association for Looki's HTTP media service."""

from __future__ import annotations

import html
import re
import subprocess
import tempfile
import time
from pathlib import Path


def _netsh(arguments: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    output = subprocess.PIPE if capture else subprocess.DEVNULL
    return subprocess.run(
        ["netsh", *arguments], check=False, text=True,
        stdout=output, stderr=subprocess.DEVNULL,
    )


def _current_ssid() -> str | None:
    result = _netsh(["wlan", "show", "interfaces"], capture=True)
    if result.returncode:
        return None
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().upper() == "SSID":
            return value.strip()
    return None


def _connected_to(ssid: str) -> bool:
    return _current_ssid() == ssid


def _has_ipv4(interface: str) -> bool:
    result = _netsh(
        ["interface", "ipv4", "show", "addresses", f"name={interface}"],
        capture=True,
    )
    addresses = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", result.stdout)
    return any(not address.startswith("169.254.") for address in addresses)


def _profile_xml(profile_name: str, ssid: str, password: str) -> str:
    escape = html.escape
    return f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{escape(profile_name)}</name>
  <SSIDConfig><SSID><name>{escape(ssid)}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType><connectionMode>manual</connectionMode>
  <MSM><security><authEncryption><authentication>WPA2PSK</authentication>
  <encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
  <sharedKey><keyType>passPhrase</keyType><protected>false</protected>
  <keyMaterial>{escape(password)}</keyMaterial></sharedKey></security></MSM>
</WLANProfile>'''


class WindowsHotspot:
    """Join one Looki hotspot and restore the previous Wi-Fi on exit."""

    def __init__(self, ssid: str, password: str, *, interface: str = "WLAN") -> None:
        self.ssid = ssid
        self.password = password
        self.interface = interface
        self.restore_ssid: str | None = None
        self.profile_name = f"Looki Direct {time.strftime('%Y%m%d%H%M%S')}"
        self.profile_added = False

    def __enter__(self) -> "WindowsHotspot":
        self.restore_ssid = _current_ssid()
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".xml", encoding="utf-8", delete=False) as handle:
                handle.write(_profile_xml(self.profile_name, self.ssid, self.password))
                temporary_path = Path(handle.name)
            result = _netsh([
                "wlan", "add", "profile", f"filename={temporary_path}",
                f"interface={self.interface}", "user=current",
            ])
            if result.returncode:
                raise RuntimeError("Windows could not add the temporary Looki Wi-Fi profile")
            self.profile_added = True
            _netsh(["wlan", "connect", f"name={self.profile_name}", f"interface={self.interface}"])
            for _ in range(20):
                if _connected_to(self.ssid):
                    break
                time.sleep(1)
            else:
                raise TimeoutError("Windows did not associate with the Looki hotspot")
            for _ in range(10):
                if _has_ipv4(self.interface):
                    return self
                time.sleep(1)
            raise TimeoutError("Looki hotspot did not provide an IPv4 address")
        except Exception:
            self._cleanup()
            raise
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def __exit__(self, *_: object) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self.profile_added:
            _netsh([
                "wlan", "delete", "profile", f"name={self.profile_name}",
                f"interface={self.interface}",
            ])
            self.profile_added = False
        if self.restore_ssid and self.restore_ssid != self.ssid:
            _netsh([
                "wlan", "connect", f"name={self.restore_ssid}",
                f"ssid={self.restore_ssid}", f"interface={self.interface}",
            ])
