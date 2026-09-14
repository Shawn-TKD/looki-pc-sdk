"""Extract one file from an ext4 partition image without mounting it."""

from __future__ import annotations

import argparse
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to an ext4 image")
    parser.add_argument("source", help="Absolute path inside the image")
    parser.add_argument("output", type=Path, help="Local output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import ext4

    with args.image.open("rb") as image_stream:
        volume = ext4.Volume(image_stream)
        data = volume.inode_at(args.source).open().read()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"extracted {args.source} ({len(data)} bytes) to {args.output}")


if __name__ == "__main__":
    main()
