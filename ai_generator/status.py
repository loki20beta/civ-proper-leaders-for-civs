"""Generation status tracking for AI pipeline.

Tracks per-pair generation status, variant files, and quality scores.
Status is persisted in assets/generated/status.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import config as config_module

STATUS_PATH = os.path.join(config_module.GENERATED_DIR, "status.json")
ASSET_TYPES = ["loading", "icon_neutral", "icon_happy", "icon_angry"]


class StatusTracker:
    """Track generation status for all leader×civ pairs."""

    def __init__(self):
        self._status = {}
        self._load()

    def _load(self):
        """Load status from disk."""
        if os.path.isfile(STATUS_PATH):
            with open(STATUS_PATH) as f:
                self._status = json.load(f)

    def _save(self):
        """Persist status to disk."""
        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
        with open(STATUS_PATH, "w") as f:
            json.dump(self._status, f, indent=2)

    def _pair_key(self, leader_key: str, civ_key: str) -> str:
        return f"{leader_key}_{civ_key}"

    def get_pair_status(self, leader_key: str, civ_key: str) -> dict:
        """Get full status for a leader×civ pair."""
        key = self._pair_key(leader_key, civ_key)
        if key not in self._status:
            self._status[key] = {
                asset: {"status": "pending", "variants": [], "selected": None}
                for asset in ASSET_TYPES
            }
        return self._status[key]

    def is_completed(self, leader_key: str, civ_key: str) -> bool:
        """Check if all assets for a pair are completed."""
        pair = self.get_pair_status(leader_key, civ_key)
        return all(pair[asset]["status"] == "completed" for asset in ASSET_TYPES)

    def get_asset_status(self, leader_key: str, civ_key: str, asset_type: str) -> str:
        """Get status of a specific asset: 'pending', 'completed', or 'failed'."""
        pair = self.get_pair_status(leader_key, civ_key)
        return pair.get(asset_type, {}).get("status", "pending")

    def add_variant(self, leader_key: str, civ_key: str, asset_type: str,
                    filename: str, auto_select: bool = True):
        """Record a new generated variant for an asset.

        Args:
            leader_key: Leader icon key
            civ_key: Civilization key
            asset_type: One of ASSET_TYPES
            filename: The variant filename (e.g., "loading_v2.png")
            auto_select: If True, automatically select this as the best variant
        """
        pair = self.get_pair_status(leader_key, civ_key)
        asset = pair[asset_type]

        variant = {
            "file": filename,
            "quality": None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        asset["variants"].append(variant)
        asset["status"] = "completed"

        if auto_select:
            asset["selected"] = filename

        self._save()

    def get_selected_variant(self, leader_key: str, civ_key: str, asset_type: str) -> str | None:
        """Get the filename of the selected (best) variant."""
        pair = self.get_pair_status(leader_key, civ_key)
        return pair.get(asset_type, {}).get("selected")

    def get_next_variant_number(self, leader_key: str, civ_key: str, asset_type: str) -> int:
        """Get the next variant number for a new generation attempt."""
        pair = self.get_pair_status(leader_key, civ_key)
        variants = pair.get(asset_type, {}).get("variants", [])
        return len(variants)

    def mark_failed(self, leader_key: str, civ_key: str, asset_type: str):
        """Mark an asset as failed."""
        pair = self.get_pair_status(leader_key, civ_key)
        pair[asset_type]["status"] = "failed"
        self._save()

    def set_quality(self, leader_key: str, civ_key: str, asset_type: str,
                    variant_file: str, score: int):
        """Set quality score (1-5) for a specific variant."""
        pair = self.get_pair_status(leader_key, civ_key)
        for variant in pair.get(asset_type, {}).get("variants", []):
            if variant["file"] == variant_file:
                variant["quality"] = score
                break
        self._save()

    def select_variant(self, leader_key: str, civ_key: str, asset_type: str,
                       variant_file: str):
        """Manually select a variant as the best one."""
        pair = self.get_pair_status(leader_key, civ_key)
        pair[asset_type]["selected"] = variant_file
        self._save()

    def get_pending_pairs(self, cfg) -> list[tuple[str, str]]:
        """Get all pairs that haven't been fully completed."""
        pending = []
        for leader_key, civ_key in cfg.get_all_pairs():
            if not self.is_completed(leader_key, civ_key):
                pending.append((leader_key, civ_key))
        return pending

    def get_failed_pairs(self, cfg) -> list[tuple[str, str]]:
        """Get all pairs that have at least one failed asset."""
        failed = []
        for leader_key, civ_key in cfg.get_all_pairs():
            pair = self.get_pair_status(leader_key, civ_key)
            if any(pair[asset]["status"] == "failed" for asset in ASSET_TYPES):
                failed.append((leader_key, civ_key))
        return failed

    def get_summary(self, cfg) -> dict:
        """Get a summary of generation progress."""
        all_pairs = cfg.get_all_pairs()
        total = len(all_pairs)
        completed = sum(1 for l, c in all_pairs if self.is_completed(l, c))
        failed = len(self.get_failed_pairs(cfg))
        pending = total - completed - failed

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "percent": round(100 * completed / total, 1) if total else 0
        }
