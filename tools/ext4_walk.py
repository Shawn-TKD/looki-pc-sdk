"""Write a recursive file listing for an ext4 partition image."""

from __future__ import annotations

import argparse
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to an ext4 image")
    parser.add_argument("output", type=Path, help="Text file to create")
    parser.add_argument("--max-depth", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import ext4
    from ext4 import EXT4_FT

    lines: list[str] = []

    with args.image.open("rb") as image_stream:
        volume = ext4.Volume(image_stream)

        def walk(path: str, depth: int) -> None:
            if depth > args.max_depth:
                return
            inode = volume.root if path == "/" else volume.inode_at(path)
            for entry, file_type in inode.opendir():
                name = entry.name_str if isinstance(entry.name, bytes) else entry.name
                if name in (".", ".."):
                    continue
                child = f"{path.rstrip('/')}/{name}"
                if file_type == EXT4_FT.DIR:
                    lines.append(f"{child}/")
                    walk(child, depth + 1)
                else:
                    lines.append(child)

        walk("/", 0)

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} entries to {args.output}")


if __name__ == "__main__":
    main()
