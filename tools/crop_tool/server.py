"""Crop position tool — Flask backend.

Serves images from assets/generated/ with background removal,
and manages crop_meta.json files for icon crop positioning.
"""

from __future__ import annotations

import io
import json
import os
import sys

from flask import Flask, jsonify, request, send_file, send_from_directory

# Add project root to path so we can import ai_generator
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from ai_generator.config import GENERATED_DIR, ASSETS_DIR  # noqa: E402
from ai_generator.postprocess import remove_white_background, remove_green_background  # noqa: E402

app = Flask(__name__, static_folder="static")

EXPRESSIONS = ("neutral", "happy", "angry")


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def detect_mode(civ_dir: str) -> str:
    """Detect image mode by sampling top-left pixel color.

    Checks neutral.png first, falls back to loading.png.
    Pixel at (5,5):
      - alpha < 50 -> portrait (transparent background)
      - green dominant (g>150, r<100, b<100) -> chromakey
      - else -> fullbody (white background)
    """
    from PIL import Image

    # Prefer neutral.png, fall back to loading.png
    for fname in ("neutral.png", "loading.png"):
        path = os.path.join(civ_dir, fname)
        if os.path.isfile(path):
            img = Image.open(path)
            img = img.convert("RGBA")
            r, g, b, a = img.getpixel((5, 5))
            if a < 50:
                return "portrait"
            if g > 150 and r < 100 and b < 100:
                return "chromakey"
            return "fullbody"

    return "fullbody"


# ---------------------------------------------------------------------------
# Image file resolution
# ---------------------------------------------------------------------------

def resolve_image_path(civ_dir: str, expression: str, mode: str) -> str | None:
    """Resolve the source image file for a given expression and mode.

    fullbody:
      neutral -> loading.png, happy -> happy.png, angry -> angry.png
      (fall back to loading.png)
    portrait/chromakey:
      expression -> {expression}.png
      (fall back to neutral.png, then loading.png)
    """
    if mode == "fullbody":
        if expression == "neutral":
            candidates = ["loading.png"]
        else:
            candidates = [f"{expression}.png", "loading.png"]
    else:
        # portrait or chromakey
        candidates = [f"{expression}.png", "neutral.png", "loading.png"]

    for fname in candidates:
        path = os.path.join(civ_dir, fname)
        if os.path.isfile(path):
            return path

    return None


# ---------------------------------------------------------------------------
# crop_meta.json handling
# ---------------------------------------------------------------------------

def get_crop_meta_path(leader: str, civ: str) -> str:
    """Path to civ-level crop_meta.json."""
    return os.path.join(GENERATED_DIR, leader, civ, "crop_meta.json")


def get_leader_crop_meta_path(leader: str) -> str:
    """Path to leader-level crop_meta.json."""
    return os.path.join(GENERATED_DIR, leader, "crop_meta.json")


def load_json(path: str) -> dict:
    """Load JSON file, returning empty dict if missing."""
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def resolve_crop(leader: str, civ: str, expression: str) -> dict | None:
    """Resolve crop metadata using cascade:

    1. civ-level, exact expression
    2. civ-level, "default"
    3. leader-level, exact expression
    4. leader-level, "default"
    5. None
    """
    civ_meta = load_json(get_crop_meta_path(leader, civ))
    leader_meta = load_json(get_leader_crop_meta_path(leader))

    for meta in (civ_meta, leader_meta):
        if expression in meta:
            return meta[expression]
        if "default" in meta:
            return meta["default"]

    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the frontend."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/pairs")
def api_pairs():
    """List all leader x civ pairs with detected mode."""
    pairs = []

    if not os.path.isdir(GENERATED_DIR):
        return jsonify(pairs)

    for leader in sorted(os.listdir(GENERATED_DIR)):
        leader_path = os.path.join(GENERATED_DIR, leader)
        if not os.path.isdir(leader_path) or leader.startswith("."):
            continue

        for civ in sorted(os.listdir(leader_path)):
            civ_path = os.path.join(leader_path, civ)
            if not os.path.isdir(civ_path) or civ.startswith("."):
                continue

            # Must have at least loading.png
            if not os.path.isfile(os.path.join(civ_path, "loading.png")):
                continue

            mode = detect_mode(civ_path)

            # Determine which expressions have source files
            available = []
            for expr in EXPRESSIONS:
                if resolve_image_path(civ_path, expr, mode) is not None:
                    available.append(expr)

            pairs.append({
                "leader": leader,
                "civ": civ,
                "mode": mode,
                "expressions": available,
            })

    return jsonify(pairs)


@app.route("/api/image/<leader>/<civ>/<expression>")
def api_image(leader: str, civ: str, expression: str):
    """Serve source image with background removal applied."""
    from PIL import Image

    civ_dir = os.path.join(GENERATED_DIR, leader, civ)
    mode = detect_mode(civ_dir)
    path = resolve_image_path(civ_dir, expression, mode)

    if path is None:
        return "Image not found", 404

    img = Image.open(path).convert("RGBA")

    if mode == "chromakey":
        img = remove_green_background(img)
    elif mode == "fullbody":
        img = remove_white_background(img)
    # portrait: pass through (already transparent)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/image_raw/<leader>/<civ>/<expression>")
def api_image_raw(leader: str, civ: str, expression: str):
    """Serve raw source image without any processing."""
    civ_dir = os.path.join(GENERATED_DIR, leader, civ)
    mode = detect_mode(civ_dir)
    path = resolve_image_path(civ_dir, expression, mode)

    if path is None:
        return "Image not found", 404

    return send_file(path, mimetype="image/png")


@app.route("/api/crop/<leader>/<civ>", methods=["GET"])
def api_crop_get(leader: str, civ: str):
    """Return resolved crop metadata for all 3 expressions."""
    result = {}
    for expr in EXPRESSIONS:
        crop = resolve_crop(leader, civ, expr)
        result[expr] = crop  # None becomes null in JSON

    return jsonify(result)


@app.route("/api/crop/<leader>/<civ>", methods=["POST"])
def api_crop_post(leader: str, civ: str):
    """Save crop metadata.

    Body: {
        "level": "leader" | "civ",
        "expression": "default" | "neutral" | "happy" | "angry",
        "crop": {"x": int, "y": int, "size": int}
    }
    """
    data = request.get_json()
    if not data:
        return "Invalid JSON", 400

    level = data.get("level")
    expression = data.get("expression")
    crop = data.get("crop")

    if level not in ("leader", "civ"):
        return "level must be 'leader' or 'civ'", 400
    if expression not in ("default", "neutral", "happy", "angry"):
        return "expression must be 'default', 'neutral', 'happy', or 'angry'", 400
    if not isinstance(crop, dict) or not all(k in crop for k in ("x", "y", "size")):
        return "crop must have x, y, size", 400

    # Determine which file to update
    if level == "civ":
        meta_path = get_crop_meta_path(leader, civ)
    else:
        meta_path = get_leader_crop_meta_path(leader)

    # Load existing, merge, save
    meta = load_json(meta_path)
    meta[expression] = {
        "x": int(crop["x"]),
        "y": int(crop["y"]),
        "size": int(crop["size"]),
    }

    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return jsonify({"ok": True, "path": meta_path})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Generated dir: {GENERATED_DIR}")
    app.run(host="127.0.0.1", port=8000, debug=True)
