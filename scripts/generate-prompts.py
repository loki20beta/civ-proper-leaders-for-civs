#!/usr/bin/env python3
"""
Generate AI image generation prompts for all leader+civilization combinations.

Reads config/leaders-civilizations.json and outputs structured prompts
suitable for Midjourney, DALL-E 3, Stable Diffusion, etc.

Usage:
    python3 generate-prompts.py [--leader LEADER_KEY] [--format midjourney|dalle|sd]
    python3 generate-prompts.py --output prompts.txt
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "config", "leaders-civilizations.json")

# Civilization visual descriptors for AI prompts
CIV_DESCRIPTORS = {
    "CIVILIZATION_ROMAN": {
        "era": "ancient Roman",
        "attire": "wearing Roman imperial toga and laurel wreath, purple and gold robes",
        "setting": "Roman columns, marble architecture, Roman eagle standards",
        "palette": "deep red, gold, marble white"
    },
    "CIVILIZATION_EGYPTIAN": {
        "era": "ancient Egyptian",
        "attire": "wearing Egyptian royal headdress and ceremonial collar, linen robes",
        "setting": "pyramids, hieroglyphics, Nile river, papyrus",
        "palette": "gold, turquoise, sandy beige, lapis blue"
    },
    "CIVILIZATION_GREEK": {
        "era": "ancient Greek",
        "attire": "wearing Greek chiton and olive wreath, draped white cloth",
        "setting": "Parthenon, Greek columns, olive groves, Aegean sea",
        "palette": "white, blue, olive green, terracotta"
    },
    "CIVILIZATION_HAN": {
        "era": "Han dynasty Chinese",
        "attire": "wearing Han dynasty silk robes and ceremonial headpiece, jade ornaments",
        "setting": "Chinese palace, silk banners, Great Wall in distance",
        "palette": "red, gold, jade green, imperial yellow"
    },
    "CIVILIZATION_KHMER": {
        "era": "ancient Khmer",
        "attire": "wearing Khmer royal crown and ornate gold jewelry, silk sampot",
        "setting": "Angkor Wat temple, tropical vegetation, stone carvings",
        "palette": "gold, stone gray, jungle green, saffron"
    },
    "CIVILIZATION_MAURYA": {
        "era": "Mauryan Empire",
        "attire": "wearing Mauryan royal turban and jeweled ornaments, cotton dhoti",
        "setting": "Indian palace, Ashoka pillar, lotus gardens",
        "palette": "saffron, white, deep blue, gold"
    },
    "CIVILIZATION_MAYA": {
        "era": "ancient Maya",
        "attire": "wearing Maya jade headdress and quetzal feathers, elaborate ear ornaments",
        "setting": "Maya pyramid, jungle, carved stelae, cenote",
        "palette": "jade green, turquoise, red, stone gray"
    },
    "CIVILIZATION_MISSISSIPPIAN": {
        "era": "Mississippian culture",
        "attire": "wearing shell gorget and feathered mantle, copper ornaments",
        "setting": "earthen mound, river valley, ceremonial plaza",
        "palette": "earth brown, copper, sky blue, forest green"
    },
    "CIVILIZATION_ACHAEMENID": {
        "era": "Achaemenid Persian",
        "attire": "wearing Persian royal tiara and flowing robes, gold arm bands",
        "setting": "Persepolis columns, Persian relief carvings, royal garden",
        "palette": "royal blue, gold, stone gray, deep purple"
    },
    "CIVILIZATION_AKSUMITE": {
        "era": "Kingdom of Aksum",
        "attire": "wearing Aksumite royal robes and crown, gold cross pendant",
        "setting": "Aksum obelisks, Ethiopian highlands, ancient church",
        "palette": "gold, deep red, green, stone gray"
    },
    "CIVILIZATION_ABBASID": {
        "era": "Abbasid Caliphate",
        "attire": "wearing Abbasid black and gold robes, turban with jeweled brooch",
        "setting": "Islamic geometric architecture, Baghdad skyline, ornate library",
        "palette": "black, gold, deep blue, white"
    },
    "CIVILIZATION_CHOLA": {
        "era": "Chola dynasty",
        "attire": "wearing Chola gold crown and silk dhoti, elaborate gold jewelry",
        "setting": "Brihadeeswarar temple, South Indian architecture, naval fleet",
        "palette": "bronze, gold, temple red, deep blue"
    },
    "CIVILIZATION_HAWAIIAN": {
        "era": "ancient Hawaiian",
        "attire": "wearing Hawaiian feather cloak (ahu ula) and mahiole helmet",
        "setting": "volcanic island, tropical ocean, tiki carvings, palm trees",
        "palette": "red, yellow feathers, ocean blue, volcanic black"
    },
    "CIVILIZATION_INCA": {
        "era": "Incan Empire",
        "attire": "wearing Sapa Inca royal fringed headband and vicuna wool tunic, gold earspools",
        "setting": "Machu Picchu, Andes mountains, Incan stone walls, terraces",
        "palette": "gold, red, mountain blue, stone gray"
    },
    "CIVILIZATION_MAJAPAHIT": {
        "era": "Majapahit Empire",
        "attire": "wearing Javanese royal crown and batik sarong, gold ornaments",
        "setting": "Javanese temple, tropical garden, Majapahit court",
        "palette": "gold, batik brown, tropical green, temple red"
    },
    "CIVILIZATION_MING": {
        "era": "Ming dynasty Chinese",
        "attire": "wearing Ming dynasty dragon robe and winged crown, jade belt",
        "setting": "Forbidden City, Chinese dragon motifs, porcelain",
        "palette": "imperial yellow, dragon red, blue porcelain, gold"
    },
    "CIVILIZATION_MONGOLIAN": {
        "era": "Mongol Empire",
        "attire": "wearing Mongol leather armor and fur-lined deel, horsehair crest helmet",
        "setting": "vast steppe, Mongol yurt, cavalry banners, endless grassland",
        "palette": "leather brown, sky blue, grass green, fur gray"
    },
    "CIVILIZATION_NORMAN": {
        "era": "medieval Norman",
        "attire": "wearing Norman chainmail and surcoat, heraldic shield, iron crown",
        "setting": "medieval castle, stone keep, Norman church, Bayeux tapestry style",
        "palette": "chainmail silver, heraldic red and blue, stone gray"
    },
    "CIVILIZATION_SONGHAI": {
        "era": "Songhai Empire",
        "attire": "wearing Songhai royal robes and turban, gold ornaments",
        "setting": "Timbuktu mosque, Niger River, Saharan trading post",
        "palette": "desert sand, gold, indigo blue, mud brown"
    },
    "CIVILIZATION_SPANISH": {
        "era": "Spanish Empire",
        "attire": "wearing Spanish conquistador armor and ruff collar, cross pendant",
        "setting": "Spanish galleon, Alhambra, New World discovery",
        "palette": "Castilian red, gold, dark steel, white ruff"
    },
    "CIVILIZATION_AMERICAN": {
        "era": "early American",
        "attire": "wearing American colonial-era frock coat and cravat, tricorn hat",
        "setting": "Independence Hall, American flag, colonial architecture",
        "palette": "navy blue, white, red, parchment beige"
    },
    "CIVILIZATION_BUGANDAN": {
        "era": "Kingdom of Buganda",
        "attire": "wearing Bugandan bark cloth robes and royal regalia, beaded crown",
        "setting": "Bugandan palace, Lake Victoria, tropical gardens",
        "palette": "bark brown, lake blue, green, royal gold"
    },
    "CIVILIZATION_FRENCH_EMPIRE": {
        "era": "French Empire",
        "attire": "wearing Napoleonic-era French military uniform with epaulettes, bicorne hat",
        "setting": "Versailles, Arc de Triomphe, French tricolor banners",
        "palette": "French blue, white, red, gold epaulettes"
    },
    "CIVILIZATION_MEIJI": {
        "era": "Meiji Japan",
        "attire": "wearing Meiji-era Japanese military uniform blended with traditional elements, chrysanthemum crest",
        "setting": "Japanese castle, cherry blossoms, rising sun, modernizing Japan",
        "palette": "imperial red, white, black, gold chrysanthemum"
    },
    "CIVILIZATION_MEXICAN": {
        "era": "independent Mexico",
        "attire": "wearing Mexican military uniform with sash, eagle and serpent emblem",
        "setting": "Mexican cathedral, agave fields, eagle on cactus symbol",
        "palette": "green, white, red, gold eagle"
    },
    "CIVILIZATION_MUGHAL": {
        "era": "Mughal Empire",
        "attire": "wearing Mughal jeweled turban and elaborate jama robe, pearl strings",
        "setting": "Taj Mahal, Mughal garden, ornate marble inlay",
        "palette": "marble white, emerald green, ruby red, gold"
    },
    "CIVILIZATION_PRUSSIAN": {
        "era": "Kingdom of Prussia",
        "attire": "wearing Prussian military uniform with iron cross, spiked pickelhaube",
        "setting": "Brandenburg Gate, Prussian parade ground, iron eagle standard",
        "palette": "Prussian blue, iron black, white, silver"
    },
    "CIVILIZATION_QING": {
        "era": "Qing dynasty Chinese",
        "attire": "wearing Qing dynasty dragon robe with Mandarin collar, court beads",
        "setting": "Forbidden City, dragon screen, Qing court",
        "palette": "imperial yellow, dragon blue, red, jade"
    },
    "CIVILIZATION_RUSSIAN": {
        "era": "Russian Empire",
        "attire": "wearing Russian imperial uniform and sash, double-headed eagle medal",
        "setting": "Winter Palace, St. Petersburg, onion dome churches, snow",
        "palette": "imperial white, gold, deep red, black eagle"
    },
    "CIVILIZATION_SIAMESE": {
        "era": "Kingdom of Siam",
        "attire": "wearing Siamese royal chada crown and silk chut thai, gold ornaments",
        "setting": "Thai temple (wat), golden spires, lotus pond, elephants",
        "palette": "temple gold, royal purple, white lotus, emerald"
    },
    "CIVILIZATION_BRITISH": {
        "era": "British Empire",
        "attire": "wearing Victorian British military uniform with medals, pith helmet or crown",
        "setting": "Houses of Parliament, British warship, Union Jack",
        "palette": "navy blue, red, white, gold"
    },
    "CIVILIZATION_OTTOMAN": {
        "era": "Ottoman Empire",
        "attire": "wearing Ottoman Sultan's kaftan and jeweled turban, tughra symbol",
        "setting": "Topkapi Palace, Blue Mosque, Ottoman court, tulips",
        "palette": "Ottoman red, gold, white, turquoise tiles"
    },
    "CIVILIZATION_QAJAR": {
        "era": "Qajar Persia",
        "attire": "wearing Qajar tall astrakhan hat and jeweled sash, ornate coat",
        "setting": "Qajar palace, Persian miniature style, rose garden",
        "palette": "deep red, gold, turquoise, black astrakhan"
    },
}

# Leader visual descriptors
LEADER_DESCRIPTORS = {
    "amina": {"gender": "female", "ethnicity": "West African", "age": "30s warrior queen", "features": "strong jawline, determined expression, braided hair"},
    "ashoka": {"gender": "male", "ethnicity": "South Asian", "age": "middle-aged emperor", "features": "contemplative expression, shaved head, serene face"},
    "augustus": {"gender": "male", "ethnicity": "Roman/Mediterranean", "age": "young emperor in 30s", "features": "clean-shaven, aquiline nose, curly hair, regal bearing"},
    "benjamin_franklin": {"gender": "male", "ethnicity": "European American", "age": "elderly statesman", "features": "balding with long hair, round spectacles, wise expression"},
    "catherine": {"gender": "female", "ethnicity": "European/Russian", "age": "middle-aged empress", "features": "powdered wig, regal posture, sharp intelligent eyes"},
    "charlemagne": {"gender": "male", "ethnicity": "Frankish/European", "age": "mature king with beard", "features": "long beard, broad shoulders, commanding presence, crown"},
    "confucius": {"gender": "male", "ethnicity": "Chinese", "age": "elderly sage", "features": "long white beard, traditional Chinese scholar appearance, kind eyes"},
    "friedrich": {"gender": "male", "ethnicity": "German/Prussian", "age": "middle-aged king", "features": "powdered wig, military bearing, sharp features"},
    "harriet_tubman": {"gender": "female", "ethnicity": "African American", "age": "middle-aged woman", "features": "determined expression, headscarf, strong presence"},
    "hatshepsut": {"gender": "female", "ethnicity": "Egyptian", "age": "regal pharaoh", "features": "Egyptian eye makeup, ceremonial crown, graceful bearing"},
    "himiko": {"gender": "female", "ethnicity": "Japanese", "age": "mystical queen", "features": "long dark hair, ceremonial ornaments, otherworldly expression"},
    "ibn_battuta": {"gender": "male", "ethnicity": "Moroccan/North African", "age": "young traveler", "features": "turban, trimmed beard, curious adventurous expression"},
    "isabella": {"gender": "female", "ethnicity": "Spanish/European", "age": "middle-aged queen", "features": "auburn hair, crown, pious but determined expression"},
    "jose_rizal": {"gender": "male", "ethnicity": "Filipino", "age": "young intellectual", "features": "neatly combed dark hair, thin mustache, scholarly appearance"},
    "lafayette": {"gender": "male", "ethnicity": "French/European", "age": "young nobleman", "features": "powdered wig, French military uniform, idealistic expression"},
    "machiavelli": {"gender": "male", "ethnicity": "Italian", "age": "middle-aged diplomat", "features": "sharp features, dark hair, cunning expression, dark robes"},
    "napoleon": {"gender": "male", "ethnicity": "French/Corsican", "age": "young general", "features": "distinctive Napoleon haircut, strong chin, intense gaze"},
    "pachacuti": {"gender": "male", "ethnicity": "Quechua/Incan", "age": "powerful emperor", "features": "royal Incan earspools, feathered crown, commanding presence"},
    "tecumseh": {"gender": "male", "ethnicity": "Shawnee/Native American", "age": "warrior chief", "features": "traditional Shawnee appearance, feather ornaments, fierce expression"},
    "trung_trac": {"gender": "female", "ethnicity": "Vietnamese", "age": "young warrior", "features": "long dark hair, traditional Vietnamese appearance, fierce determination"},
    "xerxes": {"gender": "male", "ethnicity": "Persian", "age": "young king", "features": "elaborate Persian beard, tall stature, regal bearing"},
    "ada_lovelace": {"gender": "female", "ethnicity": "British/European", "age": "young Victorian woman", "features": "dark curly hair, Victorian dress, intelligent expression"},
    "simon_bolivar": {"gender": "male", "ethnicity": "Venezuelan/South American", "age": "young revolutionary general", "features": "dark curly hair, military uniform, passionate expression"},
    "genghis_khan": {"gender": "male", "ethnicity": "Mongol", "age": "mature warrior", "features": "long braided hair, fur-lined armor, piercing eyes"},
    "lakshmibai": {"gender": "female", "ethnicity": "Indian", "age": "young warrior queen", "features": "sari and armor, determined expression, sword-wielding"},
    "edward_teach": {"gender": "male", "ethnicity": "British", "age": "fearsome pirate", "features": "massive black beard, wild hair, intimidating presence"},
    "sayyida_al_hurra": {"gender": "female", "ethnicity": "Moroccan", "age": "regal pirate queen", "features": "elegant yet fierce, head covering, commanding presence"},
    "gilgamesh": {"gender": "male", "ethnicity": "Mesopotamian/Sumerian", "age": "legendary hero king", "features": "elaborate curled beard, muscular build, semi-divine appearance"},
}


def generate_loading_prompt(leader_key, civ_type, format_type="midjourney"):
    """Generate an AI prompt for a loading screen image."""
    leader = LEADER_DESCRIPTORS.get(leader_key, {})
    civ = CIV_DESCRIPTORS.get(civ_type, {})

    if not leader or not civ:
        return None

    base_prompt = (
        f"Epic portrait of {leader.get('features', '')}, {leader.get('ethnicity', '')} {leader.get('age', '')}, "
        f"{civ.get('attire', '')}, "
        f"in the style of Civilization VII game art, "
        f"dramatic cinematic lighting from the side, dark moody background with hints of {civ.get('setting', '')}, "
        f"painterly digital art style, three-quarter view facing slightly left, "
        f"color palette: {civ.get('palette', '')}, "
        f"highly detailed, 2:3 portrait aspect ratio"
    )

    if format_type == "midjourney":
        return f"/imagine {base_prompt} --ar 2:3 --style raw --s 250"
    elif format_type == "dalle":
        return f"Create a portrait painting: {base_prompt}. The image should be 1024x1400 pixels."
    else:  # stable diffusion
        return base_prompt


def generate_icon_prompt(leader_key, expression="neutral", format_type="midjourney"):
    """Generate an AI prompt for a leader icon."""
    leader = LEADER_DESCRIPTORS.get(leader_key, {})
    if not leader:
        return None

    expr_map = {
        "neutral": "calm dignified expression",
        "happy": "warm satisfied smile, pleased expression",
        "angry": "stern angry scowl, fierce expression",
    }

    base_prompt = (
        f"Close-up headshot portrait of {leader.get('features', '')}, {leader.get('ethnicity', '')} {leader.get('age', '')}, "
        f"{expr_map.get(expression, 'neutral expression')}, "
        f"game character icon style, "
        f"dark background, dramatic lighting, "
        f"highly detailed face, digital painting, "
        f"square composition, centered face"
    )

    if format_type == "midjourney":
        return f"/imagine {base_prompt} --ar 1:1 --style raw --s 250"
    elif format_type == "dalle":
        return f"Create a portrait icon: {base_prompt}. The image should be 512x512 pixels."
    else:
        return base_prompt


def main():
    parser = argparse.ArgumentParser(description="Generate AI image prompts for Authentic Leaders mod")
    parser.add_argument("--leader", help="Generate prompts for a specific leader key only")
    parser.add_argument("--format", choices=["midjourney", "dalle", "sd"], default="midjourney",
                        help="AI tool format (default: midjourney)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--icons-only", action="store_true", help="Only generate icon prompts")
    parser.add_argument("--loading-only", action="store_true", help="Only generate loading screen prompts")
    args = parser.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    output_lines = []

    # Build civ lookup
    all_civs = {}
    for age_key, age_data in config["ages"].items():
        for civ in age_data["civilizations"]:
            all_civs[civ["type"]] = civ

    leaders = config["leaders"]
    if args.leader:
        leaders = [l for l in leaders if l["icon_key"] == args.leader]
        if not leaders:
            print(f"Error: Leader '{args.leader}' not found in config")
            sys.exit(1)

    for leader in leaders:
        key = leader["icon_key"]
        output_lines.append(f"\n{'='*60}")
        output_lines.append(f"LEADER: {leader['name']} ({key})")
        output_lines.append(f"{'='*60}")

        # Icon prompts
        if not args.loading_only:
            output_lines.append(f"\n--- ICONS ---")
            for expr in ["neutral", "happy", "angry"]:
                prompt = generate_icon_prompt(key, expr, args.format)
                if prompt:
                    output_lines.append(f"\n[{expr.upper()}]")
                    output_lines.append(prompt)

        # Loading screen prompts per civilization
        if not args.icons_only:
            output_lines.append(f"\n--- LOADING SCREENS ---")
            guaranteed_civs = leader.get("guaranteed_civs", {})
            all_civ_types = set()
            for age_civs in guaranteed_civs.values():
                all_civ_types.update(age_civs)

            if not all_civ_types:
                output_lines.append("  (no guaranteed civs found)")
                continue

            for civ_type in sorted(all_civ_types):
                civ_info = all_civs.get(civ_type, {})
                prompt = generate_loading_prompt(key, civ_type, args.format)
                if prompt:
                    civ_name = civ_info.get("name", civ_type)
                    output_lines.append(f"\n[{civ_name}] ({civ_type})")
                    output_lines.append(f"  File: images/loading/{key}_{civ_type.lower().replace('civilization_', '')}.png")
                    output_lines.append(f"  Prompt: {prompt}")
                else:
                    output_lines.append(f"\n[{civ_type}] - No descriptor available, skipping")

    result = "\n".join(output_lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Prompts written to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
