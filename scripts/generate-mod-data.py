#!/usr/bin/env python3
"""
Generate mod XML files from config and available images.

Reads config/leaders-civilizations.json and scans the images directory to
auto-generate loading-info-override.xml and leader-icons-override.xml
for all leaders that have images available.

Also regenerates the .modinfo with all required ImportFiles entries.

Usage:
    python3 generate-mod-data.py
    python3 generate-mod-data.py --dry-run
"""

import argparse
import json
import os
import sys
from xml.etree import ElementTree as ET
from xml.dom import minidom

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "leaders-civilizations.json")
MOD_DIR = os.path.join(PROJECT_DIR, "authentic-leaders")

MOD_ID = "authentic-leaders"
FS_PREFIX = f"fs://game/{MOD_ID}"

ICON_VARIANTS = [
    {"shape": "hex", "size": 256, "suffix": "", "context": None},
    {"shape": "hex", "size": 128, "suffix": "", "context": None},
    {"shape": "hex", "size": 128, "suffix": "_h", "context": "LEADER_HAPPY"},
    {"shape": "hex", "size": 128, "suffix": "_a", "context": "LEADER_ANGRY"},
    {"shape": "hex", "size": 64, "suffix": "", "context": None},
    {"shape": "circ", "size": 256, "suffix": "", "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 128, "suffix": "", "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 64, "suffix": "", "context": "CIRCLE_MASK"},
]


def prettify_xml(elem):
    """Return a pretty-printed XML string."""
    rough = ET.tostring(elem, encoding="unicode")
    parsed = minidom.parseString(rough)
    lines = parsed.toprettyxml(indent="\t", encoding=None)
    # Remove extra XML declaration added by minidom
    result = "\n".join(line for line in lines.split("\n") if line.strip() and not line.startswith("<?xml"))
    return '<?xml version="1.0" encoding="utf-8"?>\n' + result


def scan_available_images():
    """Scan the mod directory for available leader images."""
    loading_dir = os.path.join(MOD_DIR, "images", "loading")
    icons_dir = os.path.join(MOD_DIR, "icons")

    available = {"loading": {}, "icons": {}}

    # Scan loading screen images
    if os.path.isdir(loading_dir):
        for f in os.listdir(loading_dir):
            if f.endswith(".png") and f.startswith("lsl_"):
                # Parse: lsl_<leader_key>.png or lsl_<leader_key>_<civ_key>.png
                name = f[4:-4]  # strip lsl_ and .png
                parts = name.split("_", 1)
                leader_key = parts[0]
                # Check if this is a civ-specific variant
                # Look for pattern: <leader_key>_<civ_short> vs just <leader_key>
                available["loading"][name] = os.path.join("images", "loading", f)

    # Scan icon images
    if os.path.isdir(icons_dir):
        for leader_dir in os.listdir(icons_dir):
            leader_path = os.path.join(icons_dir, leader_dir)
            if os.path.isdir(leader_path) and leader_dir != ".":
                leader_icons = []
                for f in os.listdir(leader_path):
                    if f.endswith(".png"):
                        leader_icons.append(os.path.join("icons", leader_dir, f))
                if leader_icons:
                    available["icons"][leader_dir] = leader_icons

    return available


def generate_loading_info_xml(config, available):
    """Generate loading-info-override.xml."""
    root = ET.Element("Database")
    table = ET.SubElement(root, "LoadingInfo_Leaders")

    leaders_by_key = {l["icon_key"]: l for l in config["leaders"]}
    all_civs = {}
    for age_data in config["ages"].values():
        for civ in age_data["civilizations"]:
            short_key = civ["type"].lower().replace("civilization_", "")
            all_civs[short_key] = civ

    entries = []

    for img_name, img_path in sorted(available["loading"].items()):
        # Determine if this is a default or civ-specific image
        # Pattern: <leader_key> or <leader_key>_<civ_short>
        for leader in config["leaders"]:
            key = leader["icon_key"]
            if img_name == key:
                # Default loading screen for this leader (no civ override)
                entries.append({
                    "leader_type": leader["type"],
                    "image_path": f"{FS_PREFIX}/{img_path}",
                    "civ_override": None,
                })
                break
            elif img_name.startswith(key + "_"):
                civ_short = img_name[len(key) + 1:]
                civ_info = all_civs.get(civ_short)
                if civ_info:
                    entries.append({
                        "leader_type": leader["type"],
                        "image_path": f"{FS_PREFIX}/{img_path}",
                        "civ_override": civ_info["type"],
                    })
                break

    for entry in entries:
        # Default entries replace existing rows; civ-specific entries are new rows
        tag = "Replace" if entry["civ_override"] is None else "Row"
        row = ET.SubElement(table, tag)
        row.set("LeaderType", entry["leader_type"])
        row.set("LeaderImage", entry["image_path"])
        leader_key = entry["leader_type"].replace("LEADER_", "")
        row.set("LeaderText", f"LOC_LOADING_LEADER_INTRO_TEXT_{leader_key}")
        row.set("Audio", f"VO_Loading2_{leader_key}")
        if entry["civ_override"]:
            row.set("CivilizationTypeOverride", entry["civ_override"])

    return prettify_xml(root)


def generate_icon_xml(config, available):
    """Generate leader-icons-override.xml."""
    root = ET.Element("Database")
    icons = ET.SubElement(root, "IconDefinitions")

    for leader in config["leaders"]:
        key = leader["icon_key"]
        if key not in available["icons"]:
            continue

        available_files = set(os.path.basename(f) for f in available["icons"][key])

        for variant in ICON_VARIANTS:
            filename = f"lp_{variant['shape']}_{key}_{variant['size']}{variant['suffix']}.png"
            if filename not in available_files:
                continue

            replace = ET.SubElement(icons, "Replace")
            id_elem = ET.SubElement(replace, "ID")
            id_elem.text = leader["type"]
            path_elem = ET.SubElement(replace, "Path")
            path_elem.text = f"{FS_PREFIX}/icons/{key}/{filename}"
            size_elem = ET.SubElement(replace, "IconSize")
            size_elem.text = str(variant["size"])
            if variant["context"]:
                ctx_elem = ET.SubElement(replace, "Context")
                ctx_elem.text = variant["context"]

    return prettify_xml(root)


def generate_modinfo(config, available):
    """Generate the .modinfo file with all required ImportFiles."""
    all_files = set()

    # Collect all image files
    for img_path in available["loading"].values():
        all_files.add(img_path)
    for leader_key, icon_files in available["icons"].items():
        for f in icon_files:
            all_files.add(f)

    sorted_files = sorted(all_files)

    # Build modinfo XML as string (since it uses xmlns which ET handles awkwardly)
    import_items_shell = []
    import_items_game = []
    for f in sorted_files:
        item = f"          <Item>{f}</Item>"
        if f.startswith("icons/"):
            import_items_shell.append(item)
        import_items_game.append(item)

    shell_imports = "\n".join(import_items_shell)
    game_imports = "\n".join(import_items_game)

    modinfo = f'''<?xml version="1.0" encoding="utf-8"?>
<Mod id="{MOD_ID}" version="1" xmlns="ModInfo">

  <Properties>
    <Name>Authentic Leaders</Name>
    <Description>Replaces leader loading screen images and icons with civilization-specific artwork for a more historically authentic experience.</Description>
    <Authors>Custom</Authors>
    <AffectsSavedGames>0</AffectsSavedGames>
    <ShowInBrowser>1</ShowInBrowser>
    <EnabledByDefault>1</EnabledByDefault>
  </Properties>

  <Dependencies>
    <Mod id="base-standard" title="LOC_MODULE_BASE_STANDARD_NAME"/>
  </Dependencies>

  <ActionCriteria>
    <Criteria id="always">
      <AlwaysMet/>
    </Criteria>
  </ActionCriteria>

  <ActionGroups>
    <!-- Shell scope: icons visible in leader select / main menu -->
    <ActionGroup id="{MOD_ID}-shell" scope="shell" criteria="always">
      <Properties>
        <LoadOrder>200</LoadOrder>
      </Properties>
      <Actions>
        <ImportFiles>
{shell_imports}
        </ImportFiles>
        <UpdateIcons>
          <Item>icons/leader-icons-override.xml</Item>
        </UpdateIcons>
      </Actions>
    </ActionGroup>

    <!-- Game scope: loading screen images + in-game icons -->
    <ActionGroup id="{MOD_ID}-game" scope="game" criteria="always">
      <Properties>
        <LoadOrder>200</LoadOrder>
      </Properties>
      <Actions>
        <ImportFiles>
{game_imports}
        </ImportFiles>
        <UpdateDatabase>
          <Item>data/loading-info-override.xml</Item>
        </UpdateDatabase>
        <UpdateIcons>
          <Item>icons/leader-icons-override.xml</Item>
        </UpdateIcons>
      </Actions>
    </ActionGroup>
  </ActionGroups>

</Mod>'''

    return modinfo


def main():
    parser = argparse.ArgumentParser(description="Generate mod XML files from config and available images")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be generated without writing files")
    args = parser.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    available = scan_available_images()

    print(f"Found loading screen images: {len(available['loading'])}")
    for name in sorted(available['loading'].keys()):
        print(f"  - {name}")
    print(f"Found icon sets: {len(available['icons'])}")
    for key in sorted(available['icons'].keys()):
        print(f"  - {key} ({len(available['icons'][key])} files)")

    # Generate files
    loading_xml = generate_loading_info_xml(config, available)
    icon_xml = generate_icon_xml(config, available)
    modinfo = generate_modinfo(config, available)

    if args.dry_run:
        print("\n--- loading-info-override.xml ---")
        print(loading_xml)
        print("\n--- leader-icons-override.xml ---")
        print(icon_xml)
        print("\n--- authentic-leaders.modinfo ---")
        print(modinfo)
    else:
        loading_path = os.path.join(MOD_DIR, "data", "loading-info-override.xml")
        icon_path = os.path.join(MOD_DIR, "icons", "leader-icons-override.xml")
        modinfo_path = os.path.join(MOD_DIR, "authentic-leaders.modinfo")

        with open(loading_path, "w") as f:
            f.write(loading_xml)
        print(f"Written: {loading_path}")

        with open(icon_path, "w") as f:
            f.write(icon_xml)
        print(f"Written: {icon_path}")

        with open(modinfo_path, "w") as f:
            f.write(modinfo)
        print(f"Written: {modinfo_path}")

        print("\nMod data generation complete!")


if __name__ == "__main__":
    main()
