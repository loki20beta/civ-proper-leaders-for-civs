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
- **Icon extraction quality**: Game hex textures use mip tail packing — only circ_256 decodes cleanly. Current neutral icons use circ_256 with native head silhouette alpha (no custom geometric masks). Awaiting in-game verification that fxs-icon renders them correctly without geometric masks.
- **Happy/angry icons**: _h/_a variants sourced from portrait files (originally wiki-downloaded), not from game textures. Game hex_128_h/hex_128_a can't be cleanly decoded. ibn_battuta missing mood portraits — _h/_a are identical.
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
8. **Hex texture extraction** → All hex sizes have mip tail packing. Only circ_256 decodes cleanly. Use circ_256 for all neutral icon variants.

### Key Technical Findings

#### CIVBIG Texture Format
- Variable header + BC7-compressed texture data (BGRA channel order)
- 16-byte prefix: "CIVBIG\0\0" + uint32 payload_size (offset 8) + uint32 flags (offset 12)
- Header size = file_size - payload_size (not fixed!)
- Loading screens: header=144, circ icons=176, hex icons=288
- Hex textures: mip tail packing overwrites middle of base level — portrait left/right edges survive but center is destroyed
- Only circ_256 decodes cleanly (standard mip chain, no tail packing)

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
1. **Verify icons in-game** — Test that native-alpha icons (no geometric masks) render correctly in fxs-icon
2. **Build AI art generation pipeline** — API integration for generating civ-contextualized leader portraits
3. **Replace stubs with real artwork** — Loading screens + icons with actual civ-appropriate art
