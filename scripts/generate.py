#!/usr/bin/env python3
"""Generate loading screens and icons for all leader×civ pairs.

Takes leader reference images from assets/leaders/{icon_key}/reference.png
and base icons from assets/leaders/{icon_key}/icons/,
produces civ-specific loading screens and icon variants.

With --stub: overlays civ name text on base images (placeholder mode).
Without --stub: AI artwork mode (not yet implemented).

Output goes to authentic-leaders/images/loading/ and authentic-leaders/icons/
matching the existing mod directory structure.

Usage:
    python3 generate.py --stub                       # all leaders × all civs
    python3 generate.py --stub --leader augustus      # one leader × all civs
    python3 generate.py --stub --civ rome            # all leaders × one civ
    python3 generate.py --stub --dry-run             # preview without writing
    python3 generate.py --stub --force               # overwrite existing stubs
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

LOADING_SCREEN_SIZE = (800, 1060)

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
    """Scale/crop reference image to loading screen dimensions (800×1060).

    Original game loading screens are 800×1060 RGBA with transparent background.
    The game composites them over the civ scene via CSS background-image.
    We match this: scale to fit width, top-align, transparent background.
    """
    target_w, target_h = LOADING_SCREEN_SIZE

    src_w, src_h = reference_img.size

    # Scale to fill target width
    scale = target_w / src_w
    new_w = target_w
    new_h = int(src_h * scale)

    resized = reference_img.resize((new_w, new_h), Image.LANCZOS)

    # Create transparent canvas (matching game's RGBA format)
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    # Place portrait at top; bottom excess is cropped by canvas boundary
    if resized.mode == "RGBA":
        canvas.paste(resized, (0, 0), resized)
    else:
        canvas.paste(resized, (0, 0))

    return canvas


def overlay_loading_text(base_img, text):
    """Overlay civ name banner on loading screen at waist level."""
    img = base_img.copy()
    w, h = img.size

    font = get_font(31)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Banner at ~47% from top (waist area, matching existing Augustus stubs)
    padding = 10
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


def create_hex_mask(width, height):
    """Create a hexagonal mask for a rectangular canvas."""
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = width // 2, height // 2
    rx = width // 2 - 2
    ry = height // 2 - 2
    points = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        x = cx + rx * math.cos(angle)
        y = cy + ry * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=255)
    return mask


def create_circle_mask(size):
    """Create a circular mask."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([2, 2, size - 3, size - 3], fill=255)
    return mask


def crop_center_rect(img, target_w, target_h):
    """Crop the largest centered rectangle with given aspect ratio from an image."""
    w, h = img.size
    # Find largest crop matching target aspect ratio
    crop_w = min(w, int(h * target_w / target_h))
    crop_h = min(h, int(w * target_h / target_w))
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    return img.crop((left, top, left + crop_w, top + crop_h))


def apply_tint(img, tint_color, strength=0.15):
    """Apply a subtle color tint."""
    tint = Image.new("RGBA", img.size, tint_color + (int(255 * strength),))
    return Image.alpha_composite(img.convert("RGBA"), tint)


def make_base_icon(reference_img, shape, size, tint=None):
    """Create a masked icon from reference image."""
    height = size * 45 // 32 if shape == "hex" else size
    cropped = crop_center_rect(reference_img, size, height)
    resized = cropped.resize((size, height), Image.LANCZOS)

    if tint:
        resized = apply_tint(resized, tint)

    mask = create_hex_mask(size, height) if shape == "hex" else create_circle_mask(size)
    result = Image.new("RGBA", (size, height), (0, 0, 0, 0))
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
    img_h = img.size[1]
    banner_y = img_h - banner_h - (img_h // 8)

    banner = Image.new("RGBA", img.size, (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner)
    banner_draw.rectangle(
        [0, banner_y, img.size[0], banner_y + banner_h],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img, banner)

    draw = ImageDraw.Draw(img)
    text_x = (img.size[0] - text_w) // 2
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

    If portrait_neutral is missing, all portraits are set to None so icons
    use the reference consistently (avoids body-shot vs head-shot mismatch).
    """
    sources = {}
    for mood in ("neutral", "happy", "angry"):
        portrait_path = os.path.join(ASSETS_DIR, "leaders", icon_key, f"portrait_{mood}.png")
        if os.path.isfile(portrait_path):
            sources[mood] = Image.open(portrait_path).convert("RGBA")
        else:
            sources[mood] = None

    # If neutral is missing, don't use happy/angry either — the framing
    # mismatch between reference (body) and portraits (head) looks wrong.
    if sources["neutral"] is None:
        sources["happy"] = None
        sources["angry"] = None

    return sources


def generate_leader_stubs(leader, civs, dry_run=False, force=False):
    """Generate all stubs for one leader across given civs.

    Uses extracted game icons/loading screens as base when available.
    Falls back to reference/portrait images only when extracted assets
    are missing.

    Returns (loading_count, icon_count, skipped_count).
    """
    icon_key = leader["icon_key"]

    # Load base loading screen: prefer the mod's base loading screen (already
    # generated by generate_base_loading), then extracted original, then reference.
    # The base loading screen has the correct full-body image needed for ESC screen.
    base_loading_path = os.path.join(
        MOD_DIR, "images", "loading", f"lsl_{icon_key}.png"
    )
    loading_original_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "loading_original.png")
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")

    if os.path.isfile(base_loading_path):
        base_loading = Image.open(base_loading_path).convert("RGBA")
    elif os.path.isfile(loading_original_path):
        base_loading = Image.open(loading_original_path).convert("RGBA")
    elif os.path.isfile(ref_path):
        reference = Image.open(ref_path).convert("RGBA")
        base_loading = make_base_loading(reference)
    else:
        base_loading = None

    # Load base icons from assets/leaders/{icon_key}/icons/
    base_icons = {}
    for v in ICON_VARIANTS:
        key = (v["shape"], v["size"], v["suffix"])
        extracted_path = os.path.join(
            ASSETS_DIR, "leaders", icon_key, "icons",
            f"lp_{v['shape']}_{icon_key}_{v['size']}{v['suffix']}.png"
        )
        if os.path.isfile(extracted_path):
            base_icons[key] = Image.open(extracted_path).convert("RGBA")

    # Fall back to portrait/reference for any missing icon variants
    missing_keys = [
        (v["shape"], v["size"], v["suffix"])
        for v in ICON_VARIANTS
        if (v["shape"], v["size"], v["suffix"]) not in base_icons
    ]
    if missing_keys:
        if os.path.isfile(ref_path):
            reference = Image.open(ref_path).convert("RGBA")
        else:
            reference = None
        portraits = load_portrait_sources(icon_key, reference) if reference else {}
        for v in ICON_VARIANTS:
            key = (v["shape"], v["size"], v["suffix"])
            if key in base_icons:
                continue
            if reference is None:
                continue
            if v["suffix"] == "_h" and portraits.get("happy") is not None:
                source = portraits["happy"]
                tint = None
            elif v["suffix"] == "_a" and portraits.get("angry") is not None:
                source = portraits["angry"]
                tint = None
            elif portraits.get("neutral") is not None:
                source = portraits["neutral"]
                tint = None
            else:
                source = reference
                tint = v.get("tint")
            base_icons[key] = make_base_icon(source, v["shape"], v["size"], tint)

    # Load persona base loading screens and icons
    persona_loadings = {}  # pkey -> PIL Image
    persona_icons = {}     # pkey -> {(shape, size, suffix) -> PIL Image}
    for pkey, _ptype in get_persona_keys(leader):
        # Persona loading screen
        alt_loading_path = os.path.join(
            MOD_DIR, "images", "loading", f"lsl_{icon_key}_{pkey}.png"
        )
        alt_original_path = os.path.join(
            ASSETS_DIR, "leaders", icon_key, f"{pkey}_loading_original.png"
        )
        if os.path.isfile(alt_loading_path):
            persona_loadings[pkey] = Image.open(alt_loading_path).convert("RGBA")
        elif os.path.isfile(alt_original_path):
            persona_loadings[pkey] = Image.open(alt_original_path).convert("RGBA")

        # Persona icons
        p_icons = {}
        for v in ICON_VARIANTS:
            vk = (v["shape"], v["size"], v["suffix"])
            extracted = os.path.join(
                ASSETS_DIR, "leaders", icon_key, "icons",
                f"lp_{v['shape']}_{icon_key}_{pkey}_{v['size']}{v['suffix']}.png"
            )
            if os.path.isfile(extracted):
                p_icons[vk] = Image.open(extracted).convert("RGBA")
        if p_icons:
            persona_icons[pkey] = p_icons

    if not base_icons and base_loading is None and not persona_loadings and not persona_icons:
        print(f"  SKIP {icon_key} (no extracted icons or reference image)")
        return 0, 0, 0

    loading_count = 0
    icon_count = 0
    skipped = 0

    for civ_key in civs:
        label = civ_label(civ_key)
        abbrev = civ_abbrev(civ_key)

        # --- Base loading screen ---
        if base_loading is not None:
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

        # --- Persona loading screens ---
        for pkey, _ptype in get_persona_keys(leader):
            if pkey not in persona_loadings:
                continue
            alt_civ_path = os.path.join(
                MOD_DIR, "images", "loading",
                f"lsl_{icon_key}_{pkey}_{civ_key}.png"
            )
            if os.path.isfile(alt_civ_path) and not force:
                skipped += 1
            elif dry_run:
                print(f"  WOULD loading: {icon_key}/{pkey}/{civ_key}")
                loading_count += 1
            else:
                os.makedirs(os.path.dirname(alt_civ_path), exist_ok=True)
                stub = overlay_loading_text(persona_loadings[pkey], label)
                stub.save(alt_civ_path, "PNG")
                loading_count += 1

        # --- Base icons ---
        for v in ICON_VARIANTS:
            vkey = (v["shape"], v["size"], v["suffix"])
            if vkey not in base_icons:
                continue
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

        # --- Persona civ-specific icons ---
        for pkey, _ptype in get_persona_keys(leader):
            if pkey not in persona_icons:
                continue
            for v in ICON_VARIANTS:
                vkey = (v["shape"], v["size"], v["suffix"])
                if vkey not in persona_icons[pkey]:
                    continue
                out_name = (
                    f"lp_{v['shape']}_{icon_key}_{pkey}_{civ_key}"
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
                    stub = overlay_icon_text(
                        persona_icons[pkey][vkey], icon_label, v["size"]
                    )
                    stub.save(icon_path, "PNG")
                    icon_count += 1

    return loading_count, icon_count, skipped


def copy_icons_to_mod(icon_key, dry_run=False):
    """Copy all icon files from assets to mod dir for runtime use.

    Copies both base icons (lp_*_{key}_*) and alt icons (lp_*_{key}_alt_*)
    including extensionless duplicates.
    Returns count of files copied.
    """
    src_dir = os.path.join(ASSETS_DIR, "leaders", icon_key, "icons")
    dst_dir = os.path.join(MOD_DIR, "icons", icon_key)

    if not os.path.isdir(src_dir):
        return 0

    import shutil
    count = 0
    for fname in os.listdir(src_dir):
        if not fname.startswith("lp_"):
            continue
        src = os.path.join(src_dir, fname)
        dst = os.path.join(dst_dir, fname)
        if os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        if dry_run:
            count += 1
            continue
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    return count


def get_persona_keys(leader):
    """Extract persona short keys from leader config.

    Returns list of (persona_key, persona_type) tuples.
    e.g. [("alt", "LEADER_ASHOKA_ALT")]
    """
    results = []
    icon_key = leader["icon_key"]
    for persona in leader.get("personas", []):
        ptype = persona["type"]
        # Derive short key: LEADER_ASHOKA_ALT -> alt (strip LEADER_{ICON_KEY}_ prefix)
        prefix = f"LEADER_{icon_key.upper()}_"
        if ptype.startswith(prefix):
            pkey = ptype[len(prefix):].lower()
        else:
            pkey = ptype.replace("LEADER_", "").lower()
        results.append((pkey, ptype))
    return results


def generate_base_icons(leader, dry_run=False, force=False):
    """Generate default (non-civ-specific) icons for a leader from portrait images.

    Writes to assets/leaders/{icon_key}/icons/ (the canonical base icon location).
    Skips icons that already exist (e.g., extracted from game BLP files).
    Returns count of icons generated.
    """
    icon_key = leader["icon_key"]
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")

    if not os.path.isfile(ref_path):
        return 0

    reference = Image.open(ref_path).convert("RGBA")
    portraits = load_portrait_sources(icon_key, reference)
    count = 0

    icons_dir = os.path.join(ASSETS_DIR, "leaders", icon_key, "icons")

    for v in ICON_VARIANTS:
        fname = f"lp_{v['shape']}_{icon_key}_{v['size']}{v['suffix']}.png"
        icon_path = os.path.join(icons_dir, fname)

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

        os.makedirs(icons_dir, exist_ok=True)
        icon = make_base_icon(source, v["shape"], v["size"], tint)
        icon.save(icon_path, "PNG")
        count += 1

    return count


def generate_base_loading(leader, dry_run=False, force=False):
    """Generate the default (non-civ-specific) loading screen for a leader.

    Generates base loading screen and persona loading screens.
    Writes to both mod dir and assets dir.
    Returns count of loading screens generated.
    """
    icon_key = leader["icon_key"]
    ref_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")
    count = 0

    # --- Base loading screen ---
    loading_original_path = os.path.join(ASSETS_DIR, "leaders", icon_key, "loading_original.png")
    has_source = os.path.isfile(loading_original_path) or os.path.isfile(ref_path)
    if not has_source:
        return 0

    mod_path = os.path.join(MOD_DIR, "images", "loading", f"lsl_{icon_key}.png")
    asset_path = os.path.join(ASSETS_DIR, "leaders", icon_key, f"lsl_{icon_key}.png")
    need_mod = not os.path.isfile(mod_path) or force
    need_asset = not os.path.isfile(asset_path) or force

    if need_mod or need_asset:
        if dry_run:
            count += 1
        else:
            if os.path.isfile(loading_original_path):
                base_loading = Image.open(loading_original_path).convert("RGBA")
            else:
                reference = Image.open(ref_path).convert("RGBA")
                base_loading = make_base_loading(reference)

            if need_mod:
                os.makedirs(os.path.dirname(mod_path), exist_ok=True)
                base_loading.save(mod_path, "PNG")
            if need_asset:
                os.makedirs(os.path.dirname(asset_path), exist_ok=True)
                base_loading.save(asset_path, "PNG")
            count += 1

    # --- Persona loading screens ---
    for pkey, _ptype in get_persona_keys(leader):
        alt_original = os.path.join(
            ASSETS_DIR, "leaders", icon_key, f"{pkey}_loading_original.png"
        )
        if not os.path.isfile(alt_original):
            continue

        alt_mod_path = os.path.join(
            MOD_DIR, "images", "loading", f"lsl_{icon_key}_{pkey}.png"
        )
        alt_asset_path = os.path.join(
            ASSETS_DIR, "leaders", icon_key, f"lsl_{icon_key}_{pkey}.png"
        )
        need_mod = not os.path.isfile(alt_mod_path) or force
        need_asset = not os.path.isfile(alt_asset_path) or force

        if need_mod or need_asset:
            if dry_run:
                count += 1
            else:
                alt_loading = Image.open(alt_original).convert("RGBA")
                if need_mod:
                    os.makedirs(os.path.dirname(alt_mod_path), exist_ok=True)
                    alt_loading.save(alt_mod_path, "PNG")
                if need_asset:
                    os.makedirs(os.path.dirname(alt_asset_path), exist_ok=True)
                    alt_loading.save(alt_asset_path, "PNG")
                count += 1

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Generate loading screens and icons for all leader×civ pairs"
    )
    parser.add_argument("--stub", action="store_true",
                        help="Generate stub images with civ name text overlay")
    parser.add_argument("--leader", help="Generate for one leader only")
    parser.add_argument("--civ", help="Generate for one civ only")
    parser.add_argument("--base-only", action="store_true",
                        help="Only generate base icons and loading screens (no civ stubs)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing stubs")
    args = parser.parse_args()

    if not args.stub:
        print("Error: AI artwork mode not implemented yet.")
        print("Use --stub to generate placeholder images with civ name text overlay.")
        sys.exit(1)

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
    # Never force-overwrite base assets — they come from game extraction.
    # Use extractor/extract.py --force to re-extract them.
    print(f"Generating base icons/loading for {len(leaders)} leaders...")
    base_icon_total = 0
    base_loading_total = 0
    copy_total = 0
    for leader in leaders:
        ic = generate_base_icons(leader, dry_run=args.dry_run, force=False)
        lc = generate_base_loading(leader, dry_run=args.dry_run, force=args.force)
        cc = copy_icons_to_mod(leader["icon_key"], dry_run=args.dry_run)
        if ic or lc or cc:
            action = "Would create" if args.dry_run else "Created"
            parts = []
            if ic:
                parts.append(f"{ic} base icons")
            if lc:
                parts.append(f"{lc} loading")
            if cc:
                parts.append(f"{cc} icons copied to mod")
            print(f"  {leader['icon_key']}: {action} {', '.join(parts)}")
        base_icon_total += ic
        base_loading_total += lc
        copy_total += cc
    action = "Would create" if args.dry_run else "Created"
    print(f"Base: {action} {base_icon_total} icons + {base_loading_total} loading screens"
          f" + {copy_total} icons copied to mod\n")

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
