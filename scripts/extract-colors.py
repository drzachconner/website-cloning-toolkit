#!/usr/bin/env python3
"""Extract a color palette from a website by analyzing computed styles."""

import argparse
import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright is required. Install with: pip install playwright && playwright install")
    sys.exit(1)


# Elements to sample for color extraction
SELECTORS = {
    "headings": ["h1", "h2", "h3", "h4", "h5", "h6"],
    "text": ["body", "p", "span", "li"],
    "links": ["a", "a:hover"],
    "buttons": ["button", ".btn", "[type='submit']", "input[type='button']"],
    "navigation": ["nav", "nav a", ".navbar", ".menu", "header"],
    "backgrounds": ["body", "header", "footer", "nav", "main", "section", ".container"],
    "footer": ["footer", "footer a", "footer p"],
}


def extract_colors_from_page(page):
    """Use JavaScript to extract computed colors from key elements."""
    return page.evaluate("""() => {
        const selectors = {
            headings: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
            text: ['body', 'p', 'span', 'li'],
            links: ['a'],
            buttons: ['button', '.btn', "[type='submit']", "input[type='button']"],
            navigation: ['nav', 'nav a', '.navbar', '.menu', 'header'],
            backgrounds: ['body', 'header', 'footer', 'nav', 'main', 'section', '.container'],
            footer: ['footer', 'footer a', 'footer p'],
        };

        const results = {};

        for (const [category, sels] of Object.entries(selectors)) {
            const colors = new Set();
            const bgColors = new Set();

            for (const sel of sels) {
                const elements = document.querySelectorAll(sel);
                for (const el of elements) {
                    const style = window.getComputedStyle(el);
                    const color = style.color;
                    const bg = style.backgroundColor;

                    if (color && color !== 'rgba(0, 0, 0, 0)') {
                        colors.add(color);
                    }
                    if (bg && bg !== 'rgba(0, 0, 0, 0)') {
                        bgColors.add(bg);
                    }
                }
            }

            results[category] = {
                color: [...colors],
                backgroundColor: [...bgColors],
            };
        }

        return results;
    }""")


def rgb_to_hex(rgb_str):
    """Convert rgb(r, g, b) or rgba(r, g, b, a) to hex."""
    import re
    match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)', rgb_str)
    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return rgb_str


def build_palette(raw_results):
    """Organize raw results into a structured palette."""
    palette = {}

    for category, data in raw_results.items():
        text_colors = []
        bg_colors = []

        for c in data.get("color", []):
            hex_val = rgb_to_hex(c)
            entry = {"raw": c, "hex": hex_val}
            if entry not in text_colors:
                text_colors.append(entry)

        for c in data.get("backgroundColor", []):
            hex_val = rgb_to_hex(c)
            entry = {"raw": c, "hex": hex_val}
            if entry not in bg_colors:
                bg_colors.append(entry)

        palette[category] = {
            "text_colors": text_colors,
            "background_colors": bg_colors,
        }

    return palette


def print_summary(palette):
    """Print a formatted summary table to stdout."""
    print("\n--- Color Palette Summary ---\n")
    print(f"{'Category':<16} {'Type':<14} {'Colors'}")
    print("-" * 60)

    all_hex = set()

    for category, data in sorted(palette.items()):
        text_hexes = [c["hex"] for c in data["text_colors"]]
        bg_hexes = [c["hex"] for c in data["background_colors"]]

        if text_hexes:
            colors_str = ", ".join(text_hexes[:6])
            if len(text_hexes) > 6:
                colors_str += f" (+{len(text_hexes) - 6} more)"
            print(f"{category:<16} {'text':<14} {colors_str}")
            all_hex.update(text_hexes)

        if bg_hexes:
            colors_str = ", ".join(bg_hexes[:6])
            if len(bg_hexes) > 6:
                colors_str += f" (+{len(bg_hexes) - 6} more)"
            print(f"{category:<16} {'background':<14} {colors_str}")
            all_hex.update(bg_hexes)

    print(f"\nTotal unique colors: {len(all_hex)}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract a color palette from a website by analyzing computed styles of key elements."
    )
    parser.add_argument(
        "--url", required=True, help="Target page URL to extract colors from"
    )
    parser.add_argument(
        "--output", required=True, help="Output path for the JSON palette file"
    )
    args = parser.parse_args()

    print(f"Loading {args.url}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            page.goto(args.url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error loading page: {e}")
            browser.close()
            sys.exit(1)

        print("Extracting computed colors from key elements...")
        raw_results = extract_colors_from_page(page)
        browser.close()

    palette = build_palette(raw_results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(palette, f, indent=2)
    print(f"\nPalette saved to: {output_path}")

    print_summary(palette)
    print("\nDone.")


if __name__ == "__main__":
    main()
