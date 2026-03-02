# Civilization VII - Authentic Leaders Mod

A Civilization VII mod that replaces leader loading screen images and icons with civilization-specific artwork for a more historically authentic experience.

## Current Status: Phase 1 (POC) - In Progress

**Working:**
- Leader icon replacement (Augustus icons in leader select and menus)
- Loading screen image replacement (Augustus three-quarter portrait replaces default)
- Mod loads without errors, game fully functional

**Not Yet Working:**
- Civilization-specific loading screens (e.g., different Augustus portrait when playing Rome vs Abbasid)
  - Blocked by a sort-order bug in the base game's `getLeaderLoadingInfo()` JS — it picks the least specific match instead of the most specific
  - Fix requires a JS override of the loading screen model

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
    loading-info-override.xml  # Database override for loading screen images
  icons/
    leader-icons-override.xml  # Icon definition overrides
    augustus/                   # Augustus icon PNGs (8 variants)
  images/
    loading/                   # Loading screen portraits (1230x1520)

config/
  leaders-civilizations.json   # Master data: all leaders, civs, ages

scripts/
  process-images.py            # Create icon + loading variants from source portrait
  generate-prompts.py          # Generate AI image prompts per leader+civ
  generate-mod-data.py         # Generate modinfo + XML from config
```

## Development Phases

### Phase 1: Proof of Concept (current)
- [x] Mod structure and manifest
- [x] Icon replacement for Augustus (8 variants: hex/circle at multiple sizes)
- [x] Loading screen image replacement for Augustus
- [ ] Civilization-specific loading screen per Augustus civ pairing
- [ ] Fix JS sort order to enable civ-specific image selection

### Phase 2: All Leaders
- [ ] Download/generate three-quarter portraits for all 28 leaders
- [ ] Generate civ-specific image variants per leader
- [ ] Override JS loading screen model to fix sort order
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

- **LoadingInfo_Leaders table** has `LeaderType` as sole PRIMARY KEY — cannot insert multiple rows per leader for civ-specific overrides without table restructuring

- **JS sort bug**: `getLeaderLoadingInfo()` sorts ascending by specificity and picks index [0], so the generic entry always wins over civ-specific entries. Requires JS file override to fix.

- **Correct civilization type IDs**: `CIVILIZATION_ROME` (not ROMAN), `CIVILIZATION_SPAIN` (not SPANISH), `CIVILIZATION_PRUSSIA` (not PRUSSIAN)

- **Image format**: Loading screen uses CSS `background-size: cover` on a ~1230x1520px area. Three-quarter length portraits work best.

- **File references**: Mods use `fs://game/<mod-id>/<path>` for imported files, base game uses `blp:<name>` for packed assets.

## License

MIT
