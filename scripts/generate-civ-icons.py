#!/usr/bin/env python3
"""
Generate civ-specific leader icon PNGs by overlaying civilization name text
onto existing leader icon images.

For each leader × civilization combination, creates 8 icon variants
(hex/circ at various sizes with contexts) with the civ name overlaid.

Usage:
    python3 generate-civ-icons.py
    python3 generate-civ-icons.py --leader augustus
    python3 generate-civ-icons.py --dry-run
"""

import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "authentic-leaders")

# Mapping of civ short key to display label and abbreviated label (for small icons)
CIVS = {
    "aksum":          {"label": "AKSUM",          "abbrev": "AKS"},
    "egypt":          {"label": "EGYPT",          "abbrev": "EGY"},
    "greece":         {"label": "GREECE",         "abbrev": "GRE"},
    "han":            {"label": "HAN",            "abbrev": "HAN"},
    "khmer":          {"label": "KHMER",          "abbrev": "KHM"},
    "maurya":         {"label": "MAURYA",         "abbrev": "MAU"},
    "maya":           {"label": "MAYA",           "abbrev": "MAY"},
    "mississippian":  {"label": "MISSISSIPPIAN",  "abbrev": "MIS"},
    "persia":         {"label": "PERSIA",         "abbrev": "PER"},
    "rome":           {"label": "ROME",           "abbrev": "ROM"},
    "assyria":        {"label": "ASSYRIA",        "abbrev": "ASS"},
    "carthage":       {"label": "CARTHAGE",       "abbrev": "CAR"},
    "silla":          {"label": "SILLA",          "abbrev": "SIL"},
    "tonga":          {"label": "TONGA",          "abbrev": "TON"},
}

# The 8 icon variants that exist per leader
ICON_VARIANTS = [
    {"shape": "hex",  "size": 256, "suffix": "",   "context": None},
    {"shape": "hex",  "size": 128, "suffix": "",   "context": None},
    {"shape": "hex",  "size": 128, "suffix": "_h", "context": "LEADER_HAPPY"},
    {"shape": "hex",  "size": 128, "suffix": "_a", "context": "LEADER_ANGRY"},
    {"shape": "hex",  "size": 64,  "suffix": "",   "context": None},
    {"shape": "circ", "size": 256, "suffix": "",   "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 128, "suffix": "",   "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 64,  "suffix": "",   "context": "CIRCLE_MASK"},
]


def get_font(size):
    """Get a font at the given size, trying system fonts then falling back to default."""
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


def overlay_text(img, text, icon_size):
    """Overlay civilization name text onto an icon image.

    Places text at the bottom of the icon with a semi-transparent dark background
    banner for readability.
    """
    img = img.copy()
    draw = ImageDraw.Draw(img)

    # Scale font size relative to icon size
    if icon_size >= 256:
        font_size = 24
    elif icon_size >= 128:
        font_size = 14
    else:
        font_size = 9

    font = get_font(font_size)

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position: centered horizontally, near bottom
    padding = max(2, icon_size // 32)
    banner_h = text_h + padding * 2
    banner_y = img.size[1] - banner_h - (img.size[1] // 8)  # Offset up from very bottom

    # Draw semi-transparent dark banner
    banner = Image.new("RGBA", img.size, (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner)
    banner_draw.rectangle(
        [0, banner_y, img.size[0], banner_y + banner_h],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img, banner)

    # Draw text
    draw = ImageDraw.Draw(img)
    text_x = (img.size[0] - text_w) // 2
    text_y = banner_y + padding
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

    return img


def generate_civ_icons(leader_key, dry_run=False):
    """Generate all civ-specific icon variants for a leader."""
    source_dir = os.path.join(MOD_DIR, "icons", leader_key)
    if not os.path.isdir(source_dir):
        print(f"Error: Source icon directory not found: {source_dir}")
        return 0

    count = 0

    for civ_key, civ_info in CIVS.items():
        out_dir = os.path.join(MOD_DIR, "icons", leader_key, civ_key)

        for variant in ICON_VARIANTS:
            # Build source filename
            src_name = f"lp_{variant['shape']}_{leader_key}_{variant['size']}{variant['suffix']}.png"
            src_path = os.path.join(source_dir, src_name)

            if not os.path.exists(src_path):
                print(f"  Warning: source not found: {src_name}")
                continue

            # Build output filename
            out_name = f"lp_{variant['shape']}_{leader_key}_{civ_key}_{variant['size']}{variant['suffix']}.png"
            out_path = os.path.join(out_dir, out_name)

            # Choose label: abbreviated for 64px
            label = civ_info["abbrev"] if variant["size"] <= 64 else civ_info["label"]

            if dry_run:
                print(f"  Would create: icons/{leader_key}/{civ_key}/{out_name}")
            else:
                os.makedirs(out_dir, exist_ok=True)
                source_img = Image.open(src_path).convert("RGBA")
                result = overlay_text(source_img, label, variant["size"])
                result.save(out_path, "PNG")
                print(f"  Created: icons/{leader_key}/{civ_key}/{out_name}")

            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="Generate civ-specific leader icon PNGs")
    parser.add_argument("--leader", default="augustus", help="Leader key (default: augustus)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be generated without writing")
    args = parser.parse_args()

    print(f"Generating civ-specific icons for: {args.leader}")
    print(f"Civilizations: {len(CIVS)}")
    print(f"Variants per civ: {len(ICON_VARIANTS)}")
    print(f"Total expected: {len(CIVS) * len(ICON_VARIANTS)}")
    print()

    count = generate_civ_icons(args.leader, dry_run=args.dry_run)

    print(f"\n{'Would create' if args.dry_run else 'Created'} {count} icon files.")


if __name__ == "__main__":
    main()
