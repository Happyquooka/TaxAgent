from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pypdf import PdfReader


def file_checksum(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def parse_document(path: Path) -> dict[str, Any]:
    text = ""
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")

    return {
        "source_path": str(path.resolve()),
        "source_name": path.name,
        "checksum": file_checksum(path),
        "content": text.strip(),
    }
