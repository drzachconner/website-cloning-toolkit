#!/usr/bin/env python3
"""Run the website cloning pipeline end-to-end or by individual phases."""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


# All phases in execution order
ALL_PHASES = ["capture", "extract", "generate", "validate", "refine"]

# Directories to create inside the project output
PROJECT_DIRS = [
    "mirror",
    "screenshots",
    "css",
    "fonts",
    "images",
    "pages",
    "templates",
    "report",
    "archive",
]


def run_script(cmd, label=None):
    """Run a script as a subprocess, returning (success, duration, stdout, stderr)."""
    label = label or cmd[0]
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        duration = time.time() - start
        success = result.returncode == 0
        if not success:
            print(f"  [{label}] FAILED (exit {result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:10]:
                    print(f"    {line}")
        return success, duration, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"  [{label}] TIMEOUT after {duration:.0f}s")
        return False, duration, "", "Timeout after 600s"
    except FileNotFoundError:
        duration = time.time() - start
        print(f"  [{label}] ERROR: script not found: {cmd[0]}")
        return False, duration, "", f"Script not found: {cmd[0]}"


def run_parallel(tasks):
    """Run multiple script commands in parallel, returning list of (label, success, duration)."""
    results = []
    with ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {}
        for label, cmd in tasks:
            future = executor.submit(run_script, cmd, label)
            futures[future] = label

        for future in as_completed(futures):
            label = futures[future]
            try:
                success, duration, stdout, stderr = future.result()
                results.append((label, success, duration))
                if success:
                    print(f"  [{label}] done ({duration:.1f}s)")
            except Exception as e:
                print(f"  [{label}] ERROR: {e}")
                results.append((label, False, 0.0))

    return results


def find_scripts_dir():
    """Locate the scripts/ directory relative to this file."""
    this_dir = Path(__file__).resolve().parent
    # This script lives inside scripts/, so the directory is itself
    if this_dir.name == "scripts":
        return this_dir
    # Fallback: look for scripts/ in the repo root
    repo_root = this_dir.parent
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        return scripts_dir
    return this_dir


def phase_capture(url, output_dir, scripts_dir):
    """Phase 1: Scrape the target site."""
    print("\n--- Phase 1: Capture ---")
    cmd = [
        sys.executable,
        str(scripts_dir / "scrape-site.py"),
        "--url", url,
        "--output", str(Path(output_dir) / "mirror"),
        "--screenshots",
        "--sitemap",
    ]
    success, duration, stdout, stderr = run_script(cmd, "scrape-site")
    if success:
        print(f"  Capture complete ({duration:.1f}s)")
    return success, duration


def phase_extract(url, output_dir, scripts_dir):
    """Phase 2: Extract design system (parallel tasks)."""
    print("\n--- Phase 2: Extract Design System ---")
    output = Path(output_dir)
    tasks = [
        (
            "extract-css",
            [
                sys.executable,
                str(scripts_dir / "extract-css.py"),
                "--url", url,
                "--output", str(output / "css" / "styles.css"),
                "--subset",
                "--html-dir", str(output / "mirror" / "extracted"),
            ],
        ),
        (
            "extract-colors",
            [
                sys.executable,
                str(scripts_dir / "extract-colors.py"),
                "--css", str(output / "css" / "styles.css"),
                "--output", str(output / "colors.json"),
            ],
        ),
        (
            "extract-fonts",
            [
                sys.executable,
                str(scripts_dir / "extract-fonts.py"),
                "--url", url,
                "--output", str(output / "fonts"),
            ],
        ),
    ]

    results = run_parallel(tasks)

    # Run extract-design-system after CSS is available (depends on css/styles.css)
    css_path = output / "css" / "styles.css"
    if css_path.exists():
        print("  Running design system extraction...")
        cmd = [
            sys.executable,
            str(scripts_dir / "extract-design-system.py"),
            "--css", str(css_path),
            "--output", str(output / "design-system.json"),
        ]
        success, duration, stdout, stderr = run_script(cmd, "extract-design-system")
        results.append(("extract-design-system", success, duration))
    else:
        print("  Warning: css/styles.css not found, skipping design system extraction")
        results.append(("extract-design-system", False, 0.0))

    all_ok = all(r[1] for r in results)
    total_dur = sum(r[2] for r in results)
    if all_ok:
        print(f"  Extraction complete ({total_dur:.1f}s)")
    else:
        failed = [r[0] for r in results if not r[1]]
        print(f"  Extraction finished with errors in: {', '.join(failed)}")
    return all_ok, total_dur


def phase_generate(url, output_dir, scripts_dir):
    """Phase 3: Generate code (semi-manual)."""
    print("\n--- Phase 3: Generate Code ---")
    output = Path(output_dir)
    template_path = output / "templates" / "page-template.html"
    config_path = output / "class-mapping.json"

    # Check if prerequisites exist
    if not template_path.exists():
        print("  Template not found: templates/page-template.html")
        print("  Manual step required:")
        print(f"    1. Create a template at: {template_path}")
        print("    2. Use the design system and class mapping as reference")
        print("    3. Include a {{content}} placeholder for page-specific content")
        print("    4. Re-run this phase after the template is ready")
        return None, 0.0  # None = manual/skipped

    if not config_path.exists():
        print(f"  Warning: class-mapping.json not found at {config_path}")
        print("  Conversion will proceed without class mapping")

    cmd = [
        sys.executable,
        str(scripts_dir / "convert-html.py"),
        "--input", str(output / "mirror" / "extracted"),
        "--output", str(output / "pages"),
        "--template", str(template_path),
    ]
    if config_path.exists():
        cmd.extend(["--config", str(config_path)])

    success, duration, stdout, stderr = run_script(cmd, "convert-html")
    if success:
        print(f"  Code generation complete ({duration:.1f}s)")
    return success, duration


def phase_validate(url, output_dir, scripts_dir):
    """Phase 5: Validate (parallel tasks)."""
    print("\n--- Phase 4: Validate ---")
    output = Path(output_dir)
    pages_dir = output / "pages"

    if not pages_dir.exists() or not list(pages_dir.glob("*.html")):
        print("  No pages found in pages/ -- skipping validation")
        print("  Run the generate phase first")
        return None, 0.0

    tasks = [
        (
            "visual-diff",
            [
                sys.executable,
                str(scripts_dir / "visual-diff.py"),
                "--original", str(output / "mirror" / "screenshots"),
                "--clone", str(output / "pages"),
                "--output", str(output / "report" / "visual-diff"),
                "--threshold", "95",
            ],
        ),
        (
            "qa-check",
            [
                sys.executable,
                str(scripts_dir / "qa-check.py"),
                "--pages", str(pages_dir),
            ],
        ),
    ]

    # Only add a11y-check if the script exists
    a11y_script = scripts_dir / "a11y-check.py"
    if a11y_script.exists():
        tasks.append((
            "a11y-check",
            [
                sys.executable,
                str(a11y_script),
                "--url", url,
                "--clone", str(pages_dir),
                "--output", str(output / "report" / "a11y-report.json"),
            ],
        ))

    results = run_parallel(tasks)
    all_ok = all(r[1] for r in results)
    total_dur = sum(r[2] for r in results)
    if all_ok:
        print(f"  Validation complete ({total_dur:.1f}s)")
    else:
        failed = [r[0] for r in results if not r[1]]
        print(f"  Validation finished with errors in: {', '.join(failed)}")
    return all_ok, total_dur


def phase_refine(url, output_dir, scripts_dir):
    """Phase 5: Refine (conditional on validation results)."""
    print("\n--- Phase 5: Refine ---")
    output = Path(output_dir)

    # Check visual diff results to decide if refinement is needed
    diff_report_dir = output / "report" / "visual-diff"
    if not diff_report_dir.exists():
        print("  No visual diff report found -- cannot assess refinement need")
        print("  Run the validate phase first")
        return None, 0.0

    # Look for the report HTML to parse results
    report_html = diff_report_dir / "index.html"
    if not report_html.exists():
        print("  Visual diff report not generated -- skipping refinement check")
        return None, 0.0

    # Simple heuristic: check if any diff images exist (indicates differences)
    diffs_dir = diff_report_dir / "diffs"
    if diffs_dir.exists():
        diff_images = list(diffs_dir.glob("*.png"))
        if diff_images:
            print(f"  Found {len(diff_images)} page(s) with visual differences")
            print("  Refinement recommended. Suggested actions:")
            print("    1. Review the visual diff report: report/visual-diff/index.html")
            print("    2. Identify specific issues (layout, colors, fonts, spacing)")
            print("    3. Apply targeted fixes using the code-generator agent")
            print("    4. Re-run validation to confirm improvements")
            return None, 0.0
        else:
            print("  No visual differences detected -- refinement not needed")
            return True, 0.0
    else:
        print("  No diff images directory found -- assuming pass")
        return True, 0.0


def print_summary(phase_results, total_start):
    """Print the final pipeline summary dashboard."""
    total_duration = time.time() - total_start

    print("\n")
    print("=" * 40)
    print("  Pipeline Summary")
    print("=" * 40)
    print(f"  {'Phase':<14} {'Status':<12} {'Duration'}")
    print("  " + "-" * 36)

    for phase_id in ALL_PHASES:
        if phase_id in phase_results:
            success, duration = phase_results[phase_id]
            if success is True:
                status = "Done"
                status_icon = "+"
            elif success is False:
                status = "Failed"
                status_icon = "X"
            else:
                status = "Manual"
                status_icon = "!"
            dur_str = f"{duration:.1f}s" if duration > 0 else "--"
            print(f"  {phase_id:<14} {status_icon} {status:<9} {dur_str}")
        else:
            print(f"  {phase_id:<14} - Skip      --")

    print("  " + "-" * 36)
    print(f"  Total: {total_duration:.1f}s")

    # Print extra info if available
    passed = sum(1 for s, _ in phase_results.values() if s is True)
    failed = sum(1 for s, _ in phase_results.values() if s is False)
    manual = sum(1 for s, _ in phase_results.values() if s is None)
    skipped = len(ALL_PHASES) - len(phase_results)

    print(f"  Phases: {passed} done, {failed} failed, {manual} manual, {skipped} skipped")
    print("=" * 40)


def load_pipeline_config(config_path):
    """Load and return the pipeline configuration JSON."""
    if not config_path or not os.path.isfile(config_path):
        return None
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Run the website cloning pipeline end-to-end or by individual phases."
    )
    parser.add_argument(
        "--url", required=True,
        help="Target site URL to clone"
    )
    parser.add_argument(
        "--output", required=True,
        help="Project output directory (will be created if it does not exist)"
    )
    parser.add_argument(
        "--phases",
        help="Comma-separated list of phases to run (default: all). "
             "Values: capture,extract,generate,validate,refine"
    )
    parser.add_argument(
        "--config",
        help="Path to pipeline.json config (default: orchestration/pipeline.json)"
    )
    args = parser.parse_args()

    # Determine which phases to run
    if args.phases:
        phases = [p.strip().lower() for p in args.phases.split(",")]
        for p in phases:
            if p not in ALL_PHASES:
                print(f"Error: Unknown phase '{p}'. Valid phases: {', '.join(ALL_PHASES)}")
                sys.exit(1)
    else:
        phases = list(ALL_PHASES)

    # Load pipeline config (informational -- phase logic is hardcoded for reliability)
    config_path = args.config
    if not config_path:
        default_config = Path(__file__).resolve().parent.parent / "orchestration" / "pipeline.json"
        if default_config.exists():
            config_path = str(default_config)

    if config_path:
        config = load_pipeline_config(config_path)
        if config:
            print(f"Pipeline: {config.get('name', 'unknown')} v{config.get('version', '?')}")
        else:
            print("Warning: Could not load pipeline config, using defaults")
    else:
        print("No pipeline config found, using defaults")

    # Create project directory structure
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for subdir in PROJECT_DIRS:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)
    print(f"Project directory: {output_dir.resolve()}")

    # Locate scripts
    scripts_dir = find_scripts_dir()
    print(f"Scripts directory: {scripts_dir}")

    # Run phases
    total_start = time.time()
    phase_results = {}

    phase_runners = {
        "capture": lambda: phase_capture(args.url, args.output, scripts_dir),
        "extract": lambda: phase_extract(args.url, args.output, scripts_dir),
        "generate": lambda: phase_generate(args.url, args.output, scripts_dir),
        "validate": lambda: phase_validate(args.url, args.output, scripts_dir),
        "refine": lambda: phase_refine(args.url, args.output, scripts_dir),
    }

    for phase_id in ALL_PHASES:
        if phase_id not in phases:
            continue

        # Check dependencies: skip if a prior required phase failed
        if phase_id == "extract" and "capture" in phase_results:
            if phase_results["capture"][0] is False:
                print(f"\n--- Skipping {phase_id}: capture phase failed ---")
                continue
        if phase_id == "generate" and "extract" in phase_results:
            if phase_results["extract"][0] is False:
                print(f"\n--- Skipping {phase_id}: extract phase failed ---")
                continue
        if phase_id == "validate" and "generate" in phase_results:
            if phase_results["generate"][0] is False:
                print(f"\n--- Skipping {phase_id}: generate phase failed ---")
                continue
        if phase_id == "refine" and "validate" in phase_results:
            if phase_results["validate"][0] is False:
                print(f"\n--- Skipping {phase_id}: validate phase failed ---")
                continue

        runner = phase_runners[phase_id]
        success, duration = runner()
        phase_results[phase_id] = (success, duration)

    # Print summary
    print_summary(phase_results, total_start)


if __name__ == "__main__":
    main()
