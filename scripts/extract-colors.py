#!/usr/bin/env python3
"""Extract a color palette from a website by analyzing computed styles."""

import argparse
import json
import re
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
    """Use JavaScript to extract computed colors from key elements.

    Captures: color, backgroundColor, borderColor (all sides), outlineColor,
    textDecorationColor, boxShadow colors, and gradient colors from
    backgroundImage.
    """
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

        const TRANSPARENT = 'rgba(0, 0, 0, 0)';

        // Parse color values out of a box-shadow string.
        // box-shadow format: [inset] <offset-x> <offset-y> [blur] [spread] <color>
        function extractShadowColors(shadowStr) {
            const colors = [];
            if (!shadowStr || shadowStr === 'none') return colors;
            // Split multiple shadows by comma (but not commas inside rgb/rgba)
            const shadows = shadowStr.split(/,(?![^(]*\))/);
            for (const shadow of shadows) {
                const trimmed = shadow.trim();
                // Match rgb/rgba colors
                const rgbMatch = trimmed.match(/rgba?\([^)]+\)/g);
                if (rgbMatch) {
                    colors.push(...rgbMatch);
                    continue;
                }
                // Match hex colors
                const hexMatch = trimmed.match(/#[0-9a-fA-F]{3,8}/g);
                if (hexMatch) {
                    colors.push(...hexMatch);
                }
            }
            return colors;
        }

        // Parse color stops from gradient strings.
        function extractGradientColors(bgImage) {
            const colors = [];
            if (!bgImage || bgImage === 'none') return colors;
            // Match linear-gradient(...) or radial-gradient(...)
            const gradientMatch = bgImage.match(/(?:linear|radial|conic)-gradient\(([^)]+)\)/g);
            if (!gradientMatch) return colors;
            for (const grad of gradientMatch) {
                // Extract rgb/rgba colors
                const rgbMatches = grad.match(/rgba?\([^)]+\)/g);
                if (rgbMatches) colors.push(...rgbMatches);
                // Extract hex colors
                const hexMatches = grad.match(/#[0-9a-fA-F]{3,8}/g);
                if (hexMatches) colors.push(...hexMatches);
            }
            return colors;
        }

        function addIfValid(colorSet, value) {
            if (value && value !== TRANSPARENT && value !== 'none' && value !== '') {
                colorSet.add(value);
            }
        }

        const results = {};

        for (const [category, sels] of Object.entries(selectors)) {
            const colors = new Set();
            const bgColors = new Set();
            const borderColors = new Set();
            const otherColors = new Set();

            for (const sel of sels) {
                const elements = document.querySelectorAll(sel);
                for (const el of elements) {
                    const style = window.getComputedStyle(el);

                    // Text color
                    addIfValid(colors, style.color);

                    // Background color
                    addIfValid(bgColors, style.backgroundColor);

                    // Border colors (all sides)
                    addIfValid(borderColors, style.borderColor);
                    addIfValid(borderColors, style.borderTopColor);
                    addIfValid(borderColors, style.borderRightColor);
                    addIfValid(borderColors, style.borderBottomColor);
                    addIfValid(borderColors, style.borderLeftColor);

                    // Outline color
                    addIfValid(otherColors, style.outlineColor);

                    // Text decoration color
                    addIfValid(otherColors, style.textDecorationColor);

                    // Box-shadow colors
                    const shadowColors = extractShadowColors(style.boxShadow);
                    for (const sc of shadowColors) {
                        addIfValid(otherColors, sc);
                    }

                    // Gradient colors from backgroundImage
                    const gradColors = extractGradientColors(style.backgroundImage);
                    for (const gc of gradColors) {
                        addIfValid(bgColors, gc);
                    }
                }
            }

            results[category] = {
                color: [...colors],
                backgroundColor: [...bgColors],
                borderColor: [...borderColors],
                otherColor: [...otherColors],
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
        border_colors = []
        other_colors = []

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

        for c in data.get("borderColor", []):
            hex_val = rgb_to_hex(c)
            entry = {"raw": c, "hex": hex_val}
            if entry not in border_colors:
                border_colors.append(entry)

        for c in data.get("otherColor", []):
            hex_val = rgb_to_hex(c)
            entry = {"raw": c, "hex": hex_val}
            if entry not in other_colors:
                other_colors.append(entry)

        palette[category] = {
            "text_colors": text_colors,
            "background_colors": bg_colors,
            "border_colors": border_colors,
            "other_colors": other_colors,
        }

    return palette


def print_summary(palette):
    """Print a formatted summary table to stdout."""
    print("\n--- Color Palette Summary ---\n")
    print(f"{'Category':<16} {'Type':<14} {'Colors'}")
    print("-" * 60)

    all_hex = set()

    color_types = [
        ("text_colors", "text"),
        ("background_colors", "background"),
        ("border_colors", "border"),
        ("other_colors", "other"),
    ]

    for category, data in sorted(palette.items()):
        for key, label in color_types:
            hexes = [c["hex"] for c in data.get(key, [])]
            if hexes:
                colors_str = ", ".join(hexes[:6])
                if len(hexes) > 6:
                    colors_str += f" (+{len(hexes) - 6} more)"
                print(f"{category:<16} {label:<14} {colors_str}")
                all_hex.update(hexes)

    print(f"\nTotal unique colors: {len(all_hex)}")


def merge_palettes(palettes):
    """Merge multiple palette dicts, deduplicating colors by hex value.

    Each palette has the same structure: {category: {type: [entries]}}.
    Entries are deduplicated by hex value within each category+type.
    """
    merged = {}

    color_keys = ["text_colors", "background_colors", "border_colors", "other_colors"]

    for palette in palettes:
        for category, data in palette.items():
            if category not in merged:
                merged[category] = {k: [] for k in color_keys}

            for key in color_keys:
                existing_hexes = {e["hex"] for e in merged[category].get(key, [])}
                for entry in data.get(key, []):
                    if entry["hex"] not in existing_hexes:
                        merged[category][key].append(entry)
                        existing_hexes.add(entry["hex"])

    return merged


def load_urls_from_file(pages_file):
    """Read URLs from a text file, one per line. Skips blank lines and comments."""
    urls = []
    with open(pages_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def extract_from_url(browser, url):
    """Load a single URL and extract colors. Returns raw results dict or None."""
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        raw_results = extract_colors_from_page(page)
        return raw_results
    except Exception as e:
        print(f"  Error loading {url}: {e}")
        return None
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser(
        description="Extract a color palette from a website by analyzing computed styles of key elements."
    )
    parser.add_argument(
        "--url", help="Target page URL to extract colors from"
    )
    parser.add_argument(
        "--pages",
        help="Path to a text file with multiple URLs (one per line) for sampling colors across pages"
    )
    parser.add_argument(
        "--output", required=True, help="Output path for the JSON palette file"
    )
    args = parser.parse_args()

    if not args.url and not args.pages:
        parser.error("At least one of --url or --pages is required")

    # Collect all URLs to process
    urls = []
    if args.url:
        urls.append(args.url)
    if args.pages:
        pages_path = Path(args.pages)
        if not pages_path.is_file():
            print(f"Error: Pages file not found: {args.pages}")
            sys.exit(1)
        file_urls = load_urls_from_file(args.pages)
        print(f"Loaded {len(file_urls)} URL(s) from {args.pages}")
        urls.extend(file_urls)

    # Deduplicate URLs while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    urls = unique_urls

    print(f"Processing {len(urls)} URL(s)...\n")

    palettes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Loading {url}...")
            raw_results = extract_from_url(browser, url)
            if raw_results:
                print(f"  Extracting computed colors from key elements...")
                palette = build_palette(raw_results)
                palettes.append(palette)

        browser.close()

    if not palettes:
        print("Error: No colors could be extracted from any URL")
        sys.exit(1)

    # Merge palettes if multiple pages were sampled
    if len(palettes) == 1:
        final_palette = palettes[0]
    else:
        print(f"\nMerging colors from {len(palettes)} page(s)...")
        final_palette = merge_palettes(palettes)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(final_palette, f, indent=2)
    print(f"\nPalette saved to: {output_path}")

    print_summary(final_palette)
    print("\nDone.")


if __name__ == "__main__":
    main()
