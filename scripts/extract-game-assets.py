#!/usr/bin/env python3
"""Extract game assets from Civilization VII game files.

Extracts from game BLP/CIVBIG textures:
  - Loading screens → assets/leaders/{icon_key}/loading_original.png
  - Leader icons → authentic-leaders/icons/{icon_key}/lp_*.png
  - Civ backgrounds → assets/civilizations/{civ_key}/background_1080.png, background_720.png

CIVBIG format: 16-byte prefix + BC7-compressed texture data + footer padding.
Prefix = "CIVBIG\\0\\0" + uint32 payload_size + uint32 flags.
BC7 level-0 mipmap data starts immediately at byte 16.
BC7 decodes as BGRA; we swap to RGBA for PNG output.
"""

import argparse
import glob
import json
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Game install path for BLP texture extraction (macOS)
GAME_DLC_DIR = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/"
    "Sid Meier's Civilization VII/CivilizationVII.app/"
    "Contents/Resources/DLC"
)

LOADING_SCREEN_WIDTH = 800
LOADING_SCREEN_HEIGHT = 1060

# Expected total file size for loading screen CIVBIG files
CIVBIG_LOADING_EXPECTED_SIZE = 1132544

# Background dimensions: ultrawide scene paintings behind leader portrait
BG_1080_WIDTH = 2560
BG_1080_HEIGHT = 1080
BG_720_WIDTH = 1708
BG_720_HEIGHT = 720

# Expected file sizes for background CIVBIG files
CIVBIG_BG_1080_EXPECTED_SIZE = 3688448
CIVBIG_BG_720_EXPECTED_SIZE = 1641984

# civ_key → texture name overrides (where they differ)
BG_TEXTURE_NAME_OVERRIDES = {
    "britain": "great_britain",
    "normandy": "norman",
    "ottoman": "ottomans",
    "pirates": "pirate_republic",
}

# Texture names that differ from icon_key
TEXTURE_NAME_OVERRIDES = {
    "simon_bolivar": "bolivar",
}

# Persona alt texture names: persona_type → texture suffix
PERSONA_ALT_TEXTURES = {
    "LEADER_ASHOKA_ALT": "ashoka_alt",
    "LEADER_HIMIKO_ALT": "himiko_alt",
    "LEADER_FRIEDRICH_ALT": "friedrich_alt",
    "LEADER_XERXES_ALT": "xerxes_alt",
    "LEADER_NAPOLEON_ALT": "napoleon_alt",
}

# Icon variants to extract. Game texture naming: TEXTURE_lp_{shape}_{name}_{size}{suffix}
# Matches ICON_VARIANTS in generate-stubs.py.
ICON_EXTRACT_VARIANTS = [
    {"shape": "hex",  "size": 256, "suffix": ""},
    {"shape": "hex",  "size": 128, "suffix": ""},
    {"shape": "hex",  "size": 128, "suffix": "_h"},
    {"shape": "hex",  "size": 128, "suffix": "_a"},
    {"shape": "hex",  "size": 64,  "suffix": ""},
    {"shape": "circ", "size": 256, "suffix": ""},
    {"shape": "circ", "size": 128, "suffix": ""},
    {"shape": "circ", "size": 64,  "suffix": ""},
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def persona_key(leader_type, persona_type):
    """Derive short persona key from types.

    e.g. LEADER_ASHOKA + LEADER_ASHOKA_ALT → alt
    """
    prefix = leader_type + "_"
    if persona_type.startswith(prefix):
        return persona_type[len(prefix):].lower()
    return persona_type.replace("LEADER_", "").lower()


def decode_civbig(file_path, width, height, decode_height=None):
    """Decode level-0 from a CIVBIG file to an RGBA PIL Image.

    BC7 mipmap data starts at byte 16 (right after the prefix).
    Level-0 is first in the mipchain. BC7 decodes to BGRA; we swap to RGBA.

    If decode_height > height, decodes the taller texture and crops the
    bottom `height` rows. Hex icon textures have a 45/32 aspect ratio
    (e.g. 128×180 for a 128-wide icon).
    """
    import texture2ddecoder
    from PIL import Image

    if decode_height is None:
        decode_height = height

    bc7_size = max(1, (width + 3) // 4) * max(1, (decode_height + 3) // 4) * 16
    with open(file_path, "rb") as f:
        f.seek(16)
        bc7_data = f.read(bc7_size)

    decoded = texture2ddecoder.decode_bc7(bc7_data, width, decode_height)
    img = Image.frombytes("RGBA", (width, decode_height), decoded)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (b, g, r, a))

    if decode_height > height:
        img = img.crop((0, decode_height - height, width, decode_height))

    return img


# --- Loading screen extraction ---

def find_loading_textures():
    """Scan DLC directories for TEXTURE_lsl_* files of the expected size.

    Returns dict mapping texture suffix → full file path.
    E.g. {"augustus": "/path/to/TEXTURE_lsl_augustus", ...}
    """
    pattern = os.path.join(
        GAME_DLC_DIR, "*-shell", "Platforms", "Mac", "BLPs",
        "SHARED_DATA", "TEXTURE_lsl_*"
    )
    found = {}
    for path in glob.glob(pattern):
        size = os.path.getsize(path)
        if size != CIVBIG_LOADING_EXPECTED_SIZE:
            continue
        name = os.path.basename(path)  # TEXTURE_lsl_augustus
        suffix = name[len("TEXTURE_lsl_"):]  # augustus
        found[suffix] = path
    return found


def extract_loading_originals(config, force=False):
    """Extract original loading screen images from game BLP files.

    Saves to assets/leaders/{icon_key}/loading_original.png
    and assets/leaders/{icon_key}/{persona_key}_loading_original.png for alts.
    """
    textures = find_loading_textures()
    if not textures:
        print(f"ERROR: No loading screen textures found in {GAME_DLC_DIR}")
        print("  Make sure the game is installed.")
        return

    print(f"Found {len(textures)} loading screen textures in game files\n")

    extracted = 0
    skipped = 0
    missing = []

    for leader in config["leaders"]:
        icon_key = leader["icon_key"]
        tex_name = TEXTURE_NAME_OVERRIDES.get(icon_key, icon_key)

        # Base loading screen
        dest = os.path.join(ASSETS_DIR, "leaders", icon_key, "loading_original.png")
        if os.path.isfile(dest) and not force:
            print(f"  SKIP  {icon_key} (already exists)")
            skipped += 1
        elif tex_name in textures:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            img = decode_civbig(textures[tex_name], LOADING_SCREEN_WIDTH, LOADING_SCREEN_HEIGHT)
            img.save(dest, "PNG")
            size_kb = os.path.getsize(dest) / 1024
            print(f"  OK    {icon_key} ({size_kb:.0f} KB)")
            extracted += 1
        else:
            print(f"  MISS  {icon_key} (no TEXTURE_lsl_{tex_name})")
            missing.append(icon_key)

        # Persona alt loading screens
        for persona in leader.get("personas", []):
            ptype = persona["type"]
            if ptype not in PERSONA_ALT_TEXTURES:
                continue
            alt_tex = PERSONA_ALT_TEXTURES[ptype]
            pkey = persona_key(leader["type"], ptype)
            dest = os.path.join(
                ASSETS_DIR, "leaders", icon_key,
                f"{pkey}_loading_original.png"
            )
            display = f"{icon_key}/{pkey}"
            if os.path.isfile(dest) and not force:
                print(f"  SKIP  {display} (already exists)")
                skipped += 1
            elif alt_tex in textures:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                img = decode_civbig(textures[alt_tex], LOADING_SCREEN_WIDTH, LOADING_SCREEN_HEIGHT)
                img.save(dest, "PNG")
                size_kb = os.path.getsize(dest) / 1024
                print(f"  OK    {display} ({size_kb:.0f} KB)")
                extracted += 1
            else:
                print(f"  MISS  {display} (no TEXTURE_lsl_{alt_tex})")
                missing.append(display)

    print(f"\nLoading originals: extracted {extracted}, skipped {skipped}, "
          f"missing {len(missing)}")
    if missing:
        print(f"  Not found: {', '.join(missing)}")


# --- Icon extraction ---

def find_icon_texture(tex_name, shape, size, suffix):
    """Find a single icon texture file in any DLC shell directory.

    Returns full path or None.
    """
    fname = f"TEXTURE_lp_{shape}_{tex_name}_{size}{suffix}"
    pattern = os.path.join(
        GAME_DLC_DIR, "*-shell", "Platforms", "Mac", "BLPs",
        "SHARED_DATA", fname
    )
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def extract_icon_originals(config, force=False):
    """Extract original icon images from game BLP files.

    Saves 8 variants per leader to authentic-leaders/icons/{icon_key}/.
    Also extracts alt/persona icons using PERSONA_ALT_TEXTURES mapping.

    Each variant is extracted directly from its own game texture via
    level-0 BC7 decoding at byte 16. Hex and circ textures contain
    different portrait crops (hex = wider head+shoulders bottom-aligned,
    circ = tight head-shot centered), so each must come from its
    own source file.
    """
    mod_icons_dir = os.path.join(PROJECT_ROOT, "authentic-leaders", "icons")

    extracted = 0
    skipped = 0
    missing_leaders = []

    def extract_leader_icons(tex_name, icon_name, dest_dir):
        """Extract all 8 icon variants for a single leader/persona."""
        nonlocal extracted, skipped
        count = 0
        miss = 0
        for v in ICON_EXTRACT_VARIANTS:
            out_name = (
                f"lp_{v['shape']}_{icon_name}"
                f"_{v['size']}{v['suffix']}.png"
            )
            dest = os.path.join(dest_dir, out_name)

            if os.path.isfile(dest) and not force:
                skipped += 1
                continue

            tex_path = find_icon_texture(
                tex_name, v["shape"], v["size"], v["suffix"]
            )
            if tex_path is None:
                miss += 1
                continue

            # Hex textures have 45/32 aspect ratio (taller than wide)
            out_h = v["size"] * 45 // 32 if v["shape"] == "hex" else v["size"]
            img = decode_civbig(tex_path, v["size"], out_h)
            os.makedirs(dest_dir, exist_ok=True)
            img.save(dest, "PNG")
            extracted += 1
            count += 1
        return count, miss

    for leader in config["leaders"]:
        icon_key = leader["icon_key"]
        tex_name = TEXTURE_NAME_OVERRIDES.get(icon_key, icon_key)
        dest_dir = os.path.join(mod_icons_dir, icon_key)

        count, miss = extract_leader_icons(tex_name, icon_key, dest_dir)
        if count > 0:
            msg = f"  OK    {icon_key} ({count} icons)"
            if miss:
                msg += f" ({miss} missing)"
            print(msg)
        elif miss == len(ICON_EXTRACT_VARIANTS):
            missing_leaders.append(icon_key)
            print(f"  MISS  {icon_key} (no textures found)")

        # Extract alt/persona icons
        for persona in leader.get("personas", []):
            ptype = persona["type"]
            if ptype not in PERSONA_ALT_TEXTURES:
                continue
            alt_tex_name = PERSONA_ALT_TEXTURES[ptype]

            count, miss = extract_leader_icons(
                alt_tex_name, alt_tex_name, dest_dir
            )
            if count > 0:
                msg = f"  OK    {icon_key}/{alt_tex_name} ({count} alt icons)"
                if miss:
                    msg += f" ({miss} missing)"
                print(msg)

    print(f"\nIcon originals: extracted {extracted}, skipped {skipped}, "
          f"missing leaders {len(missing_leaders)}")
    if missing_leaders:
        print(f"  Not found: {', '.join(missing_leaders)}")


# --- Background extraction ---

def find_bg_textures():
    """Scan DLC directories for TEXTURE_lsbg_* files.

    Returns dict mapping texture suffix → {resolution: full_path}.
    E.g. {"rome": {"1080": "/path/to/TEXTURE_lsbg_rome_1080", "720": "..."}}
    """
    pattern = os.path.join(
        GAME_DLC_DIR, "*-shell", "Platforms", "Mac", "BLPs",
        "SHARED_DATA", "TEXTURE_lsbg_*"
    )
    found = {}
    for path in glob.glob(pattern):
        name = os.path.basename(path)  # TEXTURE_lsbg_rome_1080
        rest = name[len("TEXTURE_lsbg_"):]  # rome_1080
        # Split off resolution suffix (_1080 or _720)
        if rest.endswith("_1080"):
            civ_name = rest[:-5]
            res = "1080"
        elif rest.endswith("_720"):
            civ_name = rest[:-4]
            res = "720"
        else:
            continue
        if civ_name not in found:
            found[civ_name] = {}
        found[civ_name][res] = path
    return found


def extract_backgrounds(config, force=False):
    """Extract civilization background images from game BLP files.

    Saves to assets/civilizations/{civ_key}/background_1080.png and background_720.png.
    """
    textures = find_bg_textures()
    if not textures:
        print(f"ERROR: No background textures found in {GAME_DLC_DIR}")
        print("  Make sure the game is installed.")
        return

    print(f"Found {len(textures)} civ background texture sets in game files\n")

    # Collect all civs from config
    all_civs = []
    for age in config["ages"].values():
        for civ in age["civilizations"]:
            all_civs.append(civ)

    extracted = 0
    skipped = 0
    missing = []

    for civ in all_civs:
        civ_key = civ["civ_key"]
        tex_name = BG_TEXTURE_NAME_OVERRIDES.get(civ_key, civ_key)
        dest_dir = os.path.join(ASSETS_DIR, "civilizations", civ_key)

        if tex_name not in textures:
            print(f"  MISS  {civ_key} (no TEXTURE_lsbg_{tex_name}_*)")
            missing.append(civ_key)
            continue

        for res, (width, height, expected_size) in [
            ("1080", (BG_1080_WIDTH, BG_1080_HEIGHT, CIVBIG_BG_1080_EXPECTED_SIZE)),
            ("720", (BG_720_WIDTH, BG_720_HEIGHT, CIVBIG_BG_720_EXPECTED_SIZE)),
        ]:
            dest = os.path.join(dest_dir, f"background_{res}.png")
            display = f"{civ_key}/{res}"

            if os.path.isfile(dest) and not force:
                skipped += 1
                continue

            if res not in textures[tex_name]:
                print(f"  MISS  {display} (no {res} variant)")
                continue

            tex_path = textures[tex_name][res]
            file_size = os.path.getsize(tex_path)

            # Some DLC files may have unexpected sizes; decode anyway
            if file_size != expected_size:
                print(f"  WARN  {display}: unexpected file size "
                      f"{file_size} (expected {expected_size})")

            os.makedirs(dest_dir, exist_ok=True)
            img = decode_civbig(tex_path, width, height)
            img.save(dest, "PNG")
            size_kb = os.path.getsize(dest) / 1024
            extracted += 1

        # Print status for this civ (both resolutions done)
        has_1080 = os.path.isfile(os.path.join(dest_dir, "background_1080.png"))
        has_720 = os.path.isfile(os.path.join(dest_dir, "background_720.png"))
        if has_1080 and has_720:
            print(f"  OK    {civ_key}")

    print(f"\nBackgrounds: extracted {extracted}, skipped {skipped}, "
          f"missing {len(missing)}")
    if missing:
        print(f"  Not found: {', '.join(missing)}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract leader assets from Civ7 game BLP/CIVBIG files"
    )
    parser.add_argument("--loading", action="store_true",
                        help="Extract loading screen images")
    parser.add_argument("--icons", action="store_true",
                        help="Extract leader icon images")
    parser.add_argument("--backgrounds", action="store_true",
                        help="Extract civilization background images")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract existing files")
    args = parser.parse_args()

    if not args.loading and not args.icons and not args.backgrounds:
        args.loading = True
        args.icons = True
        args.backgrounds = True

    config = load_config()

    if args.loading:
        extract_loading_originals(config, force=args.force)

    if args.icons:
        extract_icon_originals(config, force=args.force)

    if args.backgrounds:
        extract_backgrounds(config, force=args.force)


if __name__ == "__main__":
    main()
