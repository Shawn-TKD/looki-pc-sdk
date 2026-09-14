"""HTTP client for the temporary file service advertised by Looki."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from .media import FileService


class HttpMediaClient:
    def __init__(self, service: FileService) -> None:
        self.base_url = f"http://{service.host}:{service.port}"

    def list_files(self, timeout: float = 40) -> list[dict[str, object]]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(self.base_url + "/files/list", timeout=3) as response:
                    document = json.loads(response.read().decode("utf-8"))
                items = document.get("fileList", [])
                if not isinstance(items, list):
                    raise ValueError("Looki returned an unexpected file-list structure")
                return [item for item in items if isinstance(item, dict)]
            except OSError:
                time.sleep(1)
        raise TimeoutError("Looki HTTP file service did not become reachable")

    def download(self, remote_name: str, destination: Path, timeout: float = 90) -> Path:
        query = urllib.parse.urlencode({"file": remote_name})
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".partial")
        with urllib.request.urlopen(
            self.base_url + "/files/download?" + query, timeout=timeout,
        ) as response, partial.open("wb") as handle:
            while chunk := response.read(64 * 1024):
                handle.write(chunk)
        partial.replace(destination)
        return destination


def summarize_files(items: list[dict[str, object]]) -> dict[str, object]:
    extensions = Counter(
        Path(str(item.get("name", ""))).suffix.lower() for item in items
    )
    return {"media_count": len(items), "media_by_extension": dict(sorted(extensions.items()))}
