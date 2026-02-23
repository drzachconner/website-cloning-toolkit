#!/usr/bin/env python3
"""
Sync shared files from the Cultivate template to a target site.

Usage:
  python scripts/sync-from-template.py --target ../websites/bodymind-chiro-website [--dry-run]
  python scripts/sync-from-template.py --target ../websites/bodymind-chiro-website --audit

Features:
  - Reads SYNC-MANIFEST.json for file classification
  - --dry-run: shows what would change without writing
  - --audit: finds files in template not classified in any tier
  - Copies Tier 1 (shared) files, flags Tier 2 (parameterized)
  - Never touches Tier 3 (unique) files
  - Warns if target has uncommitted git changes
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLKIT_DIR = SCRIPT_DIR.parent
MANIFEST_PATH = TOOLKIT_DIR / "SYNC-MANIFEST.json"

# Hardcoded safety blocklist — NEVER overwrite these in any target
SAFETY_BLOCKLIST = {
    "src/data/site.ts",
    "CLAUDE.md",
    "ADMIN_PANEL_PROMPT.md",
    "public/sitemap.xml",
}

# Directories that are always unique per site
SAFETY_DIRS = {
    "public/images",
    "public/guides",
}


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def get_template_dir(manifest: dict) -> Path:
    """Resolve the template site directory."""
    template_name = manifest["template"]
    websites_dir = TOOLKIT_DIR.parent / "websites"
    template_dir = websites_dir / template_name
    if not template_dir.is_dir():
        print(f"ERROR: Template directory not found: {template_dir}")
        sys.exit(1)
    return template_dir


def check_git_status(target: Path) -> bool:
    """Check if target has uncommitted changes. Returns True if clean."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=target,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return True  # Not a git repo or error — proceed anyway
        if result.stdout.strip():
            return False
        return True
    except FileNotFoundError:
        return True  # git not found — proceed anyway


def files_are_identical(src: Path, dst: Path) -> bool:
    """Check if two files have identical content."""
    if not dst.exists():
        return False
    try:
        return src.read_bytes() == dst.read_bytes()
    except (OSError, IOError):
        return False


def is_in_safety_dir(filepath: str) -> bool:
    """Check if a file path is under a safety-protected directory."""
    for d in SAFETY_DIRS:
        if filepath.startswith(d + "/") or filepath == d:
            return True
    return False


def get_all_shared_files(manifest: dict) -> set:
    return set(manifest["shared"]["files"])


def get_all_parameterized_paths(manifest: dict) -> dict:
    return {item["path"]: item["reason"] for item in manifest["parameterized"]["files"]}


def get_all_unique_paths(manifest: dict) -> set:
    paths = set()
    for item in manifest["unique"]["files"]:
        paths.add(item["path"])
    for page_list in manifest["unique"].get("site_specific_pages", {}).values():
        if isinstance(page_list, list):
            paths.update(page_list)
    return paths


def get_excluded_patterns(manifest: dict) -> list:
    return manifest.get("excluded", {}).get("patterns", [])


def should_exclude(filepath: str, patterns: list) -> bool:
    """Check if a file matches any exclusion pattern."""
    import fnmatch
    for pattern in patterns:
        if pattern.endswith("/"):
            if filepath.startswith(pattern) or f"/{pattern}" in filepath:
                return True
        elif "*" in pattern:
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(os.path.basename(filepath), pattern):
                return True
        elif filepath == pattern or filepath.endswith(f"/{pattern}"):
            return True
    return False


def sync_files(template_dir: Path, target_dir: Path, manifest: dict, dry_run: bool):
    """Sync Tier 1 files from template to target."""
    shared_files = get_all_shared_files(manifest)
    parameterized = get_all_parameterized_paths(manifest)

    synced = 0
    unchanged = 0
    flagged = 0
    skipped = 0
    created = 0

    print(f"\n{'DRY RUN — ' if dry_run else ''}Syncing from {template_dir.name} → {target_dir.name}\n")
    print("=" * 70)

    # Process shared (Tier 1) files
    print("\n📦 TIER 1 — SHARED FILES\n")
    for filepath in sorted(shared_files):
        src = template_dir / filepath
        dst = target_dir / filepath

        if not src.exists():
            print(f"  ⚠  MISSING in template: {filepath}")
            skipped += 1
            continue

        if filepath in SAFETY_BLOCKLIST or is_in_safety_dir(filepath):
            print(f"  🛡  BLOCKED (safety): {filepath}")
            skipped += 1
            continue

        if files_are_identical(src, dst):
            unchanged += 1
            continue

        if dst.exists():
            action = "UPDATE"
        else:
            action = "CREATE"
            created += 1

        if dry_run:
            print(f"  {'📝' if action == 'UPDATE' else '✨'} Would {action}: {filepath}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  {'📝' if action == 'UPDATE' else '✨'} {action}: {filepath}")

        synced += 1

    # Flag parameterized (Tier 2) files
    print("\n🔧 TIER 2 — PARAMETERIZED (manual review needed)\n")
    for filepath, reason in sorted(parameterized.items()):
        src = template_dir / filepath
        dst = target_dir / filepath

        if not src.exists():
            continue

        if files_are_identical(src, dst):
            print(f"  ✅ Already identical: {filepath}")
            continue

        print(f"  ⚠  FLAGGED: {filepath}")
        print(f"     Reason: {reason}")
        flagged += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"\n📊 SUMMARY")
    print(f"   Synced:     {synced} files {'(would be)' if dry_run else ''}")
    print(f"   Created:    {created} new files")
    print(f"   Unchanged:  {unchanged} files (already identical)")
    print(f"   Flagged:    {flagged} Tier 2 files for review")
    print(f"   Skipped:    {skipped} files (missing or safety-blocked)")
    print()

    return synced > 0


def audit_files(template_dir: Path, manifest: dict):
    """Find files in template not classified in any tier."""
    shared = get_all_shared_files(manifest)
    parameterized = set(get_all_parameterized_paths(manifest).keys())
    unique = get_all_unique_paths(manifest)
    excluded_patterns = get_excluded_patterns(manifest)

    all_classified = shared | parameterized | unique

    print(f"\n🔍 AUDIT — Finding unclassified files in {template_dir.name}\n")
    print("=" * 70)

    unclassified = []
    total_files = 0

    for root, dirs, files in os.walk(template_dir):
        # Skip excluded directories
        rel_root = Path(root).relative_to(template_dir)
        root_str = str(rel_root)

        skip = False
        for pattern in excluded_patterns:
            if pattern.endswith("/"):
                dirname = pattern.rstrip("/")
                if root_str == dirname or root_str.startswith(dirname + "/"):
                    skip = True
                    break
                if dirname in dirs:
                    dirs.remove(dirname)
        if skip:
            continue

        # Also skip common non-source dirs
        for skip_dir in ["node_modules", "dist", ".git", ".planning", ".claude", ".bolt", "admin-backend"]:
            if skip_dir in dirs:
                dirs.remove(skip_dir)

        for filename in files:
            filepath = str((Path(root) / filename).relative_to(template_dir))

            # Skip binary/non-source files
            if any(filepath.endswith(ext) for ext in [".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".woff", ".woff2", ".ttf", ".eot"]):
                continue

            # Skip lock files
            if filepath == "package-lock.json":
                continue

            if should_exclude(filepath, excluded_patterns):
                continue

            total_files += 1

            if filepath not in all_classified and not is_in_safety_dir(filepath):
                unclassified.append(filepath)

    if unclassified:
        print(f"\n⚠  {len(unclassified)} UNCLASSIFIED files found:\n")
        for f in sorted(unclassified):
            print(f"   {f}")
    else:
        print("\n✅ All files are classified!")

    print(f"\n📊 Total source files scanned: {total_files}")
    print(f"   Classified: {total_files - len(unclassified)}")
    print(f"   Unclassified: {len(unclassified)}")

    # Show tier counts
    print(f"\n📦 Tier breakdown:")
    print(f"   Tier 1 (shared):        {len(shared)} files")
    print(f"   Tier 2 (parameterized): {len(parameterized)} files")
    print(f"   Tier 3 (unique):        {len(unique)} files")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Sync shared files from the Cultivate template to a target site."
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Path to target site directory (e.g., ../websites/bodymind-chiro-website)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Find files in template not classified in any tier",
    )

    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    manifest = load_manifest()
    template_dir = get_template_dir(manifest)

    if args.audit:
        audit_files(template_dir, manifest)
        return

    if not args.target:
        print("ERROR: --target is required (unless using --audit)")
        parser.print_help()
        sys.exit(1)

    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"ERROR: Target directory not found: {target_dir}")
        sys.exit(1)

    # Safety check: warn about uncommitted changes
    if not check_git_status(target_dir):
        print("⚠  WARNING: Target has uncommitted git changes!")
        print("   Consider committing or stashing before syncing.")
        if not args.dry_run:
            response = input("   Continue anyway? [y/N] ")
            if response.lower() != "y":
                print("Aborted.")
                sys.exit(0)
        print()

    had_changes = sync_files(template_dir, target_dir, manifest, args.dry_run)

    if had_changes and not args.dry_run:
        print("💡 Next steps:")
        print("   1. cd into target site")
        print("   2. Run: npm run build")
        print("   3. Review any flagged Tier 2 files")
        print("   4. Test locally with: npm run dev")
        print("   5. Commit and push when satisfied")
        print()


if __name__ == "__main__":
    main()
