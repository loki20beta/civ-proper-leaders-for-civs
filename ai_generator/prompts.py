"""Prompt construction for AI image generation.

Builds structured prompts for loading screens and icon headshots,
incorporating identity anchors, costume references, and attire descriptors.
"""


def build_loading_prompt(leader_name: str, civ_name: str, period: str,
                         attire: dict, setting: str,
                         has_costume_ref: bool = False) -> str:
    """Build a prompt for generating a loading screen image.

    Args:
        leader_name: Display name of the leader
        civ_name: Display name of the civilization
        period: Historical period string
        attire: Attire descriptor dict with clothing, headwear, accessories, forbidden, palette
        setting: Setting/backdrop description
        has_costume_ref: Whether a costume reference image is being provided

    Returns:
        Complete prompt string
    """
    forbidden = ", ".join(attire.get("forbidden", []))
    palette = ", ".join(attire.get("palette", []))

    lines = [
        f"Generate a full-body portrait of this leader dressed as a ruler of {civ_name}.",
        "",
        f"IDENTITY: This is {leader_name}. The first reference image shows their exact appearance.",
        "Preserve their face, skin tone, facial structure, hair color, and body proportions EXACTLY.",
        "Do NOT change their ethnicity, age, or physical features.",
        "",
        f"COSTUME: Dress them in {period} {civ_name} attire:",
        f"- Clothing: {attire['clothing']}",
        f"- Headwear: {attire['headwear']}",
        f"- Accessories: {attire['accessories']}",
    ]

    if forbidden:
        lines.append(f"Do NOT include: {forbidden}")

    if has_costume_ref:
        lines.extend([
            "",
            "COSTUME REFERENCE: The second reference image shows a leader wearing authentic "
            f"{civ_name} attire. Use it as a visual guide for garment style, textile patterns, "
            "and accessory details. Apply similar garments to this leader while respecting their "
            "body type and gender.",
        ])

    lines.extend([
        "",
        "STYLE: Match the painterly digital art style of Civilization VII game art.",
        f"Dramatic cinematic side lighting. Setting hints: {setting}.",
        "TRANSPARENT BACKGROUND — the character must be on a fully transparent background,",
        "exactly like the reference image provided. No solid color behind the character.",
        "Three-quarter view, standing pose showing full body.",
        f"Color palette: {palette}.",
        "",
        "OUTPUT: Generate an 800x1060 pixel RGBA PNG with transparent background,",
        "matching the exact dimensions and transparency of the reference image.",
    ])

    return "\n".join(lines)


def build_icon_prompt(expression: str, civ_name: str) -> str:
    """Build a prompt for generating an icon headshot.

    This is used as a follow-up in a multi-turn chat session after
    the loading screen has been generated, so the AI already has context
    about the character and costume.

    Args:
        expression: One of "neutral", "happy", "angry"
        civ_name: Display name of the civilization

    Returns:
        Complete prompt string
    """
    expr_descriptions = {
        "neutral": "calm, dignified, composed expression with a slight sense of authority",
        "happy": "warm satisfied smile, pleased expression, eyes slightly crinkled with genuine warmth",
        "angry": "stern fierce scowl, furrowed brows, intense disapproving glare, tight jaw",
    }

    expr_desc = expr_descriptions.get(expression, expr_descriptions["neutral"])

    lines = [
        f"Now create a close-up head-and-shoulders portrait of this same {civ_name} character.",
        "",
        f"Expression: {expr_desc}",
        "",
        "REQUIREMENTS:",
        f"- Keep the EXACT same {civ_name} outfit, headwear, and accessories from the loading screen.",
        "- Centered face, looking slightly toward camera.",
        "- Same painterly Civilization VII art style.",
        "- TRANSPARENT BACKGROUND — match the reference image transparency exactly.",
        "- Show from mid-chest up, head centered in frame.",
        "",
        "OUTPUT: 3:4 aspect ratio RGBA PNG with transparent background, matching reference dimensions.",
    ]

    return "\n".join(lines)


def build_reference_description(leader_name: str, leader_gender: str,
                                features: str = "") -> str:
    """Build a text description to supplement the identity reference image.

    Used when the AI needs extra guidance about the leader's identity.
    """
    lines = [
        f"The reference image shows {leader_name}, a {leader_gender} leader.",
    ]
    if features:
        lines.append(f"Key identifying features: {features}")
    lines.append("You MUST preserve these features exactly in the generated image.")
    return " ".join(lines)
