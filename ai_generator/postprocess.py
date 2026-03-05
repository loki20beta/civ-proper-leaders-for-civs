"""Post-processing pipeline for AI-generated images.

Two source modes:
  --mode fullbody (default): 3 full-body images with white backgrounds
    (loading.png, happy.png, angry.png). Removes background, crops heads.
  --mode portrait: loading.png (full-body, transparent bg) + separate
    neutral.png, happy.png, angry.png (pre-cropped head portraits,
    transparent bg). Just resize + mask.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

from .config import GENERATED_DIR, MOD_DIR

LOADING_SCREEN_SIZE = (800, 1060)
INPUT_FILES = ("loading.png", "happy.png", "angry.png")
# Head region: top portion of character bounding box
HEAD_FRACTION = 0.20


def remove_white_background(img: Image.Image, tolerance: int = 35) -> Image.Image:
    """Replace white/near-white background with transparency via flood-fill.

    Flood-fills from all 4 corners. Connected pixels where all RGB channels
    are within tolerance of 255 become transparent. Anti-aliased edges get
    partial transparency based on how close they are to white.

    Args:
        img: RGBA image with white-ish background
        tolerance: Max deviation from 255 per channel to count as "white"

    Returns:
        RGBA image with background replaced by transparency
    """
    img = img.convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]

    # Mask of pixels that could be background (all RGB channels near white)
    rgb = arr[:, :, :3].astype(np.int16)
    is_white = np.all(rgb >= (255 - tolerance), axis=2)

    # BFS flood-fill from all 4 corners
    visited = np.zeros((h, w), dtype=bool)
    bg_mask = np.zeros((h, w), dtype=bool)
    queue = deque()

    # Seed from corner regions (3x3 at each corner)
    for sy, sx in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ny, nx = sy + dy, sx + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    if is_white[ny, nx]:
                        visited[ny, nx] = True
                        bg_mask[ny, nx] = True
                        queue.append((ny, nx))

    # 4-connected flood fill
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                visited[ny, nx] = True
                if is_white[ny, nx]:
                    bg_mask[ny, nx] = True
                    queue.append((ny, nx))

    # Make background transparent
    result = arr.copy()
    result[bg_mask, 3] = 0

    # Anti-alias edges: pixels adjacent to background that are somewhat white
    # get partial transparency proportional to their whiteness
    # Manual dilation (2 iterations) to find border pixels without scipy
    dilated = bg_mask.copy()
    for _ in range(2):
        new = dilated.copy()
        new[1:, :] |= dilated[:-1, :]
        new[:-1, :] |= dilated[1:, :]
        new[:, 1:] |= dilated[:, :-1]
        new[:, :-1] |= dilated[:, 1:]
        dilated = new
    border = dilated & ~bg_mask
    for y, x in zip(*np.where(border)):
        r, g, b = int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2])
        # How white is this pixel? (0 = pure white, 255*3 = pure black)
        whiteness = ((255 - r) + (255 - g) + (255 - b)) / 3.0
        if whiteness < tolerance:
            # Partially transparent — more white = more transparent
            alpha = int(255 * whiteness / tolerance)
            result[y, x, 3] = min(result[y, x, 3], alpha)

    return Image.fromarray(result)


def crop_head_region(img: Image.Image, aspect_w: int, aspect_h: int) -> Image.Image:
    """Crop head-and-shoulders from a full-body transparent image.

    1. Find bounding box of non-transparent content
    2. Take top HEAD_FRACTION of character height as the head region
    3. Center horizontally on the character
    4. Crop to target aspect ratio

    Args:
        img: RGBA image with transparent background
        aspect_w: Target aspect ratio width (e.g., 32 for hex)
        aspect_h: Target aspect ratio height (e.g., 45 for hex)

    Returns:
        Cropped RGBA image of head region at the given aspect ratio
    """
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]

    # Find bounding box of non-transparent pixels
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    if not rows.any():
        return img

    top = np.argmax(rows)
    bottom = len(rows) - np.argmax(rows[::-1])
    left = np.argmax(cols)
    right = len(cols) - np.argmax(cols[::-1])

    char_height = bottom - top
    char_width = right - left
    char_cx = (left + right) // 2

    # Head region: top portion of character
    head_height = int(char_height * HEAD_FRACTION)
    head_top = top
    head_bottom = top + head_height

    # Calculate crop dimensions to match aspect ratio
    # Try to fit the head region, expanding as needed
    target_ratio = aspect_w / aspect_h  # width / height

    # Start with head height, compute matching width
    crop_h = head_height
    crop_w = int(crop_h * target_ratio)

    # If crop_w is narrower than the character head area, expand
    head_width_estimate = int(char_width * 0.35)  # head is ~35% of body width
    if crop_w < head_width_estimate:
        crop_w = head_width_estimate
        crop_h = int(crop_w / target_ratio)

    # Center horizontally on character center
    crop_left = char_cx - crop_w // 2
    crop_right = crop_left + crop_w

    # Ensure crop stays within image bounds
    img_w, img_h = img.size
    if crop_left < 0:
        crop_left = 0
        crop_right = crop_w
    if crop_right > img_w:
        crop_right = img_w
        crop_left = max(0, img_w - crop_w)

    # Vertical: start from head_top, use crop_h
    crop_top = max(0, head_top - int(crop_h * 0.05))  # small padding above head
    crop_bottom = crop_top + crop_h
    if crop_bottom > img_h:
        crop_bottom = img_h
        crop_top = max(0, img_h - crop_h)

    return img.crop((crop_left, crop_top, crop_right, crop_bottom))


def crop_to_content(img: Image.Image, padding: float = 0.05,
                    vertical_bias: float = 0.0) -> Image.Image:
    """Crop to non-transparent content bounding box with padding.

    Args:
        img: RGBA image with transparent background
        padding: Fraction of content size to add as padding on each side
        vertical_bias: Shift crop window up (negative) or down (positive).
            Expressed as fraction of content height. E.g., -0.1 shifts up
            by 10% of content height (more top padding, less bottom).

    Returns:
        Tightly cropped RGBA image
    """
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]

    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    if not rows.any():
        return img

    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))

    content_h = bottom - top
    h_pad = int(content_h * padding)
    w_pad = int((right - left) * padding)
    v_shift = int(content_h * vertical_bias)

    img_w, img_h = img.size
    crop_top = max(0, top - h_pad + v_shift)
    crop_bottom = min(img_h, bottom + h_pad + v_shift)
    crop_left = max(0, left - w_pad)
    crop_right = min(img_w, right + w_pad)

    return img.crop((crop_left, crop_top, crop_right, crop_bottom))


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
        src_img: Source headshot image (already cropped to head region)
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
            src = neutral_img
            if src is None:
                continue

        icon = make_masked_icon(src, shape, size)

        png_name = f"lp_{shape}_{leader_key}_{civ_key}_{size}{suffix}.png"
        png_path = os.path.join(icon_dir, png_name)

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


def discover_pairs(leader: str | None = None, civ: str | None = None) -> list[tuple[str, str]]:
    """Discover leader x civ pairs from disk by finding loading.png files.

    Scans assets/generated/{leader}/{civ}/ directories for loading.png.

    Args:
        leader: Filter to this leader only
        civ: Filter to this civ only

    Returns:
        List of (leader_key, civ_key) tuples
    """
    pairs = []
    if not os.path.isdir(GENERATED_DIR):
        return pairs

    leader_dirs = [leader] if leader else sorted(os.listdir(GENERATED_DIR))
    for leader_key in leader_dirs:
        leader_path = os.path.join(GENERATED_DIR, leader_key)
        if not os.path.isdir(leader_path) or leader_key.startswith("."):
            continue

        civ_dirs = [civ] if civ else sorted(os.listdir(leader_path))
        for civ_key in civ_dirs:
            civ_path = os.path.join(leader_path, civ_key)
            if not os.path.isdir(civ_path) or civ_key.startswith("."):
                continue

            loading_path = os.path.join(civ_path, "loading.png")
            if os.path.isfile(loading_path):
                pairs.append((leader_key, civ_key))

    return pairs


def postprocess_pair(leader_key: str, civ_key: str, mode: str = "fullbody",
                     dry_run: bool = False) -> tuple[int, int]:
    """Post-process a single leader x civ pair.

    Args:
        leader_key: Leader identifier
        civ_key: Civilization identifier
        mode: "fullbody" or "portrait"
        dry_run: Preview without writing

    Returns (loading_count, icon_count).
    """
    gen_dir = os.path.join(GENERATED_DIR, leader_key, civ_key)

    loading_path = os.path.join(gen_dir, "loading.png")
    if not os.path.isfile(loading_path):
        print(f"  Skipping {leader_key} x {civ_key}: no loading.png")
        return 0, 0

    if mode == "portrait":
        return _postprocess_portrait(gen_dir, leader_key, civ_key, dry_run)
    else:
        return _postprocess_fullbody(gen_dir, leader_key, civ_key, dry_run)


def _postprocess_fullbody(gen_dir: str, leader_key: str, civ_key: str,
                          dry_run: bool) -> tuple[int, int]:
    """Fullbody mode: 3 full-body white-background images.

    Removes background, crops heads for icons.
    """
    loading_img = Image.open(os.path.join(gen_dir, "loading.png")).convert("RGBA")
    happy_path = os.path.join(gen_dir, "happy.png")
    angry_path = os.path.join(gen_dir, "angry.png")
    happy_img = Image.open(happy_path).convert("RGBA") if os.path.isfile(happy_path) else None
    angry_img = Image.open(angry_path).convert("RGBA") if os.path.isfile(angry_path) else None

    print(f"  Removing backgrounds...")
    loading_trans = remove_white_background(loading_img)
    happy_trans = remove_white_background(happy_img) if happy_img else None
    angry_trans = remove_white_background(angry_img) if angry_img else None

    loading_count = process_loading_screen(loading_trans, leader_key, civ_key, dry_run)

    print(f"  Cropping head regions...")
    hex_aspect = (32, 45)
    neutral_head = crop_head_region(loading_trans, *hex_aspect)
    happy_head = crop_head_region(happy_trans, *hex_aspect) if happy_trans else None
    angry_head = crop_head_region(angry_trans, *hex_aspect) if angry_trans else None

    icon_count = process_icons(
        neutral_img=neutral_head,
        happy_img=happy_head,
        angry_img=angry_head,
        leader_key=leader_key, civ_key=civ_key, dry_run=dry_run
    )
    return loading_count, icon_count


def _postprocess_portrait(gen_dir: str, leader_key: str, civ_key: str,
                          dry_run: bool) -> tuple[int, int]:
    """Portrait mode: full-body loading + pre-cropped head portraits.

    Loading screen already has transparent background.
    Icon sources (neutral.png, happy.png, angry.png) are pre-cropped
    head portraits — just resize and mask.
    """
    loading_img = Image.open(os.path.join(gen_dir, "loading.png")).convert("RGBA")
    loading_count = process_loading_screen(loading_img, leader_key, civ_key, dry_run)

    neutral_path = os.path.join(gen_dir, "neutral.png")
    happy_path = os.path.join(gen_dir, "happy.png")
    angry_path = os.path.join(gen_dir, "angry.png")

    neutral_img = Image.open(neutral_path).convert("RGBA") if os.path.isfile(neutral_path) else None
    happy_img = Image.open(happy_path).convert("RGBA") if os.path.isfile(happy_path) else None
    angry_img = Image.open(angry_path).convert("RGBA") if os.path.isfile(angry_path) else None

    if neutral_img is None:
        print(f"  No neutral.png for icons, skipping icons")
        return loading_count, 0

    # Crop to content bounding box so face fills the icon
    # Bias upward so headdress/crown tops aren't clipped
    neutral_img = crop_to_content(neutral_img, padding=0.10, vertical_bias=-0.12)
    if happy_img:
        happy_img = crop_to_content(happy_img, padding=0.10, vertical_bias=-0.12)
    if angry_img:
        angry_img = crop_to_content(angry_img, padding=0.10, vertical_bias=-0.12)

    icon_count = process_icons(
        neutral_img=neutral_img,
        happy_img=happy_img,
        angry_img=angry_img,
        leader_key=leader_key, civ_key=civ_key, dry_run=dry_run
    )
    return loading_count, icon_count


def main():
    parser = argparse.ArgumentParser(
        description="Post-process AI-generated images into mod assets"
    )
    parser.add_argument("--all", action="store_true",
                        help="Process all pairs with generated images")
    parser.add_argument("--leader", help="Process one leader only")
    parser.add_argument("--civ", help="Process one civ only")
    parser.add_argument("--mode", choices=["fullbody", "portrait"], default="fullbody",
                        help="Source type: fullbody (white bg, crop heads) or portrait (transparent bg, pre-cropped icons)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    if not (args.all or args.leader or args.civ):
        parser.print_help()
        sys.exit(1)

    # Discover pairs from disk
    if args.leader and args.civ:
        pairs = [(args.leader, args.civ)]
        # Verify the pair exists
        gen_dir = os.path.join(GENERATED_DIR, args.leader, args.civ)
        if not os.path.isfile(os.path.join(gen_dir, "loading.png")):
            print(f"No loading.png found for {args.leader} x {args.civ}")
            sys.exit(1)
    else:
        pairs = discover_pairs(leader=args.leader, civ=args.civ)

    if not pairs:
        print("No pairs with generated images found.")
        return

    print(f"Post-processing {len(pairs)} pair(s)...")

    total_loading = 0
    total_icons = 0

    for i, (leader_key, civ_key) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] {leader_key} x {civ_key} ({args.mode})")
        lc, ic = postprocess_pair(leader_key, civ_key, mode=args.mode, dry_run=args.dry_run)
        if lc or ic:
            action = "Would create" if args.dry_run else "Created"
            print(f"  {action} {lc} loading + {ic} icon files")
        total_loading += lc
        total_icons += ic

    action = "Would create" if args.dry_run else "Created"
    print(f"\nTotal: {action} {total_loading} loading screens + {total_icons} icon files")

    if not args.dry_run and (total_loading or total_icons):
        print("\nNext: python3 scripts/generate-mod-data.py")


if __name__ == "__main__":
    main()
