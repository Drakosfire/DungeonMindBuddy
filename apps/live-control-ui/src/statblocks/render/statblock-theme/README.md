# Statblock theme asset provenance

These files are used by [the campaign statblock stylesheet](../statblockCampaignTheme.css).
Keep this provenance record and the [font notice](FONT-LICENSE.txt) with the source
assets when copying the theme. Buddy Home links **Font credits** to a separately
emitted, fingerprinted copy of that text. The production-bundle browser witness
checks the link and readable HTTP response. Verification on a selected deployed
release and the unresolved parchment permission remain with
[#4062](https://github.com/Drakosfire/DungeonMindBuddy/issues/4062).

## Bookinsanity Remake fonts

Credit: **Solbera and Ners**, as identified by the four files’ embedded designer
name records (SFNT name ID9). Their embedded license records identify
**Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**
(name ID13) and link to the [legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode)
(name ID14). The [license summary](https://creativecommons.org/licenses/by-sa/4.0/)
explains attribution, change indication and ShareAlike; the legal code controls.

The local WOFF2 bytes are unchanged from the identified official Homebrewery
copies below. This comparison does not establish the history of upstream font
conversions or edits. Attribution to these designers does not imply endorsement.
The font notice does not assign a license to the parchment or Buddy application code.

## Exact upstream copies

All five local files match these Git blobs in
[Homebrewery revision `73df298c`](https://github.com/naturalcrit/homebrewery/tree/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes).
The upstream paths are evidence of the copies, not proof of the JPEG’s permission chain.

| Local file (relative to this directory) | Official upstream copy | Git blob |
| --- | --- | --- |
| `assets/parchmentBackground.jpg` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/assets/parchmentBackground.jpg) | `a945966b904165495946203acc8daa861ab71eb5` |
| `fonts/Bookinsanity Bold Italic.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Bold%20Italic.woff2) | `5df24b0453674485aa8c8083fb2738c700ea5387` |
| `fonts/Bookinsanity Bold.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Bold.woff2) | `6ddd39c5a84832d9dd016a153807cec1bf7c0144` |
| `fonts/Bookinsanity Italic.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Italic.woff2) | `2fd334366815399ed6a8f0415c54f2435d54b546` |
| `fonts/Bookinsanity.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity.woff2) | `05c1c9d8a0a30e72dcc0a93f3896a8252c9b2540` |

Recheck local object identities without changing the assets:

```bash
git hash-object apps/live-control-ui/src/statblocks/render/statblock-theme/fonts/*.woff2 \
  apps/live-control-ui/src/statblocks/render/statblock-theme/assets/parchmentBackground.jpg
```

These bytes were already present in Buddy at commit
[`a4e3478665d2adaced76f20ec53719ccea40c0bd`](https://github.com/Drakosfire/DungeonMindBuddy/commit/a4e3478665d2adaced76f20ec53719ccea40c0bd).
[#3045](https://github.com/Drakosfire/DungeonMindBuddy/pull/3045) relocated the
existing files from public assets into this module-managed theme.

## Parchment: permission remains unresolved

`assets/parchmentBackground.jpg` is an exact upstream copy (174,383 bytes;
SHA256 `fc153294b70f6aac4d2ce48c7e9d015945b87c48f584db29da30cbbd5b876d1c`).
The original creator and asset-specific redistribution terms have not been established.
Homebrewery’s [software license](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/license)
and [README](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/README.md#license)
do not establish that permission for this image. The related
[upstream discussion](https://github.com/naturalcrit/homebrewery/discussions/4483)
is research context, not an asset-specific grant.

Buddy statblock UI maintainers own [#4062](https://github.com/Drakosfire/DungeonMindBuddy/issues/4062):
record authoritative permission and required attribution for this exact image,
or approve a separately licensed/original replacement in a reviewed rendering
change. Keep the active renderer intact during this provenance-only work.
The issue also owns verifying font/image notice delivery for the actual distribution.
