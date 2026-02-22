#!/usr/bin/env python3
"""Scrape a website using Playwright, saving HTML and optional screenshots."""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright is required. Install with: pip install playwright && playwright install")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


def discover_sitemap_urls(base_url):
    """Fetch sitemap.xml and extract all URLs."""
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    print(f"Fetching sitemap: {sitemap_url}")
    try:
        resp = requests.get(sitemap_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Warning: Could not fetch sitemap: {e}")
        return []

    urls = []
    try:
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.findall(".//sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())
        # Also try without namespace (some sitemaps omit it)
        if not urls:
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    urls.append(loc.text.strip())
    except ET.ParseError as e:
        print(f"Warning: Could not parse sitemap XML: {e}")

    print(f"Discovered {len(urls)} URLs from sitemap")
    return urls


def load_urls_from_file(filepath):
    """Read URLs from a text file, one per line."""
    urls = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def sanitize_filename(url):
    """Convert a URL to a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    safe = path.replace("/", "_").replace(".", "_")
    return safe


def scrape_pages(urls, output_dir, screenshots=False, selector=None):
    """Scrape all given URLs using Playwright."""
    extracted_dir = Path(output_dir) / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    screenshots_dir = None
    if screenshots:
        screenshots_dir = Path(output_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Scraping: {url}")
            filename = sanitize_filename(url)
            entry = {"url": url, "filename": filename, "timestamp": time.time()}

            try:
                page.goto(url, wait_until="networkidle", timeout=60000)

                if selector:
                    elements = page.query_selector_all(selector)
                    if elements:
                        html_parts = []
                        for el in elements:
                            html_parts.append(el.inner_html())
                        html_content = "\n".join(html_parts)
                        entry["selector"] = selector
                        entry["matches"] = len(elements)
                    else:
                        print(f"  Warning: Selector '{selector}' matched no elements, saving full page")
                        html_content = page.content()
                else:
                    html_content = page.content()

                html_path = extracted_dir / f"{filename}.html"
                html_path.write_text(html_content, encoding="utf-8")
                entry["html_file"] = str(html_path.relative_to(output_dir))
                entry["status"] = "ok"
                print(f"  Saved HTML: {html_path.name}")

                if screenshots_dir:
                    screenshot_path = screenshots_dir / f"{filename}.png"
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    entry["screenshot_file"] = str(screenshot_path.relative_to(output_dir))
                    print(f"  Saved screenshot: {screenshot_path.name}")

            except Exception as e:
                print(f"  Error: {e}")
                entry["status"] = "error"
                entry["error"] = str(e)

            manifest.append(entry)

        browser.close()

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a website using Playwright. Saves raw HTML and optional screenshots."
    )
    parser.add_argument(
        "--url", help="Single URL to scrape"
    )
    parser.add_argument(
        "--urls-file", help="Path to a text file containing URLs (one per line)"
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for scraped content"
    )
    parser.add_argument(
        "--sitemap", action="store_true",
        help="Discover additional URLs from the site's sitemap.xml"
    )
    parser.add_argument(
        "--screenshots", action="store_true",
        help="Take full-page screenshots of each page"
    )
    parser.add_argument(
        "--selector", help="CSS selector to extract specific content instead of full page"
    )
    args = parser.parse_args()

    if not args.url and not args.urls_file:
        parser.error("At least one of --url or --urls-file is required")

    urls = []
    if args.url:
        urls.append(args.url)
    if args.urls_file:
        if not os.path.isfile(args.urls_file):
            print(f"Error: URLs file not found: {args.urls_file}")
            sys.exit(1)
        urls.extend(load_urls_from_file(args.urls_file))

    if args.sitemap and args.url:
        sitemap_urls = discover_sitemap_urls(args.url)
        for u in sitemap_urls:
            if u not in urls:
                urls.append(u)

    if not urls:
        print("Error: No URLs to scrape")
        sys.exit(1)

    print(f"Scraping {len(urls)} URL(s) to {args.output}/")
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    manifest = scrape_pages(
        urls, args.output,
        screenshots=args.screenshots,
        selector=args.selector
    )

    manifest_path = output_path / "index.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")

    ok = sum(1 for e in manifest if e["status"] == "ok")
    err = sum(1 for e in manifest if e["status"] == "error")
    print(f"Done: {ok} succeeded, {err} failed out of {len(manifest)} total")


if __name__ == "__main__":
    main()
