# Authentic Leaders Mod - Work Log

## Current Status (2026-03-02)

### What Works
- **Icon replacement**: Shell-scope icons for Augustus work correctly. The 8 icon variants (hex/circ at various sizes) display properly in leader select and menus.
- **Mod structure**: `.modinfo`, symlink to Mods directory, ImportFiles, UpdateIcons all functional.
- **Loading screen default image**: Proper three-quarter length Augustus portrait (1230x1520) replaces the base game image. Confirmed working with child-element `<Replace>` XML syntax.
- **Repo pushed**: `git@github.com:loki20beta/civ-proper-leaders-for-civs.git` on `main` branch.

### Awaiting Test (2026-03-02)
- **Civ-specific loading screens**: 14 antiquity civilization images + SQL table restructure + JS sort fix. All wired up, needs game restart to test.
  - SQL: DROP TABLE/CREATE TABLE with composite PK `(LeaderType, CivilizationTypeOverride)` + 14 civ-specific INSERT rows
  - JS: ImportFiles override of `load-screen-model.chunk.js` with sort fix (`b_score - a_score` instead of `a_score - b_score`)
  - If JS override doesn't work (ImportFiles can't intercept chunk imports), generic image still shows (no regression)

### History of Approaches Tried

1. **XML with `<Row>` inserts for civ-specific entries** → UNIQUE constraint failed on `LoadingInfo_Leaders.LeaderType` (sole PK).
2. **SQL DROP TABLE/CREATE TABLE with composite PK** → Game loaded but had visual issues ("wrong size", arrows didn't work). Was likely from bad images (272px), not from SQL itself.
3. **XML `<Replace>` with attribute syntax** → Game breaks when starting new game. Wrong XML syntax for Civ7.
4. **XML `<Replace>` with child-element syntax** → WORKS. Default image replacement confirmed.
5. **SQL restructure + JS ImportFiles override** → Current approach for civ-specific images (AWAITING TEST).

### Key Technical Findings

#### Loading Screen System
- Base game images referenced as `blp:lsl_<name>.png` (packed in BLP archives)
- Mods use `fs://game/<mod-id>/<path>.png` for PNG files
- CSS composites image over civ scene via `background-size: cover`
- Original loading screens: 800×1060 RGBA transparent PNGs (BC7-compressed in CIVBIG containers)
- CIVBIG format: 144-byte header + BC7 data (BGRA channel order), 1,132,544 bytes total
- Extracted via `scripts/fetch-wiki-assets.py --loading-originals` (28 leaders + 5 persona alts)

#### CivilizationTypeOverride Sort Bug
- `getLeaderLoadingInfo()` in `load-screen-model.chunk.js` (line 50-54) sorts ascending by specificity score and picks `loadingInfos[0]` (least specific)
- This means civ-specific entries (score 10) LOSE to generic entries (score 0)
- Same bug in `getCivLoadingInfo()` (line 24-28)
- Fix: Change `return a_score - b_score` to `return b_score - a_score` on both functions

#### JS Override via ImportFiles
- `ImportFiles` can override base game files when relative paths match (confirmed by BorderToggles mod)
- The load-screen chunk is loaded via relative import from `load-screen-bootstrap.js`, NOT via UIScripts
- Uncertain if ImportFiles VFS intercepts relative ES module imports — testing needed
- If it doesn't work, alternative: UIScripts with DOM manipulation, or enumerate all civs (no generic row)

#### LoadingInfo_Leaders Schema
- Original PK: `PRIMARY KEY("LeaderType")` — prevents multiple rows per leader
- `CivilizationTypeOverride` column EXISTS but isn't part of PK (Firaxis oversight)
- Fix: Composite PK `PRIMARY KEY("LeaderType", "CivilizationTypeOverride")`
- Full schema: LeaderType, AgeTypeOverride, Audio, CivilizationTypeOverride, LeaderImage, LeaderNameTextOverride (LOC_TEXT), LeaderText (LOC_TEXT)

#### XML Replace Syntax
- `UpdateIcons` context: `<Replace>` uses child elements (confirmed working)
- `UpdateDatabase` context: `<Replace>` also uses child elements (Pattern B from base game)
- Attribute-based `<Replace name="..." value="..."/>` only works for GlobalParameters
- DLC mods only ADD new `<Row>` entries for new leaders; none override existing leaders

#### Modinfo Action Types (complete list)
ImportFiles, UIScripts, UIShortcuts, UpdateArt, UpdateColors, UpdateDatabase, UpdateIcons, UpdateText, UpdateVisualRemaps, ScenarioScripts, MapGenScripts

#### Civilization Type IDs
- Antiquity (base): CIVILIZATION_AKSUM, CIVILIZATION_EGYPT, CIVILIZATION_GREECE, CIVILIZATION_HAN, CIVILIZATION_KHMER, CIVILIZATION_MAURYA, CIVILIZATION_MAYA, CIVILIZATION_MISSISSIPPIAN, CIVILIZATION_PERSIA, CIVILIZATION_ROME
- Antiquity (DLC): CIVILIZATION_ASSYRIA, CIVILIZATION_CARTHAGE, CIVILIZATION_SILLA, CIVILIZATION_TONGA
- Wrong (old): CIVILIZATION_ROMAN → CIVILIZATION_ROME, CIVILIZATION_SPANISH → CIVILIZATION_SPAIN, CIVILIZATION_PRUSSIAN → CIVILIZATION_PRUSSIA

### Current File State

```
authentic-leaders/
  authentic-leaders.modinfo             # References SQL + JS override + all 15 images
  data/
    loading-info-override.sql           # Table restructure + 14 civ-specific rows (AWAITING TEST)
  icons/
    leader-icons-override.xml           # Working - 8 Augustus icon overrides
    augustus/                            # 8 icon PNGs (working)
  images/
    loading/
      lsl_augustus.png                   # 800x1060 default portrait (no label)
      lsl_augustus_aksum.png             # With "AKSUM" label
      lsl_augustus_assyria.png           # With "ASSYRIA" label
      lsl_augustus_carthage.png          # With "CARTHAGE" label
      lsl_augustus_egypt.png             # With "EGYPT" label
      lsl_augustus_greece.png            # With "GREECE" label
      lsl_augustus_han.png               # With "HAN" label
      lsl_augustus_khmer.png             # With "KHMER" label
      lsl_augustus_maurya.png            # With "MAURYA" label
      lsl_augustus_maya.png              # With "MAYA" label
      lsl_augustus_mississippian.png     # With "MISSISSIPPIAN" label
      lsl_augustus_persia.png            # With "PERSIA" label
      lsl_augustus_rome.png              # With "ROME" label
      lsl_augustus_silla.png             # With "SILLA" label
      lsl_augustus_tonga.png             # With "TONGA" label
  ui-next/
    screens/
      load-screen/
        load-screen-model.chunk.js      # Sort fix: b_score - a_score (AWAITING TEST)
```

### Symlink
`~/Library/Application Support/Civilization VII/Mods/authentic-leaders` → `/Users/admin/work/civ7mod/authentic-leaders`

### Next Steps (in order)
1. **Test civ-specific loading screens** - Restart game, start new game with Augustus + any antiquity civ. Check if civ-specific image shows.
2. **If JS override doesn't work** - Try UIScripts approach or remove generic row and enumerate all civs
3. **If SQL breaks game again** - Revert to XML `<Replace>` for default image only (proven working)
4. **Extend to all leaders** (Phase 2)

### Fallback Plan
If the current approach (SQL + JS override) breaks the game:
- Revert SQL: switch back to XML `<Replace>` for default image only
- Revert JS: remove the ImportFiles JS override
- The mod will still work as before (default Augustus image replacement)

### Scripts
- `scripts/generate-mod-data.py` - Generates modinfo + XML from config + images
- `scripts/process-images.py` - Creates all image variants from source portrait
- `scripts/generate-prompts.py` - Generates AI image generation prompts

### Config
- `config/leaders-civilizations.json` - Master data (needs civ ID fixes: ROMAN→ROME etc.)

### Key File Paths
- Game: `~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII/CivilizationVII.app/Contents/Resources/`
- Mods: `~/Library/Application Support/Civilization VII/Mods/`
- Logs: `~/Library/Application Support/Civilization VII/Logs/` (Database.log, Modding.log, UI.log)
- Schema: `Base/Assets/schema/gameplay/01_GameplaySchema.sql`
- Load screen JS: `Base/modules/base-standard/ui-next/screens/load-screen/load-screen-model.chunk.js`
- Load screen CSS: `Base/modules/base-standard/ui-next/screens/load-screen/load-screen.css`
- Base loading-info: `Base/modules/base-standard/data/loading-info.xml`
