# Icon Extraction Research (2026-03-03)

## Problem

### Resolved: Extraction crop/offset issues
- ~~Neutral icons shifted left/up in the diplomacy banner (hex context)~~
- ~~Icons appear at wrong scale in banner — heads too small~~
- ~~Happy/angry icons centered but shifted down~~
- ~~Table view (circ context) looks OK but still slightly off~~

Fixed by extracting each variant from its own CIVBIG texture file at byte 16 offset.

### Resolved: Missing icons in relationship panel and other UI contexts (2026-03-04)
- ~~Relationship panel shows dark/empty hexagons instead of leader portraits~~
- Fixed with extensionless icon paths + DOM background-image swapping (see below)
- All 11 Path B UI contexts now render civ-specific icons correctly

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

### Leader icon container (`leader-icon`)

`Base/modules/core/ui/save-load/leader-icon.js` builds a layered hex display:
- Shadow layer (`img-hex-shadow`)
- Background (`img-hex-64`, tinted with player bg-color)
- Civ icon overlay (`img-hex-overlay`)
- Frame (`img-hex-frame`, tinted with secondary color)
- Leader portrait: `fxs-icon` with `data-icon-id={leaderType}`, `data-icon-context="LEADER"`

The `"LEADER"` context does NOT exist as an explicit row in `IconDefinitions` — only DEFAULT, LEADER_HAPPY, LEADER_ANGRY, CIRCLE_MASK exist. The engine falls back from `"LEADER"` → `"DEFAULT"` when looking up icons.

The inner `fxs-icon` is positioned with absolute insets: `-left-3 -right-3 -top-5 -bottom-1.5`, making it larger than the parent container (overflow creates the portrait-extending-above-frame effect).

Used by: save/load list, some diplomacy dialogs, diplo ribbon calls-to-action.

## Second Icon Rendering Path: `getLeaderPortraitIcon()` (2026-03-04)

### Discovery

Many UI contexts do NOT use `fxs-icon` / `UI.getIconCSS()` for leader portraits. Instead, they use `Icon.getLeaderPortraitIcon()` which constructs icon URLs via string concatenation.

**This is the root cause of missing/broken icons in the relationship panel and other UI contexts.**

### The function (`utilities-image.chunk.js:147-173`)

```javascript
function getLeaderPortraitIcon(leaderType, size, relationship) {
    const missingIcon = "blp:leader_portrait_unknown.png";
    const leader = GameInfo.Leaders.lookup(leaderType);
    if (!leader) return missingIcon;
    const sizeSuffix = size == void 0 ? "" : "_" + size.toString();
    let relationshipSuffix = "";
    if (relationship) {
        switch (relationship) {
            case HOSTILE: case UNFRIENDLY: relationshipSuffix = "_a"; break;
            case FRIENDLY: case HELPFUL:  relationshipSuffix = "_h"; break;
        }
    }
    const iconName = UI.getIconURL(leader.LeaderType, "LEADER")
                   + sizeSuffix + relationshipSuffix + ".png";
    return iconName.toLowerCase();
}
```

Key behavior:
1. Calls `UI.getIconURL(leaderType, "LEADER")` — native engine function, returns a base path
2. Appends `sizeSuffix` (e.g., `"_128"` or `""` if size undefined)
3. Appends `relationshipSuffix` (e.g., `"_a"`, `"_h"`, or `""`)
4. **Always appends `".png"`**
5. `.toLowerCase()` on the result

### Why this breaks our mod

Vanilla BLP paths in `IconDefinitions` have **no file extension**:
```
blp:lp_hex_amina_128
```

So `UI.getIconURL()` returns a base like `blp:lp_hex_amina`, and the function constructs:
```
blp:lp_hex_amina + "" + "" + ".png" → "blp:lp_hex_amina.png"  ✓ (BLP resolves this)
blp:lp_hex_amina + "_128" + "" + ".png" → "blp:lp_hex_amina_128.png"  ✓
blp:lp_hex_amina + "_128" + "_a" + ".png" → "blp:lp_hex_amina_128_a.png"  ✓
```

Our mod paths in `IconDefinitions` **already include `.png`**:
```
fs://game/authentic-leaders/icons/amina/lp_hex_amina_128.png
```

So the function likely constructs something like:
```
fs://game/.../lp_hex_amina + "" + "" + ".png" → ".../lp_hex_amina.png"  ✗ (file is lp_hex_amina_128.png)
fs://game/.../lp_hex_amina_128.png + ".png" → ".../lp_hex_amina_128.png.png"  ✗ (double extension)
```

The exact behavior depends on what `UI.getIconURL()` (native engine) returns — whether it strips the size suffix, the extension, both, or neither. In all cases the resulting path is invalid for our `fs://game/` paths.

### Affected UI contexts

All of these use `getLeaderPortraitIcon` / `getPlayerLeaderIcon` and are **broken** with our mod:

| UI Context | File | Args |
|-----------|------|------|
| **Relationship panel** (hex portraits under Neutral/Friendly/Hostile) | `panel-diplomacy-actions.js:1156` | leaderType only |
| Diplomacy action leader portraits | `panel-diplomacy-actions.js:725,773,800` | leaderType only |
| City banners (suzerain portrait) | `city-banners.js:1037,1058` | leaderType only |
| Call to arms screen | `screen-diplomacy-call-to-arms.js:101-102` | leaderType only |
| Combat preview | `panel-unit-combat-preview.js:289` | leaderType, size=32 |
| Victory progress | `model-victory-progress.chunk.js:160` | leaderType only |
| End results screen | `end-results.js:98` | leaderType only |
| Endgame screen | `model-endgame.js:58` | leaderType only |
| Age scores | `model-age-scores.js:99` | leaderType only |
| Diplomacy target select | `screen-diplomacy-target-select.js:134` | via `getPlayerLeaderIcon` |
| Diplomacy manager (war notifications) | `diplomacy-manager.js:3546` | leaderType only |

These use `createBorderedIcon()` which sets `div.style.backgroundImage = url(iconURL)` — a plain div, NOT `fxs-icon`.

### UI contexts that DO work (use Path A)

| UI Context | Mechanism |
|-----------|-----------|
| **Diplo ribbon** (top bar leader portraits) | `fxs-icon` + `UI.getIconCSS()` with `data-icon-context` = "" / LEADER_HAPPY / LEADER_ANGRY |
| **Save/load list** | `leader-icon` → inner `fxs-icon` + `UI.getIconCSS()` with `data-icon-context="LEADER"` |
| **Leader select screen** | `fxs-icon` + `UI.getIconCSS()` with `data-icon-context="CIRCLE_MASK"` |

### Fixes applied (all confirmed working in-game)

**Fix 1: Extensionless icon duplicates (committed 0f64e77)**

Stripped `.png` from all `IconDefinitions` `<Path>` values and created extensionless copies of every icon file. Both `.png` and extensionless versions are imported via `ImportFiles`.

- `fxs-icon` → `UI.getIconCSS()` → extensionless path → engine resolves to file ✓
- `getLeaderPortraitIcon()` → extensionless base + `.png` suffix → resolves original `.png` file ✓
- All 11 Path B UI contexts now render base leader icons correctly ✓

**Fix 2: Path B civ-specific icon swapping via DOM interception**

Extended the UIScript (`authentic-leaders-icons.js`) to also swap civ-specific icons in Path B contexts. After building the player cache, calls `UI.getIconURL()` for each player's base and civ-specific icon IDs to build a URL swap map. The MutationObserver scans newly added nodes for `backgroundImage` containing base leader portrait URLs and replaces with civ-specific URLs.

- Relationship panel shows civ-specific icons ✓
- City banners, combat preview, victory screen, etc. all show civ-specific icons ✓
- Both fixes work together: extensionless paths ensure correct resolution, DOM swapping ensures civ-specific art ✓

## IconDefinitions — Leader Icon Entries (8 per leader)

| Context | Sizes | Notes |
|---------|-------|-------|
| DEFAULT (omitted in XML) | 256, 128, 64 | Hex icons — diplomacy ribbon, tooltips |
| LEADER_HAPPY | 128 | Happy expression — diplomacy screen |
| LEADER_ANGRY | 128 | Angry expression — diplomacy screen |
| CIRCLE_MASK | 256, 128, 64 | Circular icons — leader select, civilopedia |

### Path formats

- Base game: `blp:lp_hex_amina_256` (packed in BLP archives, no extension)
- Mods (recommended): `fs://game/authentic-leaders/icons/amina/lp_hex_amina_256` (no `.png` — see fix Option 1)
- Mods (also works for Path A only): `fs://game/authentic-leaders/icons/amina/lp_hex_amina_256.png`

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

## UI.getIconURL() vs UI.getIconCSS()

Both are native engine functions (not defined in JS):

| Function | Returns | Used for |
|----------|---------|----------|
| `UI.getIconURL(id, context?)` | Raw URL string: `blp:...` or `fs://game/...` | `<img src>`, URL concatenation, preloading |
| `UI.getIconCSS(id, context?)` | CSS value: `url('...')` | `element.style.backgroundImage` assignment |

`getIconCSS` is essentially `"url('" + getIconURL(...) + "')"`. Both query the `IconDefinitions` table by `(ID, Context)` and pick the best-fit size.

When context has no matching rows (e.g., `"LEADER"` is not in `IconContexts`), the engine falls back to `DEFAULT`.

## fs://game/ Protocol Extension Handling

The `fs://game/` protocol resolves PNG files **with or without** the `.png` extension.

Evidence:
- Game's own `civilization-icons.xml` mixes both: `fs://game/civ_sym_aksum` (no ext) and `fs://game/civ_sym_unknown.png` (with ext)
- Game JS constructs extensionless paths: `"fs://game/core/ui/civ_sym_" + civType.slice(13).toLowerCase()` (no `.png`)
- Shadowheart custom leader mod (confirmed working) uses extensionless paths in all IconDefinitions

## All Defined IconContexts (from `core/icons/icons.xml`)

```xml
<IconContexts>
    <Row Context="DEFAULT" AllowTinting="0" />
    <Row Context="FONTICON" AllowTinting="0" />
    <Row Context="FOW" AllowTinting="0" />
    <Row Context="PLAYER" AllowTinting="1" />
    <Row Context="BADGE" AllowTinting="0" />
    <Row Context="CIRCLE_MASK" AllowTinting="1" />
    <Row Context="BACKGROUND" AllowTinting="0" />
    <Row Context="BUBBLE" AllowTinting="0" />
    <Row Context="LEADER_HAPPY" AllowTinting="0" />
    <Row Context="LEADER_ANGRY" AllowTinting="0" />
    <Row Context="OUTLINE" AllowTinting="0" />
</IconContexts>
```

Additional contexts defined in `base-standard`: `UNIT_FLAG`, `BUILDING`, `IMPROVEMENT`, `WONDER`, `PROJECT`, `TRADITION`, `YIELD`, `YIELD_G`, `NOTIFICATION`, etc.

Note: `"LEADER"` is NOT in the XML-defined `IconContexts`. It's used by `leader-icon.js` (`data-icon-context="LEADER"`) and accepted by `UI.getIconURL("LEADER")` — the engine falls back to `DEFAULT` when no explicit `LEADER` context rows exist.

## Full Icon Schema (from `Base/Assets/schema/icons/IconManager.sql`)

```sql
CREATE TABLE 'IconContexts' (
    'Context' TEXT NOT NULL,
    'AllowTinting' INTEGER DEFAULT 1,
    PRIMARY KEY('Context')
);

CREATE TABLE 'Icons' (
    'ID' TEXT NOT NULL,
    'Context' TEXT DEFAULT 'DEFAULT',
    PRIMARY KEY('ID','Context'),
    FOREIGN KEY('Context') REFERENCES IconContexts('Context')
);

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
    PRIMARY KEY('ID', 'Context', 'IconSize'),
    FOREIGN KEY('ID', 'Context') REFERENCES Icons('ID', 'Context')
);

CREATE TABLE 'IconAliases' (
    'ID' TEXT NOT NULL,
    'Context' TEXT NOT NULL DEFAULT 'DEFAULT',
    'OtherID' TEXT NOT NULL,
    'OtherContext' TEXT NOT NULL DEFAULT 'DEFAULT',
    PRIMARY KEY('ID', 'Context')
);
```

An INSERT trigger on `IconDefinitions` auto-inserts into `Icons` — no separate `<Icons>` entries needed.

## External Research

### CIVBIG extraction

Our `scripts/extract-game-assets.py` appears to be the only known CIVBIG texture extractor. No public tools, repos, or documentation exist for this format.

### Custom leader mods with icon definitions

#### Shadowheart mod (hjl2009/Civilization7_MOD_Shadowheart) — BEST REFERENCE

A confirmed working custom leader mod adding two alt persona leaders. **Uses extensionless paths** in `IconDefinitions`:

```xml
<IconDefinitions>
  <!-- Hex (DEFAULT) — 3 sizes, NO .png extension in Path -->
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_hex_SHADOWHEART_MOONLIGHT_MAIDEN_256</Path>
    <IconSize>256</IconSize>
  </Row>
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_hex_SHADOWHEART_MOONLIGHT_MAIDEN_128</Path>
    <IconSize>128</IconSize>
  </Row>
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_hex_SHADOWHEART_MOONLIGHT_MAIDEN_64</Path>
    <IconSize>64</IconSize>
  </Row>
  <!-- CIRCLE_MASK — 3 sizes -->
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_circ_SHADOWHEART_MOONLIGHT_MAIDEN_256</Path>
    <Context>CIRCLE_MASK</Context>
    <IconSize>256</IconSize>
  </Row>
  <!-- ... (128, 64 also) ... -->
  <!-- LEADER_HAPPY / LEADER_ANGRY — 128 only -->
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_happy_SHADOWHEART_MOONLIGHT_MAIDEN_128</Path>
    <Context>LEADER_HAPPY</Context>
    <IconSize>128</IconSize>
  </Row>
  <Row>
    <ID>LEADER_SHADOWHEART_MOONLIGHT_MAIDEN</ID>
    <Path>fs://game/ShadowHeart-ShadowHearts/icons/lp_angry_SHADOWHEART_MOONLIGHT_MAIDEN_128</Path>
    <Context>LEADER_ANGRY</Context>
    <IconSize>128</IconSize>
  </Row>
</IconDefinitions>
```

Key observations:
- **No `.png` extension** in any `<Path>` — ImportFiles (in `.modinfo`) still references files WITH `.png`
- Naming: `lp_hex_NAME_SIZE`, `lp_circ_NAME_SIZE`, `lp_happy_NAME_SIZE`, `lp_angry_NAME_SIZE`
- Same 8-entry pattern: 3 hex (DEFAULT) + 2 emotion (128 only) + 3 circ (CIRCLE_MASK)

#### Leader_Reshuffle mod (MarvinTM/Leader_Reshuffle)

Simpler approach — uses `.png` IN the Path, and reuses the same image for all sizes:

```xml
<Row><ID>LEADER_PERICLES</ID>
     <Path>fs://game/owain-glyndwr/icons/pericles.png</Path>
     <IconSize>256</IconSize></Row>
<!-- same path for 128, 64, all contexts... -->
```

This mod may have the same `getLeaderPortraitIcon` bug but it's less noticeable with a single reused image.

### Other community resources

- [CivFanatics: How to import PNG files for icons](https://forums.civfanatics.com/threads/how-to-import-png-files-for-some-art-icon.695384/) — definitive icon import tutorial, shows `<Replace>` with child elements
- [CivFanatics: Civ 7 Icon change (Unit, Tech)](https://forums.civfanatics.com/threads/civ-7-icon-change-unit-tech.696336/) — notes icon replacement is "inconsistent right now"
- [CivFanatics: Civilization Asset Templates](https://forums.civfanatics.com/threads/civilization-asset-templates.695913/) — 256×256 PNG templates
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
- **Use extensionless paths** in `IconDefinitions` for compatibility with both icon rendering paths
- `<Replace>` must use child-element syntax (not attribute syntax)
- ImportFiles entries still need `.png` extension

## Fallback Plan (Extraction — resolved)

Direct level-0 extraction at byte 16 works. Previous fallbacks no longer needed.

## Resolution (Path issues)

All three path issues resolved:
1. ✅ Extensionless paths in IconDefinitions (committed 0f64e77)
2. ✅ Verified working across all affected UI contexts
3. ✅ Civ-specific swapping extended to Path B via DOM background-image interception in UIScript

### Resolved: Hex icon aspect ratio was wrong (2026-03-04)

**Discovery:** Comparing with the working Oliver Cromwell custom leader mod revealed our hex icons are the wrong dimensions.

**Root cause:** Hex icon textures are NOT square — they are taller than wide with a 45/32 (1.40625) aspect ratio. Our extraction was cropping them to square.

| Variant | Correct (Cromwell) | Ours (wrong) |
|---------|-------------------|--------------|
| hex_256 | 256×360 | 256×256 |
| hex_128 | 128×180 | 128×128 |
| hex_64 | 64×90 | 64×64 |
| circ_256 | 256×256 ✓ | 256×256 ✓ |
| circ_128 | 128×128 ✓ | 128×128 ✓ |

**Aspect ratio:** All hex sizes use exactly **45/32 = 1.40625**:
- 256 × 45/32 = 360
- 128 × 45/32 = 180
- 64 × 45/32 = 90

**Alpha bounding boxes (128×180 canvas):**
- Cromwell: (11, 33, 115, 157) — content properly centered in tall hex
- Our test decode at 128×180: (11, 22, 112, 160) — also properly centered ✓
- Our current 128×128 crop: (11, 0, 112, 128) — content hits top and bottom edges

**CIVBIG payload verification:** All three hex sizes have sufficient payload for 45/32 decoding:
- hex_256: need 92,160B, payload=123,104B ✓
- hex_128: need 23,040B, payload=30,944B ✓
- hex_64: need 5,888B, payload=7,904B ✓

**Bug in extraction (`extract-game-assets.py` line 265):**
```python
# WRONG: 5/4 = 1.25 ratio, crops to square
decode_h = v["size"] * 5 // 4 if v["shape"] == "hex" else v["size"]
img = decode_civbig(tex_path, v["size"], v["size"], decode_height=decode_h)
```

**BC7 block alignment note:** For 64×90, `ceil(90/4) = 23` blocks (92 pixels). The `decode_civbig` function's `bc7_size` calculation uses floor division (`height // 4`), which gives 22 blocks — one block short. Fix: use ceiling division `(height + 3) // 4`.

**Cromwell mod reference:** `/Users/admin/Library/Application Support/Civilization VII/Mods/civmods-oliver-cromwell-39482/`
