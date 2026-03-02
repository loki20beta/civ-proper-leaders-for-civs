# Authentic Leaders Mod - Work Log

## Current Status (2026-03-02)

### What Works
- **Icon replacement**: Shell-scope icons for Augustus work correctly. The 8 icon variants (hex/circ at various sizes) display properly in leader select and menus.
- **Mod structure**: `.modinfo`, symlink to Mods directory, ImportFiles, UpdateIcons all functional.
- **Loading screen images**: Proper three-quarter length Augustus portrait (800x1200 source from wiki, scaled to 1230x1520) created for all variants.

### What's Being Debugged
- **Loading screen database override** (`UpdateDatabase` in game scope): The game crashes/fails when starting a new game due to our `loading-info-override.xml`.
- **Root cause identified**: The `<Replace>` XML element was using attribute syntax (`<Replace LeaderType="..." .../>`) but Civ7's database system requires child-element syntax for table row replacements (`<Replace><LeaderType>...</LeaderType>...</Replace>`).
- **Fix applied but NOT YET TESTED**: Changed `data/loading-info-override.xml` to use child-element syntax. User needs to restart the game and test.

### History of Approaches Tried

1. **XML with `<Row>` inserts for civ-specific entries** → UNIQUE constraint failed on `LoadingInfo_Leaders.LeaderType` (sole PK).
2. **SQL DROP TABLE/CREATE TABLE with composite PK** → Game loaded but had visual issues ("wrong size", arrows didn't work). Likely too aggressive - breaks game engine's internal state.
3. **XML `<Replace>` with attribute syntax** → Game breaks again when starting new game. Wrong XML syntax for Civ7.
4. **XML `<Replace>` with child-element syntax** → Current approach, awaiting test.

### Key Technical Findings

#### Loading Screen System
- Base game images referenced as `blp:lsl_<name>.png` (packed in BLP archives)
- Mods use `fs://game/<mod-id>/<path>.png` for PNG files
- CSS displays image in a div ~1230x1520px with `background-size: cover`
- Three-quarter length portrait source available from wiki at 800x1200

#### CivilizationTypeOverride Sort Bug
- `getLeaderLoadingInfo()` in `load-screen-model.chunk.js` (line 50-54) sorts ascending by specificity score and picks `loadingInfos[0]` (least specific)
- This means civ-specific entries (score 10) LOSE to generic entries (score 0)
- **Civ-specific loading screens cannot work without overriding the JS sort**
- This is a Phase 2 concern - for now we're just replacing the default image

#### XML Replace Syntax
- `UpdateIcons` context: `<Replace>` uses child elements (confirmed working)
- `UpdateDatabase` context: `<Replace>` also uses child elements (Pattern B from base game)
- Attribute-based `<Replace name="..." value="..."/>` only works for GlobalParameters
- DLC mods only ADD new `<Row>` entries for new leaders; none override existing leaders

#### Civilization Type IDs
- Correct: `CIVILIZATION_ROME`, `CIVILIZATION_SPAIN`, `CIVILIZATION_PRUSSIA`, `CIVILIZATION_ABBASID`, `CIVILIZATION_FRENCH_EMPIRE`
- Wrong (old): `CIVILIZATION_ROMAN`, `CIVILIZATION_SPANISH`, `CIVILIZATION_PRUSSIAN`

### Current File State

```
authentic-leaders/
  authentic-leaders.modinfo          # References XML (not SQL) for UpdateDatabase
  data/
    loading-info-override.xml        # <Replace> with child-element syntax (AWAITING TEST)
  icons/
    leader-icons-override.xml        # Working - 8 Augustus icon overrides
    augustus/                         # 8 icon PNGs (working)
  images/
    loading/
      lsl_augustus.png                # 1230x1520 proper portrait (default)
      lsl_augustus_rome.png           # With "ROME" label (not imported yet)
      lsl_augustus_abbasid.png        # With "ABBASID" label (not imported yet)
      lsl_augustus_spain.png          # With "SPAIN" label (not imported yet)
      lsl_augustus_french_empire.png  # With "FRENCH EMPIRE" label (not imported yet)
      lsl_augustus_prussia.png        # With "PRUSSIA" label (not imported yet)
```

### Symlink
`~/Library/Application Support/Civilization VII/Mods/authentic-leaders` → `/Users/admin/work/civ7mod/authentic-leaders`

### Next Steps (in order)
1. **Test the child-element `<Replace>` fix** - user needs to restart game and try starting a new game with Augustus
2. If it still fails, try **simple SQL UPDATE** as fallback: `UPDATE LoadingInfo_Leaders SET LeaderImage = '...' WHERE LeaderType = 'LEADER_AUGUSTUS';` (no DROP/CREATE)
3. Once basic image replacement works, tackle **civ-specific loading screens** (requires JS override to fix sort order)
4. Extend to all leaders (Phase 2)

### Scripts
- `scripts/generate-mod-data.py` - Generates modinfo + XML from config + images (needs updating: still generates XML not SQL for loading info; sort uses `<Replace>` for default, `<Row>` for new)
- `scripts/process-images.py` - Creates all image variants from source portrait
- `scripts/generate-prompts.py` - Generates AI image generation prompts

### Config
- `config/leaders-civilizations.json` - Master data (needs civ ID fixes: ROMAN→ROME etc.)

### Key File Paths
- Game: `~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII/CivilizationVII.app/Contents/Resources/`
- Mods: `~/Library/Application Support/Civilization VII/Mods/`
- Logs: `~/Library/Application Support/Civilization VII/Logs/` (Database.log, Modding.log, UI.log)
- Plan: `/Users/admin/.claude/plans/zazzy-stirring-lerdorf.md`
- Load screen JS: `Base/modules/base-standard/ui-next/screens/load-screen/load-screen-model.chunk.js`
- Load screen CSS: `Base/modules/base-standard/ui-next/screens/load-screen/load-screen.css`
- Base loading-info: `Base/modules/base-standard/data/loading-info.xml`
