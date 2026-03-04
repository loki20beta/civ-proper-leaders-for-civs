# Civilization VII - Authentic Leaders Mod

A Civilization VII mod that replaces leader loading screen images and icons with civilization-specific artwork for a more historically authentic experience.

## Current Status

The mod infrastructure is complete and working for all 28 leaders across all 43 civilizations. Loading screens, icons, SQL overrides, JS fixes, and runtime UIScript icon swapping are all functional. Current images are stubs (original game art with civ-name text overlay) — real civ-contextualized artwork is the next milestone.

**Working:**
- Civ-specific loading screens for all 28 leaders × 43 civilizations (stub images)
- Civ-specific in-game icons for all players (local + AI) via runtime UIScript
- SQL table restructure (composite PK) + JS sort fix for civ-specific image selection
- Leader icon extraction from game CIVBIG/BLP textures (all 8 variants per leader, properly centered)
- Loading screen extraction from game BLP files (800×1060 RGBA transparent PNGs)
- Full build pipeline: config → generate SQL/XML/modinfo → mod

**Known Issues:**
- All civ-specific images are currently stubs (original portrait + text label), not real civ-contextualized artwork.
- Icons break when a leader is custom (from another mod). The runtime icon swapping script expects leaders defined in the base game config.
- Tonga and Pirates 720p background extracts are visually broken (game ships oversized CIVBIG containers for these two; 1080p variants are fine).

## How It Works

Civilization VII's `LoadingInfo_Leaders` table supports `CivilizationTypeOverride` for per-civ images, but two issues prevent it from working out of the box:

1. **Schema limitation**: The table's primary key is just `LeaderType`, so only one row per leader is allowed. This mod restructures the PK to `(LeaderType, CivilizationTypeOverride)` via SQL.

2. **JS sort bug**: `getLeaderLoadingInfo()` sorts matches ascending by specificity and picks index `[0]`, meaning the generic (least specific) entry always wins. This mod overrides the JS to sort descending, so the civ-specific entry wins when available.

3. **Icon system has no civ awareness**: `IconDefinitions` table has no `CivilizationTypeOverride` column. This mod registers civ-specific icon IDs (e.g., `LEADER_AUGUSTUS_ROME`) and swaps them at runtime via a UIScript that reads each player's civilization.

4. **Two icon rendering paths**: The game renders leader icons via two separate code paths — `fxs-icon` web components (diplo ribbon, save/load, leader select) and `getLeaderPortraitIcon()` string concatenation (relationship panel, city banners, combat preview, etc.). This mod handles both: `fxs-icon` elements are intercepted by MutationObserver, and `getLeaderPortraitIcon()` contexts are handled by background-image URL swapping with extensionless icon duplicates.

## Installation

### macOS
1. Clone or download this repository
2. Create a symlink from the mod directory to the game's Mods folder:
   ```bash
   ln -s /path/to/civ7mod/authentic-leaders "$HOME/Library/Application Support/Civilization VII/Mods/authentic-leaders"
   ```
3. Launch Civilization VII — the mod auto-enables

### Windows
1. Copy the `authentic-leaders/` folder to:
   ```
   %LOCALAPPDATA%\Firaxis Games\Civilization VII\Mods\
   ```

## Project Structure

```
authentic-leaders/                    # The mod (this folder goes into Mods/)
  authentic-leaders.modinfo           # Mod manifest (~22,000 items)
  data/
    loading-info-override.sql         # Table restructure + civ-specific entries
  icons/
    leader-icons-override.xml         # Default icon overrides (shell scope)
    leader-icons-civ-override.xml     # Civ-specific icon definitions (game scope)
    {leader}/                         # 8 default icon PNGs per leader
    {leader}/{civ}/                   # 8 civ-specific icon PNGs per combination
  images/
    loading/                          # 800x1060 RGBA transparent PNGs
      lsl_{leader}.png                # Default (fallback)
      lsl_{leader}_{civ}.png          # Civ-specific (28 × 43 = 1,204 images)
  scripts/
    authentic-leaders-icons.js        # UIScript: runtime icon swapping per player civ
  ui-next/
    screens/
      load-screen/
        load-screen-model.chunk.js    # JS sort fix override

config/
  leaders-civilizations.json          # Master data: all leaders, civs, ages

scripts/
  extract-game-assets.py              # Extract icons + loading screens from game BLP files
  generate-stubs.py                   # Generate stub images (original + text overlay)
  generate-civ-icons.py               # Generate civ-specific icon PNGs
  generate-mod-data.py                # Generate SQL, XML, modinfo from config
  generate-manifest.py                # Generate modinfo ImportFiles list
  generate-prompts.py                 # Generate AI image generation prompts
  process-images.py                   # Image processing utilities
```

## Development Phases

### Phase 1: Infrastructure (complete)
- [x] Mod structure and manifest
- [x] SQL table restructure for civ-specific overrides (composite PK)
- [x] JS sort fix for civ-specific image selection
- [x] UIScript for runtime civ-specific icon swapping (MutationObserver)
- [x] Persona/alt leader support (LEADER_X_ALT → LEADER_X mapping)
- [x] Build pipeline: config → SQL/XML/modinfo generation
- [x] Verified working in-game (loading screens + icons)
- [x] Extensionless icon duplicates for `getLeaderPortraitIcon()` compatibility
- [x] Path B civ-specific icon swapping (DOM background-image interception)

### Phase 2: Game Asset Extraction (complete)
- [x] Extract original loading screens from game BLP files (28 leaders + 5 persona alts)
- [x] Extract all 8 icon variants per leader from game textures (28 leaders + 5 alts)
- [x] Stub images for all 28 leaders × 43 civilizations (loading screens + icons)
- [x] CIVBIG format decoded: BC7 data at byte 16, hex icons 45/32 aspect ratio (256×360, 128×180, 64×90)
- [x] Icon dimensions verified: hex = rectangular (45/32), circ = square
- [x] Icons working in all UI contexts (both fxs-icon and getLeaderPortraitIcon paths)
- [x] ESC/pause menu loading screen fix: civ stubs use base loading screen (full body) not raw CIVBIG extract

### Phase 3: AI-Generated Artwork (next)
- [ ] Build image generation pipeline (API integration with DALL-E / Midjourney / SD)
- [ ] Generate civ-contextualized leader portraits (leader in civ-appropriate attire, architecture, setting)
- [ ] Replace stub loading screens with real artwork
- [ ] Replace stub civ-specific icons with artwork-derived icons
- [ ] Quality review and manual curation

### Phase 4: 3D Animation Override (stretch)
- [ ] Investigate leader 3D model/animation system
- [ ] Leader model swapping via JS or asset override
- [ ] Custom animation sets per civilization

## Technical Notes

### Key Findings

- **`<Replace>` in UpdateDatabase XML must use child-element syntax**, not attribute syntax:
  ```xml
  <!-- CORRECT -->
  <Replace>
    <LeaderType>LEADER_AUGUSTUS</LeaderType>
    <LeaderImage>fs://game/authentic-leaders/images/loading/lsl_augustus.png</LeaderImage>
  </Replace>

  <!-- WRONG — causes game to fail loading -->
  <Replace LeaderType="LEADER_AUGUSTUS" LeaderImage="..."/>
  ```

- **LoadingInfo_Leaders schema bug**: `CivilizationTypeOverride` column exists but isn't part of the PK — Firaxis designed the JS to handle civ-specific entries but the schema doesn't allow them.

- **JS sort bug**: Both `getLeaderLoadingInfo()` and `getCivLoadingInfo()` sort ascending by specificity (`a_score - b_score`) and pick index `[0]`. Fix: `b_score - a_score`.

- **CIVBIG texture format**: 16-byte prefix (`"CIVBIG\0\0"` + uint32 payload_size + uint32 flags) followed immediately by BC7-compressed texture data (BGRA channel order). Level-0 mipmap starts at byte 16. Mipchain stops at 4×4. Footer = transparent BC7 padding blocks.

- **ImportFiles can override base game files** when the relative path matches the base module's path (confirmed by BorderToggles community mod).

- **Image format**: Loading screens are 800×1060 RGBA transparent PNGs. The loading screen uses `background-size: cover` (clips bottom); the ESC/pause menu uses `background-size: contain` (shows full image). Civ stubs must use the full-body base image, not the raw CIVBIG extract which may have truncated alpha.

- **Icon system has no civ awareness**: `IconDefinitions` table has no `CivilizationTypeOverride` column. Civ-specific icons require registering new IDs (e.g., `LEADER_AUGUSTUS_ROME`) and a UIScript to swap them at runtime.

- **Correct civilization type IDs**: `CIVILIZATION_ROME` (not ROMAN), `CIVILIZATION_SPAIN` (not SPANISH), `CIVILIZATION_PRUSSIA` (not PRUSSIAN).

- **Persona/alt leader DB types** are `LEADER_X_ALT` (not flavor names like WORLD_RENOUNCER). Alt types have their own `LoadingInfo_Leaders` + `IconDefinitions` entries.

- **Two icon rendering paths**: `fxs-icon` components use `UI.getIconCSS(id, context)` for direct lookup. `getLeaderPortraitIcon()` uses `UI.getIconURL()` + string concatenation + `.png` suffix. To support both: `IconDefinitions` paths are extensionless, and both `.png` and extensionless copies are imported. The UIScript handles civ-specific swapping for both paths.

## Author

loki20beta

## License

MIT
