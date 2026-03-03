# Icon Extraction Research (2026-03-03)

## Problem

Mod icons display incorrectly in-game:
- Neutral icons shifted left/up in the diplomacy banner (hex context)
- Icons appear at wrong scale in banner — heads too small
- Happy/angry icons centered but shifted down
- Table view (circ context) looks OK but still slightly off

## Root Cause: Two Different Portrait Crops

The game stores **two completely different portrait crops** per leader in separate CIVBIG texture files:

| Variant | Content | Position on canvas | Alpha shape |
|---------|---------|-------------------|-------------|
| **HEX** (default context) | Wide frame: head + shoulders | Bottom-aligned (row ~35→128 of 128px) | Head silhouette, wider |
| **CIRC** (CIRCLE_MASK) | Tight head-shot only | Vertically centered (row ~17→115 of 128px) | Head silhouette, tighter |

Our mod was extracting only `circ_256` and using it as the source for ALL 8 icon variants (both hex and circ contexts). This gives correct results for circ icons but completely wrong framing for hex icons.

### Measured bounding boxes (alpha channel) at 128×128

```
game_hex_128:    bbox=(0, 34, 128, 128)  center=(64,80)  — wide, bottom-aligned
game_circ_128:   bbox=(0, 17, 128, 115)  center=(64,66)  — tight, centered
our_hex_128:     bbox=(4, 17, 127, 117)  center=(65,66)  — WRONG: circ crop in hex context
```

### At 256×256

```
game_hex_256:    bbox=(0, 77, 256, 256)  — content starts ~30% down, extends to bottom edge
game_circ_256:   bbox=(13, 34, 254, 229) — content centered, doesn't reach edges
```

### Consistent across all leaders

Verified with Augustus, Hatshepsut, Napoleon, Confucius, Isabella, Ibn Battuta — all show the same pattern: hex is wider + bottom-aligned, circ is tighter + centered.

## Key Discovery: BC7 Data Starts at Byte 16

All previous extraction failures were caused by the wrong data start offset. The correct CIVBIG file structure is:

```
[16-byte prefix] [BC7 mipchain data (payload_size bytes)] [footer padding]
```

- **Prefix** (16 bytes): `"CIVBIG\0\0"` + uint32 payload_size + uint32 flags
- **BC7 data** starts at **byte 16** — level-0 mipmap is first
- **Footer** = transparent BC7 padding blocks (decode to RGBA(0,0,0,0))
- Mipchain stops at 4×4 (not 1×1)

The `payload_size` field (offset 8) gives the BC7 mipchain size. Footer size = `file_size - 16 - payload_size`.

Previous wrong assumption: `header_size = file_size - payload_size` was used as the BC7 start offset. This included footer padding in the "header", shifting all extractions by 128-272 bytes (= 32-68 pixels of horizontal shift).

## Fix: Direct Level-0 Extraction for All 8 Variants

Instead of deriving all icons from circ_256, extract each variant directly from its own game texture:

| Variant | Source texture file | Size | Context |
|---------|-------------------|------|---------|
| hex_256 | `TEXTURE_lp_hex_{name}_256` | 256×256 | DEFAULT |
| hex_128 | `TEXTURE_lp_hex_{name}_128` | 128×128 | DEFAULT |
| hex_128_h | `TEXTURE_lp_hex_{name}_128_h` | 128×128 | LEADER_HAPPY |
| hex_128_a | `TEXTURE_lp_hex_{name}_128_a` | 128×128 | LEADER_ANGRY |
| hex_64 | `TEXTURE_lp_hex_{name}_64` | 64×64 | DEFAULT |
| circ_256 | `TEXTURE_lp_circ_{name}_256` | 256×256 | CIRCLE_MASK |
| circ_128 | `TEXTURE_lp_circ_{name}_128` | 128×128 | CIRCLE_MASK |
| circ_64 | `TEXTURE_lp_circ_{name}_64` | 64×64 | CIRCLE_MASK |

This gives pixel-perfect game-matching icons — correct crop, correct framing, correct alpha, no resizing artifacts, no custom masks, no portrait file fallbacks.

## fxs-icon Rendering Pipeline

The game's `fxs-icon` web component renders icons as CSS background images with no geometric clipping:

```css
/* Base/modules/core/ui/themes/default/default.css lines 2270-2277 */
fxs-icon {
    width: inherit;
    height: inherit;
    pointer-events: none;
    background-position: center;
    background-size: contain;
    background-repeat: no-repeat;
}
```

### Rendering flow

1. `fxs-icon` observes `data-icon-id`, `data-icon-context`, `data-icon-size` attributes
2. On change, queues `render()` via `queueMicrotask()`
3. `render()` calls `UI.getIconCSS(id, context)` → looks up `IconDefinitions` table
4. Returns CSS `url('blp:...')` or `url('fs://game/...')` string
5. Sets `this.Root.style.backgroundImage = iconUrl`

**No clip-path, no mask-image, no CSS masking at all.** The hex/circle shapes are entirely baked into the PNG alpha channels.

### Component source

`Base/modules/core/ui/components/fxs-icon.chunk.js` (55 lines):

```javascript
class FxsIcon extends Component {
    onAttributeChanged(name, oldValue, newValue) {
        if (name == "data-icon-id" || name == "data-icon-context" || name == "data-icon-size") {
            if (!this.renderQueued) {
                this.renderQueued = true;
                queueMicrotask(this.render.bind(this));
            }
        }
    }
    render() {
        this.renderQueued = false;
        const id = this.Root.getAttribute("data-icon-id");
        const context = this.Root.getAttribute("data-icon-context");
        if (id) {
            const iconUrl = UI.getIconCSS(id, context ? context : void 0);
            this.Root.style.backgroundImage = iconUrl;
        }
    }
}
```

### Leader icon container

`Base/modules/core/ui/save-load/leader-icon.js` builds a layered hex display:
- Shadow layer (`img-hex-shadow`)
- Banner/flag area (`img-hud-frontbanner`)
- Civ icon overlay (`img-hex-overlay`)
- Frame (`img-hex-frame`)
- Leader portrait (`fxs-icon` with `data-icon-context="LEADER"`)

## IconDefinitions Schema

From `Base/Assets/schema/icons/IconManager.sql`:

```sql
CREATE TABLE 'IconDefinitions' (
    'ID' TEXT NOT NULL,
    'Context' TEXT NOT NULL DEFAULT 'DEFAULT',
    'IconSize' INTEGER NOT NULL DEFAULT 0,
    'Path' Text NOT NULL,
    'NeedsTinting' INTEGER DEFAULT 0,
    'FitToContent' INTEGER DEFAULT 0,
    'InteractiveTop' INTEGER,
    'InteractiveRight' INTEGER,
    'InteractiveBottom' INTEGER,
    'InteractiveLeft' INTEGER,
    PRIMARY KEY('ID', 'Context', 'IconSize')
);
```

Composite PK: `(ID, Context, IconSize)`. Each combination is unique.

### Leader icon entries (8 per leader)

| Context | Sizes | Notes |
|---------|-------|-------|
| DEFAULT (omitted in XML) | 256, 128, 64 | Hex icons — diplomacy ribbon, tooltips |
| LEADER_HAPPY | 128 | Happy expression — diplomacy screen |
| LEADER_ANGRY | 128 | Angry expression — diplomacy screen |
| CIRCLE_MASK | 256, 128, 64 | Circular icons — leader select, civilopedia |

### Path formats

- Base game: `blp:lp_hex_amina_256` (packed in BLP archives)
- Mods: `fs://game/authentic-leaders/icons/amina/lp_hex_amina_256.png`

## CIVBIG File Format

```
Offset  Size  Description
0       8     Magic: "CIVBIG\0\0"
8       4     uint32 LE: payload_size (BC7 mipchain size)
12      4     uint32 LE: flags (always 0x10000100)
16      ...   BC7 compressed texture data (level-0 first, then mip levels)
16+P    ...   Footer padding: transparent BC7 blocks (P = payload_size)
```

BC7 data starts at byte 16. Level-0 is first in the mipchain. Mipchain stops at 4×4.
Footer = repeating 16-byte blocks (`80 00 00 00 00 00 00 00 00 00 00 00 ac aa aa aa`) that decode to fully transparent RGBA(0,0,0,0).

BC7 decodes as BGRA — swap R and B channels for RGBA.

## External Research

### No existing extraction tools

Our `scripts/extract-game-assets.py` appears to be the only known CIVBIG texture extractor. No public tools, repos, or documentation exist for this format.

### No reference mods for leader icon replacement

No other Civ7 mod replaces leader portrait icons. Community mods that modify icons focus on tech/civic/unit icons (simpler: single flat images without portrait crops).

### Relevant community resources

- [CivFanatics: How to import PNG files for icons](https://forums.civfanatics.com/threads/how-to-import-png-files-for-some-art-icon.695384/) — definitive icon import tutorial, shows `<Replace>` with child elements
- [CivFanatics: Civ 7 Icon change (Unit, Tech)](https://forums.civfanatics.com/threads/civ-7-icon-change-unit-tech.696336/) — notes icon replacement is "inconsistent right now"
- [CivFanatics: Civilization Asset Templates](https://forums.civfanatics.com/threads/civilization-asset-templates.695913/) — 256×256 PNG templates
- [CivFanatics: Proof of Concept - Custom Tech/Civic Icons](https://forums.civfanatics.com/resources/proof-of-concept-custom-tech-civic-unique-civic-ideology-icons.31923/) — 256×256 with ~234×234 centered circle
- [CivFanatics: 3D Leader mods](https://forums.civfanatics.com/threads/3d-leader-mods.697062/) — leader art modding discussion
- [CivFanatics: BLP files discussion](https://forums.civfanatics.com/threads/blp-files.600399/) — BLP cannot be extracted/decompiled (Civ6 era)
- [GitHub: izica/civ7-modding-tools](https://github.com/izica/civ7-modding-tools) — TypeScript mod builder with `ImportFileBuilder` for icons
- [GitHub: Zei33/Civilization-VII-Modding-Documentation](https://github.com/Zei33/Civilization-VII-Modding-Documentation) — community modding docs (no icon-specific content)
- [Civ7 Community Modding Docs](https://civ7community.mintlify.app/community/documentation-guide) — 37-page modding docs including Assets & Icons guide
- [texture2ddecoder (PyPI)](https://pypi.org/project/texture2ddecoder/) — Python BC7 decoder used by our extraction script
- [BC7 Format - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format) — official BC7 spec

### Key community advice

- Icon PNGs must have transparent backgrounds — game checks for transparency
- Standard icon dimensions: 256×256 for leaders, 128×128 for units
- `fs://game/{mod-id}/{path}.png` for mod file references
- `<Replace>` must use child-element syntax (not attribute syntax)

## Fallback Plan

If direct level-0 extraction still produces issues:

1. **Try extracting at different offsets** — the payload might have a sub-header before level-0
2. **Use circ_256 for circ contexts, hex_128 for hex contexts** — at least get the crop right even if some sizes need resizing
3. **Screenshot-based extraction** — render icons in-game via an icon browser and screenshot them (like Sukritact's Civ6 tool)
4. **Manual crop adjustment** — measure the exact offset between our icons and game icons, apply a pixel shift to compensate
