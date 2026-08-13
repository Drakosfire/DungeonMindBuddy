# Of Conks & Cons — local world source root

This directory holds **local copyrighted third-party module sources**.

- Do **not** commit module prose or mined page rasters.
- Seeded by the Of Conks gold package under `~/Downloads/of-conks-cons-v21-gold/`.
- World id: `of-conks-cons`. Campaign id: `of-conks-cons`.

## Media

Run `uv run python scripts/mine_of_conks_pdf_media.py` against the local PDF to fill `media/` with high-res **module page rasters**.

The DriveThru PDF (`1399969-20190116_Conks-Cons_PF_v21.pdf`) has **no embedded adventure art** (map / Fig.1 slots are empty). Page rasters are the usable table reference until a true illustrated source is available.

Node → media associations live in `apps/live-control-ui/src/graphReference/ofConksNodeMedia.ts` and project on Play Object Sheets / Of Conks Threat play sheets via `/corpus/of-conks-cons-markdown/media/…`.

See `scripts/seed_of_conks_cons_world.py`.
