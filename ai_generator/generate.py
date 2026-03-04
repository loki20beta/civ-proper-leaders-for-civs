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
    """Generate all assets for a single leader×civ pair.

    Uses a single multi-turn chat session for consistency:
    Turn 1: Loading screen (3:4, 2K)
    Turn 2: Neutral icon headshot (3:4, 1K)
    Turn 3: Happy icon headshot (3:4, 1K)
    Turn 4: Angry icon headshot (3:4, 1K)

    Never overwrites existing files — saves as numbered variants.

    Returns True if all assets generated successfully.
    """
    leader_name = cfg.get_leader_name(leader_key)
    civ_name = cfg.get_civ_name(civ_key)

    # Skip if already completed (unless --force)
    if not force and status.is_completed(leader_key, civ_key):
        return True

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

    # Load reference images
    identity_path = cfg.get_identity_image_path(leader_key)
    if not os.path.isfile(identity_path):
        print(f"  ERROR: Identity image not found: {identity_path}")
        return False

    identity_img = Image.open(identity_path).convert("RGBA")
    ref_images = [identity_img]

    # Costume reference (same gender native leader)
    costume_ref_key = cfg.get_costume_ref(leader_key, civ_key)
    has_costume_ref = False
    if costume_ref_key:
        costume_path = cfg.get_costume_ref_image_path(costume_ref_key)
        if os.path.isfile(costume_path):
            costume_img = Image.open(costume_path).convert("RGBA")
            ref_images.append(costume_img)
            has_costume_ref = True
            print(f"  Costume ref: {costume_ref_key}")

    # Background reference (optional)
    bg_path = cfg.get_background_image_path(civ_key)
    if os.path.isfile(bg_path):
        bg_img = Image.open(bg_path).convert("RGBA")
        ref_images.append(bg_img)

    # Get attire info
    gender = cfg.get_leader_gender(leader_key)
    attire = cfg.get_attire(civ_key, gender)
    civ_info = cfg.get_civ_info(civ_key)

    if not attire or not civ_info:
        print(f"  ERROR: No attire data for {civ_key}/{gender}")
        return False

    if dry_run:
        print(f"  Would generate: loading + 3 icons")
        print(f"  Ref images: {len(ref_images)} (identity"
              f"{' + costume' if has_costume_ref else ''}"
              f"{' + background' if os.path.isfile(bg_path) else ''})")
        return True

    # Create chat session for multi-turn consistency
    session = client.create_chat_session()
    success = True

    # --- Turn 1: Loading screen ---
    asset_type = "loading"
    if force or status.get_asset_status(leader_key, civ_key, asset_type) != "completed":
        variant_num = status.get_next_variant_number(leader_key, civ_key, asset_type)
        filename = f"loading_v{variant_num}.png"

        prompt = build_loading_prompt(
            leader_name=leader_name,
            civ_name=civ_name,
            period=civ_info.get("period", ""),
            attire=attire,
            setting=civ_info.get("setting", ""),
            has_costume_ref=has_costume_ref
        )

        print(f"  Generating loading screen (v{variant_num})...")
        img = session.send(prompt, ref_images=ref_images, aspect_ratio="3:4", image_size="2K")

        if img:
            save_path = os.path.join(out_dir, filename)
            img.save(save_path, "PNG")
            status.add_variant(leader_key, civ_key, asset_type, filename)
            print(f"  Loading screen saved: {filename}")
        else:
            status.mark_failed(leader_key, civ_key, asset_type)
            print(f"  Loading screen FAILED")
            success = False

    # --- Turns 2-4: Icon headshots ---
    for expression in ["neutral", "happy", "angry"]:
        asset_type = f"icon_{expression}"
        if not force and status.get_asset_status(leader_key, civ_key, asset_type) == "completed":
            continue

        variant_num = status.get_next_variant_number(leader_key, civ_key, asset_type)
        filename = f"icon_{expression}_v{variant_num}.png"

        prompt = build_icon_prompt(expression=expression, civ_name=civ_name)

        print(f"  Generating {expression} icon (v{variant_num})...")
        # Icons use 1K resolution, same 3:4 aspect
        img = session.send(prompt, aspect_ratio="3:4", image_size="1K")

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
