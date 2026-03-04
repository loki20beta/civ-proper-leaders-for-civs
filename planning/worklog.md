# Authentic Leaders Mod - Work Log

## Current Status (2026-03-04)

### What Works
- **Full mod infrastructure**: All 28 leaders (+ 5 persona alts) × 43 civilizations wired up with SQL, XML, JS, UIScript
- **Loading screens**: Civ-specific loading screen selection via SQL composite PK + JS sort fix — works for both base and persona/alt leaders
- **Icons**: Civ-specific icon swapping at runtime via UIScript + MutationObserver — works for both base and persona/alt leaders in all UI contexts (fxs-icon Path A + getLeaderPortraitIcon Path B)
- **Persona/alt leaders**: Full support — persona-specific civ icons and loading screens with persona-first lookup (falls back to base leader if no persona-specific art exists)
- **Game asset extraction**: Loading screens (28 + 5 alts) and icons (28 + 5 alts) extracted from game BLP/CIVBIG files
- **Civ background scenes**: Extracted from game CIVBIG textures (44 civs × 2 resolutions)
- **Stub images**: All loading screens and civ-specific icons generated as stubs (original art + civ text overlay)
- **Modinfo**: ~22,000 items, all assets referenced, all integrations configured
- **Repo**: `git@github.com:loki20beta/civ-proper-leaders-for-civs.git` on `main` branch

### Known Issues
- **All civ-specific images are stubs**: Original portrait with text overlay. No real civ-contextualized artwork yet.
- **Icons break with custom leader mods**: The runtime icon swapping script expects leaders defined in the base game config.
- **Tonga/Pirates 720p background extracts**: Visually broken (game ships oversized CIVBIG containers for these two; 1080p variants are fine).

### Mod File Counts
| Asset | Count |
|-------|-------|
| Loading screen PNGs | ~1,450 (28 base + 5 alt defaults, + 33 × 43 civ-specific) |
| Icon PNGs (default) | ~264 (33 leaders/alts × 8 variants) |
| Icon PNGs (civ-specific) | ~11,350 (33 leaders/alts × 43 civs × 8 variants) |
| Extensionless icon copies | Same count as icon PNGs (for getLeaderPortraitIcon compatibility) |
| SQL override | 1 file (composite PK restructure + all entries) |
| XML icon definitions | 2 files (default overrides + civ-specific definitions incl. persona) |
| JS override | 1 file (load-screen sort fix) |
| UIScript | 1 file (runtime icon swapping, persona-first lookup) |

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
- Loading screen CSS: `background-size: cover` (clips bottom ~35%)
- ESC/pause menu CSS: `background-size: contain` (shows full image)
- CIVBIG extracts may have truncated alpha; civ stubs use base loading screen (full body) as source

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
- `scripts/extract-game-assets.py` — Extract loading screens + icons + civ backgrounds from game BLP/CIVBIG files
- `scripts/generate.py` — Unified generator: base icons/loading, civ stubs (loading + icons). Supports `--stub`, `--force`, `--leader`
- `scripts/generate-civ-icons.py` — Generate civ-specific icon PNGs (standalone, also called by generate.py)
- `scripts/generate-mod-data.py` — Generate SQL, XML, modinfo from config + available images
- `scripts/process-images.py` — Image processing utilities
- `scripts/generate-prompts.py` — Generate AI image generation prompts

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
1. **BUILD AI ART GENERATION PIPELINE** ← NEXT
   - Design prompt templates per leader × civ (attire, setting, architecture, era)
   - API integration (DALL-E / Midjourney / Stable Diffusion / Flux)
   - Batch generation script: reads config, generates prompts, calls API, saves outputs
   - Post-processing: resize to 800×1060 loading screens, crop to icon variants (hex + circ)
   - Maintain consistent art style matching Civ7 painterly aesthetic
2. **Replace stubs with real artwork** — Swap generated art into mod, regenerate icons from new loading screens
3. **Quality review and curation** — Manual review of generated images, re-generate poor results, verify in-game
