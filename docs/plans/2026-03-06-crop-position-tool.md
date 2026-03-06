# Crop Position Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Browser-based tool with a draggable hex selector overlay on leader portrait images, producing crop metadata that `postprocess.py` consumes to position icons.

**Architecture:** Flask backend serves source images (with on-the-fly background removal) and manages crop_meta.json files. Single-page HTML/JS frontend renders the source image with a draggable/resizable hex overlay. Crop metadata cascades: leader default → civ override → per-expression override.

**Tech Stack:** Python (Flask, Pillow, NumPy), vanilla HTML/CSS/JS (Canvas API)

---

### Task 1: Install Flask and create project skeleton

**Files:**
- Create: `tools/crop_tool/__init__.py`
- Create: `tools/crop_tool/server.py` (minimal Flask app)
- Create: `tools/crop_tool/static/index.html` (placeholder)

**Step 1: Install Flask**

Run: `pip3 install flask`
Expected: Successfully installed flask

**Step 2: Create skeleton server**

Create `tools/crop_tool/__init__.py` (empty file).

Create `tools/crop_tool/server.py`:

```python
"""Crop Position Tool — interactive hex icon crop selector."""

import json
import os
import sys

from flask import Flask, jsonify, send_file, request, send_from_directory

# Add project root to path for ai_generator imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from ai_generator.config import GENERATED_DIR, ASSETS_DIR
from ai_generator.postprocess import remove_white_background, remove_green_background

from PIL import Image
import io

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/pairs")
def list_pairs():
    """List all leader x civ pairs with detected mode."""
    pairs = []
    if not os.path.isdir(GENERATED_DIR):
        return jsonify(pairs)

    for leader_key in sorted(os.listdir(GENERATED_DIR)):
        leader_path = os.path.join(GENERATED_DIR, leader_key)
        if not os.path.isdir(leader_path) or leader_key.startswith("."):
            continue
        for civ_key in sorted(os.listdir(leader_path)):
            civ_path = os.path.join(leader_path, civ_key)
            if not os.path.isdir(civ_path) or civ_key.startswith("."):
                continue
            loading = os.path.join(civ_path, "loading.png")
            if not os.path.isfile(loading):
                continue

            has_neutral = os.path.isfile(os.path.join(civ_path, "neutral.png"))
            has_happy = os.path.isfile(os.path.join(civ_path, "happy.png"))
            has_angry = os.path.isfile(os.path.join(civ_path, "angry.png"))

            # Detect mode from background color
            mode = _detect_mode(civ_path, has_neutral)

            pairs.append({
                "leader": leader_key,
                "civ": civ_key,
                "mode": mode,
                "has_neutral": has_neutral,
                "has_happy": has_happy,
                "has_angry": has_angry,
            })

    return jsonify(pairs)


def _detect_mode(civ_path, has_neutral):
    """Detect source mode by checking background color."""
    import numpy as np
    # Check neutral.png if it exists, else loading.png
    check_file = "neutral.png" if has_neutral else "loading.png"
    img_path = os.path.join(civ_path, check_file)
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img)
    r, g, b, a = arr[5, 5, 0], arr[5, 5, 1], arr[5, 5, 2], arr[5, 5, 3]
    if a < 50:
        return "portrait"
    if g > 150 and r < 100 and b < 100:
        return "chromakey"
    return "fullbody"


@app.route("/api/image/<leader>/<civ>/<expression>")
def get_image(leader, civ, expression):
    """Serve source image with background removal applied.

    For icon sources: serves neutral/happy/angry.png (portrait/chromakey)
    or loading.png (fullbody) with background removed, as PNG with transparency.
    """
    civ_path = os.path.join(GENERATED_DIR, leader, civ)
    if not os.path.isdir(civ_path):
        return "Not found", 404

    has_neutral = os.path.isfile(os.path.join(civ_path, "neutral.png"))
    mode = _detect_mode(civ_path, has_neutral)

    # Determine which file to load
    if mode == "fullbody":
        # All expressions come from their respective files (or loading.png)
        if expression == "neutral":
            filename = "loading.png"
        else:
            filename = f"{expression}.png"
            if not os.path.isfile(os.path.join(civ_path, filename)):
                filename = "loading.png"
    else:
        # portrait/chromakey: use expression files
        filename = f"{expression}.png"
        if not os.path.isfile(os.path.join(civ_path, filename)):
            filename = "neutral.png" if has_neutral else "loading.png"

    img_path = os.path.join(civ_path, filename)
    if not os.path.isfile(img_path):
        return "Not found", 404

    img = Image.open(img_path).convert("RGBA")

    # Remove background based on mode
    if mode == "chromakey":
        img = remove_green_background(img)
    elif mode == "fullbody":
        img = remove_white_background(img)
    # portrait: already transparent

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/image_raw/<leader>/<civ>/<expression>")
def get_image_raw(leader, civ, expression):
    """Serve raw source image without background removal (for display under hex)."""
    civ_path = os.path.join(GENERATED_DIR, leader, civ)
    has_neutral = os.path.isfile(os.path.join(civ_path, "neutral.png"))
    mode = _detect_mode(civ_path, has_neutral)

    if mode == "fullbody":
        filename = "loading.png" if expression == "neutral" else f"{expression}.png"
        if not os.path.isfile(os.path.join(civ_path, filename)):
            filename = "loading.png"
    else:
        filename = f"{expression}.png"
        if not os.path.isfile(os.path.join(civ_path, filename)):
            filename = "neutral.png" if has_neutral else "loading.png"

    img_path = os.path.join(civ_path, filename)
    if not os.path.isfile(img_path):
        return "Not found", 404
    return send_file(img_path, mimetype="image/png")


def _resolve_crop_meta(leader, civ, expression):
    """Resolve crop meta using cascade: civ/expression → civ/default → leader/expression → leader/default → None."""
    # Level 1: civ-specific
    civ_meta_path = os.path.join(GENERATED_DIR, leader, civ, "crop_meta.json")
    if os.path.isfile(civ_meta_path):
        with open(civ_meta_path) as f:
            civ_meta = json.load(f)
        if expression in civ_meta:
            return civ_meta[expression], "civ_expression"
        if "default" in civ_meta:
            return civ_meta["default"], "civ_default"

    # Level 2: leader-level default
    leader_meta_path = os.path.join(GENERATED_DIR, leader, "crop_meta.json")
    if os.path.isfile(leader_meta_path):
        with open(leader_meta_path) as f:
            leader_meta = json.load(f)
        if expression in leader_meta:
            return leader_meta[expression], "leader_expression"
        if "default" in leader_meta:
            return leader_meta["default"], "leader_default"

    return None, "none"


@app.route("/api/crop/<leader>/<civ>")
def get_crop(leader, civ):
    """Get resolved crop meta for all expressions."""
    result = {}
    for expr in ["neutral", "happy", "angry"]:
        meta, source = _resolve_crop_meta(leader, civ, expr)
        result[expr] = {"crop": meta, "source": source}
    return jsonify(result)


@app.route("/api/crop/<leader>/<civ>", methods=["POST"])
def save_crop(leader, civ):
    """Save crop meta.

    Body: {
        "level": "leader" | "civ",
        "expression": "default" | "neutral" | "happy" | "angry",
        "crop": { "x": int, "y": int, "size": int }
    }
    """
    data = request.json
    level = data.get("level", "civ")
    expression = data.get("expression", "default")
    crop = data["crop"]

    if level == "leader":
        meta_path = os.path.join(GENERATED_DIR, leader, "crop_meta.json")
    else:
        meta_path = os.path.join(GENERATED_DIR, leader, civ, "crop_meta.json")

    # Load existing or create new
    if os.path.isfile(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {}

    meta[expression] = crop

    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return jsonify({"ok": True, "path": meta_path})


if __name__ == "__main__":
    app.run(debug=True, port=8000)
```

**Step 3: Create placeholder HTML**

Create `tools/crop_tool/static/index.html`:
```html
<!DOCTYPE html>
<html><body><h1>Crop Tool loading...</h1></body></html>
```

**Step 4: Verify server starts**

Run: `cd /Users/admin/work/civ7mod && python3 tools/crop_tool/server.py`
Expected: Flask dev server starts on port 8000, no import errors.
Kill with Ctrl+C.

**Step 5: Test API endpoints**

Run (in separate terminal):
```bash
python3 tools/crop_tool/server.py &
sleep 2
curl -s http://localhost:8000/api/pairs | python3 -m json.tool | head -20
curl -s http://localhost:8000/api/crop/friedrich/egypt | python3 -m json.tool
kill %1
```
Expected: pairs list with mode detection, crop returns null for all (no meta yet).

**Step 6: Commit**

```bash
git add tools/crop_tool/
git commit -m "feat: crop position tool — Flask backend with image/crop API"
```

---

### Task 2: Frontend — image display and hex overlay

**Files:**
- Create: `tools/crop_tool/static/index.html` (full rewrite of placeholder)

This is the core UI task. Single HTML file with embedded CSS and JS.

**Step 1: Build the HTML/CSS/JS**

Create `tools/crop_tool/static/index.html` with:

**Layout:**
- Full viewport, dark background (#1a1a2e or similar game dark)
- Left area (70%): source image canvas with hex overlay
- Right sidebar (30%): pair selector, expression toggle, preview panel, save controls

**Canvas layer:**
- Source image rendered to canvas, scaled to fit viewport height
- Hex overlay drawn on top: semi-transparent fill inside hex, dimmed/darkened area outside hex
- Hex shape: pointy-top hexagon with aspect ratio 32:45 (same as game icons)

**Hex interaction:**
- Click and drag inside hex → move hex position
- Click and drag on hex edges → resize (maintain 32:45 aspect)
- Show hex dimensions in source pixels

**Right sidebar:**
- Dropdown or prev/next for leader×civ pair
- Three buttons: Neutral / Happy / Angry — toggles which image is shown under the hex
- Preview: 128px hex icon showing the cropped result (updated live as hex moves)
- Inheritance display: shows "leader default" / "civ override" / "expression override" / "none"
- Save button with level selector (radio: "Leader default" / "Civ override")
- Expression selector for save (radio: "Default" / current expression name)

**Key implementation details for `index.html`:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Crop Position Tool</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #1a1a2e;
    color: #e0d8c8;
    font-family: -apple-system, sans-serif;
    display: flex;
    height: 100vh;
    overflow: hidden;
    user-select: none;
}

#canvas-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}

canvas {
    cursor: crosshair;
}

#sidebar {
    width: 320px;
    background: #16213e;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    border-left: 1px solid #333;
}

.section {
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 12px;
}

.section h3 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8a7e6b;
    margin-bottom: 8px;
}

.pair-nav {
    display: flex;
    gap: 8px;
    align-items: center;
}

.pair-nav button {
    background: #2a2a4a;
    border: 1px solid #444;
    color: #e0d8c8;
    padding: 6px 12px;
    cursor: pointer;
    border-radius: 4px;
}

.pair-nav button:hover { background: #3a3a5a; }

.pair-nav .current {
    flex: 1;
    text-align: center;
    font-size: 14px;
    font-weight: bold;
}

.expr-toggle {
    display: flex;
    gap: 4px;
}

.expr-toggle button {
    flex: 1;
    background: #2a2a4a;
    border: 1px solid #444;
    color: #e0d8c8;
    padding: 8px;
    cursor: pointer;
    border-radius: 4px;
    font-size: 12px;
}

.expr-toggle button.active {
    background: #4a3a2a;
    border-color: #c8a86e;
    color: #c8a86e;
}

#preview-container {
    display: flex;
    gap: 12px;
    justify-content: center;
    align-items: flex-end;
    padding: 16px 0;
}

.preview-hex {
    position: relative;
    background: #0d0d1a;
    border: 2px solid #6b5a3e;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
}

.preview-hex canvas { display: block; }

.preview-label {
    font-size: 10px;
    color: #666;
    text-align: center;
    margin-top: 4px;
}

#inheritance-info {
    font-size: 11px;
    color: #8a7e6b;
    font-style: italic;
}

#crop-info {
    font-size: 12px;
    font-family: monospace;
    color: #aaa;
}

.save-controls {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.save-controls label {
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
}

.save-controls input[type="radio"] {
    accent-color: #c8a86e;
}

#save-btn {
    background: #4a3a2a;
    border: 1px solid #c8a86e;
    color: #c8a86e;
    padding: 10px;
    cursor: pointer;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
}

#save-btn:hover { background: #5a4a3a; }

#save-status {
    font-size: 11px;
    color: #6b8a6b;
    min-height: 16px;
}
</style>
</head>
<body>

<div id="canvas-area">
    <canvas id="main-canvas"></canvas>
</div>

<div id="sidebar">
    <div class="section">
        <h3>Leader / Civ</h3>
        <div class="pair-nav">
            <button id="prev-btn">&laquo; Prev</button>
            <span class="current" id="pair-label">...</span>
            <button id="next-btn">Next &raquo;</button>
        </div>
        <div style="margin-top:8px;font-size:11px;color:#666" id="mode-label"></div>
    </div>

    <div class="section">
        <h3>Expression</h3>
        <div class="expr-toggle">
            <button class="active" data-expr="neutral">Neutral</button>
            <button data-expr="happy">Happy</button>
            <button data-expr="angry">Angry</button>
        </div>
    </div>

    <div class="section">
        <h3>Preview (game size)</h3>
        <div id="preview-container">
            <div>
                <div class="preview-hex"><canvas id="preview-128" width="128" height="180"></canvas></div>
                <div class="preview-label">128px</div>
            </div>
            <div>
                <div class="preview-hex"><canvas id="preview-64" width="64" height="90"></canvas></div>
                <div class="preview-label">64px</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h3>Crop Info</h3>
        <div id="crop-info">x: — y: — size: —</div>
        <div id="inheritance-info" style="margin-top:6px">No crop data</div>
    </div>

    <div class="section">
        <h3>Save</h3>
        <div class="save-controls">
            <label><input type="radio" name="save-level" value="civ" checked> Civ override</label>
            <label><input type="radio" name="save-level" value="leader"> Leader default</label>
            <hr style="border-color:#333">
            <label><input type="radio" name="save-expr" value="default" checked> Default (all expressions)</label>
            <label><input type="radio" name="save-expr" value="current"> Current expression only</label>
        </div>
        <button id="save-btn" style="margin-top:8px">Save Crop</button>
        <div id="save-status"></div>
    </div>
</div>

<script>
// ===== State =====
let pairs = [];
let currentIndex = 0;
let currentExpr = "neutral";
let sourceImg = null;       // Image element for current expression
let imgScale = 1;           // display pixels per source pixel
let imgOffsetX = 0;         // canvas offset for centered image
let imgOffsetY = 0;

// Hex selector state (in SOURCE image coordinates)
let hex = { x: 100, y: 50, size: 400 };
const HEX_ASPECT = 45 / 32; // height/width ratio

// Drag state
let dragging = null; // "move" | "resize" | null
let dragStart = { mx: 0, my: 0, hx: 0, hy: 0, hs: 0 };

const canvas = document.getElementById("main-canvas");
const ctx = canvas.getContext("2d");

// ===== Init =====
async function init() {
    pairs = await (await fetch("/api/pairs")).json();
    if (!pairs.length) {
        document.getElementById("pair-label").textContent = "No generated pairs found";
        return;
    }
    // Find friedrich/egypt as default, or first pair
    currentIndex = pairs.findIndex(p => p.leader === "friedrich" && p.civ === "egypt");
    if (currentIndex < 0) currentIndex = 0;

    setupEvents();
    await loadPair();
}

// ===== Pair loading =====
async function loadPair() {
    const pair = pairs[currentIndex];
    document.getElementById("pair-label").textContent = `${pair.leader} / ${pair.civ}`;
    document.getElementById("mode-label").textContent = `Mode: ${pair.mode}`;

    // Load crop meta
    const cropData = await (await fetch(`/api/crop/${pair.leader}/${pair.civ}`)).json();
    const exprData = cropData[currentExpr];
    if (exprData && exprData.crop) {
        hex = { ...exprData.crop };
        document.getElementById("inheritance-info").textContent = `Source: ${exprData.source}`;
    } else {
        // Auto-detect initial hex position (center of image)
        hex = { x: 100, y: 50, size: 400 };
        document.getElementById("inheritance-info").textContent = "No crop data (auto)";
    }

    await loadExpression();
}

async function loadExpression() {
    const pair = pairs[currentIndex];
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
            sourceImg = img;
            // If hex is default and no saved crop, center it
            fitCanvasAndImage();
            draw();
            updatePreview();
            resolve();
        };
        img.src = `/api/image_raw/${pair.leader}/${pair.civ}/${currentExpr}`;
    });
}

function fitCanvasAndImage() {
    const area = document.getElementById("canvas-area");
    canvas.width = area.clientWidth;
    canvas.height = area.clientHeight;

    if (!sourceImg) return;

    // Scale image to fit canvas with padding
    const pad = 40;
    const scaleX = (canvas.width - pad * 2) / sourceImg.width;
    const scaleY = (canvas.height - pad * 2) / sourceImg.height;
    imgScale = Math.min(scaleX, scaleY);
    imgOffsetX = (canvas.width - sourceImg.width * imgScale) / 2;
    imgOffsetY = (canvas.height - sourceImg.height * imgScale) / 2;
}

// ===== Drawing =====
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!sourceImg) return;

    // Draw source image
    ctx.drawImage(sourceImg, imgOffsetX, imgOffsetY,
                  sourceImg.width * imgScale, sourceImg.height * imgScale);

    // Draw dimming overlay with hex cutout
    const hexW = hex.size * imgScale;
    const hexH = hex.size * HEX_ASPECT * imgScale;
    const hx = imgOffsetX + hex.x * imgScale;
    const hy = imgOffsetY + hex.y * imgScale;
    const cx = hx + hexW / 2;
    const cy = hy + hexH / 2;

    // Dim everything outside hex
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    // Cut out hex (counter-clockwise for hole)
    const hexPoints = getHexPoints(cx, cy, hexW / 2, hexH / 2);
    ctx.moveTo(hexPoints[0][0], hexPoints[0][1]);
    for (let i = hexPoints.length - 1; i >= 0; i--) {
        ctx.lineTo(hexPoints[i][0], hexPoints[i][1]);
    }
    ctx.closePath();
    ctx.fill();

    // Draw hex border
    ctx.beginPath();
    ctx.moveTo(hexPoints[0][0], hexPoints[0][1]);
    for (let i = 1; i < hexPoints.length; i++) {
        ctx.lineTo(hexPoints[i][0], hexPoints[i][1]);
    }
    ctx.closePath();
    ctx.strokeStyle = "#c8a86e";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw resize handle (bottom-right area)
    const brPoint = hexPoints[2]; // bottom-right vertex
    ctx.fillStyle = "rgba(200, 168, 110, 0.8)";
    ctx.beginPath();
    ctx.arc(brPoint[0], brPoint[1], 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    // Update crop info
    const hexHeight = Math.round(hex.size * HEX_ASPECT);
    document.getElementById("crop-info").textContent =
        `x: ${Math.round(hex.x)}  y: ${Math.round(hex.y)}  size: ${Math.round(hex.size)}  (${Math.round(hex.size)}×${hexHeight})`;
}

function getHexPoints(cx, cy, rx, ry) {
    // Pointy-top hexagon (matching game icons)
    const points = [];
    for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 6 + i * Math.PI / 3;
        points.push([
            cx + rx * Math.cos(angle),
            cy + ry * Math.sin(angle)
        ]);
    }
    return points;
}

// ===== Preview =====
function updatePreview() {
    if (!sourceImg) return;

    // Load the bg-removed version for preview
    const pair = pairs[currentIndex];
    const previewImg = new Image();
    previewImg.onload = () => {
        drawPreviewIcon(previewImg, "preview-128", 128, 180);
        drawPreviewIcon(previewImg, "preview-64", 64, 90);
    };
    previewImg.src = `/api/image/${pair.leader}/${pair.civ}/${currentExpr}`;
}

function drawPreviewIcon(img, canvasId, w, h) {
    const c = document.getElementById(canvasId);
    const pctx = c.getContext("2d");
    pctx.clearRect(0, 0, w, h);

    // Crop from source: hex bounds → icon
    const srcX = hex.x;
    const srcY = hex.y;
    const srcW = hex.size;
    const srcH = hex.size * HEX_ASPECT;

    // Draw cropped region scaled to icon size
    pctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, w, h);

    // Apply hex mask
    pctx.globalCompositeOperation = "destination-in";
    drawHexMask(pctx, w, h);
    pctx.globalCompositeOperation = "source-over";
}

function drawHexMask(pctx, w, h) {
    const cx = w / 2, cy = h / 2;
    const rx = w / 2 - 1, ry = h / 2 - 1;
    pctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 6 + i * Math.PI / 3;
        const x = cx + rx * Math.cos(angle);
        const y = cy + ry * Math.sin(angle);
        if (i === 0) pctx.moveTo(x, y);
        else pctx.lineTo(x, y);
    }
    pctx.closePath();
    pctx.fill();
}

// ===== Mouse interaction =====
function canvasToSource(mx, my) {
    return {
        x: (mx - imgOffsetX) / imgScale,
        y: (my - imgOffsetY) / imgScale
    };
}

function isInsideHex(mx, my) {
    const s = canvasToSource(mx, my);
    const cx = hex.x + hex.size / 2;
    const cy = hex.y + (hex.size * HEX_ASPECT) / 2;
    // Approximate: check if within bounding box (good enough for drag)
    const dx = Math.abs(s.x - cx) / (hex.size / 2);
    const dy = Math.abs(s.y - cy) / (hex.size * HEX_ASPECT / 2);
    return dx < 1 && dy < 1;
}

function isNearResizeHandle(mx, my) {
    const hexW = hex.size * imgScale;
    const hexH = hex.size * HEX_ASPECT * imgScale;
    const hx = imgOffsetX + hex.x * imgScale;
    const hy = imgOffsetY + hex.y * imgScale;
    const cx = hx + hexW / 2;
    const cy = hy + hexH / 2;
    const points = getHexPoints(cx, cy, hexW / 2, hexH / 2);
    const brPoint = points[2];
    const dist = Math.hypot(mx - brPoint[0], my - brPoint[1]);
    return dist < 15;
}

function setupEvents() {
    canvas.addEventListener("mousedown", (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        if (isNearResizeHandle(mx, my)) {
            dragging = "resize";
        } else if (isInsideHex(mx, my)) {
            dragging = "move";
        }

        if (dragging) {
            dragStart = { mx, my, hx: hex.x, hy: hex.y, hs: hex.size };
        }
    });

    canvas.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        // Update cursor
        if (isNearResizeHandle(mx, my)) {
            canvas.style.cursor = "nwse-resize";
        } else if (isInsideHex(mx, my)) {
            canvas.style.cursor = "move";
        } else {
            canvas.style.cursor = "crosshair";
        }

        if (!dragging) return;

        const dx = (mx - dragStart.mx) / imgScale;
        const dy = (my - dragStart.my) / imgScale;

        if (dragging === "move") {
            hex.x = dragStart.hx + dx;
            hex.y = dragStart.hy + dy;
        } else if (dragging === "resize") {
            // Resize from bottom-right: increase size based on diagonal movement
            const delta = (dx + dy) / 2;
            hex.size = Math.max(50, dragStart.hs + delta);
        }

        draw();
        updatePreview();
    });

    canvas.addEventListener("mouseup", () => { dragging = null; });
    canvas.addEventListener("mouseleave", () => { dragging = null; });

    // Pair navigation
    document.getElementById("prev-btn").addEventListener("click", () => {
        currentIndex = (currentIndex - 1 + pairs.length) % pairs.length;
        loadPair();
    });
    document.getElementById("next-btn").addEventListener("click", () => {
        currentIndex = (currentIndex + 1) % pairs.length;
        loadPair();
    });

    // Expression toggle
    document.querySelectorAll(".expr-toggle button").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".expr-toggle button").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentExpr = btn.dataset.expr;
            loadExpression();
        });
    });

    // Save
    document.getElementById("save-btn").addEventListener("click", saveCrop);

    // Window resize
    window.addEventListener("resize", () => {
        fitCanvasAndImage();
        draw();
    });
}

async function saveCrop() {
    const pair = pairs[currentIndex];
    const level = document.querySelector('input[name="save-level"]:checked').value;
    const exprChoice = document.querySelector('input[name="save-expr"]:checked').value;
    const expression = exprChoice === "current" ? currentExpr : "default";

    const resp = await fetch(`/api/crop/${pair.leader}/${pair.civ}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            level,
            expression,
            crop: { x: Math.round(hex.x), y: Math.round(hex.y), size: Math.round(hex.size) }
        })
    });
    const result = await resp.json();
    document.getElementById("save-status").textContent =
        result.ok ? `Saved to ${result.path.split("/").slice(-2).join("/")}` : "Error saving";

    // Refresh inheritance display
    const cropData = await (await fetch(`/api/crop/${pair.leader}/${pair.civ}`)).json();
    const exprData = cropData[currentExpr];
    if (exprData) {
        document.getElementById("inheritance-info").textContent = `Source: ${exprData.source}`;
    }
}

// ===== Start =====
init();
</script>
</body>
</html>
```

**Step 2: Verify the tool works end-to-end**

Run: `cd /Users/admin/work/civ7mod && python3 tools/crop_tool/server.py`
Open: `http://localhost:8000` in browser
Expected: Friedrich/egypt loads, hex overlay visible and draggable, preview updates live.

**Step 3: Commit**

```bash
git add tools/crop_tool/static/index.html
git commit -m "feat: crop tool frontend — draggable hex overlay with live preview"
```

---

### Task 3: Integrate crop_meta.json into postprocess.py

**Files:**
- Modify: `ai_generator/postprocess.py`

**Step 1: Add crop meta resolution function**

Add to `postprocess.py` after the imports:

```python
def load_crop_meta(leader_key: str, civ_key: str, expression: str) -> dict | None:
    """Load crop meta using cascade: civ/expression → civ/default → leader/expression → leader/default."""
    import json

    # Level 1: civ-specific
    civ_meta_path = os.path.join(GENERATED_DIR, leader_key, civ_key, "crop_meta.json")
    if os.path.isfile(civ_meta_path):
        with open(civ_meta_path) as f:
            meta = json.load(f)
        if expression in meta:
            return meta[expression]
        if "default" in meta:
            return meta["default"]

    # Level 2: leader default
    leader_meta_path = os.path.join(GENERATED_DIR, leader_key, "crop_meta.json")
    if os.path.isfile(leader_meta_path):
        with open(leader_meta_path) as f:
            meta = json.load(f)
        if expression in meta:
            return meta[expression]
        if "default" in meta:
            return meta["default"]

    return None
```

**Step 2: Add crop-from-meta function**

```python
def crop_from_meta(img: Image.Image, crop_meta: dict) -> Image.Image:
    """Crop image using saved crop_meta {x, y, size}.

    The crop_meta defines the hex bounding box in source image coordinates.
    Returns the cropped region at the hex aspect ratio.
    """
    x = crop_meta["x"]
    y = crop_meta["y"]
    size = crop_meta["size"]
    height = int(size * 45 / 32)

    img = img.convert("RGBA")
    # Clamp to image bounds
    img_w, img_h = img.size
    x = max(0, min(x, img_w - size))
    y = max(0, min(y, img_h - height))

    return img.crop((x, y, x + size, y + height))
```

**Step 3: Modify icon processing paths to use crop_meta**

In `_postprocess_chromakey`, `_postprocess_portrait`, and `_postprocess_fullbody`,
before calling `process_icons`, check for crop_meta and use it instead of
`crop_to_content` / `_pad_on_canvas` / `crop_head_region`.

For each expression image, replace the crop logic with:

```python
# Try crop_meta first, fall back to auto crop
meta = load_crop_meta(leader_key, civ_key, "neutral")
if meta:
    neutral_img = crop_from_meta(neutral_img, meta)
else:
    # existing auto-crop logic
    neutral_img = crop_to_content(neutral_img, ...)

meta_h = load_crop_meta(leader_key, civ_key, "happy")
if meta_h and happy_img:
    happy_img = crop_from_meta(happy_img, meta_h)
elif happy_img:
    # existing auto-crop

meta_a = load_crop_meta(leader_key, civ_key, "angry")
if meta_a and angry_img:
    angry_img = crop_from_meta(angry_img, meta_a)
elif angry_img:
    # existing auto-crop
```

**Step 4: Test postprocess with saved crop_meta**

First, use the crop tool to save a crop_meta.json for friedrich/egypt, then run:

```bash
python3 -m ai_generator.postprocess --leader friedrich --civ egypt --mode chromakey
```

Verify the resulting icon matches the preview from the crop tool.

**Step 5: Test fallback (no crop_meta)**

```bash
python3 -m ai_generator.postprocess --leader napoleon --civ egypt --mode fullbody
```

Expected: Works as before using auto-crop (no crop_meta.json for napoleon).

**Step 6: Commit**

```bash
git add ai_generator/postprocess.py
git commit -m "feat: postprocess reads crop_meta.json with cascade fallback"
```

---

### Task 4: Polish and edge cases

**Files:**
- Modify: `tools/crop_tool/static/index.html`
- Modify: `tools/crop_tool/server.py`

**Step 1: Add keyboard shortcuts**

In the frontend JS, add:
- Left/Right arrow: prev/next pair
- 1/2/3: switch expression (neutral/happy/angry)
- S: save with current settings
- +/-: resize hex by 10px

**Step 2: Add hex bounds clamping**

In the drag handler, clamp hex position so it doesn't go outside the source image bounds:
```javascript
hex.x = Math.max(0, Math.min(hex.x, sourceImg.width - hex.size));
hex.y = Math.max(0, Math.min(hex.y, sourceImg.height - hex.size * HEX_ASPECT));
```

**Step 3: Auto-initialize hex position for pairs without crop_meta**

When loading a pair with no crop_meta, instead of a fixed default, center the hex on the image and set size to ~40% of image width:
```javascript
hex.size = Math.round(sourceImg.width * 0.4);
hex.x = Math.round((sourceImg.width - hex.size) / 2);
hex.y = Math.round((sourceImg.height - hex.size * HEX_ASPECT) / 4);
```

**Step 4: Show saved/unsaved state**

Track whether hex has been modified since last load/save. Show indicator next to pair name.

**Step 5: Commit**

```bash
git add tools/crop_tool/
git commit -m "feat: crop tool polish — keyboard shortcuts, bounds clamping, auto-init"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Flask backend + API | `tools/crop_tool/server.py` |
| 2 | Frontend: canvas, hex overlay, preview, save | `tools/crop_tool/static/index.html` |
| 3 | postprocess.py reads crop_meta.json | `ai_generator/postprocess.py` |
| 4 | Polish: keys, clamping, auto-init | both |
