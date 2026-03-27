from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChunkConfig:
    max_chars: int = 1200
    overlap_chars: int = 150
    min_chars: int = 120


def chunk_text(content: str, config: ChunkConfig | None = None) -> list[str]:
    cfg = config or ChunkConfig()
    text = " ".join(content.split())
    if len(text) < cfg.min_chars:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + cfg.max_chars)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - cfg.overlap_chars)
    return [c for c in chunks if len(c) >= cfg.min_chars]
