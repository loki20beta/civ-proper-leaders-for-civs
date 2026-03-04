"""Post-processing pipeline for AI-generated images.

Takes selected variants from the generation status and produces all
final mod assets: loading screens, hex icons, circle icons, and
extensionless copies.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import sys

from PIL import Image, ImageDraw

from .config import Config, GENERATED_DIR, MOD_DIR, ASSETS_DIR
from .status import StatusTracker

LOADING_SCREEN_SIZE = (800, 1060)


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
    """Crop the largest centered rectangle with given aspect ratio."""
    w, h = img.size
    crop_w = min(w, int(h * target_w / target_h))
    crop_h = min(h, int(w * target_h / target_w))
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    return img.crop((left, top, left + crop_w, top + crop_h))


def process_loading_screen(src_img: Image.Image, leader_key: str, civ_key: str,
                           dry_run: bool = False) -> int:
    """Process a loading screen image into final mod format.

    Resizes to 800x1060 RGBA and saves to mod directory.
    Returns count of files written.
    """
    target_w, target_h = LOADING_SCREEN_SIZE

    # Resize to target dimensions
    img = src_img.convert("RGBA")
    img = crop_center_rect(img, target_w, target_h)
    img = img.resize((target_w, target_h), Image.LANCZOS)

    out_path = os.path.join(MOD_DIR, "images", "loading", f"lsl_{leader_key}_{civ_key}.png")

    if dry_run:
        print(f"  Would write: {out_path}")
        return 1

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG")
    return 1


def make_masked_icon(src_img: Image.Image, shape: str, size: int) -> Image.Image:
    """Create a masked icon from source image.

    Args:
        src_img: Source headshot image
        shape: "hex" or "circ"
        size: Nominal size (width)

    Returns:
        Masked RGBA icon image
    """
    height = size * 45 // 32 if shape == "hex" else size

    cropped = crop_center_rect(src_img.convert("RGBA"), size, height)
    resized = cropped.resize((size, height), Image.LANCZOS)

    mask = create_hex_mask(size, height) if shape == "hex" else create_circle_mask(size)
    result = Image.new("RGBA", (size, height), (0, 0, 0, 0))
    result.paste(resized, (0, 0), mask)
    return result


def process_icons(neutral_img: Image.Image | None, happy_img: Image.Image | None,
                  angry_img: Image.Image | None, leader_key: str, civ_key: str,
                  dry_run: bool = False) -> int:
    """Process headshot images into all icon variants.

    Generates from the 3 expression images:
    - hex_256, hex_128, hex_64 (from neutral)
    - hex_128_h (from happy)
    - hex_128_a (from angry)
    - circ_256, circ_128, circ_64 (from neutral)

    Also creates extensionless copies for getLeaderPortraitIcon compatibility.
    Returns count of files written.
    """
    icon_dir = os.path.join(MOD_DIR, "icons", leader_key, civ_key)
    count = 0

    # Map variant specs to source images
    variants = [
        # (shape, size, suffix, source_expression)
        ("hex",  256, "",   "neutral"),
        ("hex",  128, "",   "neutral"),
        ("hex",  128, "_h", "happy"),
        ("hex",  128, "_a", "angry"),
        ("hex",   64, "",   "neutral"),
        ("circ", 256, "",   "neutral"),
        ("circ", 128, "",   "neutral"),
        ("circ",  64, "",   "neutral"),
    ]

    source_map = {
        "neutral": neutral_img,
        "happy": happy_img,
        "angry": angry_img,
    }

    for shape, size, suffix, expr in variants:
        src = source_map.get(expr)
        if src is None:
            # Fall back to neutral for missing expressions
            src = neutral_img
            if src is None:
                continue

        icon = make_masked_icon(src, shape, size)

        png_name = f"lp_{shape}_{leader_key}_{civ_key}_{size}{suffix}.png"
        png_path = os.path.join(icon_dir, png_name)

        # Extensionless copy name
        ext_name = f"lp_{shape}_{leader_key}_{civ_key}_{size}{suffix}"
        ext_path = os.path.join(icon_dir, ext_name)

        if dry_run:
            print(f"  Would write: {png_name} + extensionless")
            count += 2
            continue

        os.makedirs(icon_dir, exist_ok=True)
        icon.save(png_path, "PNG")
        shutil.copy2(png_path, ext_path)
        count += 2

    return count


def postprocess_pair(cfg: Config, status: StatusTracker,
                     leader_key: str, civ_key: str,
                     dry_run: bool = False) -> tuple[int, int]:
    """Post-process a single leader x civ pair.

    Reads selected variants from status, produces final mod assets.
    Returns (loading_count, icon_count).
    """
    gen_dir = cfg.get_generated_dir(leader_key, civ_key)
    loading_count = 0
    icon_count = 0

    # Loading screen
    loading_file = status.get_selected_variant(leader_key, civ_key, "loading")
    if loading_file:
        loading_path = os.path.join(gen_dir, loading_file)
        if os.path.isfile(loading_path):
            img = Image.open(loading_path)
            loading_count = process_loading_screen(img, leader_key, civ_key, dry_run)

    # Icons
    icon_images = {}
    for expr in ["neutral", "happy", "angry"]:
        variant_file = status.get_selected_variant(leader_key, civ_key, f"icon_{expr}")
        if variant_file:
            icon_path = os.path.join(gen_dir, variant_file)
            if os.path.isfile(icon_path):
                icon_images[expr] = Image.open(icon_path).convert("RGBA")

    if icon_images.get("neutral"):
        icon_count = process_icons(
            neutral_img=icon_images.get("neutral"),
            happy_img=icon_images.get("happy"),
            angry_img=icon_images.get("angry"),
            leader_key=leader_key,
            civ_key=civ_key,
            dry_run=dry_run
        )

    return loading_count, icon_count


def main():
    parser = argparse.ArgumentParser(
        description="Post-process AI-generated images into mod assets"
    )
    parser.add_argument("--all", action="store_true", help="Process all completed pairs")
    parser.add_argument("--leader", help="Process one leader only")
    parser.add_argument("--civ", help="Process one civ only")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    cfg = Config()
    status = StatusTracker()

    # Determine pairs to process
    if args.leader and args.civ:
        pairs = [(args.leader, args.civ)]
    elif args.leader:
        pairs = [(args.leader, c) for c in cfg.get_all_civ_keys()
                 if status.is_completed(args.leader, c)]
    elif args.civ:
        pairs = [(l, args.civ) for l in cfg.get_all_leader_keys()
                 if status.is_completed(l, args.civ)]
    elif args.all:
        pairs = [
            (l, c) for l, c in cfg.get_all_pairs()
            if status.is_completed(l, c)
        ]
    else:
        parser.print_help()
        sys.exit(1)

    if not pairs:
        print("No completed pairs to process.")
        return

    print(f"Post-processing {len(pairs)} pairs...")

    total_loading = 0
    total_icons = 0

    for i, (leader_key, civ_key) in enumerate(pairs, 1):
        lc, ic = postprocess_pair(cfg, status, leader_key, civ_key, dry_run=args.dry_run)
        if lc or ic:
            action = "Would create" if args.dry_run else "Created"
            print(f"  [{i}/{len(pairs)}] {leader_key} x {civ_key}: "
                  f"{action} {lc} loading + {ic} icon files")
        total_loading += lc
        total_icons += ic

    action = "Would create" if args.dry_run else "Created"
    print(f"\nTotal: {action} {total_loading} loading screens + {total_icons} icon files")

    if not args.dry_run and (total_loading or total_icons):
        print("\nNext: python3 scripts/generate-mod-data.py")


if __name__ == "__main__":
    main()
