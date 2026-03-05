"""Prompt construction for AI image generation.

Uses Gemini's image editing capability: pass original image + edit prompt.
Each request is independent — no multi-turn context.
"""


def build_loading_prompt(leader_name: str, civ_name: str, period: str,
                         attire: dict, setting: str,
                         has_costume_ref: bool = False) -> str:
    """Build an edit prompt for a loading screen image."""
    forbidden = ", ".join(attire.get("forbidden", []))
    palette = ", ".join(attire.get("palette", []))

    lines = [
        f"This is a game loading screen graphic showing a historical leader.",
        f"Using the provided image, change only the clothing, headwear, and accessories "
        f"to {period} {civ_name} attire:",
        f"- Clothing: {attire['clothing']}",
        f"- Headwear: {attire['headwear']}",
        f"- Accessories: {attire['accessories']}",
        f"- Colors: {palette}",
    ]

    if forbidden:
        lines.append(f"- Avoid: {forbidden}")

    if has_costume_ref:
        lines.append(f"The second image shows authentic {civ_name} attire for reference.")

    lines.append(
        "Keep everything else in the image exactly the same, preserving the original "
        "style, lighting, and composition."
    )

    return "\n".join(lines)


def build_icon_prompt(expression: str, civ_name: str, period: str,
                      attire: dict) -> str:
    """Build an edit prompt for an icon headshot.

    Each icon is an independent request with its own attire description.
    """
    palette = ", ".join(attire.get("palette", []))

    expr_context = {
        "neutral": "a calm composed expression",
        "happy": "a pleased smiling expression",
        "angry": "an angry scowling expression",
    }
    expr_desc = expr_context.get(expression, "a neutral expression")

    lines = [
        f"This is a small in-game portrait icon of a character with {expr_desc}, "
        f"used during gameplay.",
        f"Using the provided image, change the headwear (if any) and visible part of clothing "
        f"to {period} {civ_name} attire:",
        f"- Clothing: {attire['clothing']}",
        f"- Headwear: {attire['headwear']}",
        f"- Colors: {palette}",
        "Keep everything else in the image exactly the same, preserving the original "
        "style, lighting, and composition.",
    ]

    return "\n".join(lines)


def build_reference_description(leader_name: str, leader_gender: str,
                                features: str = "") -> str:
    """Build a text description to supplement the identity reference image."""
    lines = [
        f"The reference image shows {leader_name}, a {leader_gender} leader.",
    ]
    if features:
        lines.append(f"Key identifying features: {features}")
    lines.append("You MUST preserve these features exactly in the generated image.")
    return " ".join(lines)
