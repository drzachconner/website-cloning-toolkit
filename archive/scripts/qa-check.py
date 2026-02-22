#!/usr/bin/env python3
"""Automated QA validation of cloned HTML pages against a configurable checklist."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)


# Status constants
PASS = "pass"
FAIL = "fail"
WARN = "warn"

# Default placeholder patterns to detect
PLACEHOLDER_PATTERNS = [
    re.compile(r'lorem\s+ipsum', re.IGNORECASE),
    re.compile(r'\bTODO\b'),
    re.compile(r'\bPLACEHOLDER\b', re.IGNORECASE),
    re.compile(r'\bTBD\b'),
    re.compile(r'\bFIXME\b'),
    re.compile(r'\bXXX\b'),
]


def check_doctype(html_text, soup, page_path, config):
    """Check that the page has a DOCTYPE declaration."""
    has_doctype = html_text.strip().lower().startswith("<!doctype")
    return {
        "check": "Has DOCTYPE declaration",
        "category": "structure",
        "status": PASS if has_doctype else FAIL,
        "detail": None if has_doctype else "Missing <!DOCTYPE html> at start of file",
    }


def check_html_lang(html_text, soup, page_path, config):
    """Check that <html> has a lang attribute."""
    html_tag = soup.find("html")
    has_lang = html_tag and html_tag.get("lang")
    return {
        "check": "Has <html lang> attribute",
        "category": "structure",
        "status": PASS if has_lang else FAIL,
        "detail": None if has_lang else "Missing lang attribute on <html> tag",
    }


def check_single_h1(html_text, soup, page_path, config):
    """Check that the page has exactly one <h1> element."""
    h1_tags = soup.find_all("h1")
    count = len(h1_tags)
    if count == 1:
        return {
            "check": "Exactly one <h1>",
            "category": "structure",
            "status": PASS,
            "detail": None,
        }
    elif count == 0:
        return {
            "check": "Exactly one <h1>",
            "category": "structure",
            "status": FAIL,
            "detail": "No <h1> element found",
        }
    else:
        return {
            "check": "Exactly one <h1>",
            "category": "structure",
            "status": FAIL,
            "detail": f"Found {count} <h1> elements (expected 1)",
        }


def check_heading_hierarchy(html_text, soup, page_path, config):
    """Check that heading levels are sequential (no h1 -> h3 skipping h2)."""
    headings = soup.find_all(re.compile(r'^h[1-6]$'))
    if not headings:
        return {
            "check": "Sequential heading hierarchy",
            "category": "structure",
            "status": WARN,
            "detail": "No headings found",
        }

    levels = [int(h.name[1]) for h in headings]
    skips = []
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            skips.append(f"h{levels[i-1]} -> h{levels[i]}")

    if skips:
        return {
            "check": "Sequential heading hierarchy",
            "category": "structure",
            "status": FAIL,
            "detail": f"Heading level skipped: {', '.join(skips)}",
        }
    return {
        "check": "Sequential heading hierarchy",
        "category": "structure",
        "status": PASS,
        "detail": None,
    }


def check_valid_html(html_text, soup, page_path, config):
    """Check for obviously malformed HTML using BeautifulSoup parsing."""
    # BeautifulSoup is lenient, but we can check for common issues
    # Look for stray closing tags or severely broken structure
    issues = []

    # Check if body exists
    if not soup.find("body") and not soup.find("html"):
        issues.append("Missing <body> or <html> element")

    # Check for empty required elements
    head = soup.find("head")
    if not head:
        issues.append("Missing <head> element")

    if issues:
        return {
            "check": "Valid HTML structure",
            "category": "structure",
            "status": FAIL,
            "detail": "; ".join(issues),
        }
    return {
        "check": "Valid HTML structure",
        "category": "structure",
        "status": PASS,
        "detail": None,
    }


def check_no_inline_style_tags(html_text, soup, page_path, config):
    """Check that there are no inline <style> tags in the document."""
    style_tags = soup.find_all("style")
    if style_tags:
        return {
            "check": "No inline <style> tags",
            "category": "css",
            "status": FAIL,
            "detail": f"Found {len(style_tags)} inline <style> tag(s)",
            "fixable": True,
        }
    return {
        "check": "No inline <style> tags",
        "category": "css",
        "status": PASS,
        "detail": None,
    }


def check_external_stylesheet(html_text, soup, page_path, config):
    """Check that an external stylesheet link is present in <head>."""
    head = soup.find("head")
    if not head:
        return {
            "check": "Has external stylesheet",
            "category": "css",
            "status": FAIL,
            "detail": "No <head> element found",
        }

    links = head.find_all("link", rel="stylesheet")
    if not links:
        return {
            "check": "Has external stylesheet",
            "category": "css",
            "status": FAIL,
            "detail": "No <link rel='stylesheet'> found in <head>",
        }
    return {
        "check": "Has external stylesheet",
        "category": "css",
        "status": PASS,
        "detail": None,
    }


def check_css_file_exists(html_text, soup, page_path, config):
    """Check that referenced CSS files actually exist at the resolved path."""
    head = soup.find("head")
    if not head:
        return {
            "check": "CSS file exists",
            "category": "css",
            "status": WARN,
            "detail": "No <head> element to check",
        }

    links = head.find_all("link", rel="stylesheet")
    missing = []

    for link in links:
        href = link.get("href", "")
        if not href or href.startswith("http://") or href.startswith("https://"):
            continue
        resolved = (page_path.parent / href).resolve()
        if not resolved.is_file():
            missing.append(href)

    if missing:
        return {
            "check": "CSS file exists",
            "category": "css",
            "status": FAIL,
            "detail": f"Missing CSS file(s): {', '.join(missing)}",
        }
    return {
        "check": "CSS file exists",
        "category": "css",
        "status": PASS,
        "detail": None,
    }


def check_favicon(html_text, soup, page_path, config):
    """Check that a favicon link is present."""
    favicon = soup.find("link", rel=lambda x: x and "icon" in x)
    if not favicon:
        return {
            "check": "Has favicon link",
            "category": "assets",
            "status": FAIL,
            "detail": "No <link rel='icon'> or <link rel='shortcut icon'> found",
        }
    return {
        "check": "Has favicon link",
        "category": "assets",
        "status": PASS,
        "detail": None,
    }


def check_images_exist(html_text, soup, page_path, config):
    """Check that all img src paths resolve to existing files."""
    images = soup.find_all("img")
    if not images:
        return {
            "check": "All images exist",
            "category": "assets",
            "status": PASS,
            "detail": "No images found",
        }

    missing = []
    for img in images:
        src = img.get("src", "")
        if not src or src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
            continue
        resolved = (page_path.parent / src).resolve()
        if not resolved.is_file():
            missing.append(src)

    if missing:
        display = missing[:5]
        extra = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
        return {
            "check": "All images exist",
            "category": "assets",
            "status": FAIL,
            "detail": f"Missing image(s): {', '.join(display)}{extra}",
        }
    return {
        "check": "All images exist",
        "category": "assets",
        "status": PASS,
        "detail": None,
    }


def check_no_absolute_original_urls(html_text, soup, page_path, config):
    """Check for leftover absolute URLs pointing to the original domain."""
    original_domain = config.get("original_domain")
    if not original_domain:
        return {
            "check": "No absolute original URLs",
            "category": "assets",
            "status": WARN,
            "detail": "No original_domain configured in checklist; skipping",
        }

    pattern = re.compile(re.escape(original_domain), re.IGNORECASE)
    matches = pattern.findall(html_text)
    if matches:
        return {
            "check": "No absolute original URLs",
            "category": "assets",
            "status": FAIL,
            "detail": f"Found {len(matches)} reference(s) to original domain '{original_domain}'",
        }
    return {
        "check": "No absolute original URLs",
        "category": "assets",
        "status": PASS,
        "detail": None,
    }


def check_title(html_text, soup, page_path, config):
    """Check that <title> is present and non-empty."""
    title = soup.find("title")
    if not title or not title.string or not title.string.strip():
        return {
            "check": "Has non-empty <title>",
            "category": "metadata",
            "status": FAIL,
            "detail": "Missing or empty <title> tag",
        }
    return {
        "check": "Has non-empty <title>",
        "category": "metadata",
        "status": PASS,
        "detail": None,
    }


def check_meta_description(html_text, soup, page_path, config):
    """Check that <meta name='description'> is present."""
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content", "").strip():
        return {
            "check": "Has meta description",
            "category": "metadata",
            "status": FAIL,
            "detail": "Missing or empty <meta name='description'>",
        }
    return {
        "check": "Has meta description",
        "category": "metadata",
        "status": PASS,
        "detail": None,
    }


def check_schema_org(html_text, soup, page_path, config):
    """Check for Schema.org JSON-LD structured data (optional, warn only)."""
    scripts = soup.find_all("script", type="application/ld+json")
    if not scripts:
        return {
            "check": "Schema.org JSON-LD present",
            "category": "metadata",
            "status": WARN,
            "detail": "No Schema.org JSON-LD found (optional)",
        }
    return {
        "check": "Schema.org JSON-LD present",
        "category": "metadata",
        "status": PASS,
        "detail": None,
    }


def check_no_placeholder_text(html_text, soup, page_path, config):
    """Check for placeholder text like Lorem ipsum, TODO, PLACEHOLDER, TBD."""
    # Get visible text content only
    text = soup.get_text()
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            found.append(f"'{matches[0]}' ({len(matches)}x)")

    if found:
        return {
            "check": "No placeholder text",
            "category": "content",
            "status": FAIL,
            "detail": f"Found placeholder text: {', '.join(found)}",
        }
    return {
        "check": "No placeholder text",
        "category": "content",
        "status": PASS,
        "detail": None,
    }


def check_content_wrapper(html_text, soup, page_path, config):
    """Check that the configured content wrapper class is present."""
    wrapper_class = config.get("content_wrapper_class")
    if not wrapper_class:
        return {
            "check": "Content wrapper class present",
            "category": "content",
            "status": WARN,
            "detail": "No content_wrapper_class configured in checklist; skipping",
        }

    wrapper = soup.find(class_=wrapper_class)
    if not wrapper:
        return {
            "check": "Content wrapper class present",
            "category": "content",
            "status": FAIL,
            "detail": f"Content wrapper class '{wrapper_class}' not found",
        }
    return {
        "check": "Content wrapper class present",
        "category": "content",
        "status": PASS,
        "detail": None,
    }


# All check functions in execution order
ALL_CHECKS = [
    # Structure
    check_doctype,
    check_html_lang,
    check_single_h1,
    check_heading_hierarchy,
    check_valid_html,
    # CSS
    check_no_inline_style_tags,
    check_external_stylesheet,
    check_css_file_exists,
    # Assets
    check_favicon,
    check_images_exist,
    check_no_absolute_original_urls,
    # Metadata
    check_title,
    check_meta_description,
    check_schema_org,
    # Content
    check_no_placeholder_text,
    check_content_wrapper,
]


def load_checklist_config(checklist_path):
    """Load configuration from a checklist file.

    Supports JSON format with optional keys:
    - original_domain: domain to detect leftover absolute URLs
    - content_wrapper_class: expected content wrapper CSS class
    - disabled_checks: list of check names to skip
    """
    if not checklist_path:
        return {}

    path = Path(checklist_path)
    if not path.is_file():
        print(f"Warning: Checklist file not found: {checklist_path}, using defaults")
        return {}

    text = path.read_text(encoding="utf-8", errors="replace")

    # Try JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Parse markdown checklist for configuration hints
    config = {}
    for line in text.splitlines():
        line = line.strip()
        # Look for key: value patterns in markdown
        match = re.match(r'^[-*]?\s*\*?\*?(\w[\w_]+)\*?\*?\s*[:=]\s*(.+)', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip().strip("`\"'")
            config[key] = value

    return config


def apply_fixes(page_path, html_text, soup, results):
    """Apply auto-fixes for common issues and return updated HTML text."""
    modified = False

    head = soup.find("head")
    if not head:
        return html_text, False

    # Fix: Add missing <meta charset="utf-8">
    charset = soup.find("meta", attrs={"charset": True})
    if not charset:
        charset_equiv = soup.find("meta", attrs={"http-equiv": re.compile("content-type", re.I)})
        if not charset_equiv:
            new_meta = soup.new_tag("meta", charset="utf-8")
            head.insert(0, new_meta)
            modified = True
            print(f"  Fixed: Added <meta charset='utf-8'>")

    # Fix: Add missing <meta name="viewport">
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        new_meta = soup.new_tag("meta", attrs={
            "name": "viewport",
            "content": "width=device-width, initial-scale=1",
        })
        # Insert after charset if it exists, otherwise at start of head
        charset_tag = soup.find("meta", attrs={"charset": True})
        if charset_tag:
            charset_tag.insert_after(new_meta)
        else:
            head.insert(0, new_meta)
        modified = True
        print(f"  Fixed: Added <meta name='viewport'>")

    # Fix: Move inline <style> content to external CSS
    style_tags = soup.find_all("style")
    if style_tags:
        css_content_parts = []
        for style in style_tags:
            text = style.string or style.get_text()
            if text.strip():
                css_content_parts.append(text.strip())
            style.decompose()

        if css_content_parts:
            # Look for existing CSS link to determine filename
            css_link = head.find("link", rel="stylesheet")
            if css_link and css_link.get("href"):
                href = css_link["href"]
                css_path = (page_path.parent / href).resolve()
            else:
                css_path = page_path.parent / "extracted-inline.css"
                # Also add a link to the new CSS file
                new_link = soup.new_tag("link", rel="stylesheet",
                                        href="extracted-inline.css")
                head.append(new_link)

            # Append extracted CSS to the file
            inline_css = "\n\n/* Extracted from inline <style> tags */\n" + "\n\n".join(css_content_parts)
            try:
                with open(css_path, "a", encoding="utf-8") as f:
                    f.write(inline_css)
                print(f"  Fixed: Moved inline styles to {css_path.name}")
            except Exception as e:
                print(f"  Warning: Could not write extracted CSS: {e}")

            modified = True

    if modified:
        return soup.prettify(), True
    return html_text, False


def run_checks(page_path, config):
    """Run all checks on a single HTML file and return results."""
    html_text = page_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html_text, "html.parser")

    disabled = config.get("disabled_checks", [])
    results = []

    for check_fn in ALL_CHECKS:
        check_name = check_fn.__doc__.strip().split(".")[0] if check_fn.__doc__ else check_fn.__name__
        if check_name in disabled:
            continue
        try:
            result = check_fn(html_text, soup, page_path, config)
            results.append(result)
        except Exception as e:
            results.append({
                "check": check_name,
                "category": "error",
                "status": FAIL,
                "detail": f"Check raised an exception: {e}",
            })

    return results, html_text, soup


def print_terminal_results(all_results):
    """Print a colored summary table to the terminal."""
    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    status_colors = {
        PASS: GREEN,
        FAIL: RED,
        WARN: YELLOW,
    }

    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}QA Check Results{RESET}")
    print(f"{'='*80}\n")

    for file_name, results in sorted(all_results.items()):
        pass_count = sum(1 for r in results if r["status"] == PASS)
        fail_count = sum(1 for r in results if r["status"] == FAIL)
        warn_count = sum(1 for r in results if r["status"] == WARN)

        overall_color = GREEN if fail_count == 0 else RED
        print(f"{BOLD}{file_name}{RESET}  "
              f"{GREEN}{pass_count} pass{RESET}  "
              f"{RED}{fail_count} fail{RESET}  "
              f"{YELLOW}{warn_count} warn{RESET}")

        for result in results:
            status = result["status"]
            color = status_colors.get(status, RESET)
            icon = {"pass": "+", "fail": "X", "warn": "!"}[status]
            line = f"  [{icon}] {result['check']}"
            if result.get("detail"):
                line += f" -- {result['detail']}"
            print(f"  {color}{line}{RESET}")

        print()

    # Grand totals
    total_files = len(all_results)
    total_pass = sum(sum(1 for r in results if r["status"] == PASS)
                     for results in all_results.values())
    total_fail = sum(sum(1 for r in results if r["status"] == FAIL)
                     for results in all_results.values())
    total_warn = sum(sum(1 for r in results if r["status"] == WARN)
                     for results in all_results.values())

    print(f"{'='*80}")
    print(f"{BOLD}Total: {total_files} files, "
          f"{GREEN}{total_pass} pass{RESET}, "
          f"{RED}{total_fail} fail{RESET}, "
          f"{YELLOW}{total_warn} warn{RESET}")
    print(f"{'='*80}")

    return total_fail


def generate_html_report(all_results, output_path):
    """Generate an HTML report with per-file, per-check details."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>QA Check Report</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; ",
        "  margin: 0; padding: 20px; background: #f5f5f5; color: #333; }",
        "h1 { text-align: center; margin-bottom: 10px; }",
        ".summary { text-align: center; margin-bottom: 30px; color: #666; }",
        ".file-section { background: #fff; border-radius: 8px; padding: 20px; ",
        "  margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
        ".file-section h2 { margin-top: 0; cursor: pointer; }",
        ".file-section h2:hover { color: #0066cc; }",
        ".status { display: inline-block; padding: 2px 10px; border-radius: 12px; ",
        "  font-size: 13px; font-weight: bold; }",
        ".pass { background: #d4edda; color: #155724; }",
        ".fail { background: #f8d7da; color: #721c24; }",
        ".warn { background: #fff3cd; color: #856404; }",
        "table { width: 100%; border-collapse: collapse; margin: 10px 0; }",
        "th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; }",
        "th { background: #f8f9fa; }",
        ".detail { color: #666; font-size: 13px; }",
        ".checks-table { display: block; }",
        ".category-label { font-size: 11px; text-transform: uppercase; color: #999; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>QA Check Report</h1>",
    ]

    # Grand totals
    total_files = len(all_results)
    total_pass = sum(sum(1 for r in results if r["status"] == PASS)
                     for results in all_results.values())
    total_fail = sum(sum(1 for r in results if r["status"] == FAIL)
                     for results in all_results.values())
    total_warn = sum(sum(1 for r in results if r["status"] == WARN)
                     for results in all_results.values())

    clean_files = sum(1 for results in all_results.values()
                      if all(r["status"] != FAIL for r in results))

    html_parts.append(
        f"<p class='summary'>{total_files} files checked: "
        f"{clean_files} clean, {total_files - clean_files} with issues "
        f"({total_pass} pass, {total_fail} fail, {total_warn} warn)</p>"
    )

    # Summary table
    html_parts.append("<table>")
    html_parts.append("<tr><th>File</th><th>Pass</th><th>Fail</th><th>Warn</th><th>Status</th></tr>")

    for file_name, results in sorted(all_results.items()):
        pc = sum(1 for r in results if r["status"] == PASS)
        fc = sum(1 for r in results if r["status"] == FAIL)
        wc = sum(1 for r in results if r["status"] == WARN)
        status = "pass" if fc == 0 else "fail"
        html_parts.append(
            f"<tr><td>{file_name}</td><td>{pc}</td><td>{fc}</td><td>{wc}</td>"
            f"<td><span class='status {status}'>{status.upper()}</span></td></tr>"
        )

    html_parts.append("</table>")

    # Detailed per-file sections
    for file_name, results in sorted(all_results.items()):
        fc = sum(1 for r in results if r["status"] == FAIL)
        overall = "pass" if fc == 0 else "fail"

        html_parts.append("<div class='file-section'>")
        html_parts.append(
            f"<h2>{file_name} <span class='status {overall}'>{overall.upper()}</span></h2>"
        )

        html_parts.append("<table class='checks-table'>")
        html_parts.append("<tr><th>Check</th><th>Category</th><th>Status</th><th>Detail</th></tr>")

        for r in results:
            status_class = r["status"]
            detail = r.get("detail") or ""
            html_parts.append(
                f"<tr>"
                f"<td>{r['check']}</td>"
                f"<td><span class='category-label'>{r['category']}</span></td>"
                f"<td><span class='status {status_class}'>{r['status'].upper()}</span></td>"
                f"<td class='detail'>{detail}</td>"
                f"</tr>"
            )

        html_parts.append("</table>")
        html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])

    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(html_parts), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run automated QA checks on cloned HTML pages. Validates structure, "
            "CSS, assets, metadata, and content against a configurable checklist."
        )
    )
    parser.add_argument(
        "--pages", required=True,
        help="Directory of HTML files to check (required)"
    )
    parser.add_argument(
        "--checklist",
        help=(
            "Checklist config file (JSON) with optional keys: original_domain, "
            "content_wrapper_class, disabled_checks. Uses built-in defaults if omitted."
        )
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Attempt to auto-fix common issues (missing charset, viewport, inline styles)"
    )
    parser.add_argument(
        "--output",
        help="Output path for JSON results. An HTML report is also generated alongside it."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.pages):
        print(f"Error: Pages directory not found: {args.pages}")
        sys.exit(1)

    pages_dir = Path(args.pages)
    html_files = sorted(pages_dir.glob("*.html")) + sorted(pages_dir.glob("*.htm"))

    if not html_files:
        print(f"No HTML files found in {args.pages}")
        sys.exit(1)

    config = load_checklist_config(args.checklist)
    print(f"Checking {len(html_files)} HTML file(s) in {args.pages}/")

    if config:
        if config.get("original_domain"):
            print(f"  Original domain: {config['original_domain']}")
        if config.get("content_wrapper_class"):
            print(f"  Content wrapper: {config['content_wrapper_class']}")

    all_results = {}
    fix_count = 0

    for html_file in html_files:
        results, html_text, soup = run_checks(html_file, config)
        all_results[html_file.name] = results

        if args.fix:
            updated_text, was_fixed = apply_fixes(html_file, html_text, soup, results)
            if was_fixed:
                html_file.write_text(updated_text, encoding="utf-8")
                fix_count += 1
                # Re-run checks after fix
                results, _, _ = run_checks(html_file, config)
                all_results[html_file.name] = results

    # Print terminal output
    total_fail = print_terminal_results(all_results)

    if args.fix:
        print(f"\nAuto-fix: applied fixes to {fix_count} file(s)")

    # Write JSON output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nJSON results saved to: {output_path}")

        # Generate HTML report alongside JSON
        html_report_path = output_path.with_suffix(".html")
        report = generate_html_report(all_results, html_report_path)
        print(f"HTML report saved to: {report}")

    print("\nDone.")

    # Exit with non-zero status if there were failures
    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
