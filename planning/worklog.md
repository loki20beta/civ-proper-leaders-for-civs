# Authentic Leaders Mod - Work Log

## Current Status (2026-03-03)

### What Works
- **Full mod infrastructure**: All 28 leaders × 43 civilizations wired up with SQL, XML, JS, UIScript
- **Loading screens**: Civ-specific loading screen selection via SQL composite PK + JS sort fix
- **Icons**: Civ-specific icon swapping at runtime via UIScript + MutationObserver
- **Game asset extraction**: Loading screens (28 + 5 alts) and icons (28 + 5 alts) extracted from game BLP/CIVBIG files
- **Stub images**: All 1,232 loading screens and 9,504 civ-specific icons generated as stubs (original art + civ text overlay)
- **Modinfo**: ~11,400 items, all assets referenced, all integrations configured
- **Repo**: `git@github.com:loki20beta/civ-proper-leaders-for-civs.git` on `main` branch

### Known Issues
- **Icon sizing/missing in some UI contexts**: Some in-game icons appear slightly wrong size; in some places icons seem to be missing entirely. Needs investigation — could be IconDefinitions `IconSize` mismatch, missing context entries, or the game expecting BLP-native dimensions vs our PNG dimensions.
- **All civ-specific images are stubs**: Original portrait with text overlay. No real civ-contextualized artwork yet.

### Mod File Counts
| Asset | Count |
|-------|-------|
| Loading screen PNGs | 1,232 (28 leaders × 1 default + 28 × 43 civ-specific) |
| Icon PNGs (default) | 224 (28 leaders × 8 variants) |
| Icon PNGs (civ-specific) | 9,288 (27 leaders × 43 civs × 8 variants + ibn_battuta generic only) |
| SQL override | 1 file (composite PK restructure + all entries) |
| XML icon definitions | 2 files (default overrides + civ-specific definitions) |
| JS override | 1 file (load-screen sort fix) |
| UIScript | 1 file (runtime icon swapping) |

### History of Approaches Tried

1. **XML with `<Row>` inserts for civ-specific entries** → UNIQUE constraint failed on `LoadingInfo_Leaders.LeaderType` (sole PK).
2. **SQL DROP TABLE/CREATE TABLE with composite PK** → Game loaded but had visual issues ("wrong size", arrows didn't work). Was likely from bad images (272px), not from SQL itself.
3. **XML `<Replace>` with attribute syntax** → Game breaks when starting new game. Wrong XML syntax for Civ7.
4. **XML `<Replace>` with child-element syntax** → WORKS. Default image replacement confirmed.
5. **SQL restructure + JS ImportFiles override** → Works for civ-specific loading screens.
6. **Wiki-sourced images** → Abandoned. Now extract everything from game files via `scripts/extract-game-assets.py`.
7. **Custom hex/circ masks for icons** → Caused ~5px shift (game portrait centered at 133,131 not 128,128). Switched to native head silhouette alpha from circ_256 texture.
8. **Hex texture extraction with header_size offset** → Icons shifted horizontally/vertically. Root cause: BC7 data starts at byte 16, NOT at `file_size - payload_size`.
9. **Byte-16 extraction (CORRECT)** → All 8 icon variants per leader + loading screens extract perfectly from byte 16. No special hex skip needed.

### Key Technical Findings

#### CIVBIG Texture Format
- 16-byte prefix: "CIVBIG\0\0" + uint32 payload_size (offset 8) + uint32 flags (offset 12)
- BC7-compressed texture data starts at **byte 16** (immediately after prefix)
- Level-0 mipmap is first in the mipchain; BC7 decodes as BGRA (swap R↔B for RGBA)
- Mipchain stops at 4×4 (not 1×1)
- Footer padding after mipchain: transparent BC7 blocks (`80 00 00 00 ... AC AA AA AA`)
- `payload_size` = mipchain data size; footer_size = file_size - 16 - payload_size
- Hex textures have 45/32 aspect ratio (128×180, 256×360, 64×90); decode at full rectangular size
- Circ textures are square at nominal size; decode directly
- All texture types decode correctly from byte 16

#### Loading Screen System
- Original images: 800×1060 RGBA transparent PNGs (BC7-compressed in CIVBIG, 1,132,544 bytes each)
- Base game references: `blp:lsl_<name>.png` (packed in BLP archives)
- Mod references: `fs://game/<mod-id>/<path>.png` for PNG files
- CSS composites image over civ scene via `background-size: cover`

#### Icon System
- `IconDefinitions` table has no `CivilizationTypeOverride` column
- Civ-specific icons: register new IDs (e.g., `LEADER_AUGUSTUS_ROME`), swap at runtime via UIScript
- `fxs-icon` web component calls `UI.getIconCSS(id, context)` via queued microtask
- Override via `setTimeout(fn, 0)` after attribute changes
- Players API returns internal hashes — use `GameInfo.Leaders.lookup()` / `GameInfo.Civilizations.lookup()` for string IDs

#### Database / XML
- `LoadingInfo_Leaders` original PK: `PRIMARY KEY("LeaderType")` — can't have multiple rows per leader
- Fix: composite PK `PRIMARY KEY("LeaderType", "CivilizationTypeOverride")`
- `<Replace>` must use child-element syntax (not attribute syntax)
- Persona/alt leaders: DB type is `LEADER_X_ALT` (not flavor names)

### Scripts
- `scripts/extract-game-assets.py` — Extract loading screens + icons from game BLP/CIVBIG files
- `scripts/generate-stubs.py` — Generate stub images (original + text overlay) for all leader×civ combinations
- `scripts/generate-civ-icons.py` — Generate civ-specific icon PNGs
- `scripts/generate-mod-data.py` — Generate SQL, XML, modinfo from config
- `scripts/generate-manifest.py` — Generate modinfo ImportFiles list
- `scripts/generate-prompts.py` — Generate AI image generation prompts
- `scripts/process-images.py` — Image processing utilities

### Config
- `config/leaders-civilizations.json` — Master data: all leaders, civilizations, ages

### Key File Paths
- Game: `~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII/CivilizationVII.app/Contents/Resources/`
- Mods: `~/Library/Application Support/Civilization VII/Mods/`
- Logs: `~/Library/Application Support/Civilization VII/Logs/` (Database.log, Modding.log, UI.log)
- Schema: `Base/Assets/schema/gameplay/01_GameplaySchema.sql`
- Load screen JS: `Base/modules/base-standard/ui-next/screens/load-screen/load-screen-model.chunk.js`
- Base loading-info: `Base/modules/base-standard/data/loading-info.xml`

### Symlink
`~/Library/Application Support/Civilization VII/Mods/authentic-leaders` → `/Users/admin/work/civ7mod/authentic-leaders`

### Next Steps
1. **Investigate icon size/missing issues** — Some icons appear wrong size or missing in certain UI contexts. Check IconDefinitions entries, compare our PNG dimensions with what the game expects, inspect which contexts/sizes are affected.
2. **Build AI art generation pipeline** — API integration for generating civ-contextualized leader portraits
3. **Replace stubs with real artwork** — Loading screens + icons with actual civ-appropriate art
