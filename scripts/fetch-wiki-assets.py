#!/usr/bin/env python3
"""Fetch reference assets from the Civilization VII wiki.

Downloads:
  - Civilization backgrounds → assets/civilizations/{civ_key}/background.png
  - Leader three-quarter portraits → assets/leaders/{icon_key}/reference.png
  - Leader portrait icons → assets/leaders/{icon_key}/portrait_{mood}.png

Uses the MediaWiki API at civilization.fandom.com to resolve image URLs.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

WIKI_API = "https://civilization.fandom.com/api.php"
USER_AGENT = "Civ7AuthenticLeadersMod/1.0 (asset-fetcher)"

# Wiki filenames that don't follow the standard "{config_name} Background (Civ7)" pattern.
CIV_WIKI_NAMES = {
    "persia": ["Achaemenid Persian Background (Civ7).png"],
    "pirates": ["Pirate Background (Civ7).jpg"],
    "meiji": ["Meiji Japanese Background (Civ7).png"],
    "qing": ["Qing Background (Civ7).jpg"],
    "french_empire": ["French Imperial Background (Civ7).jpg"],
    "maurya": ["Mauryan Background (Civ7).png"],
    "iceland": ["Iceland Background (Civ7).jpg"],
}

# Wiki filenames that don't follow the standard "{leader_name} three-quarter length (Civ7)" pattern.
# Used for picking the default reference.png per leader.
LEADER_WIKI_NAMES = {
    "friedrich": ["Oblique three-quarter length (Civ7).png"],
    "genghis_khan": ["Genghis three-quarter length (Civ7).png"],
    "harriet_tubman": ["Harriet three-quarter length (Civ7).png"],
    "himiko": ["Wa three-quarter length (Civ7).png"],
    "jose_rizal": ["José Rizal three-quarter length (Civ7).png"],
    "napoleon": ["Napoleon (Emperor) three-quarter length (Civ7).png"],
    "xerxes": ["Xerxes Achaemenid three-quarter length (Civ7).png"],
}

# Wiki filenames for persona variants. Maps persona type → wiki filename.
# These get saved as assets/leaders/{icon_key}/{persona_key}.png alongside reference.png.
PERSONA_WIKI_NAMES = {
    "LEADER_ASHOKA_WORLD_RENOUNCER": "Ashoka, World Renouncer three-quarter length (Civ7).png",
    "LEADER_ASHOKA_WORLD_CONQUEROR": "Ashoka, World Conqueror three-quarter length (Civ7).png",
    "LEADER_FRIEDRICH_OBLIQUE": "Oblique three-quarter length (Civ7).png",
    "LEADER_FRIEDRICH_BAROQUE": "Baroque three-quarter length (Civ7).png",
    "LEADER_HIMIKO_QUEEN": "Wa three-quarter length (Civ7).png",
    "LEADER_HIMIKO_SHAMAN": "Shaman three-quarter length (Civ7).png",
    "LEADER_NAPOLEON_EMPEROR": "Napoleon (Emperor) three-quarter length (Civ7).png",
    "LEADER_NAPOLEON_REVOLUTIONARY": "Napoleon (Revolutionary) three-quarter length (Civ7).png",
    "LEADER_XERXES_KING": "Xerxes King three-quarter length (Civ7).png",
    "LEADER_XERXES_ACHAEMENID": "Xerxes Achaemenid three-quarter length (Civ7).png",
}

# Portrait icon overrides for non-standard wiki naming.
# Maps icon_key → {mood: [candidate_filenames]}.
# Leaders not in this dict use standard: "{config_name} portrait {mood} (Civ7).png"
PORTRAIT_WIKI_NAMES = {
    "ada_lovelace": {
        "neutral": ["Ada portrait neutral 256 (Civ7).png", "Ada portrait neutral (Civ7).png"],
        "happy": ["Ada portrait happy (Civ7).png"],
        "angry": ["Ada portrait angry (Civ7).png"],
    },
    "catherine": {
        "neutral": ["Catherine head portrait (neutral) (Civ7).png"],
        "happy": ["Catherine head portrait (happy) (Civ7).png"],
        "angry": ["Catherine head portrait (angry) (Civ7).png"],
    },
    "genghis_khan": {
        "neutral": ["Genghis portrait neutral (Civ7).png"],
        "happy": ["Genghis portrait happy (Civ7).png"],
        "angry": ["Genghis portrait angry (Civ7).png"],
    },
    "harriet_tubman": {
        "neutral": ["Harriet portrait neutral (Civ7).png"],
        "happy": ["Harriet portrait happy (Civ7).png"],
        "angry": ["Harriet portrait angry (Civ7).png"],
    },
    "jose_rizal": {
        "neutral": ["José portrait neutral (Civ7).png"],
        "happy": ["José portrait happy (Civ7).png"],
        "angry": ["José portrait angry (Civ7).png"],
    },
    "simon_bolivar": {
        "neutral": ["Simón portrait neutral (Civ7).png"],
        "happy": ["Simón portrait happy (Civ7).png"],
        "angry": ["Simón portrait angry (Civ7).png"],
    },
    # Persona-only leaders: use first persona's portrait as base
    "ashoka": {
        "neutral": ["Ashoka, World Conqueror portrait neutral (Civ7).png"],
        "happy": ["Ashoka, World Conqueror portrait happy (Civ7).png"],
        "angry": ["Ashoka, World Conqueror portrait angry (Civ7).png"],
    },
    "friedrich": {
        "neutral": ["Friedrich (Oblique) portrait neutral (Civ7).png"],
        "happy": ["Friedrich (Oblique) portrait happy (Civ7).png"],
        "angry": ["Friedrich (Oblique) portrait angry (Civ7).png"],
    },
    "himiko": {
        "neutral": ["Himiko Queen portrait neutral (Civ7).png"],
        "happy": ["Himiko Queen portrait happy (Civ7).png"],
        "angry": ["Himiko Queen portrait angry (Civ7).png"],
    },
    "napoleon": {
        "neutral": ["Napoleon Emperor portrait neutral (Civ7).png"],
        "happy": ["Napoleon Emperor portrait happy (Civ7).png"],
        "angry": ["Napoleon Emperor portrait angry (Civ7).png"],
    },
    "xerxes": {
        "neutral": ["Xerxes Achaemenid portrait neutral (Civ7).png"],
        "happy": ["Xerxes Achaemenid portrait happy (Civ7).png"],
        "angry": ["Xerxes Achaemenid portrait angry (Civ7).png"],
    },
}

PORTRAIT_MOODS = ["neutral", "happy", "angry"]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def wiki_api_query(params):
    """Make a MediaWiki API request and return parsed JSON."""
    params["format"] = "json"
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def resolve_image_urls(filenames):
    """Query MediaWiki API to get download URLs for a list of image filenames.

    Returns dict mapping filename → URL for files that exist on the wiki.
    """
    results = {}
    for i in range(0, len(filenames), 50):
        batch = filenames[i : i + 50]
        titles = "|".join(f"File:{f}" for f in batch)
        data = wiki_api_query(
            {"action": "query", "titles": titles, "prop": "imageinfo", "iiprop": "url"}
        )
        for page_id, page in data.get("query", {}).get("pages", {}).items():
            if int(page_id) > 0 and "imageinfo" in page:
                fname = page["title"].replace("File:", "")
                results[fname] = page["imageinfo"][0]["url"]
    return results


def download_file(url, dest_path):
    """Download a URL to a local file."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        with open(dest_path, "wb") as f:
            f.write(resp.read())


def build_civ_candidates(config):
    """Build candidate wiki filenames for each civilization background.

    Returns list of (civ_key, dest_path, [candidate_filenames]).
    """
    candidates = []
    for age_id, age_data in config["ages"].items():
        for civ in age_data["civilizations"]:
            civ_key = civ["civ_key"]
            dest = os.path.join(ASSETS_DIR, "civilizations", civ_key, "background.png")
            name = civ["name"]

            # Start with override names if any
            filenames = list(CIV_WIKI_NAMES.get(civ_key, []))
            # Then try standard pattern with both extensions
            filenames.append(f"{name} Background (Civ7).png")
            filenames.append(f"{name} Background (Civ7).jpg")

            candidates.append((civ_key, dest, filenames))
    return candidates


def build_leader_candidates(config):
    """Build candidate wiki filenames for each leader portrait.

    Returns list of (icon_key, dest_path, [candidate_filenames]).
    """
    candidates = []
    for leader in config["leaders"]:
        icon_key = leader["icon_key"]
        dest = os.path.join(ASSETS_DIR, "leaders", icon_key, "reference.png")
        name = leader["name"]

        # Start with override names if any
        filenames = list(LEADER_WIKI_NAMES.get(icon_key, []))
        # Then try base leader name
        filenames.append(f"{name} three-quarter length (Civ7).png")
        filenames.append(f"{name} three-quarter length (Civ7).jpg")
        # Then try persona names
        for persona in leader.get("personas", []):
            pname = persona["name"]
            filenames.append(f"{pname} three-quarter length (Civ7).png")
            filenames.append(f"{pname} three-quarter length (Civ7).jpg")

        candidates.append((icon_key, dest, filenames))
    return candidates


def persona_key(leader_type, persona_type):
    """Derive short persona key from types. e.g. LEADER_ASHOKA + LEADER_ASHOKA_WORLD_RENOUNCER → world_renouncer"""
    prefix = leader_type + "_"
    if persona_type.startswith(prefix):
        return persona_type[len(prefix):].lower()
    return persona_type.replace("LEADER_", "").lower()


def build_persona_candidates(config):
    """Build candidates for persona variant images.

    Returns list of (display_key, dest_path, [candidate_filenames]).
    """
    candidates = []
    for leader in config["leaders"]:
        if not leader.get("personas"):
            continue
        icon_key = leader["icon_key"]
        for persona in leader["personas"]:
            ptype = persona["type"]
            pkey = persona_key(leader["type"], ptype)
            dest = os.path.join(ASSETS_DIR, "leaders", icon_key, f"{pkey}.png")
            display = f"{icon_key}/{pkey}"

            # Use override if available, otherwise try the persona name from config
            if ptype in PERSONA_WIKI_NAMES:
                filenames = [PERSONA_WIKI_NAMES[ptype]]
            else:
                pname = persona["name"]
                filenames = [
                    f"{pname} three-quarter length (Civ7).png",
                    f"{pname} three-quarter length (Civ7).jpg",
                ]
            candidates.append((display, dest, filenames))
    return candidates


def build_portrait_candidates(config):
    """Build candidate wiki filenames for leader portrait icons.

    Downloads neutral, happy, and angry portrait icons used for in-game icons.
    Returns list of (display_key, dest_path, [candidate_filenames]).
    """
    candidates = []
    for leader in config["leaders"]:
        icon_key = leader["icon_key"]
        name = leader["name"]
        overrides = PORTRAIT_WIKI_NAMES.get(icon_key, {})

        for mood in PORTRAIT_MOODS:
            dest = os.path.join(ASSETS_DIR, "leaders", icon_key, f"portrait_{mood}.png")
            display = f"{icon_key}/portrait_{mood}"

            # Start with override filenames if any
            filenames = list(overrides.get(mood, []))

            # For neutral, try 256 variant first, then standard
            if mood == "neutral":
                filenames.append(f"{name} portrait neutral 256 (Civ7).png")
            filenames.append(f"{name} portrait {mood} (Civ7).png")

            candidates.append((display, dest, filenames))
    return candidates


def fetch_assets(candidates, asset_type, dry_run=False, force=False):
    """Resolve wiki URLs and download assets for a list of candidates.

    Returns (downloaded_count, skipped_count, failed_keys).
    """
    # Collect all candidate filenames for bulk API query
    all_filenames = []
    for _key, _dest, filenames in candidates:
        all_filenames.extend(filenames)

    if not all_filenames:
        return 0, 0, []

    print(f"\nResolving {asset_type} ({len(candidates)} items, "
          f"{len(all_filenames)} candidate filenames)...")
    found_urls = resolve_image_urls(all_filenames)
    print(f"  {len(found_urls)} images found on wiki\n")

    downloaded = 0
    skipped = 0
    failed = []

    for key, dest, filenames in candidates:
        if os.path.isfile(dest) and not force:
            print(f"  SKIP  {key} (already exists)")
            skipped += 1
            continue

        # Find first matching candidate
        url = None
        matched = None
        for fname in filenames:
            if fname in found_urls:
                url = found_urls[fname]
                matched = fname
                break

        if url is None:
            print(f"  MISS  {key}")
            failed.append(key)
            continue

        if dry_run:
            print(f"  WOULD {key} <- {matched}")
            downloaded += 1
            continue

        try:
            download_file(url, dest)
            size_kb = os.path.getsize(dest) / 1024
            print(f"  OK    {key} <- {matched} ({size_kb:.0f} KB)")
            downloaded += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  FAIL  {key}: {e}")
            failed.append(key)

    action = "Would download" if dry_run else "Downloaded"
    print(f"\n{asset_type}: {action} {downloaded}, skipped {skipped}, "
          f"missing {len(failed)}")
    if failed:
        print(f"  Not on wiki: {', '.join(failed)}")

    return downloaded, skipped, failed


def main():
    parser = argparse.ArgumentParser(
        description="Fetch reference assets from the Civ7 wiki"
    )
    parser.add_argument("--civs", action="store_true", help="Download civ backgrounds only")
    parser.add_argument("--leaders", action="store_true", help="Download leader portraits only")
    parser.add_argument("--portraits", action="store_true", help="Download leader portrait icons only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    if not args.civs and not args.leaders and not args.portraits:
        args.civs = True
        args.leaders = True
        args.portraits = True

    config = load_config()

    if args.civs:
        civ_candidates = build_civ_candidates(config)
        fetch_assets(civ_candidates, "Civilization backgrounds", args.dry_run, args.force)

    if args.leaders:
        leader_candidates = build_leader_candidates(config)
        fetch_assets(leader_candidates, "Leader portraits", args.dry_run, args.force)

        persona_candidates = build_persona_candidates(config)
        if persona_candidates:
            fetch_assets(persona_candidates, "Persona variants", args.dry_run, args.force)

    if args.portraits:
        portrait_candidates = build_portrait_candidates(config)
        fetch_assets(portrait_candidates, "Portrait icons", args.dry_run, args.force)

    if not args.dry_run:
        print("\nRun 'python3 scripts/generate-manifest.py' to update the manifest.")


if __name__ == "__main__":
    main()
