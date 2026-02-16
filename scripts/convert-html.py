#!/usr/bin/env python3
"""Convert scraped HTML files by applying class mappings, rewriting paths, and cleaning up."""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)


def load_class_map(config_path):
    """Load class mapping configuration from JSON file.

    Expected format:
    {
        "class_map": {"source-class": "target-class", ...},
        "remove_elements": ["nav", "footer", "script", ...],
        "page_shell": "<div id='wrapper'>{{content}}</div>",
        "asset_base": "../images/"
    }
    """
    with open(config_path, "r") as f:
        config = json.load(f)
    return config


def archive_originals(input_dir, archive_name="input_archive"):
    """Copy original files to archive directory before processing."""
    input_path = Path(input_dir)
    archive_path = input_path.parent / archive_name
    if archive_path.exists():
        print(f"Archive already exists: {archive_path}")
        return

    print(f"Archiving originals to: {archive_path}")
    shutil.copytree(input_path, archive_path)
    print(f"  Archived {sum(1 for _ in archive_path.rglob('*.html'))} HTML files")


def structure_pass(soup, config):
    """Pass 1: Wrap content in target page shell if configured."""
    page_shell = config.get("page_shell")
    if not page_shell:
        return soup

    if "{{content}}" not in page_shell:
        print("  Warning: page_shell missing {{content}} placeholder, skipping structure pass")
        return soup

    body = soup.find("body")
    if body:
        inner_html = body.decode_contents()
    else:
        inner_html = soup.decode_contents()

    wrapped_html = page_shell.replace("{{content}}", inner_html)
    new_soup = BeautifulSoup(wrapped_html, "html.parser")

    if body:
        body.clear()
        for child in list(new_soup.children):
            body.append(child.extract())
        return soup
    else:
        return new_soup


def class_pass(soup, config):
    """Pass 2: Rename CSS classes per the mapping configuration."""
    class_map = config.get("class_map", {})
    if not class_map:
        return soup

    rename_count = 0
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        if not classes:
            continue

        new_classes = []
        changed = False
        for cls in classes:
            if cls in class_map:
                mapped = class_map[cls]
                if mapped:  # Non-empty string means rename
                    new_classes.append(mapped)
                    changed = True
                else:  # Empty string means remove the class
                    changed = True
            else:
                new_classes.append(cls)

        if changed:
            if new_classes:
                tag["class"] = new_classes
            else:
                del tag["class"]
            rename_count += 1

    if rename_count:
        print(f"  Class pass: renamed classes on {rename_count} element(s)")

    return soup


def asset_pass(soup, config):
    """Pass 3: Rewrite image and link paths to relative paths."""
    asset_base = config.get("asset_base", "")
    rewrite_count = 0

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src and (src.startswith("http://") or src.startswith("https://")):
            filename = os.path.basename(src.split("?")[0])
            if asset_base:
                img["src"] = asset_base + filename
            else:
                img["src"] = filename
            rewrite_count += 1

    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href", "")
        if href and (href.startswith("http://") or href.startswith("https://")):
            filename = os.path.basename(href.split("?")[0])
            if asset_base:
                link["href"] = asset_base + filename
            else:
                link["href"] = filename
            rewrite_count += 1

    if rewrite_count:
        print(f"  Asset pass: rewrote {rewrite_count} path(s)")

    return soup


def cleanup_pass(soup, config):
    """Pass 4: Remove unwanted elements (nav, footer, scripts, etc.)."""
    remove_selectors = config.get("remove_elements", [])
    if not remove_selectors:
        remove_selectors = ["script", "noscript"]

    removed = 0
    for selector in remove_selectors:
        for el in soup.select(selector):
            el.decompose()
            removed += 1

    if removed:
        print(f"  Cleanup pass: removed {removed} element(s)")

    return soup


def inject_into_template(content_html, template_path):
    """Inject converted content into a template file."""
    template_text = Path(template_path).read_text(encoding="utf-8")

    if "{{content}}" in template_text:
        return template_text.replace("{{content}}", content_html)
    elif "<!-- CONTENT -->" in template_text:
        return template_text.replace("<!-- CONTENT -->", content_html)
    else:
        print("  Warning: Template has no {{content}} or <!-- CONTENT --> placeholder")
        return template_text + "\n" + content_html


def process_file(html_path, config, template_path=None):
    """Run all conversion passes on a single HTML file."""
    print(f"Processing: {html_path.name}")

    html_text = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html_text, "html.parser")

    soup = structure_pass(soup, config)
    soup = class_pass(soup, config)
    soup = asset_pass(soup, config)
    soup = cleanup_pass(soup, config)

    if template_path:
        content_div = soup.find(class_=re.compile("entry-content|content|main"))
        if content_div:
            content_html = content_div.decode_contents()
        else:
            content_html = soup.decode_contents()
        return inject_into_template(content_html, template_path)
    else:
        return soup.prettify()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert scraped HTML files by applying class mappings, "
            "rewriting asset paths, and removing unwanted elements."
        )
    )
    parser.add_argument(
        "--input", required=True, help="Input directory containing HTML files"
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for converted HTML files"
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to JSON config file with class mappings and conversion rules"
    )
    parser.add_argument(
        "--template",
        help="Optional HTML template file. Content will be injected at {{content}} placeholder."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"Error: Input directory not found: {args.input}")
        sys.exit(1)

    if not os.path.isfile(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    if args.template and not os.path.isfile(args.template):
        print(f"Error: Template file not found: {args.template}")
        sys.exit(1)

    config = load_class_map(args.config)
    print(f"Loaded config with {len(config.get('class_map', {}))} class mappings")

    archive_originals(args.input)

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_path.glob("*.html")) + sorted(input_path.glob("*.htm"))

    if not html_files:
        print(f"No HTML files found in {args.input}")
        sys.exit(1)

    print(f"\nConverting {len(html_files)} file(s)...\n")

    success = 0
    errors = 0

    for html_file in html_files:
        try:
            result = process_file(html_file, config, args.template)
            out_file = output_path / html_file.name
            out_file.write_text(result, encoding="utf-8")
            success += 1
        except Exception as e:
            print(f"  Error processing {html_file.name}: {e}")
            errors += 1

    print(f"\nDone: {success} converted, {errors} errors")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
