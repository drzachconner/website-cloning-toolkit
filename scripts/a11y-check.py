#!/usr/bin/env python3
"""Accessibility audit tool that compares original site vs clone.

Runs axe-core against both the original URL and the cloned HTML file(s),
then reports NEW accessibility violations introduced in the clone.
The key insight: the clone does not need to be 100% accessible, just no
worse than the original.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright is required. Install with: pip install playwright && playwright install")
    sys.exit(1)


AXE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"

SEVERITY_ORDER = ["critical", "serious", "moderate", "minor"]


def inject_axe_and_run(page):
    """Inject axe-core into the page and run a full audit.

    Uses the CDN script tag approach. Returns the raw axe.run() result
    as a Python dict.
    """
    page.add_script_tag(url=AXE_CDN_URL)
    # Wait for axe to be available
    page.wait_for_function("typeof window.axe !== 'undefined'", timeout=15000)

    results = page.evaluate("""async () => {
        const results = await axe.run(document, {
            resultTypes: ['violations']
        });
        return {
            violations: results.violations.map(v => ({
                id: v.id,
                impact: v.impact,
                description: v.description,
                helpUrl: v.helpUrl,
                tags: v.tags,
                nodes: v.nodes.map(n => ({
                    target: n.target,
                    html: n.html ? n.html.substring(0, 200) : '',
                    failureSummary: n.failureSummary || ''
                }))
            })),
            url: window.location.href,
            timestamp: new Date().toISOString()
        };
    }""")

    return results


def make_violation_key(violation, node):
    """Create a comparable key from a violation rule ID and target selector.

    Used to match violations between original and clone.
    """
    target = tuple(node.get("target", []))
    return (violation["id"], target)


def index_violations(axe_results):
    """Build a set of (rule_id, target) keys from axe results."""
    keys = set()
    for v in axe_results.get("violations", []):
        for node in v.get("nodes", []):
            keys.add(make_violation_key(v, node))
    return keys


def compute_diff(original_results, clone_results):
    """Find NEW violations in the clone that are not in the original.

    Returns a list of violation dicts (same shape as axe violations) containing
    only the nodes that are new in the clone.
    """
    original_keys = index_violations(original_results)

    new_violations = []
    for v in clone_results.get("violations", []):
        new_nodes = []
        for node in v.get("nodes", []):
            key = make_violation_key(v, node)
            if key not in original_keys:
                new_nodes.append(node)

        if new_nodes:
            new_v = dict(v)
            new_v["nodes"] = new_nodes
            new_violations.append(new_v)

    return new_violations


def count_by_severity(violations):
    """Count violations grouped by severity (impact) level."""
    counts = {s: 0 for s in SEVERITY_ORDER}
    for v in violations:
        impact = v.get("impact", "minor")
        counts[impact] = counts.get(impact, 0) + len(v.get("nodes", []))
    return counts


def total_violation_nodes(violations):
    """Count total violation node instances across all rules."""
    return sum(len(v.get("nodes", [])) for v in violations)


def print_summary(original_results, clone_results, new_violations):
    """Print a formatted summary table to stdout."""
    orig_violations = original_results.get("violations", [])
    clone_violations = clone_results.get("violations", [])

    orig_total = total_violation_nodes(orig_violations)
    clone_total = total_violation_nodes(clone_violations)
    new_total = total_violation_nodes(new_violations)

    orig_by_sev = count_by_severity(orig_violations)
    clone_by_sev = count_by_severity(clone_violations)
    new_by_sev = count_by_severity(new_violations)

    print("\n--- Accessibility Comparison ---\n")
    print(f"{'Severity':<12} {'Original':>10} {'Clone':>10} {'New in Clone':>14}")
    print("-" * 50)

    for sev in SEVERITY_ORDER:
        orig_n = orig_by_sev.get(sev, 0)
        clone_n = clone_by_sev.get(sev, 0)
        new_n = new_by_sev.get(sev, 0)
        marker = " <<<" if new_n > 0 else ""
        print(f"{sev:<12} {orig_n:>10} {clone_n:>10} {new_n:>14}{marker}")

    print("-" * 50)
    print(f"{'TOTAL':<12} {orig_total:>10} {clone_total:>10} {new_total:>14}")

    if new_total == 0:
        print("\nResult: PASS -- clone introduces no new accessibility violations.")
    else:
        print(f"\nResult: FAIL -- clone introduces {new_total} new violation(s).")
        print("\nNew violations in clone:")
        print()
        for v in new_violations:
            impact = v.get("impact", "unknown")
            print(f"  [{impact.upper()}] {v['id']}: {v['description']}")
            for node in v.get("nodes", []):
                targets = ", ".join(node.get("target", []))
                print(f"    Target: {targets}")
                if node.get("failureSummary"):
                    # Indent the failure summary lines
                    for line in node["failureSummary"].split("\n"):
                        if line.strip():
                            print(f"      {line.strip()}")
            print()


def build_report(original_results, clone_results, new_violations):
    """Build the JSON report dict."""
    return {
        "original": {
            "url": original_results.get("url", ""),
            "timestamp": original_results.get("timestamp", ""),
            "violation_count": total_violation_nodes(
                original_results.get("violations", [])
            ),
            "by_severity": count_by_severity(
                original_results.get("violations", [])
            ),
            "violations": original_results.get("violations", []),
        },
        "clone": {
            "url": clone_results.get("url", ""),
            "timestamp": clone_results.get("timestamp", ""),
            "violation_count": total_violation_nodes(
                clone_results.get("violations", [])
            ),
            "by_severity": count_by_severity(
                clone_results.get("violations", [])
            ),
            "violations": clone_results.get("violations", []),
        },
        "diff": {
            "new_violation_count": total_violation_nodes(new_violations),
            "by_severity": count_by_severity(new_violations),
            "new_violations": new_violations,
        },
        "result": "pass" if total_violation_nodes(new_violations) == 0 else "fail",
    }


def audit_url(browser, url):
    """Run axe-core audit on a URL (http/https or file://)."""
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        results = inject_axe_and_run(page)
    finally:
        page.close()
    return results


def resolve_clone_paths(clone_arg):
    """Resolve --clone argument to a list of file:// URLs.

    Accepts a single HTML file or a directory of HTML files.
    """
    clone_path = Path(clone_arg).resolve()
    if clone_path.is_file():
        return [f"file://{clone_path}"]
    elif clone_path.is_dir():
        html_files = sorted(clone_path.glob("*.html")) + sorted(clone_path.glob("*.htm"))
        if not html_files:
            print(f"Error: No HTML files found in {clone_path}")
            sys.exit(1)
        return [f"file://{f.resolve()}" for f in html_files]
    else:
        print(f"Error: Clone path not found: {clone_arg}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Accessibility audit that compares original site vs clone. "
            "Uses axe-core to detect violations and reports NEW issues "
            "introduced in the clone."
        )
    )
    parser.add_argument(
        "--url", required=True,
        help="Original site URL to audit (the baseline)"
    )
    parser.add_argument(
        "--clone", required=True,
        help="Path to clone HTML file or directory of HTML files"
    )
    parser.add_argument(
        "--output",
        help="Output path for JSON report (optional)"
    )
    args = parser.parse_args()

    clone_urls = resolve_clone_paths(args.clone)

    print(f"Original URL: {args.url}")
    print(f"Clone target(s): {len(clone_urls)} file(s)")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Audit the original URL
        print(f"Auditing original: {args.url}")
        try:
            original_results = audit_url(browser, args.url)
        except Exception as e:
            print(f"Error auditing original URL: {e}")
            browser.close()
            sys.exit(1)

        orig_count = total_violation_nodes(original_results.get("violations", []))
        print(f"  Found {orig_count} violation(s) on original")

        # Audit each clone file
        all_clone_violations = []
        clone_results_combined = {"violations": [], "url": "", "timestamp": ""}

        for clone_url in clone_urls:
            filename = clone_url.replace("file://", "").split("/")[-1]
            print(f"Auditing clone: {filename}")
            try:
                clone_results = audit_url(browser, clone_url)
            except Exception as e:
                print(f"  Error auditing clone {filename}: {e}")
                continue

            clone_count = total_violation_nodes(clone_results.get("violations", []))
            print(f"  Found {clone_count} violation(s) on clone")

            # Merge clone results if multiple files
            clone_results_combined["violations"].extend(
                clone_results.get("violations", [])
            )
            clone_results_combined["url"] = clone_results.get("url", "")
            clone_results_combined["timestamp"] = clone_results.get("timestamp", "")

        browser.close()

    # Deduplicate clone violations by (rule_id, impact, description)
    seen_rules = {}
    deduped_violations = []
    for v in clone_results_combined["violations"]:
        rule_id = v["id"]
        if rule_id not in seen_rules:
            seen_rules[rule_id] = v
            deduped_violations.append(v)
        else:
            # Merge nodes from duplicate rules
            existing_targets = {
                tuple(n.get("target", []))
                for n in seen_rules[rule_id].get("nodes", [])
            }
            for node in v.get("nodes", []):
                target_key = tuple(node.get("target", []))
                if target_key not in existing_targets:
                    seen_rules[rule_id]["nodes"].append(node)
                    existing_targets.add(target_key)

    clone_results_combined["violations"] = deduped_violations

    # Compute diff: new violations in clone not present in original
    new_violations = compute_diff(original_results, clone_results_combined)

    # Print terminal summary
    print_summary(original_results, clone_results_combined, new_violations)

    # Write JSON report if requested
    if args.output:
        report = build_report(original_results, clone_results_combined, new_violations)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    # Exit with non-zero status if new violations found
    if total_violation_nodes(new_violations) > 0:
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
