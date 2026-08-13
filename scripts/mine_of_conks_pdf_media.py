#!/usr/bin/env python3
"""Mine Of Conks illustrated PDF art into local gitignored media.

Default source is the illustrated DriveThru PDF::

  ~/Downloads/1399969-20190116_Conks-Cons_v21.pdf

(Do **not** use the text-only ``…_PF_v21.pdf`` — its figure slots are empty.)

Extracts named maps/cover/plates via ``pdfimages``, writes
``corpus/of-conks-cons-markdown/media/``, and an inventory JSON.

Example::

  uv run python scripts/mine_of_conks_pdf_media.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Downloads" / "1399969-20190116_Conks-Cons_v21.pdf"
MEDIA_DIR = ROOT / "corpus" / "of-conks-cons-markdown" / "media"

# Stable names projected by ofConksNodeMedia.ts. Values are (min_w, min_h, max_w, max_h)
# selection hints applied after chroma/size filtering + perceptual dedupe, then
# ordered by discovery. We also prefer known pixel sizes from the illustrated PDF.
NAMED_TARGETS: list[tuple[str, tuple[int, int]]] = [
    ("cover-of-conks.jpg", (992, 1403)),
    ("map-greenfields.jpg", (840, 649)),
    ("map-hempholm.jpg", (1000, 773)),
    ("fig-1-the-shacks.jpg", (1000, 773)),  # same village map plate
    ("art-greenfields-oaks.jpg", (780, 600)),  # first 780x600 pastoral (page 6)
    ("art-area-5-harvest.jpg", (780, 600)),  # later harvest plate (page 11)
    ("art-pastoral-cattle.jpg", (780, 600)),
    ("art-road-travelers.jpg", (780, 600)),
]


def _sample_stats(im: Image.Image) -> tuple[float, float, str]:
    rgb = im.convert("RGB")
    sample = rgb.resize((48, 48))
    pixels = list(sample.getdata())
    mean = sum(sum(c) for c in pixels) / (3 * len(pixels))
    chroma = sum(max(c) - min(c) for c in pixels) / len(pixels)
    digest = hashlib.md5(sample.tobytes()).hexdigest()
    return mean, chroma, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    if shutil.which("pdfimages") is None:
        print("pdfimages not found (poppler-utils)", file=sys.stderr)
        return 2
    if "PF_v21" in args.pdf.name:
        print(
            "Refusing text-only PF PDF (empty figure slots). "
            "Use 1399969-20190116_Conks-Cons_v21.pdf",
            file=sys.stderr,
        )
        return 2

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    for stale in MEDIA_DIR.glob("page-*.jpg"):
        stale.unlink()

    with tempfile.TemporaryDirectory(prefix="of-conks-media-") as tmp:
        work = Path(tmp)
        prefix = work / "img"
        subprocess.run(
            ["pdfimages", "-all", str(args.pdf), str(prefix)],
            check=True,
        )

        candidates: list[tuple[Path, int, int, float, float]] = []
        seen: set[str] = set()
        for path in sorted(work.iterdir()):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".ppm", ".tif", ".tiff"}:
                continue
            im = Image.open(path)
            w, h = im.size
            if w * h < 200_000:
                continue
            mean, chroma, digest = _sample_stats(im)
            if digest in seen:
                continue
            seen.add(digest)
            # Skip blank plates / parchment page textures.
            if mean > 220 and chroma < 10:
                continue
            if abs(w - 794) < 20 and abs(h - 1123) < 20 and chroma < 30:
                continue
            if chroma < 15 and mean > 150:
                continue
            candidates.append((path, w, h, mean, chroma))

        # Bucket 780x600 pastorals in discovery order for sequential naming.
        pastorals = [c for c in candidates if abs(c[1] - 780) < 15 and abs(c[2] - 600) < 15]
        by_size: dict[tuple[int, int], list[tuple[Path, int, int, float, float]]] = {}
        for c in candidates:
            by_size.setdefault((c[1], c[2]), []).append(c)

        files: list[dict[str, object]] = []
        pastoral_idx = 0
        used_paths: set[Path] = set()

        for name, (tw, th) in NAMED_TARGETS:
            chosen: tuple[Path, int, int, float, float] | None = None
            if name.startswith("art-") and (tw, th) == (780, 600):
                if pastoral_idx < len(pastorals):
                    chosen = pastorals[pastoral_idx]
                    pastoral_idx += 1
            else:
                pool = by_size.get((tw, th), [])
                for item in pool:
                    if item[0] not in used_paths:
                        chosen = item
                        break
            if chosen is None:
                print(f"missing target {name} @ {tw}x{th}", file=sys.stderr)
                return 1
            src, w, h, _mean, _chroma = chosen
            used_paths.add(src)
            dest = MEDIA_DIR / name
            Image.open(src).convert("RGB").save(dest, quality=92)
            files.append(
                {
                    "file": name,
                    "width": w,
                    "height": h,
                    "bytes": dest.stat().st_size,
                }
            )
            print(f"wrote {dest.relative_to(ROOT)} ({w}x{h}, {dest.stat().st_size} bytes)")

    inventory = {
        "schema": "of_conks_module_media_v1",
        "source_pdf": args.pdf.name,
        "note": (
            "Illustrated PDF art via pdfimages. Maps/cover/pastoral plates "
            "named for Play Object Sheet / Threat sheet projection."
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
