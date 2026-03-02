#!/usr/bin/env python3
"""
Process source images into all required icon sizes and variants for the Authentic Leaders mod.

Usage:
    python3 process-images.py <leader_key> <source_image> [--loading-source <path>]

Example:
    python3 process-images.py augustus source_augustus.png --loading-source augustus_loading.png

This takes a source portrait image and generates:
  - Loading screen image (1024x1400)
  - Hex icons at 256, 128, 64 (neutral, plus happy/angry at 128)
  - Circle icons at 256, 128, 64
"""

import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOD_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "authentic-leaders")

ICON_SIZES = {
    "hex": [256, 128, 64],
    "circ": [256, 128, 64],
}

LOADING_SCREEN_SIZE = (1024, 1400)


def create_hex_mask(size):
    """Create a hexagonal mask for icon cropping."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = size // 2, size // 2
    r = size // 2 - 2
    import math
    points = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=255)
    return mask


def create_circle_mask(size):
    """Create a circular mask for icon cropping."""
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


def apply_color_tint(img, tint_color, strength=0.15):
    """Apply a subtle color tint to an image."""
    tint = Image.new("RGBA", img.size, tint_color + (int(255 * strength),))
    return Image.alpha_composite(img.convert("RGBA"), tint)


def process_icon(source_img, leader_key, shape, size, suffix="", tint=None):
    """Process a single icon variant."""
    squared = crop_center_square(source_img)
    resized = squared.resize((size, size), Image.LANCZOS)

    if tint:
        resized = apply_color_tint(resized, tint)

    if shape == "hex":
        mask = create_hex_mask(size)
    else:
        mask = create_circle_mask(size)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(resized, (0, 0), mask)

    suffix_str = f"_{suffix}" if suffix else ""
    filename = f"lp_{shape}_{leader_key}_{size}{suffix_str}.png"
    outpath = os.path.join(MOD_DIR, "icons", leader_key, filename)
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    result.save(outpath, "PNG")
    print(f"  Created: {filename}")
    return outpath


def process_loading_screen(source_img, leader_key):
    """Process a loading screen image."""
    target_w, target_h = LOADING_SCREEN_SIZE
    src_w, src_h = source_img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)

    resized = source_img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    cropped = resized.crop((left, top, left + target_w, top + target_h))

    filename = f"lsl_{leader_key}.png"
    outpath = os.path.join(MOD_DIR, "images", "loading", filename)
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    cropped.save(outpath, "PNG")
    print(f"  Created: {filename} ({target_w}x{target_h})")
    return outpath


def process_leader(leader_key, icon_source_path, loading_source_path=None):
    """Process all images for a single leader."""
    print(f"\nProcessing leader: {leader_key}")
    print("=" * 40)

    icon_source = Image.open(icon_source_path).convert("RGBA")

    # Process hex icons
    print("\nHex icons:")
    for size in ICON_SIZES["hex"]:
        process_icon(icon_source, leader_key, "hex", size)
    # Happy variant (slight warm tint)
    process_icon(icon_source, leader_key, "hex", 128, "h", tint=(255, 200, 50))
    # Angry variant (slight red tint)
    process_icon(icon_source, leader_key, "hex", 128, "a", tint=(200, 50, 50))

    # Process circle icons
    print("\nCircle icons:")
    for size in ICON_SIZES["circ"]:
        process_icon(icon_source, leader_key, "circ", size)

    # Process loading screen
    if loading_source_path:
        loading_source = Image.open(loading_source_path).convert("RGBA")
    else:
        loading_source = icon_source

    print("\nLoading screen:")
    process_loading_screen(loading_source, leader_key)

    print(f"\nDone processing {leader_key}!")


def main():
    parser = argparse.ArgumentParser(description="Process images for Authentic Leaders mod")
    parser.add_argument("leader_key", help="Leader key (e.g., 'augustus')")
    parser.add_argument("source_image", help="Path to source portrait image for icons")
    parser.add_argument("--loading-source", help="Path to source image for loading screen (uses icon source if not provided)")
    args = parser.parse_args()

    if not os.path.exists(args.source_image):
        print(f"Error: Source image not found: {args.source_image}")
        sys.exit(1)

    loading_src = args.loading_source
    if loading_src and not os.path.exists(loading_src):
        print(f"Error: Loading source image not found: {loading_src}")
        sys.exit(1)

    process_leader(args.leader_key, args.source_image, loading_src)


if __name__ == "__main__":
    main()
