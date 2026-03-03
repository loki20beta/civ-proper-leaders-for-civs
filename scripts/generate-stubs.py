#!/usr/bin/env python3
"""Generate stub loading screens and icons for all leader×civ pairs.

Takes leader reference images from assets/leaders/{icon_key}/reference.png,
produces civ-specific loading screens and icon variants with civ name overlaid.

Output goes to authentic-leaders/images/loading/ and authentic-leaders/icons/
matching the existing mod directory structure.

Usage:
    python3 generate-stubs.py                    # all leaders × all civs
    python3 generate-stubs.py --leader augustus   # one leader × all civs
    python3 generate-stubs.py --civ rome         # all leaders × one civ
    python3 generate-stubs.py --dry-run          # preview without writing
    python3 generate-stubs.py --force            # overwrite existing stubs
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
MOD_DIR = os.path.join(PROJECT_ROOT, "authentic-leaders")

LOADING_SCREEN_SIZE = (1230, 1520)

ICON_VARIANTS = [
    {"shape": "hex",  "size": 256, "suffix": ""},
    {"shape": "hex",  "size": 128, "suffix": ""},
    {"shape": "hex",  "size": 128, "suffix": "_h", "tint": (255, 200, 50)},
    {"shape": "hex",  "size": 128, "suffix": "_a", "tint": (200, 50, 50)},
    {"shape": "hex",  "size": 64,  "suffix": ""},
    {"shape": "circ", "size": 256, "suffix": ""},
    {"shape": "circ", "size": 128, "suffix": ""},
    {"shape": "circ", "size": 64,  "suffix": ""},
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_font(size):
    """Get a font at the given size."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


# --- Loading screen generation ---


def make_base_loading(reference_img):
    """Scale/crop reference image to loading screen dimensions (1230×1520).

    The game CSS clips the top 100px of the image (margin-top: -5.56rem).
    We place the reference image below that clip zone so the head is visible,
    and crop excess from the bottom (lower body/legs).
    """
    target_w, target_h = LOADING_SCREEN_SIZE
    # Game clips top ~100px. Place image below that with a small margin.
    GAME_TOP_CLIP = 120  # px of padding above the reference image

    src_w, src_h = reference_img.size

    # Scale to fill target width
    scale = target_w / src_w
    new_w = target_w
    new_h = int(src_h * scale)

    resized = reference_img.resize((new_w, new_h), Image.LANCZOS)

    # Create canvas with dark background matching game color (#161c23)
    canvas = Image.new("RGBA", (target_w, target_h), (22, 28, 35, 255))

    # Center horizontally (already fills width), place below clip zone vertically
    if resized.mode == "RGBA":
        canvas.paste(resized, (0, GAME_TOP_CLIP), resized)
    else:
        canvas.paste(resized, (0, GAME_TOP_CLIP))

    return canvas


def overlay_loading_text(base_img, text):
    """Overlay civ name banner on loading screen at waist level."""
    img = base_img.copy()
    w, h = img.size

    font = get_font(48)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Banner at ~47% from top (waist area, matching existing Augustus stubs)
    padding = 16
    banner_h = text_h + padding * 2
    banner_y = int(h * 0.47) - banner_h // 2

    # Semi-transparent dark banner
    banner = Image.new("RGBA", img.size, (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner)
    banner_draw.rectangle(
        [0, banner_y, w, banner_y + banner_h],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img, banner)

    # Centered white text
    draw = ImageDraw.Draw(img)
    text_x = (w - text_w) // 2
    text_y = banner_y + padding
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

    return img


# --- Icon generation ---


def create_hex_mask(size):
    """Create a hexagonal mask."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = size // 2, size // 2
    r = size // 2 - 2
    points = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=255)
    return mask


def create_circle_mask(size):
    """Create a circular mask."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([2, 2, size - 3, size - 3], fill=255)
    return mask


def crop_center_square(img):
    """Crop the largest centered square from an image."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def apply_tint(img, tint_color, strength=0.15):
    """Apply a subtle color tint."""
    tint = Image.new("RGBA", img.size, tint_color + (int(255 * strength),))
    return Image.alpha_composite(img.convert("RGBA"), tint)


def make_base_icon(reference_img, shape, size, tint=None):
    """Create a masked icon from reference image."""
    squared = crop_center_square(reference_img)
    resized = squared.resize((size, size), Image.LANCZOS)

    if tint:
        resized = apply_tint(resized, tint)

    mask = create_hex_mask(size) if shape == "hex" else create_circle_mask(size)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(resized, (0, 0), mask)
    return result


def overlay_icon_text(icon_img, text, icon_size):
    """Overlay civ name text on an icon with dark banner."""
    img = icon_img.copy()
    draw = ImageDraw.Draw(img)

    if icon_size >= 256:
        font_size = 24
    elif icon_size >= 128:
        font_size = 14
    else:
        font_size = 9

    font = get_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = max(2, icon_size // 32)
    banner_h = text_h + padding * 2
    banner_y = icon_size - banner_h - (icon_size // 8)

    banner = Image.new("RGBA", img.size, (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner)
    banner_draw.rectangle(
        [0, banner_y, icon_size, banner_y + banner_h],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img, banner)

    draw = ImageDraw.Draw(img)
    text_x = (icon_size - text_w) // 2
    text_y = banner_y + padding
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

    return img


# --- Civ label helpers ---


def civ_label(civ_key):
    """Full uppercase label for a civ key."""
    return civ_key.upper().replace("_", " ")


def civ_abbrev(civ_key):
    """3-letter abbreviation for 64px icons."""
    # Special cases for multi-word keys
    abbrevs = {
        "dai_viet": "DAI",
        "french_empire": "FRE",
        "mississippian": "MIS",
        "pirates": "PIR",
    }
    if civ_key in abbrevs:
        return abbrevs[civ_key]
    return civ_key[:3].upper()


# --- Main generation ---


def load_portrait_sources(icon_key, fallback_img):
    """Load portrait images for icon generation.

    Returns dict mapping mood → PIL Image. Falls back to the reference
    image (with tint for happy/angry) when portrait files aren't available.
    """
    sources = {}
    for mood in ("neutral", "happy", "angry"):
        portrait_path = os.path.join(ASSETS_DIR, "leaders", icon_key, f"portrait_{mood}.png")
        if os.path.isfile(portrait_path):
            sources[mood] = Image.open(portrait_path).convert("RGBA")
        else:
            sources[mood] = None
    return sources


def generate_leader_stubs(leader, civs, dry_run=False, force=False):
    """Generate all stubs for one leader across given civs.

    Returns (loading_count, icon_count, skipped_count).
    """
    icon_key = leader["icon_key"]
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")

    if not os.path.isfile(ref_path):
        print(f"  SKIP {icon_key} (no reference image)")
        return 0, 0, 0

    reference = Image.open(ref_path).convert("RGBA")
    base_loading = make_base_loading(reference)

    # Load portrait images for icons (proper game portraits, not three-quarter refs)
    portraits = load_portrait_sources(icon_key, reference)
    has_portraits = portraits["neutral"] is not None

    # Pre-generate base icons for all variants
    base_icons = {}
    for v in ICON_VARIANTS:
        key = (v["shape"], v["size"], v["suffix"])
        # Select source image: use proper portrait when available
        if v["suffix"] == "_h" and portraits["happy"] is not None:
            source = portraits["happy"]
            tint = None  # real happy portrait, no fake tint needed
        elif v["suffix"] == "_a" and portraits["angry"] is not None:
            source = portraits["angry"]
            tint = None  # real angry portrait, no fake tint needed
        elif portraits["neutral"] is not None:
            source = portraits["neutral"]
            tint = None
        else:
            source = reference
            tint = v.get("tint")
        base_icons[key] = make_base_icon(source, v["shape"], v["size"], tint)

    loading_count = 0
    icon_count = 0
    skipped = 0

    for civ_key in civs:
        label = civ_label(civ_key)
        abbrev = civ_abbrev(civ_key)

        # --- Loading screen ---
        loading_path = os.path.join(
            MOD_DIR, "images", "loading", f"lsl_{icon_key}_{civ_key}.png"
        )
        if os.path.isfile(loading_path) and not force:
            skipped += 1
        elif dry_run:
            print(f"  WOULD loading: {icon_key}/{civ_key}")
            loading_count += 1
        else:
            os.makedirs(os.path.dirname(loading_path), exist_ok=True)
            stub = overlay_loading_text(base_loading, label)
            stub.save(loading_path, "PNG")
            loading_count += 1

        # --- Icons ---
        for v in ICON_VARIANTS:
            vkey = (v["shape"], v["size"], v["suffix"])
            out_name = (
                f"lp_{v['shape']}_{icon_key}_{civ_key}"
                f"_{v['size']}{v['suffix']}.png"
            )
            icon_path = os.path.join(
                MOD_DIR, "icons", icon_key, civ_key, out_name
            )
            if os.path.isfile(icon_path) and not force:
                skipped += 1
                continue

            icon_label = abbrev if v["size"] <= 64 else label
            if dry_run:
                icon_count += 1
            else:
                os.makedirs(os.path.dirname(icon_path), exist_ok=True)
                stub = overlay_icon_text(base_icons[vkey], icon_label, v["size"])
                stub.save(icon_path, "PNG")
                icon_count += 1

    return loading_count, icon_count, skipped


def generate_base_icons(leader, dry_run=False, force=False):
    """Generate default (non-civ-specific) icons for a leader from portrait images.

    Returns count of icons generated.
    """
    icon_key = leader["icon_key"]
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")

    if not os.path.isfile(ref_path):
        return 0

    reference = Image.open(ref_path).convert("RGBA")
    portraits = load_portrait_sources(icon_key, reference)
    count = 0

    for v in ICON_VARIANTS:
        fname = f"lp_{v['shape']}_{icon_key}_{v['size']}{v['suffix']}.png"
        icon_path = os.path.join(MOD_DIR, "icons", icon_key, fname)

        if os.path.isfile(icon_path) and not force:
            continue

        if v["suffix"] == "_h" and portraits["happy"] is not None:
            source = portraits["happy"]
            tint = None
        elif v["suffix"] == "_a" and portraits["angry"] is not None:
            source = portraits["angry"]
            tint = None
        elif portraits["neutral"] is not None:
            source = portraits["neutral"]
            tint = None
        else:
            source = reference
            tint = v.get("tint")

        if dry_run:
            count += 1
            continue

        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
        icon = make_base_icon(source, v["shape"], v["size"], tint)
        icon.save(icon_path, "PNG")
        count += 1

    return count


def generate_base_loading(leader, dry_run=False, force=False):
    """Generate the default (non-civ-specific) loading screen for a leader.

    Returns 1 if generated, 0 if skipped.
    """
    icon_key = leader["icon_key"]
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")

    if not os.path.isfile(ref_path):
        return 0

    loading_path = os.path.join(MOD_DIR, "images", "loading", f"lsl_{icon_key}.png")
    if os.path.isfile(loading_path) and not force:
        return 0

    if dry_run:
        return 1

    reference = Image.open(ref_path).convert("RGBA")
    base_loading = make_base_loading(reference)
    os.makedirs(os.path.dirname(loading_path), exist_ok=True)
    base_loading.save(loading_path, "PNG")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="Generate stub loading screens and icons for all leader×civ pairs"
    )
    parser.add_argument("--leader", help="Generate for one leader only")
    parser.add_argument("--civ", help="Generate for one civ only")
    parser.add_argument("--base-only", action="store_true",
                        help="Only generate base icons and loading screens (no civ stubs)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing stubs")
    args = parser.parse_args()

    config = load_config()

    # Build leader list
    if args.leader:
        leaders = [l for l in config["leaders"] if l["icon_key"] == args.leader]
        if not leaders:
            print(f"Error: unknown leader key '{args.leader}'")
            sys.exit(1)
    else:
        leaders = config["leaders"]

    # Generate base icons and loading screens for selected leaders
    print(f"Generating base icons/loading for {len(leaders)} leaders...")
    base_icon_total = 0
    base_loading_total = 0
    for leader in leaders:
        ic = generate_base_icons(leader, dry_run=args.dry_run, force=args.force)
        lc = generate_base_loading(leader, dry_run=args.dry_run, force=args.force)
        if ic or lc:
            action = "Would create" if args.dry_run else "Created"
            print(f"  {leader['icon_key']}: {action} {ic} base icons + {lc} loading")
        base_icon_total += ic
        base_loading_total += lc
    action = "Would create" if args.dry_run else "Created"
    print(f"Base: {action} {base_icon_total} icons + {base_loading_total} loading screens\n")

    if args.base_only:
        if not args.dry_run and (base_icon_total or base_loading_total):
            print("Run 'python3 scripts/generate-mod-data.py' to update mod data.")
        return

    # Build civ list
    all_civs = []
    for age_data in config["ages"].values():
        for civ in age_data["civilizations"]:
            all_civs.append(civ["civ_key"])

    if args.civ:
        if args.civ not in all_civs:
            print(f"Error: unknown civ key '{args.civ}'")
            sys.exit(1)
        civs = [args.civ]
    else:
        civs = all_civs

    print(f"Generating civ stubs: {len(leaders)} leaders × {len(civs)} civs")
    print(f"  = {len(leaders) * len(civs)} pairs")
    print(f"  = {len(leaders) * len(civs)} loading screens + "
          f"{len(leaders) * len(civs) * len(ICON_VARIANTS)} icons")
    print()

    total_loading = 0
    total_icons = 0
    total_skipped = 0

    for leader in leaders:
        lc, ic, sk = generate_leader_stubs(
            leader, civs, dry_run=args.dry_run, force=args.force
        )
        if lc or ic:
            action = "Would create" if args.dry_run else "Created"
            print(f"  {leader['icon_key']}: {action} {lc} loading + {ic} icons")
        elif sk:
            print(f"  {leader['icon_key']}: skipped {sk} (already exist)")
        total_loading += lc
        total_icons += ic
        total_skipped += sk

    action = "Would create" if args.dry_run else "Created"
    print(f"\nTotal: {action} {total_loading} loading screens + {total_icons} icons"
          f" (skipped {total_skipped})")

    if not args.dry_run and (total_loading or total_icons):
        print("\nRun 'python3 scripts/generate-mod-data.py' to update mod data.")


if __name__ == "__main__":
    main()
