"""List partitions stored in an Android update-engine payload.

Install a compatible payload-dumper package that exposes
``payload_dumper.update_metadata_pb2`` before using this research helper.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Path to payload.bin")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from payload_dumper import update_metadata_pb2

    with args.payload.open("rb") as stream:
        if stream.read(4) != b"CrAU":
            raise ValueError("not an Android update-engine payload")
        version = struct.unpack(">Q", stream.read(8))[0]
        manifest_size = struct.unpack(">Q", stream.read(8))[0]
        signature_size = struct.unpack(">I", stream.read(4))[0] if version >= 2 else 0
        manifest = update_metadata_pb2.DeltaArchiveManifest()
        manifest.ParseFromString(stream.read(manifest_size))

    print(
        f"version={version} manifest_size={manifest_size} "
        f"metadata_signature_size={signature_size} block_size={manifest.block_size}"
    )
    rows = []
    for partition in manifest.partitions:
        payload_bytes = sum(operation.data_length for operation in partition.operations)
        image_bytes = partition.new_partition_info.size
        rows.append(
            (image_bytes, payload_bytes, partition.partition_name, len(partition.operations))
        )

    for image_bytes, payload_bytes, name, operation_count in sorted(rows, reverse=True):
        print(
            f"{name:20s} image={image_bytes:12,d} "
            f"payload={payload_bytes:12,d} operations={operation_count}"
        )


if __name__ == "__main__":
    main()
