from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import DocumentRepository
from app.ingest.parser import parse_document
from app.rag.chunking import chunk_text


def _extract_metadata(text: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    year_match = re.search(r"(20[1-3][0-9]\s*-\s*[0-9]{2})", text)
    if year_match:
        metadata["assessment_year"] = year_match.group(1).replace(" ", "")
    act_match = re.search(r"(income tax act|gst act)", text, flags=re.IGNORECASE)
    if act_match:
        metadata["act_name"] = act_match.group(1).title()
    sec_match = re.search(r"(section|sec)\s*([0-9]{1,3}[A-Z]?)", text, flags=re.IGNORECASE)
    if sec_match:
        metadata["section_hint"] = sec_match.group(2).upper()
    metadata["issue_date"] = date.today()
    return metadata


def ingest_path(db: Session, path: Path) -> dict[str, Any]:
    parsed = parse_document(path)
    content = parsed.pop("content")
    if len(content) < 120:
        return {"file": path.name, "status": "skipped", "reason": "content_too_short"}

    metadata = _extract_metadata(content)
    payload = {
        "source_path": parsed["source_path"],
        "source_name": parsed["source_name"],
        "checksum": parsed["checksum"],
        "assessment_year": metadata.get("assessment_year"),
        "act_name": metadata.get("act_name"),
        "section_hint": metadata.get("section_hint"),
        "issue_date": metadata.get("issue_date"),
        "metadata_json": metadata,
    }
    repo = DocumentRepository(db)
    doc = repo.upsert_document(payload)

    raw_chunks = chunk_text(content)
    chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(raw_chunks):
        chunks.append(
            {
                "chunk_index": index,
                "content": chunk,
                "source_ref": f"{path.name}#chunk-{index}",
                "token_count": max(1, len(chunk) // 4),
                "embedding": None,
                "metadata_json": metadata,
                "score": 0.0,
            }
        )
    repo.replace_chunks(doc.id, chunks)
    db.commit()
    return {"file": path.name, "status": "indexed", "chunks": len(chunks)}
