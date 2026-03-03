#!/usr/bin/env python3
"""Generate assets/manifest.json from config and filesystem state.

Reads config/leaders-civilizations.json, scans assets/ directories for
existing files, and produces a manifest tracking every leader, civilization,
and leader×civ pair with their asset status.
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
MANIFEST_PATH = os.path.join(ASSETS_DIR, "manifest.json")
MOD_DIR = os.path.join(PROJECT_ROOT, "authentic-leaders")

# Config type → Game DB type mapping.
# Config uses adjective forms; game database uses place-name forms.
CONFIG_TO_DB_TYPE = {
    "CIVILIZATION_AKSUMITE": "CIVILIZATION_AKSUM",
    "CIVILIZATION_EGYPTIAN": "CIVILIZATION_EGYPT",
    "CIVILIZATION_GREEK": "CIVILIZATION_GREECE",
    "CIVILIZATION_ACHAEMENID": "CIVILIZATION_PERSIA",
    "CIVILIZATION_ROMAN": "CIVILIZATION_ROME",
    "CIVILIZATION_ASSYRIAN": "CIVILIZATION_ASSYRIA",
    "CIVILIZATION_CARTHAGINIAN": "CIVILIZATION_CARTHAGE",
    "CIVILIZATION_TONGAN": "CIVILIZATION_TONGA",
    "CIVILIZATION_HAWAIIAN": "CIVILIZATION_HAWAII",
    "CIVILIZATION_MONGOLIAN": "CIVILIZATION_MONGOLIA",
    "CIVILIZATION_SPANISH": "CIVILIZATION_SPAIN",
    "CIVILIZATION_BULGARIAN": "CIVILIZATION_BULGARIA",
    "CIVILIZATION_ICELANDIC": "CIVILIZATION_ICELAND",
    "CIVILIZATION_AMERICAN": "CIVILIZATION_AMERICA",
    "CIVILIZATION_BUGANDAN": "CIVILIZATION_BUGANDA",
    "CIVILIZATION_MEXICAN": "CIVILIZATION_MEXICO",
    "CIVILIZATION_PRUSSIAN": "CIVILIZATION_PRUSSIA",
    "CIVILIZATION_RUSSIAN": "CIVILIZATION_RUSSIA",
    "CIVILIZATION_SIAMESE": "CIVILIZATION_SIAM",
    "CIVILIZATION_BRITISH": "CIVILIZATION_GREAT_BRITAIN",
    "CIVILIZATION_NEPALESE": "CIVILIZATION_NEPAL",
    "CIVILIZATION_REPUBLIC_OF_PIRATES": "CIVILIZATION_PIRATE_REPUBLIC",
    "CIVILIZATION_OTTOMAN": "CIVILIZATION_OTTOMANS",
}


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def file_status(path):
    """Return 'ready' if file exists at path, 'missing' otherwise."""
    return "ready" if os.path.isfile(os.path.join(PROJECT_ROOT, path)) else "missing"


def persona_key(leader_type, persona_type):
    """Derive short persona key from types.

    e.g. LEADER_ASHOKA + LEADER_ASHOKA_WORLD_RENOUNCER → world_renouncer
    """
    prefix = leader_type + "_"
    if persona_type.startswith(prefix):
        return persona_type[len(prefix):].lower()
    return persona_type.replace("LEADER_", "").lower()


def build_leaders(config):
    """Build leader entries from config."""
    leaders = {}
    for leader in config["leaders"]:
        icon_key = leader["icon_key"]
        ref_path = f"assets/leaders/{icon_key}/reference.png"
        entry = {
            "type": leader["type"],
            "name": leader["name"],
            "reference": ref_path,
            "reference_status": file_status(ref_path),
            "dlc": leader["dlc"],
        }
        if leader.get("personas"):
            personas = {}
            for p in leader["personas"]:
                pkey = persona_key(leader["type"], p["type"])
                p_ref = f"assets/leaders/{icon_key}/{pkey}.png"
                personas[pkey] = {
                    "type": p["type"],
                    "name": p["name"],
                    "reference": p_ref,
                    "reference_status": file_status(p_ref),
                }
            entry["personas"] = personas
        leaders[icon_key] = entry
    return leaders


def build_civilizations(config):
    """Build civilization entries from config."""
    civs = {}
    for age_id, age_data in config["ages"].items():
        for civ in age_data["civilizations"]:
            civ_key = civ["civ_key"]
            config_type = civ["type"]
            db_type = CONFIG_TO_DB_TYPE.get(config_type, config_type)
            bg_path = f"assets/civilizations/{civ_key}/background.png"
            civs[civ_key] = {
                "type": db_type,
                "config_type": config_type,
                "name": civ["name"],
                "age": age_id,
                "background": bg_path,
                "background_status": file_status(bg_path),
                "dlc": civ["dlc"],
            }
    return civs


def pair_loading_status(leader_key, civ_key):
    """Determine loading screen status: ready > stub > missing."""
    # AI-generated asset in assets/generated/
    generated = os.path.join(
        PROJECT_ROOT, "assets", "generated", leader_key, civ_key, "loading.png"
    )
    if os.path.isfile(generated):
        return "ready"
    # Stub asset in mod output directory
    stub = os.path.join(MOD_DIR, "images", "loading", f"lsl_{leader_key}_{civ_key}.png")
    if os.path.isfile(stub):
        return "stub"
    return "missing"


def pair_icon_status(leader_key, civ_key):
    """Determine icon status: ready > stub > missing."""
    # AI-generated source icon in assets/generated/
    generated = os.path.join(
        PROJECT_ROOT, "assets", "generated", leader_key, civ_key, "icon.png"
    )
    if os.path.isfile(generated):
        return "ready"
    # Stub icons in mod output directory (check for 256px hex icon as proxy)
    stub = os.path.join(
        MOD_DIR, "icons", leader_key, civ_key, f"lp_hex_{leader_key}_{civ_key}_256.png"
    )
    if os.path.isfile(stub):
        return "stub"
    return "missing"


def build_pairs(leaders, civs):
    """Build all leader×civ pair entries."""
    pairs = {}
    for leader_key in sorted(leaders.keys()):
        for civ_key in sorted(civs.keys()):
            pair_key = f"{leader_key}/{civ_key}"
            pairs[pair_key] = {
                "loading_status": pair_loading_status(leader_key, civ_key),
                "icon_status": pair_icon_status(leader_key, civ_key),
            }
    return pairs


def build_stats(leaders, civs, pairs):
    """Compute summary statistics."""
    ready = sum(
        1 for p in pairs.values()
        if p["loading_status"] == "ready" and p["icon_status"] == "ready"
    )
    stub = sum(
        1 for p in pairs.values()
        if "stub" in (p["loading_status"], p["icon_status"])
        and "missing" not in (p["loading_status"], p["icon_status"])
    )
    missing = len(pairs) - ready - stub
    return {
        "total_leaders": len(leaders),
        "total_civs": len(civs),
        "total_pairs": len(pairs),
        "ready_pairs": ready,
        "stub_pairs": stub,
        "missing_pairs": missing,
    }


def main():
    config = load_config()

    leaders = build_leaders(config)
    civs = build_civilizations(config)
    pairs = build_pairs(leaders, civs)
    stats = build_stats(leaders, civs, pairs)

    manifest = {
        "leaders": leaders,
        "civilizations": civs,
        "pairs": pairs,
        "stats": stats,
    }

    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Manifest generated: {MANIFEST_PATH}")
    print(f"  Leaders:  {stats['total_leaders']}")
    print(f"  Civs:     {stats['total_civs']}")
    print(f"  Pairs:    {stats['total_pairs']}")
    print(f"  Ready:    {stats['ready_pairs']}")
    print(f"  Stub:     {stats['stub_pairs']}")
    print(f"  Missing:  {stats['missing_pairs']}")


if __name__ == "__main__":
    main()
