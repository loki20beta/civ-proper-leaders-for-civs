"""Configuration and metadata access for AI generation pipeline."""

from __future__ import annotations

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERS_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "leaders-civilizations.json")
AI_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "ai-generation.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
MOD_DIR = os.path.join(PROJECT_ROOT, "authentic-leaders")
GENERATED_DIR = os.path.join(ASSETS_DIR, "generated")


class Config:
    """Central configuration for the AI generation pipeline."""

    def __init__(self):
        with open(LEADERS_CONFIG_PATH) as f:
            self._leaders_config = json.load(f)
        with open(AI_CONFIG_PATH) as f:
            self._ai_config = json.load(f)

        # Build lookup tables
        self._leaders = {}  # icon_key -> leader dict
        for leader in self._leaders_config["leaders"]:
            self._leaders[leader["icon_key"]] = leader

        self._civs = {}  # civ_key -> civ dict
        for age_data in self._leaders_config["ages"].values():
            for civ in age_data["civilizations"]:
                self._civs[civ["civ_key"]] = civ

    def is_native(self, leader_key: str, civ_key: str) -> bool:
        """Check if this leader×civ pair is native (should be skipped)."""
        native = self._ai_config["native_pairings"]
        # Check base pairings
        if native.get("base", {}).get(leader_key) == civ_key:
            return True
        # Check persona pairings
        if native.get("persona", {}).get(leader_key) == civ_key:
            return True
        return False

    def get_leader_gender(self, leader_key: str) -> str:
        """Get leader gender: 'male' or 'female'."""
        return self._ai_config["leader_genders"].get(leader_key, "male")

    def get_costume_ref(self, leader_key: str, civ_key: str) -> str | None:
        """Get the native leader whose costume should be referenced for this civ.

        Returns the icon_key of the costume reference leader (same gender only),
        or None if no same-gender reference exists.
        Only returns a reference if the leader is NOT the native leader themselves.
        """
        gender = self.get_leader_gender(leader_key)
        refs = self._ai_config.get("costume_references", {}).get(civ_key, {})
        ref_leader = refs.get(gender)
        # Don't reference yourself
        if ref_leader and ref_leader != leader_key:
            # Also strip _alt suffix for persona comparison
            base_key = leader_key.replace("_alt", "")
            if ref_leader != base_key:
                return ref_leader
        return None

    def get_attire(self, civ_key: str, gender: str) -> dict | None:
        """Get gender-appropriate attire descriptor for a civilization.

        Returns dict with keys: clothing, headwear, accessories, forbidden, palette
        Or None if civ not found.
        """
        civ_data = self._ai_config.get("civilizations", {}).get(civ_key)
        if not civ_data:
            return None
        attire_key = f"{gender}_attire"
        return civ_data.get(attire_key)

    def get_civ_info(self, civ_key: str) -> dict | None:
        """Get full civ info from ai-generation.json (name, period, setting, attire)."""
        return self._ai_config.get("civilizations", {}).get(civ_key)

    def get_all_civ_keys(self) -> list[str]:
        """Get all civilization keys."""
        return list(self._civs.keys())

    def get_all_leader_keys(self) -> list[str]:
        """Get all leader icon_keys including persona alts."""
        keys = []
        for leader in self._leaders_config["leaders"]:
            keys.append(leader["icon_key"])
            for persona in leader.get("personas", []):
                # Derive short key: LEADER_ASHOKA_ALT -> ashoka_alt
                icon_key = leader["icon_key"]
                ptype = persona["type"]
                prefix = f"LEADER_{icon_key.upper()}_"
                if ptype.startswith(prefix):
                    pkey = f"{icon_key}_{ptype[len(prefix):].lower()}"
                else:
                    pkey = ptype.replace("LEADER_", "").lower()
                keys.append(pkey)
        return keys

    def get_base_leader_key(self, leader_key: str) -> str:
        """Get the base leader key for a persona alt. Returns same key if not a persona."""
        # e.g., ashoka_alt -> ashoka, napoleon_alt -> napoleon
        if leader_key.endswith("_alt"):
            base = leader_key[:-4]
            if base in self._leaders:
                return base
        return leader_key

    def get_all_pairs(self, include_native: bool = False) -> list[tuple[str, str]]:
        """Get all (leader_key, civ_key) pairs needing generation.

        By default excludes native pairs.
        """
        pairs = []
        civ_keys = self.get_all_civ_keys()
        for leader_key in self.get_all_leader_keys():
            for civ_key in civ_keys:
                if not include_native and self.is_native(leader_key, civ_key):
                    continue
                pairs.append((leader_key, civ_key))
        return pairs

    def get_leader_name(self, leader_key: str) -> str:
        """Get display name for a leader."""
        base_key = self.get_base_leader_key(leader_key)
        leader = self._leaders.get(base_key)
        if leader:
            if leader_key != base_key:
                return f"{leader['name']} (Alt)"
            return leader["name"]
        return leader_key.replace("_", " ").title()

    def get_civ_name(self, civ_key: str) -> str:
        """Get display name for a civilization."""
        civ_info = self._ai_config.get("civilizations", {}).get(civ_key, {})
        return civ_info.get("name", civ_key.replace("_", " ").title())

    def get_identity_image_path(self, leader_key: str) -> str:
        """Get path to the leader's identity anchor image (loading_original.png)."""
        base_key = self.get_base_leader_key(leader_key)
        if leader_key != base_key:
            # Persona alt
            suffix = leader_key[len(base_key)+1:]  # e.g., "alt"
            return os.path.join(ASSETS_DIR, "leaders", base_key, f"{suffix}_loading_original.png")
        return os.path.join(ASSETS_DIR, "leaders", leader_key, "loading_original.png")

    def get_costume_ref_image_path(self, ref_leader_key: str) -> str:
        """Get path to a costume reference leader's image."""
        return os.path.join(ASSETS_DIR, "leaders", ref_leader_key, "loading_original.png")

    def get_background_image_path(self, civ_key: str) -> str:
        """Get path to civilization background scene image."""
        return os.path.join(ASSETS_DIR, "civilizations", civ_key, "background_1080.png")

    def get_icon_ref_path(self, leader_key: str, expression: str) -> str:
        """Get path to original game icon for a leader and expression.

        Args:
            leader_key: Leader icon key
            expression: "neutral", "happy", or "angry"

        Returns:
            Path to the 128px icon PNG (hex shape)
        """
        base_key = self.get_base_leader_key(leader_key)
        suffix_map = {"neutral": "", "happy": "_h", "angry": "_a"}
        suffix = suffix_map.get(expression, "")
        return os.path.join(
            ASSETS_DIR, "leaders", base_key, "icons",
            f"lp_hex_{base_key}_128{suffix}.png"
        )

    def get_generated_dir(self, leader_key: str, civ_key: str) -> str:
        """Get output directory for generated images."""
        return os.path.join(GENERATED_DIR, leader_key, civ_key)
