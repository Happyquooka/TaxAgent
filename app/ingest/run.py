from __future__ import annotations

import argparse
from pathlib import Path

from app.db.base import SessionLocal, init_db
from app.ingest.pipeline import ingest_path


def collect_files(source: Path, recursive: bool) -> list[Path]:
    if source.is_file():
        return [source]
    pattern = "**/*" if recursive else "*"
    candidates = [p for p in source.glob(pattern) if p.is_file()]
    return [p for p in candidates if p.suffix.lower() in {".pdf", ".txt", ".md"}]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest tax documents into TaxAgent")
    parser.add_argument("--source", required=True, help="Source file or directory")
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    files = collect_files(source, recursive=args.recursive)
    if not files:
        print("No supported files found.")
        return

    init_db()
    db = SessionLocal()
    try:
        for path in files:
            result = ingest_path(db, path)
            print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
