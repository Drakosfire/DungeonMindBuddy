#!/usr/bin/env python3
"""Mine Of Conks PDF pages into local gitignored media for Play sheet projection.

The DriveThru PDF ``1399969-20190116_Conks-Cons_PF_v21.pdf`` has **no embedded
adventure illustrations** (map / Fig.1 slots are empty white plates). This script
rasterizes the key module pages at 200 DPI for table reference and writes an
inventory under ``corpus/of-conks-cons-markdown/media/``.

Example::

  uv run python scripts/mine_of_conks_pdf_media.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Downloads" / "1399969-20190116_Conks-Cons_PF_v21.pdf"
MEDIA_DIR = ROOT / "corpus" / "of-conks-cons-markdown" / "media"

# printed_page → (pdf_page, output_filename, caption)
# This PDF: file page 1 == printed TOC page 2, so pdf_page = printed_page - 1.
PAGE_PLAN: list[tuple[int, int, str, str]] = [
    (4, 3, "page-04-greenfields.jpg", "The Greenfields"),
    (7, 6, "page-07-area-1-the-shacks.jpg", "Area 1: The Shacks"),
    (9, 8, "page-09-area-2-3-store-wagon.jpg", "Area 2–3: Store + Saladin"),
    (10, 9, "page-10-area-4-jove-home.jpg", "Area 4: The Jove's Home"),
    (11, 10, "page-11-area-5-grotesque-tree.jpg", "Area 5: The Grotesque Tree"),
    (15, 14, "page-15-descent-marrow.jpg", "Descent / The Marrow"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    if shutil.which("pdftoppm") is None:
        print("pdftoppm not found (poppler-utils)", file=sys.stderr)
        return 2

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    work = MEDIA_DIR / ".work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    files: list[dict[str, object]] = []
    for printed, pdf_page, filename, caption in PAGE_PLAN:
        prefix = work / f"p{pdf_page}"
        subprocess.run(
            [
                "pdftoppm",
                "-jpeg",
                "-r",
                str(args.dpi),
                "-f",
                str(pdf_page),
                "-l",
                str(pdf_page),
                str(args.pdf),
                str(prefix),
            ],
            check=True,
        )
        produced = sorted(work.glob(f"p{pdf_page}*.jpg"))
        if not produced:
            print(f"No raster for PDF page {pdf_page}", file=sys.stderr)
            return 1
        dest = MEDIA_DIR / filename
        shutil.copyfile(produced[0], dest)
        files.append(
            {
                "file": filename,
                "printed_page": printed,
                "pdf_page": pdf_page,
                "caption": caption,
                "bytes": dest.stat().st_size,
            }
        )
        print(f"wrote {dest.relative_to(ROOT)} ({dest.stat().st_size} bytes)")

    shutil.rmtree(work)
    inventory = {
        "schema": "of_conks_module_media_v1",
        "source_pdf": args.pdf.name,
        "dpi": args.dpi,
        "note": (
            "This PDF has no embedded adventure illustrations "
            "(Fig.1 / maps are empty plates). Mined assets are high-res "
            "module page rasters for table reference."
        ),
        "files": files,
    }
    (MEDIA_DIR / "INVENTORY.json").write_text(
        json.dumps(inventory, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"inventory → {MEDIA_DIR / 'INVENTORY.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
