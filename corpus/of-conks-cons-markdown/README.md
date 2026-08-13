# Of Conks & Cons — local world source root

This directory holds **local copyrighted third-party module sources**.

- Do **not** commit module prose or mined media bitmaps.
- Seeded by the Of Conks gold package under `~/Downloads/of-conks-cons-v21-gold/`.
- World id: `of-conks-cons`. Campaign id: `of-conks-cons`.

## Media

Use the **illustrated** PDF (not the text-only `…_PF_v21.pdf`):

```bash
uv run python scripts/mine_of_conks_pdf_media.py \
  --pdf ~/Downloads/1399969-20190116_Conks-Cons_v21.pdf
```

Writes maps/cover/plates into `media/` (gitignored). Node associations live in
`apps/live-control-ui/src/graphReference/ofConksNodeMedia.ts` and project on
Play Object Sheets / Of Conks Threat sheets via `/corpus/of-conks-cons-markdown/media/…`.

See `scripts/seed_of_conks_cons_world.py`.
