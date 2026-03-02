# Civilization VII - Authentic Leaders Mod

A Civilization VII mod that replaces leader loading screen images and icons with civilization-specific artwork for a more historically authentic experience.

## Current Status: Phase 1 (POC) - In Progress

**Working:**
- Leader icon replacement (Augustus icons in leader select and menus)
- Loading screen image replacement (Augustus three-quarter portrait replaces default)
- Mod loads without errors, game fully functional

**In Testing:**
- Civilization-specific loading screens for Augustus across all 14 antiquity civilizations
  - SQL table restructure: composite PK `(LeaderType, CivilizationTypeOverride)` to allow multiple rows per leader
  - JS sort fix: override `load-screen-model.chunk.js` to pick the most specific match instead of least specific
  - Placeholder images with civilization name labels (to be replaced with proper art)

## How It Works

Civilization VII's `LoadingInfo_Leaders` table supports `CivilizationTypeOverride` for per-civ images, but two issues prevent it from working out of the box:

1. **Schema limitation**: The table's primary key is just `LeaderType`, so only one row per leader is allowed. This mod restructures the PK to `(LeaderType, CivilizationTypeOverride)` via SQL.

2. **JS sort bug**: `getLeaderLoadingInfo()` sorts matches ascending by specificity and picks index `[0]`, meaning the generic (least specific) entry always wins. This mod overrides the JS to sort descending, so the civ-specific entry wins when available.

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
authentic-leaders/          # The mod (this folder goes into Mods/)
  authentic-leaders.modinfo # Mod manifest
  data/
    loading-info-override.sql  # Table restructure + civ-specific entries
  icons/
    leader-icons-override.xml  # Icon definition overrides
    augustus/                   # Augustus icon PNGs (8 variants)
  images/
    loading/                   # Loading screen portraits (1230x1520)
      lsl_augustus.png          # Default (fallback for non-antiquity civs)
      lsl_augustus_rome.png     # Civ-specific (14 antiquity civs)
      ...
  ui-next/
    screens/
      load-screen/
        load-screen-model.chunk.js  # JS sort fix override

config/
  leaders-civilizations.json   # Master data: all leaders, civs, ages

scripts/
  process-images.py            # Create icon + loading variants from source portrait
  generate-prompts.py          # Generate AI image prompts per leader+civ
  generate-mod-data.py         # Generate modinfo + XML from config
```

## Supported Civilizations (Augustus)

All antiquity-age civilizations have civ-specific loading screen images:

| Base Game | DLC |
|-----------|-----|
| Aksum | Assyria |
| Egypt | Carthage |
| Greece | Silla |
| Han | Tonga |
| Khmer | |
| Maurya | |
| Maya | |
| Mississippian | |
| Persia | |
| Rome | |

Non-antiquity civilizations fall back to the default Augustus portrait.

## Development Phases

### Phase 1: Proof of Concept (current)
- [x] Mod structure and manifest
- [x] Icon replacement for Augustus (8 variants: hex/circle at multiple sizes)
- [x] Loading screen image replacement for Augustus (default)
- [x] SQL table restructure for civ-specific overrides
- [x] JS sort fix for civ-specific image selection
- [x] Placeholder images for all 14 antiquity civilizations
- [ ] Verify civ-specific images display in-game

### Phase 2: All Leaders
- [ ] Download/generate three-quarter portraits for all leaders
- [ ] Generate civ-specific image variants per leader
- [ ] Full icon set for all leaders

### Phase 3: AI-Generated Art
- [ ] Generate civilization-contextualized portraits via AI (Midjourney/DALL-E/SD)
- [ ] Leader in civ-appropriate attire, architecture, setting
- [ ] Polish and quality review

### Phase 4: 3D Animation Override (stretch)
- [ ] Investigate leader model swapping via JS
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

- **ImportFiles can override base game files** when the relative path matches the base module's path (confirmed by BorderToggles community mod).

- **Correct civilization type IDs**: `CIVILIZATION_ROME` (not ROMAN), `CIVILIZATION_SPAIN` (not SPANISH), `CIVILIZATION_PRUSSIA` (not PRUSSIAN)

- **Image format**: Loading screen uses CSS `background-size: cover` on a ~1230x1520px area. Three-quarter length portraits work best.

- **File references**: Mods use `fs://game/<mod-id>/<path>` for imported files, base game uses `blp:<name>` for packed assets.

## License

MIT
