#!/usr/bin/env python3
"""Generate all mod data files from config and available images.

Scans authentic-leaders/ for available images and produces:
  - data/loading-info-override.sql   (loading screen DB entries)
  - icons/leader-icons-override.xml  (default icon overrides)
  - icons/leader-icons-civ-override.xml (civ-specific icon definitions)
  - authentic-leaders.modinfo        (mod manifest with all ImportFiles)

Usage:
    python3 generate-mod-data.py
    python3 generate-mod-data.py --dry-run
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
MOD_DIR = os.path.join(PROJECT_ROOT, "authentic-leaders")

MOD_ID = "authentic-leaders"
FS_PREFIX = f"fs://game/{MOD_ID}"

# Config type → Game DB type mapping (adjective → place name)
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

ICON_VARIANTS = [
    {"shape": "hex",  "size": 256, "suffix": "",   "context": None},
    {"shape": "hex",  "size": 128, "suffix": "",   "context": None},
    {"shape": "hex",  "size": 128, "suffix": "_h",  "context": "LEADER_HAPPY"},
    {"shape": "hex",  "size": 128, "suffix": "_a",  "context": "LEADER_ANGRY"},
    {"shape": "hex",  "size": 64,  "suffix": "",   "context": None},
    {"shape": "circ", "size": 256, "suffix": "",   "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 128, "suffix": "",   "context": "CIRCLE_MASK"},
    {"shape": "circ", "size": 64,  "suffix": "",   "context": "CIRCLE_MASK"},
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def build_civ_db_types(config):
    """Build civ_key → game DB type mapping."""
    db_types = {}
    for age_data in config["ages"].values():
        for civ in age_data["civilizations"]:
            civ_key = civ["civ_key"]
            config_type = civ["type"]
            db_types[civ_key] = CONFIG_TO_DB_TYPE.get(config_type, config_type)
    return db_types


def scan_leaders(config):
    """Scan mod dir for leaders that have images available.

    Returns list of dicts with leader info and available civ keys.
    """
    leaders = []
    loading_dir = os.path.join(MOD_DIR, "images", "loading")
    icons_dir = os.path.join(MOD_DIR, "icons")

    for leader in config["leaders"]:
        key = leader["icon_key"]
        leader_type = leader["type"]

        # Check for base loading screen
        base_loading = os.path.join(loading_dir, f"lsl_{key}.png")
        if not os.path.isfile(base_loading):
            continue

        # Find civ-specific loading screens
        civ_keys = []
        for f in sorted(os.listdir(loading_dir)):
            if f.startswith(f"lsl_{key}_") and f.endswith(".png"):
                civ_key = f[len(f"lsl_{key}_"):-4]
                civ_keys.append(civ_key)

        # Check for base icons
        base_icon = os.path.join(icons_dir, key, f"lp_hex_{key}_256.png")
        has_base_icons = os.path.isfile(base_icon)

        # Find civ-specific icon dirs
        icon_civs = []
        leader_icon_dir = os.path.join(icons_dir, key)
        if os.path.isdir(leader_icon_dir):
            for d in sorted(os.listdir(leader_icon_dir)):
                if os.path.isdir(os.path.join(leader_icon_dir, d)):
                    icon_civs.append(d)

        # Collect persona types from config
        persona_types = [p["type"] for p in leader.get("personas", [])]

        leaders.append({
            "key": key,
            "type": leader_type,
            "persona_types": persona_types,
            "civ_keys": civ_keys,
            "has_base_icons": has_base_icons,
            "icon_civs": icon_civs,
        })

    return leaders


def generate_sql(leaders, civ_db_types):
    """Generate loading-info-override.sql."""
    lines = [
        "-- Authentic Leaders - Loading screen overrides",
        "-- Auto-generated by generate-mod-data.py",
        "",
        "-- Restructure LoadingInfo_Leaders to support civilization-specific overrides.",
        "-- The original table has LeaderType as sole PK, preventing multiple rows per leader.",
        "-- We need composite PK (LeaderType, CivilizationTypeOverride) for civ-specific images.",
        "",
        "-- Step 1: Backup existing data",
        "CREATE TEMP TABLE _LIL_Backup AS SELECT * FROM LoadingInfo_Leaders;",
        "",
        "-- Step 2: Drop the original table (single-column PK)",
        "DROP TABLE IF EXISTS LoadingInfo_Leaders;",
        "",
        "-- Step 3: Recreate with composite primary key",
        "CREATE TABLE 'LoadingInfo_Leaders' (",
        "\t'LeaderType' TEXT NOT NULL,",
        "\t'AgeTypeOverride' TEXT,",
        "\t'Audio' TEXT,",
        "\t'CivilizationTypeOverride' TEXT,",
        "\t'LeaderImage' TEXT,",
        "\t'LeaderNameTextOverride' LOC_TEXT,",
        "\t'LeaderText' LOC_TEXT,",
        '\tPRIMARY KEY("LeaderType", "CivilizationTypeOverride"),',
        '\tFOREIGN KEY ("LeaderType") REFERENCES "Leaders"("LeaderType") ON DELETE CASCADE ON UPDATE CASCADE',
        ");",
        "",
        "-- Step 4: Restore all existing data",
        "INSERT INTO LoadingInfo_Leaders SELECT * FROM _LIL_Backup;",
        "",
        "-- Step 5: Clean up backup",
        "DROP TABLE _LIL_Backup;",
    ]

    for leader in leaders:
        key = leader["key"]
        ltype = leader["type"]

        # All leader types that need entries: base + personas
        all_types = [ltype] + leader.get("persona_types", [])

        for lt in all_types:
            lt_short = lt.replace("LEADER_", "")

            lines.append("")
            lines.append(f"-- === {lt} ===")
            lines.append("")

            # Update default loading screen
            lines.append(f"-- Default loading screen for {key} ({lt})")
            lines.append(f"UPDATE LoadingInfo_Leaders")
            lines.append(f"SET LeaderImage = '{FS_PREFIX}/images/loading/lsl_{key}.png'")
            lines.append(f"WHERE LeaderType = '{lt}' AND CivilizationTypeOverride IS NULL;")

            if leader["civ_keys"]:
                lines.append("")
                lines.append(f"-- Civ-specific loading screens for {key} ({lt})")
                for civ_key in leader["civ_keys"]:
                    db_type = civ_db_types.get(civ_key)
                    if not db_type:
                        lines.append(f"-- WARNING: unknown civ_key '{civ_key}', skipping")
                        continue
                    lines.append(
                        f"INSERT OR IGNORE INTO LoadingInfo_Leaders "
                        f"(LeaderType, CivilizationTypeOverride, LeaderText, LeaderImage, Audio) VALUES "
                        f"('{lt}', '{db_type}', "
                        f"'LOC_LOADING_LEADER_INTRO_TEXT_{lt_short}', "
                        f"'{FS_PREFIX}/images/loading/lsl_{key}_{civ_key}.png', "
                        f"'VO_Loading2_{lt_short}');"
                    )

    lines.append("")
    return "\n".join(lines)


def generate_default_icons_xml(leaders):
    """Generate leader-icons-override.xml (default icon <Replace> entries)."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<Database>", "\t<IconDefinitions>"]

    for leader in leaders:
        if not leader["has_base_icons"]:
            continue
        key = leader["key"]

        # All leader types that need icon entries: base + personas
        all_types = [leader["type"]] + leader.get("persona_types", [])

        for ltype in all_types:
            for v in ICON_VARIANTS:
                fname = f"lp_{v['shape']}_{key}_{v['size']}{v['suffix']}.png"
                lines.append("\t\t<Replace>")
                lines.append(f"\t\t\t<ID>{ltype}</ID>")
                lines.append(f"\t\t\t<Path>{FS_PREFIX}/icons/{key}/{fname}</Path>")
                lines.append(f"\t\t\t<IconSize>{v['size']}</IconSize>")
                if v["context"]:
                    lines.append(f"\t\t\t<Context>{v['context']}</Context>")
                lines.append("\t\t</Replace>")

    lines.append("\t</IconDefinitions>")
    lines.append("</Database>")
    return "\n".join(lines)


def generate_civ_icons_xml(leaders, civ_db_types):
    """Generate leader-icons-civ-override.xml (civ-specific icon <Row> entries)."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<Database>", "\t<IconDefinitions>"]

    for leader in leaders:
        key = leader["key"]
        ltype = leader["type"]

        for civ_key in leader["icon_civs"]:
            db_type = civ_db_types.get(civ_key)
            if not db_type:
                continue
            civ_suffix = db_type.replace("CIVILIZATION_", "")
            icon_id = f"{ltype}_{civ_suffix}"

            lines.append(f"\t\t<!-- {civ_suffix} -->")
            for v in ICON_VARIANTS:
                fname = (
                    f"lp_{v['shape']}_{key}_{civ_key}"
                    f"_{v['size']}{v['suffix']}.png"
                )
                lines.append("\t\t<Row>")
                lines.append(f"\t\t\t<ID>{icon_id}</ID>")
                lines.append(
                    f"\t\t\t<Path>{FS_PREFIX}/icons/{key}/{civ_key}/{fname}</Path>"
                )
                lines.append(f"\t\t\t<IconSize>{v['size']}</IconSize>")
                if v["context"]:
                    lines.append(f"\t\t\t<Context>{v['context']}</Context>")
                lines.append("\t\t</Row>")

    lines.append("\t</IconDefinitions>")
    lines.append("</Database>")
    return "\n".join(lines)


def generate_modinfo(leaders):
    """Generate authentic-leaders.modinfo."""
    shell_imports = []
    game_imports = []

    for leader in leaders:
        key = leader["key"]

        # Base icons (shell + game)
        if leader["has_base_icons"]:
            for v in ICON_VARIANTS:
                fname = f"lp_{v['shape']}_{key}_{v['size']}{v['suffix']}.png"
                path = f"icons/{key}/{fname}"
                shell_imports.append(path)
                game_imports.append(path)

        # Civ-specific icons (game only)
        for civ_key in leader["icon_civs"]:
            for v in ICON_VARIANTS:
                fname = (
                    f"lp_{v['shape']}_{key}_{civ_key}"
                    f"_{v['size']}{v['suffix']}.png"
                )
                game_imports.append(f"icons/{key}/{civ_key}/{fname}")

        # Loading screens (game only)
        game_imports.append(f"images/loading/lsl_{key}.png")
        for civ_key in leader["civ_keys"]:
            game_imports.append(f"images/loading/lsl_{key}_{civ_key}.png")

    shell_items = "\n".join(f"          <Item>{f}</Item>" for f in sorted(shell_imports))
    game_items = "\n".join(f"          <Item>{f}</Item>" for f in sorted(game_imports))

    return f'''<?xml version="1.0" encoding="utf-8"?>
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
{shell_items}
        </ImportFiles>
        <UpdateIcons>
          <Item>icons/leader-icons-override.xml</Item>
        </UpdateIcons>
      </Actions>
    </ActionGroup>

    <!-- Game scope: loading screen images + in-game icons + JS sort fix -->
    <ActionGroup id="{MOD_ID}-game" scope="game" criteria="always">
      <Properties>
        <LoadOrder>200</LoadOrder>
      </Properties>
      <Actions>
        <ImportFiles>
{game_items}
          <!-- JS override: fix sort order so civ-specific entries win over generic -->
          <Item>ui-next/screens/load-screen/load-screen-model.chunk.js</Item>
          <!-- UIScript for civ-specific icon swapping -->
          <Item>scripts/authentic-leaders-icons.js</Item>
        </ImportFiles>
        <UpdateDatabase>
          <Item>data/loading-info-override.sql</Item>
        </UpdateDatabase>
        <UpdateIcons>
          <Item>icons/leader-icons-override.xml</Item>
          <Item>icons/leader-icons-civ-override.xml</Item>
        </UpdateIcons>
        <UIScripts>
          <Item>scripts/authentic-leaders-icons.js</Item>
        </UIScripts>
      </Actions>
    </ActionGroup>
  </ActionGroups>

</Mod>'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate mod data files from config and available images"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing files")
    args = parser.parse_args()

    config = load_config()
    civ_db_types = build_civ_db_types(config)
    leaders = scan_leaders(config)

    print(f"Found {len(leaders)} leaders with images:")
    for l in leaders:
        print(f"  {l['key']}: {len(l['civ_keys'])} loading screens, "
              f"{'base icons' if l['has_base_icons'] else 'no base icons'}, "
              f"{len(l['icon_civs'])} civ icon sets")

    sql = generate_sql(leaders, civ_db_types)
    default_xml = generate_default_icons_xml(leaders)
    civ_xml = generate_civ_icons_xml(leaders, civ_db_types)
    modinfo = generate_modinfo(leaders)

    if args.dry_run:
        print(f"\nSQL: {sql.count('INSERT')} inserts, {sql.count('UPDATE')} updates")
        print(f"Default icons XML: {default_xml.count('<Replace>')} entries")
        print(f"Civ icons XML: {civ_xml.count('<Row>')} entries")
        total_imports = modinfo.count("<Item>")
        print(f"Modinfo: {total_imports} ImportFiles entries")
        return

    paths = {
        "data/loading-info-override.sql": sql,
        "icons/leader-icons-override.xml": default_xml,
        "icons/leader-icons-civ-override.xml": civ_xml,
        "authentic-leaders.modinfo": modinfo,
    }

    for rel_path, content in paths.items():
        full_path = os.path.join(MOD_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")
        print(f"  Written: {rel_path}")

    print("\nMod data generation complete!")


if __name__ == "__main__":
    main()
