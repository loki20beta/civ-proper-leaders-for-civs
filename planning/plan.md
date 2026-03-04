# Civ7 Authentic Leaders Mod - Development Plan

> **Status (2026-03-04):** Phase 1 (infrastructure) and Phase 2 (asset extraction + stubs) are complete. All 33 leaders/alts × 43 civs have working civ-specific loading screens and icons (currently stubs). Persona/alt leaders fully supported with persona-first icon lookup. Next: Phase 3 (AI-generated artwork).

## Context

Civilization VII decouples leaders from civilizations - any leader can play any civ. This means the same generic leader portrait (e.g., Augustus) is shown whether you're playing Rome, Abbasid, or Spanish. The goal of this mod is to generate and display leader images that reflect the civilization they're leading, making the experience more historically authentic (e.g., Augustus in Roman imperial regalia vs. Augustus in Abbasid-influenced attire).

The game's loading screen system already supports `CivilizationTypeOverride` and `AgeTypeOverride` fields in `LoadingInfo_Leaders`, which means the engine natively supports showing different leader images per civilization - it just doesn't ship with civilization-specific variants.

## Key Technical Findings

### Loading Screen Images
- Defined in `LoadingInfo_Leaders` table (see `base-standard/data/loading-info.xml`)
- Each row has: `LeaderType`, `LeaderImage` (path), `LeaderText`, `Audio`
- Supports optional `CivilizationTypeOverride` and `AgeTypeOverride` for specific combos
- The JS code (`load-screen-model.chunk.js`) sorts matches by specificity (leader+civ scores highest)
- Images referenced as `blp:lsl_<name>.png` in base game; mods use `fs://game/<mod-id>/path.png`
- Images displayed as CSS `background-image` in a dedicated `load-screen-leader-image` div
- Background comes from `LoadingInfo_Civilizations` (separate table, civ-specific)

### Leader Icons
- Defined in `IconDefinitions` table (see `base-standard/data/icons/leader-icons.xml`)
- 8 variants per leader: hex (256/128/128_h/128_a/64) + circle (256/128/64)
- Contexts: DEFAULT, LEADER_HAPPY, LEADER_ANGRY, CIRCLE_MASK
- Base game uses `blp:` prefix; mods use PNG via `fs://game/<mod-id>/path.png`
- Override with `<Replace>` elements in icon XML

### 3D Animations
- Leader 3D models managed by `leader-select-model-manager.chunk.js`
- Community "Leader Model Changer" mod (by izica) can swap models via JS config
- Custom 3D models are extremely difficult (no official art pipeline)
- Realistic approach: swap between existing in-game models based on civ context

### File Paths (macOS Steam)
- Game: `~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII/CivilizationVII.app/Contents/Resources/`
- Mods: `~/Library/Application Support/Civilization VII/Mods/`
- Key source files:
  - `Base/modules/base-standard/data/loading-info.xml`
  - `Base/modules/base-standard/data/icons/leader-icons.xml`
  - `Base/modules/base-standard/ui-next/screens/load-screen/load-screen-model.chunk.js`
  - `Base/modules/base-standard/ui-next/screens/load-screen/load-screen.chunk.js`

---

## Phase 1: POC - Augustus Loading Screen + Icon Replacement

**Goal**: Replace Augustus's loading screen image and leader icons with a custom image, regardless of civilization. Proves the mod pipeline works.

### Mod Structure
```
authentic-leaders/
  authentic-leaders.modinfo
  data/
    loading-info-override.xml       # Override LoadingInfo_Leaders for Augustus
  icons/
    leader-icons-override.xml       # Override IconDefinitions for Augustus
    augustus/
      lp_hex_augustus_256.png        # 256x256 hex icon
      lp_hex_augustus_128.png        # 128x128 hex icon (neutral)
      lp_hex_augustus_128_h.png      # 128x128 hex icon (happy)
      lp_hex_augustus_128_a.png      # 128x128 hex icon (angry)
      lp_hex_augustus_64.png         # 64x64 hex icon
      lp_circ_augustus_256.png       # 256x256 circle icon
      lp_circ_augustus_128.png       # 128x128 circle icon
      lp_circ_augustus_64.png        # 64x64 circle icon
      lsl_augustus.png               # Loading screen portrait (tall, ~1024px wide)
```

### Steps
1. Create mod directory structure at `/Users/admin/work/civ7mod/authentic-leaders/`
2. Create `.modinfo` XML with:
   - `ImportFiles` for all PNG assets
   - `UpdateDatabase` (scope=`game`) for loading-info override
   - `UpdateIcons` (scope=`game` and `shell`) for icon overrides
3. Create `loading-info-override.xml` with `<Replace>` row for `LEADER_AUGUSTUS`
4. Create `leader-icons-override.xml` with `<Replace>` rows for all 8 Augustus icon variants
5. Generate AI images for Augustus (loading screen + 3 icon expressions) using prompt templates
6. Process images: resize to required dimensions, create all 9 variants from source images
7. Symlink or copy mod to `~/Library/Application Support/Civilization VII/Mods/`
8. Test in-game: start a new game with Augustus, verify loading screen and icons change

### Image Specifications
| Type | Dimensions | Format | Notes |
|------|-----------|--------|-------|
| Loading screen | ~1024x1400 | PNG | Portrait orientation, character on transparent/dark bg |
| Hex icon 256 | 256x256 | PNG | Transparent bg, hexagonal frame area |
| Hex icon 128 | 128x128 | PNG | Transparent bg, neutral expression |
| Hex icon 128_h | 128x128 | PNG | Happy expression variant |
| Hex icon 128_a | 128x128 | PNG | Angry expression variant |
| Hex icon 64 | 64x64 | PNG | Small thumbnail |
| Circle icon 256 | 256x256 | PNG | Circular crop area |
| Circle icon 128 | 128x128 | PNG | Circular crop area |
| Circle icon 64 | 64x64 | PNG | Circular crop area |

### AI Image Generation Pipeline
- **Tool**: Use any text-to-image AI (Midjourney, DALL-E 3, Stable Diffusion, etc.)
- **Loading screen prompt template**: `"Portrait of [leader name], [historical era] [civilization] style, wearing [civ-appropriate attire], dramatic lighting, dark background, painterly style matching Civilization VII art direction, three-quarter view, 2:3 aspect ratio"`
- **Icon prompt template**: `"Close-up portrait headshot of [leader name], [expression: neutral/happy/angry], [civilization] cultural styling, hexagonal portrait frame, dark background, game icon style"`
- **Processing script** (`scripts/process-images.py`): Takes source AI images, resizes to all required dimensions (256/128/64), creates hex and circle variants with appropriate masking
- **Naming convention**: `{leader_key}_{civ_key}.png` for loading screens, `{leader_key}_{variant}.png` for icons

---

## Phase 2: All Leaders x All Civilizations

**Goal**: Provide civilization-specific loading screen images for every leader+civ combination. Each image depicts the leader in attire/setting appropriate to their current civilization.

### Scope
- 19 base game leaders (unique characters, not counting persona variants)
- 30 base game civilizations across 3 ages
- Persona variants (Napoleon Emperor/Revolutionary, etc.) share base leader type in `LoadingInfo_Leaders`
- Not every leader+civ combo needs a unique image - focus on guaranteed/historical pairings first, then expand

### Approach
1. **Create `config/leaders-civilizations.json`** - master config mapping leaders to their guaranteed civilizations (from research data)
2. **Generate images** - Use AI image generation with prompt templates from config; batch-generate using the `scripts/generate-prompts.py` script that reads `leaders-civilizations.json` and outputs prompts per leader+civ combo
3. **Use `CivilizationTypeOverride`** in `LoadingInfo_Leaders` to serve different images per combo:
   ```xml
   <Row LeaderType="LEADER_AUGUSTUS" CivilizationTypeOverride="CIVILIZATION_ROMAN"
        LeaderImage="fs://game/authentic-leaders/images/augustus_roman.png" ... />
   <Row LeaderType="LEADER_AUGUSTUS" CivilizationTypeOverride="CIVILIZATION_ABBASID"
        LeaderImage="fs://game/authentic-leaders/images/augustus_abbasid.png" ... />
   ```
4. **Icon replacement** can remain leader-specific (same icon regardless of civ) or be extended per-civ if desired
5. **Build script** (Python/Node) to auto-generate the XML from the config + image assets

### Priority Order
1. Augustus + all guaranteed civs (Roman, Abbasid, Spanish, French Empire, Prussia)
2. All leaders + their primary/historical civ only
3. All leaders + all guaranteed civ combos
4. Remaining leader+civ combos (stretch goal)

### Directory Structure
```
authentic-leaders/
  images/
    loading/
      augustus_roman.png
      augustus_abbasid.png
      augustus_spanish.png
      ...
    icons/
      augustus/
        (8 icon variants)
      amina/
        (8 icon variants)
      ...
  data/
    loading-info-override.xml
  icons/
    leader-icons-override.xml
  scripts/
    generate-mod-data.py          # Generates XML from config + available images
  config/
    leaders-civilizations.json    # Master data file
```

---

## Phase 3: 3D Animation Changes

**Goal**: Change the 3D leader model/animation based on the civilization being played.

### Feasibility Assessment
- **Creating new 3D models**: Not feasible. No art import pipeline exists in the SDK.
- **Swapping existing models**: Feasible using the Leader Model Changer approach (JS-based)
- **Changing animations on existing models**: Feasible (different idle/spawn animations)

### Realistic Approach
1. **Integrate with Leader Model Changer** - use its JS API to swap leader models contextually
2. **Create `shell.js` and `game.js`** scripts that:
   - Detect which civilization the player selected
   - Map leader+civ to an appropriate existing 3D model from the game
   - Override the model display in leader select and diplomacy screens
3. **Example**: When Augustus leads Abbasid, show him with a different animation set or swap to a thematically appropriate existing character model

### Limitations
- Only existing in-game 3D models can be used (no custom models)
- This phase depends heavily on community tooling evolution
- May need to be revisited when Firaxis releases art tools in the SDK

---

## Files to Create

| File | Purpose |
|------|---------|
| `/Users/admin/work/civ7mod/authentic-leaders/authentic-leaders.modinfo` | Mod manifest |
| `/Users/admin/work/civ7mod/authentic-leaders/data/loading-info-override.xml` | Loading screen image overrides |
| `/Users/admin/work/civ7mod/authentic-leaders/icons/leader-icons-override.xml` | Icon definition overrides |
| `/Users/admin/work/civ7mod/config/leaders-civilizations.json` | Master leader+civ data config |
| `/Users/admin/work/civ7mod/scripts/generate-mod-data.py` | Build script for XML generation from config |
| `/Users/admin/work/civ7mod/scripts/process-images.py` | Image processing: resize, mask, create variants |
| `/Users/admin/work/civ7mod/scripts/generate-prompts.py` | Generate AI image prompts from config |
| `/Users/admin/work/civ7mod/plan.md` | Copy of this plan for project reference |

## Verification

### Phase 1
1. Place mod in `~/Library/Application Support/Civilization VII/Mods/authentic-leaders/`
2. Launch Civ7, check Add-Ons screen for "Authentic Leaders" mod
3. Enable the mod, start a new game with Augustus
4. Verify: loading screen shows custom image instead of default
5. Verify: leader selection and in-game icons show custom images
6. Check `~/Library/Application Support/Civilization VII/Logs/UI.log` for any errors

### Phase 2
1. Test multiple leader+civ combinations
2. Verify that `CivilizationTypeOverride` correctly selects the right image
3. Verify fallback to default image when no civ-specific image exists

### Phase 3
1. Test leader model swap in leader select screen
2. Test model swap in diplomacy encounters
3. Verify no crashes or visual glitches
