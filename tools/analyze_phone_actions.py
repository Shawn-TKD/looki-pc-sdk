"""Summarize safe LCMP metadata from a phone HCI capture for one Looki device.

The report deliberately omits raw message bodies and string/bytes values.  It
keeps only timestamps, message types, field numbers and integer enum values so
that captured credentials, hotspot passwords and user content never enter the
derived analysis files.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import struct
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from looki.protocol.lcmp import Framer, fields


BTSNOOP_EPOCH_OFFSET_US = 0x00DC_DDB3_0E2F_0000
SENSITIVE_TAGS = {103, 200, 201, 205, 219, 263, 268, 275, 276, 284}


@dataclass(frozen=True)
class L2capPacket:
    timestamp: str
    direction: str
    handle: int
    cid: int
    payload: bytes


def timestamp_from_btsnoop(value: int) -> str:
    seconds = (value - BTSNOOP_EPOCH_OFFSET_US) / 1_000_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone().isoformat(timespec="milliseconds")


def message_names() -> dict[int, str]:
    proto = (ROOT / "proto" / "lcmp_v1.proto").read_text(encoding="utf-8")
    start = proto.index("message LcmpMessagePb")
    envelope = proto[start:]
    return {
        int(number): name
        for name, number in re.findall(r"\b(\w+)\s*=\s*(\d+);", envelope)
    }


def iter_hci_records(source: Path):
    data = source.read_bytes()
    if data[:16] != b"btsnoop\0" + struct.pack(">II", 1, 1002):
        raise ValueError("not a Bluetooth HCI btsnoop file")
    position = 16
    while position + 24 <= len(data):
        _, included, flags, _, timestamp = struct.unpack_from(">IIIIQ", data, position)
        packet_end = position + 24 + included
        if packet_end > len(data):
            break
        yield flags, timestamp, data[position + 24:packet_end]
        position = packet_end


def looki_handles(source: Path, looki_mac: str) -> set[int]:
    handles: set[int] = set()
    wanted = bytes.fromhex(looki_mac.replace(":", "").replace("-", ""))[::-1]
    for _, _, packet in iter_hci_records(source):
        if len(packet) >= 12 and packet[0] == 0x04 and packet[1] == 0x03 and packet[6:12] == wanted:
            handles.add(struct.unpack_from("<H", packet, 4)[0] & 0x0FFF)
    return handles


def iter_l2cap(source: Path, handles: set[int]):
    """Reassemble HCI ACL fragments into L2CAP payloads for Looki handles."""
    fragments: dict[tuple[str, int], tuple[str, bytearray]] = {}
    for flags, timestamp_raw, packet in iter_hci_records(source):
        if len(packet) < 9 or packet[0] != 0x02:
            continue
        handle_flags, acl_length = struct.unpack_from("<HH", packet, 1)
        handle, packet_boundary = handle_flags & 0x0FFF, (handle_flags >> 12) & 0x03
        if handle not in handles or len(packet) != acl_length + 5:
            continue
        direction = "phone_to_looki" if (flags & 1) == 0 else "looki_to_phone"
        timestamp = timestamp_from_btsnoop(timestamp_raw)
        key = direction, handle
        acl_payload = packet[5:]
        if packet_boundary in (0, 2):
            fragments[key] = timestamp, bytearray(acl_payload)
        elif packet_boundary == 1 and key in fragments:
            fragments[key][1].extend(acl_payload)
        else:
            continue

        start_time, buffer = fragments[key]
        while len(buffer) >= 4:
            length, cid = struct.unpack_from("<HH", buffer)
            total = 4 + length
            if len(buffer) < total:
                break
            yield L2capPacket(start_time, direction, handle, cid, bytes(buffer[4:total]))
            del buffer[:total]


def rfcomm_information(packet: L2capPacket) -> tuple[int, bytes] | None:
    frame = packet.payload
    if len(frame) < 4:
        return None
    control = frame[1]
    if control & 0xEF != 0xEF:
        return None
    position = 3
    length = frame[2] >> 1
    if frame[2] & 1 == 0:
        if position >= len(frame):
            return None
        length |= frame[position] << 7
        position += 1
    if control & 0x10:
        position += 1
    end = position + length
    if end >= len(frame):  # one RFCOMM FCS byte must follow the information field
        return None
    return frame[0] >> 2, frame[position:end]


def safe_field_summary(payload: bytes) -> list[dict[str, int | str]]:
    summary: list[dict[str, int | str]] = []
    for field_number, wire_type, value in fields(payload):
        item: dict[str, int | str] = {"field": field_number, "wire": wire_type}
        if wire_type == 0 and isinstance(value, int):
            item["value"] = value
        elif isinstance(value, bytes):
            item["bytes"] = len(value)
        summary.append(item)
    return summary


def analyze(source: Path, output: Path, looki_mac: str) -> dict[str, object]:
    names = message_names()
    handles = looki_handles(source, looki_mac)
    if not handles:
        raise RuntimeError(f"no HCI connection event found for {looki_mac}")

    framers: dict[tuple[str, int, int], Framer] = {}
    rows: list[dict[str, object]] = []
    type_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for l2cap in iter_l2cap(source, handles):
        info = rfcomm_information(l2cap)
        if info is None:
            continue
        dlci, information = info
        if dlci != 6:  # RFCOMM server channel 3, observed as DLCI 6
            continue
        key = l2cap.direction, l2cap.handle, l2cap.cid
        framer = framers.setdefault(key, Framer())
        for body in framer.feed(information):
            for tag, wire_type, value in fields(body):
                if tag <= 3:
                    continue
                name = names.get(tag, f"unknown_{tag}")
                type_counts[l2cap.direction][name] += 1
                row: dict[str, object] = {
                    "timestamp": l2cap.timestamp,
                    "direction": l2cap.direction,
                    "handle": l2cap.handle,
                    "cid": l2cap.cid,
                    "tag": tag,
                    "type": name,
                }
                if wire_type == 2 and isinstance(value, bytes) and tag not in SENSITIVE_TAGS:
                    row["fields"] = safe_field_summary(value)
                elif tag in SENSITIVE_TAGS:
                    row["fields"] = "withheld"
                rows.append(row)

    report = {
        "source": source.name,
        "looki_mac": looki_mac,
        "handles": sorted(handles),
        "message_counts": {direction: dict(sorted(counts.items())) for direction, counts in type_counts.items()},
        "events": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--looki-mac", required=True)
    args = parser.parse_args()
    report = analyze(args.source, args.output, args.looki_mac)
    print(json.dumps({
        "handles": report["handles"],
        "message_counts": report["message_counts"],
        "events": len(report["events"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
