# Civ7 Authentic Leaders Mod - Development Plan

> **Status (2026-03-04):** Phase 1 (infrastructure) and Phase 2 (asset extraction + stubs) are complete. All 33 leaders/alts × 43 civs have working civ-specific loading screens and icons (currently stubs). Persona/alt leaders fully supported with persona-first icon lookup. Phase 3A (AI generation pipeline code) built and dry-run tested — not yet tested with live API calls. Next: Phase 3B (generation run).

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

## Phase 3: AI Art Generation Pipeline

**Goal**: Replace all ~1,427 stub images with AI-generated artwork where each leader wears civilization-appropriate attire. Uses **Nano Banana 2** (`google/gemini-3.1-flash-image-preview`) via **OpenRouter API** with multi-image reference for identity preservation and costume transfer.

**Key principles:**
- Native leader×civ pairs are **skipped** — default game art already correct
- Non-native pairs **reference the native leader's image** as costume source
- **Gender-aware**: female leaders get period-appropriate female attire
- **Generate largest icon size only** (hex 256×360, circ 256×256), downscale smaller programmatically
- **AI-generate all 3 expressions** (neutral, happy, angry) — no color tinting
- Optimize for quality, no budget limit
- API key stored in `ai_generator/.env` (git-ignored)

### 3.1 Master Metadata — `config/ai-generation.json`

Central config for native pairings, gender-aware attire descriptors, and generation status tracking.

#### Native Pairings (skip list — ~25 pairs)

Leader×civ combos where the default game art already matches. Generator skips these and uses original extracted images.

```
augustus           → rome
hatshepsut        → egypt
ashoka            → maurya
xerxes            → persia
confucius         → han
pachacuti         → inca
charlemagne       → normandy
isabella          → spain
napoleon          → french_empire
lafayette         → french_empire
catherine         → russia
benjamin_franklin → america
harriet_tubman    → america
friedrich         → prussia
genghis_khan      → mongolia
tecumseh          → shawnee
trung_trac        → dai_viet
ada_lovelace      → britain
edward_teach      → pirates
sayyida_al_hurra  → pirates
simon_bolivar     → mexico

# No native civ (generate for ALL civs):
amina, ibn_battuta, jose_rizal, lakshmibai,
himiko, gilgamesh, machiavelli
```

Persona alts:
```
ashoka_alt    → maurya
friedrich_alt → prussia
napoleon_alt  → french_empire
xerxes_alt    → persia
himiko_alt    → (none — generate for all)
```

#### Costume Reference Leader per Civilization

When dressing a non-native leader for a civ, use the native leader's game image as a **costume reference** (same gender only). Cross-gender pairs use text-only attire descriptions.

```
rome           → augustus (M)          | female: text-only
egypt          → hatshepsut (F)       | male: text-only
han            → confucius (M)        | female: text-only
maurya         → ashoka (M)           | female: text-only
persia         → xerxes (M)           | female: text-only
inca           → pachacuti (M)        | female: text-only
normandy       → charlemagne (M)      | female: text-only
spain          → isabella (F)         | male: text-only
french_empire  → napoleon (M)         | female: text-only
russia         → catherine (F)        | male: text-only
america        → benjamin_franklin(M) | female: harriet_tubman (F)
prussia        → friedrich (M)        | female: text-only
mongolia       → genghis_khan (M)     | female: text-only
shawnee        → tecumseh (M)         | female: text-only
dai_viet       → trung_trac (F)       | male: text-only
pirates        → edward_teach (M)     | female: sayyida_al_hurra (F)
britain        → ada_lovelace (F)     | male: text-only
mexico         → simon_bolivar (M)    | female: text-only

# No native leader — text-only prompts for both genders:
greece, khmer, maya, mississippian, aksum, assyria, carthage, silla, tonga,
abbasid, chola, hawaii, majapahit, ming, songhai, bulgaria, iceland,
meiji, mughal, qing, siam, buganda, ottoman, qajar, nepal
```

#### Gender-Aware Civ Attire Descriptors

Each of the 44 civs gets `male_attire` and `female_attire` with:
- `clothing`: main garment description
- `headwear`: era-appropriate headwear
- `accessories`: jewelry, ornaments, weapons
- `forbidden`: anachronisms that MUST NOT appear
- `palette`: color scheme

Example (Rome):
```json
{
  "rome": {
    "period": "1st century BCE - 5th century CE",
    "setting": "Roman marble columns, eagle standards, Forum backdrop",
    "male_attire": {
      "clothing": "imperial toga picta with purple trim over tunica, gold-embroidered borders",
      "headwear": "laurel wreath",
      "accessories": "gold fibula brooch, imperial signet ring, arm bands",
      "forbidden": ["trousers", "buttons", "epaulettes", "modern boots"],
      "palette": ["imperial red", "gold", "marble white", "deep purple"]
    },
    "female_attire": {
      "clothing": "Roman stola in imperial purple with gold belt, palla draped over shoulder",
      "headwear": "golden diadem with jewels, or pearl-studded hair ornaments",
      "accessories": "pearl necklace, gold armillae bracelets, cameo brooch",
      "forbidden": ["trousers", "boots", "military armor", "modern elements"],
      "palette": ["imperial red", "gold", "marble white", "deep purple"]
    }
  }
}
```

**Work needed**: 33 civs have male-only descriptors in `generate-prompts.py` → add female variants. 10 civs missing entirely (Assyrian, Carthaginian, Silla, Tongan, Bulgarian, Dai Viet, Icelandic, Pirates, Shawnee, Nepalese) → create both genders. Total: **88 attire descriptors** (44 civs × 2 genders).

#### Generation Status Tracking

Per-pair status with attempts and quality scores for resume/retry. **Never overwrite generated files** — each attempt is saved as a numbered variant. The status tracks which variant is selected as "best".

```json
{
  "augustus_abbasid": {
    "loading": {
      "status": "completed",
      "variants": [
        {"file": "loading_v1.png", "quality": 3},
        {"file": "loading_v2.png", "quality": 5}
      ],
      "selected": "loading_v2.png"
    },
    "icon_neutral": {
      "status": "completed",
      "variants": [{"file": "icon_neutral_v1.png", "quality": 4}],
      "selected": "icon_neutral_v1.png"
    },
    "icon_happy": {"status": "pending", "variants": []},
    "icon_angry": {"status": "pending", "variants": []}
  }
}
```

Generated files stored as:
```
assets/generated/{leader}/{civ}/
  loading_v1.png
  loading_v2.png       # retry — v1 NOT deleted
  icon_neutral_v1.png
  icon_happy_v1.png
  icon_angry_v1.png
```

### 3.2 Python Package — `ai-generator/`

```
ai-generator/
  __init__.py
  .env               # OPENROUTER_API_KEY=sk-or-v1-... (git-ignored)
  config.py          # Load configs, native pairings, attire descriptors
  client.py          # OpenRouter API wrapper with retry/rate-limiting
  prompts.py         # Prompt construction (loading screen + 3 icon expressions)
  generate.py        # Main CLI orchestrator
  postprocess.py     # Resize, mask, downscale pipeline
  status.py          # Status tracking (resume, retry)
```

#### `.env` — API key (git-ignored)

```
OPENROUTER_API_KEY=sk-or-v1-...
```

#### `config.py` — Metadata access layer

- `load_config()` — reads `config/ai-generation.json` + `config/leaders-civilizations.json`
- `is_native(leader, civ)` — checks skip list
- `get_costume_ref(leader, civ)` — returns reference leader for same-gender costume, or None
- `get_attire(civ, gender)` — returns gender-appropriate attire descriptor
- `get_all_pairs()` — returns all (leader, civ) pairs needing generation
- `get_leader_gender(leader)` — "male" or "female"

#### `client.py` — OpenRouter API wrapper

Uses OpenRouter's OpenAI-compatible chat completions endpoint (`https://openrouter.ai/api/v1/chat/completions`) with model `google/gemini-3.1-flash-image-preview`.

```python
class OpenRouterClient:
    def __init__(self, api_key, model="google/gemini-3.1-flash-image-preview")
    def generate_image(self, prompt, ref_images, aspect_ratio, resolution) -> Image
    def multi_turn_generate(self, messages, aspect_ratio, resolution) -> Image
```

**Request format:**
```python
{
    "model": "google/gemini-3.1-flash-image-preview",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "prompt text here"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
            ]
        }
    ],
    "modalities": ["image", "text"],
    "image_config": {
        "aspect_ratio": "3:4",
        "image_size": "2K"
    }
}
```

**Response format** — images returned as base64 in `choices[0].message.images[].image_url.url`

**Multi-turn** — append assistant response + new user message to messages array for each turn (loading screen → icon neutral → icon happy → icon angry).

**Features:**
- Exponential backoff retry on 429/500
- Rate limiting (80 RPM per OpenRouter limits)
- Cost tracking per call
- Image save with metadata
- Reference images sent as base64-encoded PNG in content array

#### `prompts.py` — Prompt construction

Three reference image roles per generation:
1. **Identity anchor**: `assets/leaders/{leader}/loading_original.png`
2. **Costume reference**: native leader's `loading_original.png` (same gender only, optional)
3. **Background reference**: `assets/civilizations/{civ}/background_1080.png`

#### Image Specs — Reference vs Output

All reference images are **RGBA with transparent backgrounds**. Output must match.

| Asset | Reference size | Reference ratio | API aspect_ratio | API image_size | Post-process to |
|-------|---------------|-----------------|-----------------|----------------|-----------------|
| Loading screen | 800×1060 | ~3:4 | `"3:4"` | `"2K"` | Resize to 800×1060 RGBA |
| Hex icon (from headshot) | 256×360 | 32:45 | `"3:4"` | `"1K"` | Crop to 32:45, resize to 256×360, hex mask |
| Circ icon (from headshot) | 256×256 | 1:1 | `"1:1"` | `"1K"` | Resize to 256×256, circ mask |

**Note**: Gemini may not produce true alpha transparency. Post-processing must:
1. Generate on dark/flat background
2. Detect and remove background → convert to RGBA with transparent bg
3. Or: request "solid dark background" and threshold to alpha in post-processing

**Loading screen prompt template:**
```
Generate a portrait of this leader dressed as a ruler of [CIV_NAME].

IDENTITY: This is [LEADER_NAME]. [Identity anchor image] shows their exact appearance.
Preserve their face, skin tone, facial structure, hair color, and body proportions exactly.

COSTUME: Dress them in [PERIOD] [CIV_NAME] attire:
- Clothing: [attire.clothing]
- Headwear: [attire.headwear]
- Accessories: [attire.accessories]
Do NOT include: [attire.forbidden]

[IF costume_ref exists]:
Use [costume reference image] as a visual guide for the attire style and details.
Apply similar garments and accessories to this leader while respecting their body type.

STYLE: Match the painterly digital art style of Civilization VII game art.
Dramatic cinematic side lighting, solid dark background (for easy removal).
Three-quarter view, standing pose.
Color palette: [attire.palette].
Image should be 3:4 aspect ratio matching the reference images provided.
```

**Icon headshot prompt template (per expression):**
```
Now create a close-up head-and-shoulders portrait of this same character
in the same [CIV] costume.

Expression: [NEUTRAL: calm dignified | HAPPY: warm satisfied smile | ANGRY: stern fierce scowl]
Keep the exact same outfit, headwear, and accessories from the loading screen.
Centered face, solid dark background, same painterly Civ7 art style.
3:4 aspect ratio matching the reference.
```

#### `generate.py` — Main CLI orchestrator

```bash
python3 -m ai-generator.generate --leader augustus              # one leader, all civs
python3 -m ai-generator.generate --leader augustus --civ abbasid # one pair
python3 -m ai-generator.generate --all                          # all pending pairs
python3 -m ai-generator.generate --resume                       # pick up where left off
python3 -m ai-generator.generate --retry                        # retry failures
python3 -m ai-generator.generate --dry-run                      # preview only
```

**Per-pair workflow** (single multi-turn chat session for consistency):

```
1. Check if pair is native → SKIP
2. Check if already completed in status → SKIP (unless --force)
3. Load reference images:
   - identity: assets/leaders/{leader}/loading_original.png
   - costume_ref: assets/leaders/{native_leader}/loading_original.png (if same gender)
   - background: assets/civilizations/{civ}/background_1080.png
4. Create chat session via OpenRouter
5. Turn 1: Generate loading screen (3:4 aspect, 2K resolution)
   → Save to assets/generated/{leader}/{civ}/loading_v{N}.png (never overwrite)
6. Turn 2: Generate neutral icon headshot (3:4 aspect, 1K)
   → Save to assets/generated/{leader}/{civ}/icon_neutral_v{N}.png
7. Turn 3: Generate happy icon headshot (3:4 aspect, 1K)
   → Save to assets/generated/{leader}/{civ}/icon_happy_v{N}.png
8. Turn 4: Generate angry icon headshot (3:4 aspect, 1K)
   → Save to assets/generated/{leader}/{civ}/icon_angry_v{N}.png
9. Update status JSON with new variant, auto-select latest as "selected"
```

#### `postprocess.py` — Image processing pipeline

Takes the **selected** variant from each pair's status and produces all final mod assets:

```
For each pair:
  Read status JSON → get "selected" variant for each asset type

  Loading screen:
    selected loading_v{N}.png (3:4) → resize to 800×1060 RGBA → save as lsl_{leader}_{civ}.png

  Hex icons (from selected neutral/happy/angry headshots):
    selected icon_*_v{N}.png (3:4) → crop to 32:45 aspect → resize to 256×360 → apply hex mask
    → downscale to 128×180 and 64×90
    Neutral → hex_256, hex_128, hex_64
    Happy   → hex_128_h
    Angry   → hex_128_a

  Circle icons (from selected neutral headshot):
    selected icon_neutral_v{N}.png (3:4) → crop center square → resize to 256×256 → apply circle mask
    → downscale to 128×128 and 64×64

  Create extensionless copies for all icons
  Copy to authentic-leaders/ mod directory
```

Reuses existing functions from `scripts/generate.py`:
- `create_hex_mask()` — hex icon mask generation
- `create_circle_mask()` — circle icon mask generation
- `crop_center_rect()` — center cropping utility

### 3.3 Persona/Alt Leader Handling

5 persona alts: Ashoka Alt, Friedrich Alt, Himiko Alt, Napoleon Alt, Xerxes Alt

- Same face as base leader, different default outfit
- Use persona's own `alt_loading_original.png` as identity anchor
- Native skips: ashoka_alt→maurya, friedrich_alt→prussia, napoleon_alt→french_empire, xerxes_alt→persia, himiko_alt→(none)
- Output naming: `lsl_{key}_alt_{civ}.png`, `lp_hex_{key}_alt_{civ}_256.png`
- Generate independently (don't reuse base leader's civ images)

### 3.4 Quality Control

**Automated checks** after each generation:
1. Dimensions: correct aspect ratio and minimum resolution
2. Face present: lightweight face detection (mediapipe or similar)
3. Background: transparent/dark background verified via alpha histogram
4. Visual similarity: leader face embedding distance vs reference

**Re-generation** for failures:
- Max 3 retries with prompt adjustments (more specific, higher thinking level)
- Track all attempts in status JSON — never overwrite previous variants
- Fall back to stub for persistent failures

**Manual review**:
```bash
python3 -m ai-generator.generate --review  # web gallery for review
```

### 3.5 Integration with Existing Pipeline

After AI generation:
```bash
python3 -m ai-generator.postprocess --all   # resize, mask, downscale
python3 scripts/generate-mod-data.py         # regenerate SQL, XML, modinfo
```

Output paths match existing stub conventions — `generate-mod-data.py` picks up new images automatically.

### 3.6 Volume & Cost Estimates

Base leaders: 28 × 44 = 1,232 pairs − 21 native skips = **~1,211 pairs**
Persona alts: 5 × 44 = 220 pairs − 4 native skips = **~216 pairs**
Total pairs: **~1,427**

| Item | Count | $/image | Total |
|------|-------|---------|-------|
| Loading screens | ~1,427 | $0.10 | ~$143 |
| Icon neutral headshots | ~1,427 | $0.07 | ~$100 |
| Icon happy headshots | ~1,427 | $0.07 | ~$100 |
| Icon angry headshots | ~1,427 | $0.07 | ~$100 |
| Re-generations (~20%) | ~1,140 | $0.08 | ~$91 |
| **Total** | **~6,848** | | **~$534** |

Time: ~6,850 API calls at 80 RPM = ~1.4 hours interactive.

### 3.7 Implementation — Phase A: Build Pipeline (code, metadata, config) ✅ BUILT (dry-run tested)

1. ✅ `.gitignore` + `ai_generator/.env` — API key setup (git-ignored)
2. ✅ `config/ai-generation.json` — metadata, native pairings, 43 civs × 2 genders attire descriptors (86 total)
3. ✅ `ai_generator/config.py` — load and query metadata
4. ✅ `ai_generator/client.py` — OpenRouter API wrapper
5. ✅ `ai_generator/prompts.py` — prompt construction
6. ✅ `ai_generator/status.py` — generation tracking
7. ✅ `ai_generator/generate.py` — main CLI orchestrator
8. ✅ `ai_generator/postprocess.py` — resize/mask/downscale pipeline

**Note:** Package directory is `ai_generator` (underscore) for Python import compatibility. Dry-run tested (config loading, native skip detection, costume refs, prompt generation, status tracking). Not yet tested with live API calls.

### 3.8 Implementation — Phase B: Generation Run

9. Test with 1 leader × 2-3 civs, validate quality and prompt effectiveness
10. Full generation run across all ~1,394 non-native pairs
11. Quality review, re-generation of failures
12. Run `generate-mod-data.py` to rebuild mod data from generated images
13. In-game verification

---

## Phase 4: 3D Animation Changes

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
1. Dry-run: `python3 -m ai_generator.generate --leader augustus --dry-run` — verify prompts and ref images ✅
2. Test 1 leader × 2-3 civs with live API — verify image quality and identity preservation
3. Full generation run — verify all ~1,394 pairs complete
4. Post-process: `python3 -m ai_generator.postprocess --all` — verify icon variants at correct dimensions
5. Run `generate-mod-data.py` — verify SQL/XML/modinfo updated
6. In-game: verify loading screens and icons display correctly

### Phase 4
1. Test leader model swap in leader select screen
2. Test model swap in diplomacy encounters
3. Verify no crashes or visual glitches
