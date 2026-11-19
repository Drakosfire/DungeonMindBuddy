# Statblock theme asset provenance

These files are used by [the campaign statblock stylesheet](../statblockCampaignTheme.css).
Keep this provenance record and the [font notice](FONT-LICENSE.txt) with the source
assets when copying the theme. Buddy Home links **Font credits** to a separately
emitted, fingerprinted copy of that text. The production-bundle browser witness
checks the link and readable HTTP response. Verification on a selected deployed
release remains with
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
The font notice applies to the fonts, independently of the paper texture and Buddy application code.

## Exact upstream copies

The four font files match these Git blobs in
[Homebrewery revision `73df298c`](https://github.com/naturalcrit/homebrewery/tree/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes).
These upstream paths document the font copies. The former JPEG is described separately below.

| Local file (relative to this directory) | Official upstream copy | Git blob |
| --- | --- | --- |
| `fonts/Bookinsanity Bold Italic.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Bold%20Italic.woff2) | `5df24b0453674485aa8c8083fb2738c700ea5387` |
| `fonts/Bookinsanity Bold.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Bold.woff2) | `6ddd39c5a84832d9dd016a153807cec1bf7c0144` |
| `fonts/Bookinsanity Italic.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity%20Italic.woff2) | `2fd334366815399ed6a8f0415c54f2435d54b546` |
| `fonts/Bookinsanity.woff2` | [Homebrewery](https://github.com/naturalcrit/homebrewery/blob/73df298c2504e22cdfc1a0961ce6306d1e62d5ba/themes/fonts/5e/Bookinsanity.woff2) | `05c1c9d8a0a30e72dcc0a93f3896a8252c9b2540` |

Recheck local object identities without changing the assets:

```bash
git hash-object apps/live-control-ui/src/statblocks/render/statblock-theme/fonts/*.woff2
```

These bytes were already present in Buddy at commit
[`a4e3478665d2adaced76f20ec53719ccea40c0bd`](https://github.com/Drakosfire/DungeonMindBuddy/commit/a4e3478665d2adaced76f20ec53719ccea40c0bd).
[#3045](https://github.com/Drakosfire/DungeonMindBuddy/pull/3045) relocated the
existing files from public assets into this module-managed theme.

## Original Buddy paper

`assets/buddy-paper.svg` is an original procedural texture authored for Buddy.
It combines a cream-to-tan radial gradient with faint monochrome grain. It has
no embedded or external images, scripts, fonts, or copied upstream image bytes.
Both the campaign statblock renderer and Home preview use this same asset.
The SVG source and its history are the authoring record; no third-party image
license is inferred from the former upstream copy.

The replacement preserves the existing paper role, layout and font files.
Source replacement does not prove deployment or satisfy the separate font-notice
delivery gate. Verify the actual selected release under
[#4062](https://github.com/Drakosfire/DungeonMindBuddy/issues/4062).

## Retired JPEG provenance

The removed `parchmentBackground.jpg` was an exact Homebrewery copy (174,383 bytes;
SHA256 `fc153294b70f6aac4d2ce48c7e9d015945b87c48f584db29da30cbbd5b876d1c`,
Git blob `a945966b904165495946203acc8daa861ab71eb5`). Its creator and asset-specific
redistribution terms were not established. No permission for that image is
claimed by replacing it. Git preserves the
[former file and complete provenance record](https://github.com/Drakosfire/DungeonMindBuddy/tree/9aca8915b3e984464609e4d0c9347a2204592455/apps/live-control-ui/src/statblocks/render/statblock-theme).
Do not restore or redistribute it on the assumption that an upstream software
license or the adjacent fonts' license covers the image.
