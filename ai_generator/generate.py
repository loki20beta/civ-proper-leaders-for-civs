"""Main CLI orchestrator for AI image generation pipeline.

Usage:
    python3 -m ai_generator.generate --leader augustus              # one leader, all civs
    python3 -m ai_generator.generate --leader augustus --civ abbasid # one pair
    python3 -m ai_generator.generate --all                          # all pending pairs
    python3 -m ai_generator.generate --resume                       # pick up where left off
    python3 -m ai_generator.generate --retry                        # retry failures
    python3 -m ai_generator.generate --dry-run                      # preview only
    python3 -m ai_generator.generate --status                       # show progress
"""

import argparse
import os
import sys

from PIL import Image

from .config import Config, GENERATED_DIR
from .client import OpenRouterClient
from .prompts import build_loading_prompt, build_icon_prompt
from .status import StatusTracker



def generate_pair(cfg: Config, client: OpenRouterClient, status: StatusTracker,
                  leader_key: str, civ_key: str, force: bool = False,
                  dry_run: bool = False) -> bool:
    """Generate all assets for a single leader x civ pair.

    Uses a single multi-turn chat session for consistency:
    Turn 1: Loading screen (pass original loading as ref, redress)
    Turn 2: Neutral icon (pass original neutral icon as ref)
    Turn 3: Happy icon (pass original happy icon as ref)
    Turn 4: Angry icon (pass original angry icon as ref)

    Never overwrites existing files — saves as numbered variants.

    Returns True if all assets generated successfully.
    """
    leader_name = cfg.get_leader_name(leader_key)
    civ_name = cfg.get_civ_name(civ_key)

    # Skip native pairs
    if cfg.is_native(leader_key, civ_key):
        return True

    print(f"\n{'='*60}")
    print(f"Generating: {leader_name} x {civ_name}")
    print(f"  Key: {leader_key} x {civ_key}")

    # Prepare output directory
    out_dir = cfg.get_generated_dir(leader_key, civ_key)
    if not dry_run:
        os.makedirs(out_dir, exist_ok=True)

    # Load reference images for loading screen
    identity_path = cfg.get_identity_image_path(leader_key)
    if not os.path.isfile(identity_path):
        print(f"  ERROR: Identity image not found: {identity_path}")
        return False

    identity_img = Image.open(identity_path)
    ref_images = [identity_img]

    # Costume reference (same gender native leader)
    costume_ref_key = cfg.get_costume_ref(leader_key, civ_key)
    has_costume_ref = False
    if costume_ref_key:
        costume_path = cfg.get_costume_ref_image_path(costume_ref_key)
        if os.path.isfile(costume_path):
            costume_img = Image.open(costume_path)
            ref_images.append(costume_img)
            has_costume_ref = True
            print(f"  Costume ref: {costume_ref_key}")

    # Get attire info
    gender = cfg.get_leader_gender(leader_key)
    attire = cfg.get_attire(civ_key, gender)
    civ_info = cfg.get_civ_info(civ_key)

    if not attire or not civ_info:
        print(f"  ERROR: No attire data for {civ_key}/{gender}")
        return False

    period = civ_info.get("period", "")

    if dry_run:
        print(f"  Ref images: {len(ref_images)} (identity"
              f"{' + costume' if has_costume_ref else ''})")

        # Show loading prompt
        loading_prompt = build_loading_prompt(
            leader_name=leader_name, civ_name=civ_name,
            period=period, attire=attire,
            setting=civ_info.get("setting", ""), has_costume_ref=has_costume_ref
        )
        print(f"\n  --- LOADING SCREEN PROMPT (independent request) ---")
        for line in loading_prompt.split("\n"):
            print(f"  {line}")

        # Show icon prompts with ref paths
        for expression in ["neutral", "happy", "angry"]:
            icon_ref_path = cfg.get_icon_ref_path(leader_key, expression)
            icon_exists = os.path.isfile(icon_ref_path)
            prompt = build_icon_prompt(
                expression=expression, civ_name=civ_name,
                period=period, attire=attire
            )
            print(f"\n  --- {expression.upper()} ICON PROMPT (independent request) ---")
            print(f"  Icon ref: {os.path.basename(icon_ref_path)} ({'found' if icon_exists else 'MISSING'})")
            for line in prompt.split("\n"):
                print(f"  {line}")

        return True

    success = True

    # --- Request 1: Loading screen (independent) ---
    asset_type = "loading"
    variant_num = status.get_next_variant_number(leader_key, civ_key, asset_type)
    filename = f"loading_{variant_num:02d}.png"

    prompt = build_loading_prompt(
        leader_name=leader_name,
        civ_name=civ_name,
        period=period,
        attire=attire,
        setting=civ_info.get("setting", ""),
        has_costume_ref=has_costume_ref
    )

    print(f"  Generating loading screen (#{variant_num:02d})...")
    img = client.generate_image(prompt, ref_images=ref_images)

    if img:
        save_path = os.path.join(out_dir, filename)
        img.save(save_path, "PNG")
        status.add_variant(leader_key, civ_key, asset_type, filename)
        print(f"  Loading screen saved: {filename}")
    else:
        status.mark_failed(leader_key, civ_key, asset_type)
        print(f"  Loading screen FAILED")
        success = False

    # --- Requests 2-4: Icon headshots (each independent) ---
    for expression in ["neutral", "happy", "angry"]:
        asset_type = f"icon_{expression}"
        variant_num = status.get_next_variant_number(leader_key, civ_key, asset_type)
        filename = f"icon_{expression}_{variant_num:02d}.png"

        # Load original game icon as reference
        icon_ref_path = cfg.get_icon_ref_path(leader_key, expression)
        icon_ref_images = None
        if os.path.isfile(icon_ref_path):
            icon_ref_img = Image.open(icon_ref_path)
            icon_ref_images = [icon_ref_img]

        prompt = build_icon_prompt(
            expression=expression, civ_name=civ_name,
            period=period, attire=attire
        )

        print(f"  Generating {expression} icon (#{variant_num:02d})...")
        img = client.generate_image(prompt, ref_images=icon_ref_images)

        if img:
            save_path = os.path.join(out_dir, filename)
            img.save(save_path, "PNG")
            status.add_variant(leader_key, civ_key, asset_type, filename)
            print(f"  {expression} icon saved: {filename}")
        else:
            status.mark_failed(leader_key, civ_key, asset_type)
            print(f"  {expression} icon FAILED")
            success = False

    return success


def show_status(cfg: Config, status: StatusTracker):
    """Display generation progress summary."""
    summary = status.get_summary(cfg)
    print(f"\nGeneration Progress:")
    print(f"  Total pairs:  {summary['total']}")
    print(f"  Completed:    {summary['completed']} ({summary['percent']}%)")
    print(f"  Failed:       {summary['failed']}")
    print(f"  Pending:      {summary['pending']}")

    if summary['failed'] > 0:
        print(f"\nFailed pairs:")
        for leader_key, civ_key in status.get_failed_pairs(cfg):
            print(f"  {leader_key} x {civ_key}")


def main():
    parser = argparse.ArgumentParser(
        description="AI image generation for Authentic Leaders mod"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Generate all pending pairs")
    group.add_argument("--resume", action="store_true", help="Resume from where left off")
    group.add_argument("--retry", action="store_true", help="Retry failed pairs")
    group.add_argument("--status", action="store_true", help="Show progress")

    parser.add_argument("--leader", help="Generate for one leader only (icon_key)")
    parser.add_argument("--civ", help="Generate for one civ only (civ_key)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if completed")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument("--limit", type=int, help="Maximum number of pairs to process")

    args = parser.parse_args()

    cfg = Config()
    status_tracker = StatusTracker()

    if args.status:
        show_status(cfg, status_tracker)
        return

    # Determine which pairs to process
    if args.retry:
        pairs = status_tracker.get_failed_pairs(cfg)
        print(f"Retrying {len(pairs)} failed pairs...")
    elif args.resume or args.all:
        pairs = status_tracker.get_pending_pairs(cfg)
        print(f"Processing {len(pairs)} pending pairs...")
    elif args.leader and args.civ:
        pairs = [(args.leader, args.civ)]
    elif args.leader:
        civ_keys = cfg.get_all_civ_keys()
        pairs = [
            (args.leader, c) for c in civ_keys
            if not cfg.is_native(args.leader, c)
        ]
        print(f"Generating {args.leader} x {len(pairs)} civs...")
    elif args.civ:
        leader_keys = cfg.get_all_leader_keys()
        pairs = [
            (l, args.civ) for l in leader_keys
            if not cfg.is_native(l, args.civ)
        ]
        print(f"Generating {len(pairs)} leaders x {args.civ}...")
    else:
        parser.print_help()
        print("\nSpecify --all, --resume, --retry, --leader, or --status")
        sys.exit(1)

    if args.limit and len(pairs) > args.limit:
        pairs = pairs[:args.limit]
        print(f"Limited to {args.limit} pairs")

    if not pairs:
        print("No pairs to process.")
        return

    # Initialize API client
    if not args.dry_run:
        client = OpenRouterClient()
    else:
        client = None

    # Process pairs
    succeeded = 0
    failed = 0

    for i, (leader_key, civ_key) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}]", end="")

        ok = generate_pair(
            cfg, client, status_tracker,
            leader_key, civ_key,
            force=args.force, dry_run=args.dry_run
        )

        if ok:
            succeeded += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Done: {succeeded} succeeded, {failed} failed out of {len(pairs)} pairs")

    if client and not args.dry_run:
        print(f"API calls: {client.call_count}")
        if client.total_cost > 0:
            print(f"Estimated cost: ${client.total_cost:.2f}")

    if not args.dry_run and succeeded > 0:
        print(f"\nNext steps:")
        print(f"  1. python3 -m ai_generator.postprocess --all")
        print(f"  2. python3 scripts/generate-mod-data.py")


if __name__ == "__main__":
    main()
