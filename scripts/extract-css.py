#!/usr/bin/env python3
"""Extract and combine CSS from a website, optionally subsetting to used rules only."""

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    import cssutils
    import logging
    cssutils.log.setLevel(logging.CRITICAL)
except ImportError:
    print("Error: cssutils is required. Install with: pip install cssutils")
    sys.exit(1)


def fetch_url(url, timeout=30):
    """Fetch URL content with error handling."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  Warning: Could not fetch {url}: {e}")
        return None


def discover_css_urls(page_url):
    """Find all linked CSS files from an HTML page."""
    print(f"Fetching page: {page_url}")
    html = fetch_url(page_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    css_urls = []

    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            absolute = urljoin(page_url, href)
            css_urls.append(absolute)

    for style in soup.find_all("style"):
        text = style.string or ""
        for match in re.finditer(r'@import\s+url\(["\']?([^"\')]+)["\']?\)', text):
            absolute = urljoin(page_url, match.group(1))
            css_urls.append(absolute)

    return css_urls


def download_css(css_urls):
    """Download all CSS files and return combined content."""
    combined = []
    for i, url in enumerate(css_urls, 1):
        print(f"  [{i}/{len(css_urls)}] Downloading: {url}")
        content = fetch_url(url)
        if content:
            combined.append(f"/* Source: {url} */\n{content}")
    return "\n\n".join(combined)


def collect_used_classes(html_dir):
    """Scan HTML files to find all CSS classes and IDs in use."""
    html_dir = Path(html_dir)
    classes = set()
    ids = set()
    elements = set()

    html_files = list(html_dir.glob("**/*.html")) + list(html_dir.glob("**/*.htm"))
    print(f"Scanning {len(html_files)} HTML files for used selectors...")

    for html_file in html_files:
        try:
            soup = BeautifulSoup(html_file.read_text(encoding="utf-8", errors="replace"), "html.parser")
        except Exception as e:
            print(f"  Warning: Could not parse {html_file.name}: {e}")
            continue

        for tag in soup.find_all(True):
            elements.add(tag.name)
            for cls in tag.get("class", []):
                classes.add(cls)
            tag_id = tag.get("id")
            if tag_id:
                ids.add(tag_id)

    print(f"  Found {len(classes)} classes, {len(ids)} IDs, {len(elements)} element types")
    return classes, ids, elements


def selector_matches_used(selector_text, used_classes, used_ids, used_elements):
    """Check if a CSS selector references any of the used classes/IDs/elements."""
    selector_text = selector_text.strip()
    if not selector_text:
        return False

    # Always keep @-rules, pseudo-elements on universal selectors, etc.
    if selector_text.startswith("@") or selector_text in ("*", "html", "body", ":root"):
        return True

    for cls in used_classes:
        if f".{cls}" in selector_text:
            return True
    for id_ in used_ids:
        if f"#{id_}" in selector_text:
            return True
    for elem in used_elements:
        if re.search(r'(?:^|[\s>+~,])' + re.escape(elem) + r'(?:$|[\s>+~,.:[\]#])', selector_text):
            return True

    return False


def subset_css(css_text, used_classes, used_ids, used_elements):
    """Remove CSS rules that don't match any used selectors."""
    sheet = cssutils.parseString(css_text)
    kept = 0
    removed = 0

    rules_to_remove = []
    for rule in sheet:
        if rule.type == rule.STYLE_RULE:
            if not selector_matches_used(rule.selectorText, used_classes, used_ids, used_elements):
                rules_to_remove.append(rule)
                removed += 1
            else:
                kept += 1
        else:
            kept += 1

    for rule in rules_to_remove:
        sheet.deleteRule(rule)

    print(f"  Subset result: kept {kept} rules, removed {removed} unused rules")
    return sheet.cssText.decode("utf-8") if isinstance(sheet.cssText, bytes) else sheet.cssText


def analyze_css(css_text):
    """Extract font families, colors, and key measurements from CSS."""
    fonts = set()
    colors = set()
    measurements = {}

    for match in re.finditer(r'font-family\s*:\s*([^;}{]+)', css_text):
        families = match.group(1).strip().rstrip("!important").strip()
        fonts.add(families)

    color_pattern = r'(?:color|background-color|background|border-color|border)\s*:\s*([^;}{]+)'
    for match in re.finditer(color_pattern, css_text):
        value = match.group(1).strip()
        hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}', value)
        colors.update(hex_matches)
        rgb_matches = re.findall(r'rgba?\([^)]+\)', value)
        colors.update(rgb_matches)
        hsl_matches = re.findall(r'hsla?\([^)]+\)', value)
        colors.update(hsl_matches)

    for prop in ["max-width", "min-width", "font-size", "line-height"]:
        values = set()
        for match in re.finditer(re.escape(prop) + r'\s*:\s*([^;}{]+)', css_text):
            values.add(match.group(1).strip())
        if values:
            measurements[prop] = sorted(values)

    return fonts, colors, measurements


def main():
    parser = argparse.ArgumentParser(
        description="Extract and combine CSS from a website. Optionally subset to only used rules."
    )
    parser.add_argument(
        "--url", required=True, help="Target page URL to discover CSS files from"
    )
    parser.add_argument(
        "--output", required=True, help="Output path for the combined CSS file"
    )
    parser.add_argument(
        "--subset", action="store_true",
        help="Subset CSS to only rules used in HTML files (requires --html-dir)"
    )
    parser.add_argument(
        "--html-dir",
        help="Directory of HTML files to scan for used CSS classes (used with --subset)"
    )
    args = parser.parse_args()

    if args.subset and not args.html_dir:
        parser.error("--subset requires --html-dir to scan for used CSS classes")

    if args.html_dir and not os.path.isdir(args.html_dir):
        print(f"Error: HTML directory not found: {args.html_dir}")
        sys.exit(1)

    css_urls = discover_css_urls(args.url)
    if not css_urls:
        print("No CSS files found on the page")
        sys.exit(1)

    print(f"Found {len(css_urls)} CSS file(s)")
    combined = download_css(css_urls)

    if not combined:
        print("Error: No CSS content could be downloaded")
        sys.exit(1)

    if args.subset:
        used_classes, used_ids, used_elements = collect_used_classes(args.html_dir)
        combined = subset_css(combined, used_classes, used_ids, used_elements)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined, encoding="utf-8")
    print(f"\nCSS saved to: {output_path}")

    print("\n--- Design System Summary ---")
    fonts, colors, measurements = analyze_css(combined)

    if fonts:
        print(f"\nFont families ({len(fonts)}):")
        for f in sorted(fonts):
            print(f"  {f}")

    if colors:
        print(f"\nColors ({len(colors)}):")
        for c in sorted(colors):
            print(f"  {c}")

    if measurements:
        print("\nKey measurements:")
        for prop, values in sorted(measurements.items()):
            print(f"  {prop}: {', '.join(values[:5])}")
            if len(values) > 5:
                print(f"    ... and {len(values) - 5} more")

    print("\nDone.")


if __name__ == "__main__":
    main()
