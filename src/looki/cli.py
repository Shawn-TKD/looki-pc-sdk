"""Command-line interface for the verified Looki PC SDK surface."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .credentials.binding import OwnerBinding, owner_binding_from_framed_capture
from .diagnostics import host_diagnostics
from .device.control import LookiControls
from .device.http_media import HttpMediaClient, summarize_files
from .device.media import request_file_service
from .device.session import LookiSession
from .device.status import read_status
from .host import hotspot_connection, pair_device


CONTROL_METHODS = {
    "photo": "capture_photo",
    "audio-start": "start_audio_recording",
    "audio-stop": "stop_audio_recording",
    "video-start": "start_video_recording",
    "video-stop": "stop_video_recording",
    "diary-start": "start_diary_recording",
    "diary-stop": "stop_diary_recording",
}


def _binding(path: str | None) -> OwnerBinding | None:
    return OwnerBinding.load_portable(Path(path)) if path else None


def _add_device_arguments(parser: argparse.ArgumentParser, *, binding_required: bool) -> None:
    parser.add_argument("--address", required=True, help="Looki Bluetooth MAC address")
    parser.add_argument("--channel", type=int, default=3)
    parser.add_argument("--binding", required=binding_required, help="private .looki-binding file")


def _observe(session: LookiSession, seconds: float) -> list[dict[str, int]]:
    events: list[dict[str, int]] = []
    deadline = time.monotonic() + seconds
    for received in session.receive(deadline):
        event = {"tag": received.tag, "wire_type": received.wire_type}
        if isinstance(received.payload, int):
            event["value"] = received.payload
        else:
            event["payload_length"] = len(received.payload)
        events.append(event)
    return events


def _control(args: argparse.Namespace) -> dict[str, object]:
    owner = _binding(args.binding)
    assert owner is not None
    with LookiSession(args.address, args.channel) as session:
        session.authenticate(owner_binding=owner)
        controls = LookiControls(session)
        if args.command == "privacy-on":
            controls.set_privacy_light(True)
        elif args.command == "privacy-off":
            controls.set_privacy_light(False)
        else:
            getattr(controls, CONTROL_METHODS[args.command])()
        return {"command": args.command, "sent": True, "events": _observe(session, args.observe)}


def _media(args: argparse.Namespace) -> dict[str, object]:
    owner = _binding(args.binding)
    assert owner is not None
    with LookiSession(args.address, args.channel) as session:
        service = request_file_service(session, owner)
        with hotspot_connection(service.ssid, service.password, interface=args.interface):
            client = HttpMediaClient(service)
            items = client.list_files()
            summary = summarize_files(items)
            if args.command == "media-list":
                return summary

            suffix = "." + args.kind.lower().lstrip(".")
            matching = [
                item for item in items
                if str(item.get("name", "")).lower().endswith(suffix)
            ]
            if not matching:
                raise RuntimeError(f"Looki has no {suffix} media")
            remote_name = str(matching[-1]["name"])
            destination = Path(args.output) / Path(remote_name).name
            client.download(remote_name, destination)
            return {**summary, "downloaded": str(destination.resolve()), "bytes": destination.stat().st_size}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="print non-sensitive host integration diagnostics")

    pair = commands.add_parser("pair", help="establish the host Classic Bluetooth bond")
    pair.add_argument("--address", required=True)
    pair.add_argument("--renew", action="store_true")

    enroll = commands.add_parser("enroll", help="create a private portable owner bundle")
    enroll.add_argument("--capture", required=True, help="reassembled framed LCMP stream")
    enroll.add_argument("--output", required=True, help="output .looki-binding path")

    status = commands.add_parser("status", help="read battery, device, storage and media status")
    _add_device_arguments(status, binding_required=False)

    for name in (*CONTROL_METHODS, "privacy-on", "privacy-off"):
        control = commands.add_parser(name)
        _add_device_arguments(control, binding_required=True)
        control.add_argument("--observe", type=float, default=2)

    media_list = commands.add_parser("media-list", help="list media counts without filenames")
    _add_device_arguments(media_list, binding_required=True)
    media_list.add_argument("--interface", help="Wi-Fi interface; detected automatically on macOS")

    download = commands.add_parser("download-one", help="download one media item by type")
    _add_device_arguments(download, binding_required=True)
    download.add_argument("--interface", help="Wi-Fi interface; detected automatically on macOS")
    download.add_argument("--kind", choices=("jpg", "m4a", "mp4"), required=True)
    download.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "doctor":
        result = host_diagnostics()
    elif args.command == "pair":
        pair_device(args.address, renew=args.renew)
        result: dict[str, object] = {"paired": True, "address": args.address}
    elif args.command == "enroll":
        owner = owner_binding_from_framed_capture(Path(args.capture))
        output = Path(args.output)
        owner.save_portable(output)
        result = {"binding_created": str(output.resolve())}
    elif args.command == "status":
        with LookiSession(args.address, args.channel) as session:
            session.authenticate(owner_binding=_binding(args.binding))
            result = read_status(session)
    elif args.command in (*CONTROL_METHODS, "privacy-on", "privacy-off"):
        result = _control(args)
    else:
        result = _media(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
