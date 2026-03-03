# Civ7 Game Asset Format Knowledge Base

Definitive documentation of how Civilization VII stores and organizes visual
assets, derived from binary analysis of game files. This document exists
because no public documentation of these formats exists anywhere.

Last updated: 2026-03-03

## File Locations

### macOS

```
~/Library/Application Support/Steam/steamapps/common/
  Sid Meier's Civilization VII/CivilizationVII.app/Contents/Resources/
    Base/
      modules/base-standard/
        data/icons/leader-icons.xml     # Icon definitions (ID → path + context + size)
        data/loading-info.xml           # Loading screen definitions
      ui-next/screens/load-screen/      # Loading screen JS/CSS
    DLC/
      boot-shell/Platforms/Mac/BLPs/SHARED_DATA/   # Most leader textures
      {dlc}-shell/Platforms/Mac/BLPs/SHARED_DATA/  # DLC leader textures
```

DLC shell directories for specific leaders:
- `boot-shell` — amina, ashoka, augustus, benjamin_franklin, catherine, charlemagne,
  confucius, friedrich, harriet_tubman, hatshepsut, himiko, ibn_battuta, isabella,
  jose_rizal, lafayette, machiavelli, pachacuti, tecumseh, trung_trac, xerxes
- `ada-lovelace-shell` — ada_lovelace
- `bolivar-shell` — simon_bolivar (texture name: `bolivar`, not `simon_bolivar`)
- `edward-teach-shell` — edward_teach
- `genghis-khan-shell` — genghis_khan
- `gilgamesh-shell` — gilgamesh
- `lakshmibai-shell` — lakshmibai
- `napoleon-shell` — napoleon
- `sayyida-al-hurra-shell` — sayyida_al_hurra
- `shawnee-tecumseh-shell` — tecumseh (also in boot-shell)

### Mod file paths

- Mods directory: `~/Library/Application Support/Civilization VII/Mods/`
- Logs: `~/Library/Application Support/Civilization VII/Logs/`

---

## CIVBIG Container Format

All game textures (icons, loading screens) are stored in CIVBIG container files.
These are NOT standard image formats — they contain BC7-compressed texture data
with a variable-length header.

### File Structure

```
Offset  Size  Field
0       8     Magic: "CIVBIG\0\0" (ASCII)
8       4     uint32 LE: payload_size (BC7 mipchain data size)
12      4     uint32 LE: flags (always 0x00010010)
16      P     BC7 texture data (level-0 mipmap starts here)
16+P    F     Footer padding (transparent BC7 blocks)
```

**BC7 level-0 data always starts at byte 16.** The `payload_size` field is the
size of the BC7 mipchain data. The footer after the mipchain consists of
transparent BC7 padding blocks (`80 00 00 00 00 00 00 00 00 00 00 00 AC AA AA AA`)
which decode to RGBA(0,0,0,0).

The same transparent block pattern also appears within the texture data itself,
encoding the transparent border areas of portraits.

### Footer Sizes by Texture Type

| Texture type | Footer size | Footer blocks |
|-------------|-------------|---------------|
| Loading screens (`TEXTURE_lsl_*`) | 128 bytes | 8 blocks |
| Circ icons (`TEXTURE_lp_circ_*`) | 160 bytes | 10 blocks |
| Hex icons (`TEXTURE_lp_hex_*`) | 272 bytes | 17 blocks |

### BC7 Texture Data

BC7 mipchain data starts at **byte 16** of the file. Level-0 (the full-size
texture) is first in the mipchain.

BC7 format basics:
- 4×4 pixel blocks, 16 bytes per block
- For an NxN texture: `(N/4)² × 16` bytes for level-0
- BC7 decodes to **BGRA** channel order — must swap R and B for RGBA
- Decoder: `texture2ddecoder.decode_bc7()` (Python, via pip)

### Extraction

```python
# For ALL texture types (loading, circ, hex):
with open(file_path, "rb") as f:
    f.seek(16)  # Skip 16-byte prefix, BC7 starts here
    bc7_data = f.read(bc7_level0_size)
```

---

## Loading Screen Textures

### File naming

`TEXTURE_lsl_{leader_name}` — e.g., `TEXTURE_lsl_augustus`

Exception: `simon_bolivar` → `TEXTURE_lsl_bolivar`

### Dimensions

800×1060 pixels, RGBA with transparency. The game composites these over a
civilization scene background via CSS `background-size: cover`.

### File sizes

All loading screen CIVBIG files are exactly **1,132,544 bytes**.

### Payload layout

BC7 mipchain starts at byte 16. Level-0 is first.

```
[prefix: 16 bytes]
[BC7 level-0: 800×1060]
[mip levels...]
[footer: 128 bytes]
```

```python
bc7_size = (800 // 4) * (1060 // 4) * 16  # = 848,000 bytes
# Read from byte 16
```

### Leaders with loading screens

28 base leaders + 5 persona alts = 33 total.

Persona alt texture names:
- `LEADER_ASHOKA_ALT` → `ashoka_alt`
- `LEADER_HIMIKO_ALT` → `himiko_alt`
- `LEADER_FRIEDRICH_ALT` → `friedrich_alt`
- `LEADER_XERXES_ALT` → `xerxes_alt`
- `LEADER_NAPOLEON_ALT` → `napoleon_alt`

---

## Icon Textures

### Two portrait crops: HEX vs CIRC

**Critical**: The game stores two completely different portrait crops per leader.
They are NOT the same image with different masks — they have different framing,
different zoom levels, and different positioning on the canvas.

| Crop | Content | Canvas position | Alpha shape |
|------|---------|----------------|-------------|
| **HEX** | Wide: head + shoulders | Bottom-aligned, top is transparent | Head silhouette, wider framing |
| **CIRC** | Tight: head only | Vertically centered | Head silhouette, tighter framing |

Measured at 128×128 (Augustus, consistent across leaders):
```
hex_128:  alpha bbox = (7, 38, 105, 128)    — content centered, bottom-aligned
circ_128: alpha bbox = (17, 17, 101, 115)   — content centered vertically
```

At 256×256:
```
hex_256:  alpha bbox = (14, 77, 211, 256)   — content centered, bottom-aligned
circ_256: alpha bbox = (34, 34, 203, 229)   — content centered, doesn't reach edges
```

**You cannot use circ images for hex contexts or vice versa.** Each must be
extracted from its own source texture.

### Icon variants per leader

8 textures per leader (and per persona alt):

| Variant | Texture name pattern | Size | IconDefinitions Context |
|---------|---------------------|------|------------------------|
| hex_256 | `TEXTURE_lp_hex_{name}_256` | 256×256 | DEFAULT |
| hex_128 | `TEXTURE_lp_hex_{name}_128` | 128×128 | DEFAULT |
| hex_128_h | `TEXTURE_lp_hex_{name}_128_h` | 128×128 | LEADER_HAPPY |
| hex_128_a | `TEXTURE_lp_hex_{name}_128_a` | 128×128 | LEADER_ANGRY |
| hex_64 | `TEXTURE_lp_hex_{name}_64` | 64×64 | DEFAULT |
| circ_256 | `TEXTURE_lp_circ_{name}_256` | 256×256 | CIRCLE_MASK |
| circ_128 | `TEXTURE_lp_circ_{name}_128` | 128×128 | CIRCLE_MASK |
| circ_64 | `TEXTURE_lp_circ_{name}_64` | 64×64 | CIRCLE_MASK |

### File sizes (FIXED — identical across all leaders)

| Variant | File size | Header | Payload |
|---------|----------|--------|---------|
| hex_256 | 123,392 | 288 | 123,104 |
| hex_128 | 31,232 | 288 | 30,944 |
| hex_128_h | 31,232 | 288 | 30,944 |
| hex_128_a | 31,232 | 288 | 30,944 |
| hex_64 | 8,192 | 288 | 7,904 |
| circ_256 | 87,552 | 176 | 87,376 |
| circ_128 | 22,016 | 176 | 21,840 |
| circ_64 | 5,632 | 176 | 5,456 |

### CIRC payload layout

Circ payloads contain a standard BC7 mipchain from NxN down to 4×4
(omitting the 2×2 and 1×1 levels). Level-0 is at byte 16.

```
[prefix: 16 bytes]
[BC7 mipchain: NxN → 4×4, level-0 first]
[footer: 160 bytes]
```

Mipchain sizes:
- circ_256: payload = 87,376 = standard mipchain 256→4×4
- circ_128: payload = 21,840 = standard mipchain 128→4×4
- circ_64:  payload = 5,456  = standard mipchain 64→4×4

### HEX payload layout

Hex payloads are larger than circ because they contain additional mip data
after the main mipchain. Level-0 is still at byte 16.

```
[prefix: 16 bytes]
[BC7 level-0: NxN]          ← decode from here (byte 16)
[BC7 mip levels: N/2 → 4×4]
[extra mip data]             ← additional data, purpose unknown
[footer: 272 bytes]
```

| Variant | Payload | Mipchain (N→4×4) | Extra data |
|---------|---------|-------------------|-----------|
| hex_256 | 123,104 | 87,376 | 35,728 |
| hex_128 | 30,944 | 21,840 | 9,104 |
| hex_64 | 7,904 | 5,456 | 2,448 |

**Extraction: same as circ — decode level-0 at byte 16. No skip needed.**
```

### Previous wrong conclusions (for reference)

1. "Header_size = file_size - payload_size marks the BC7 data start" — **WRONG**.
   The BC7 mipchain starts at byte 16 (right after the prefix). The footer
   padding at the end of the file is what `file_size - 16 - payload_size` bytes.
   Using `header_size` as the BC7 start caused all icons and loading screens
   to be horizontally shifted by `(header_size - 16) / 16` blocks.

2. "Hex textures need a special skip offset" — **WRONG**. Level-0 starts at
   byte 16 for ALL texture types (loading, circ, hex). The hex "extra data"
   comes after the mipchain, not before it.

3. "Only circ_256 decodes cleanly" — **WRONG**. All sizes and types decode
   correctly from byte 16.

4. "Hex textures have mip tail packing that destroys the base level" — **WRONG**.
   The base level was being read from the wrong offset (header_size instead of 16).

---

## Icon Rendering in Game

### fxs-icon Web Component

Source: `Base/modules/core/ui/components/fxs-icon.chunk.js`

The game renders icons as CSS background images in a custom web component.
No geometric clipping is applied via CSS — all masking is baked into the
PNG alpha channel.

```css
/* Base/modules/core/ui/themes/default/default.css */
fxs-icon {
    width: inherit;
    height: inherit;
    pointer-events: none;
    background-position: center;
    background-size: contain;
    background-repeat: no-repeat;
}
```

Rendering flow:
1. Component observes `data-icon-id`, `data-icon-context`, `data-icon-size`
2. Calls `UI.getIconCSS(id, context)` → looks up `IconDefinitions` table
3. Returns `url('blp:...')` or `url('fs://game/...')` CSS string
4. Sets `element.style.backgroundImage = url`

### IconDefinitions Table

Schema (from `Base/Assets/schema/icons/IconManager.sql`):

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

Composite PK: `(ID, Context, IconSize)`.

Path formats:
- Base game: `blp:lp_hex_amina_256` (BLP archive reference)
- Mods: `fs://game/authentic-leaders/icons/amina/lp_hex_amina_256.png`

### Context Values for Leader Icons

| Context | Used for | Sizes |
|---------|----------|-------|
| DEFAULT (omitted in XML) | Hex icons — diplomacy ribbon, tooltips | 256, 128, 64 |
| LEADER_HAPPY | Happy expression | 128 |
| LEADER_ANGRY | Angry expression | 128 |
| CIRCLE_MASK | Circular icons — leader select, civilopedia | 256, 128, 64 |

### Leader Icon Container

`Base/modules/core/ui/save-load/leader-icon.js` builds a layered display:
- Shadow layer (`img-hex-shadow`)
- Banner/flag area (`img-hud-frontbanner`)
- Civ icon overlay (`img-hex-overlay`)
- Frame (`img-hex-frame`)
- Leader portrait via `<fxs-icon data-icon-id="LEADER_X" data-icon-context="LEADER">`

---

## LoadingInfo_Leaders Table

### Schema bug

Original PK is just `LeaderType` — prevents multiple rows per leader.
`CivilizationTypeOverride` column exists but isn't part of PK (Firaxis oversight).

Fix: composite PK `PRIMARY KEY("LeaderType", "CivilizationTypeOverride")`

Full schema:
```
LeaderType, AgeTypeOverride, Audio, CivilizationTypeOverride,
LeaderImage, LeaderNameTextOverride (LOC_TEXT), LeaderText (LOC_TEXT)
```

### JS sort bug

`getLeaderLoadingInfo()` in `load-screen-model.chunk.js` sorts ascending
by specificity and picks `[0]` (least specific). Civ-specific entries (score 10)
lose to generic entries (score 0). Fix: sort descending (`b_score - a_score`).

---

## Mod Integration

### XML syntax

`<Replace>` must use **child-element syntax** (not attribute syntax):

```xml
<!-- CORRECT -->
<Replace>
    <ID>LEADER_AUGUSTUS</ID>
    <Path>fs://game/authentic-leaders/icons/augustus/lp_hex_augustus_256.png</Path>
    <IconSize>256</IconSize>
</Replace>

<!-- WRONG — breaks the game -->
<Replace ID="LEADER_AUGUSTUS" Path="..." IconSize="256"/>
```

### Modinfo action types

ImportFiles, UIScripts, UIShortcuts, UpdateArt, UpdateColors, UpdateDatabase,
UpdateIcons, UpdateText, UpdateVisualRemaps, ScenarioScripts, MapGenScripts

### Image requirements for mods

- PNG format with RGBA channels
- Transparent background required (game checks for this)
- Dimensions must match `IconSize` in IconDefinitions
- No geometric mask needed in the image — game handles display via CSS

---

## Extraction Summary

### Correct extraction procedure

```python
import struct
import texture2ddecoder
from PIL import Image

def decode_civbig(file_path, width, height):
    """Decode level-0 from a CIVBIG file.

    BC7 data starts at byte 16 for ALL texture types.
    """
    bc7_size = (max(1, width // 4)) ** 2 * 16
    with open(file_path, "rb") as f:
        f.seek(16)  # Skip prefix, BC7 level-0 starts here
        bc7_data = f.read(bc7_size)
    decoded = texture2ddecoder.decode_bc7(bc7_data, width, height)
    img = Image.frombytes("RGBA", (width, height), decoded)
    r, g, b, a = img.split()
    return Image.merge("RGBA", (b, g, r, a))

# Works for ALL types — no special cases needed:
img = decode_civbig(circ_path, 256, 256)   # circ icon
img = decode_civbig(hex_path, 128, 128)    # hex icon
img = decode_civbig(lsl_path, 800, 1060)   # loading screen
```

---

## External Resources

No public tools exist for CIVBIG extraction. Our `scripts/extract-game-assets.py`
is the only known extractor.

### Community resources

- [CivFanatics: How to import PNG files for icons](https://forums.civfanatics.com/threads/how-to-import-png-files-for-some-art-icon.695384/)
- [CivFanatics: Civ 7 Icon change](https://forums.civfanatics.com/threads/civ-7-icon-change-unit-tech.696336/)
- [CivFanatics: Civilization Asset Templates](https://forums.civfanatics.com/threads/civilization-asset-templates.695913/)
- [CivFanatics: Proof of Concept - Custom Tech/Civic Icons](https://forums.civfanatics.com/resources/proof-of-concept-custom-tech-civic-unique-civic-ideology-icons.31923/)
- [CivFanatics: 3D Leader mods](https://forums.civfanatics.com/threads/3d-leader-mods.697062/)
- [CivFanatics: BLP files discussion (Civ6)](https://forums.civfanatics.com/threads/blp-files.600399/)
- [GitHub: izica/civ7-modding-tools](https://github.com/izica/civ7-modding-tools) — TypeScript mod builder
- [GitHub: Zei33/Civilization-VII-Modding-Documentation](https://github.com/Zei33/Civilization-VII-Modding-Documentation)
- [Civ7 Community Modding Docs](https://civ7community.mintlify.app/community/documentation-guide)
- [texture2ddecoder (PyPI)](https://pypi.org/project/texture2ddecoder/) — BC7 decoder
- [BC7 Format - Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format)
