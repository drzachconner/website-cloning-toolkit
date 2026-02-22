#!/usr/bin/env python3
"""Parse CSS into structured design tokens JSON with optional live extraction and HTML cross-referencing."""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import cssutils
    import logging
    cssutils.log.setLevel(logging.CRITICAL)
except ImportError:
    print("Error: cssutils is required. Install with: pip install cssutils")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)


# Color property names that indicate usage context
COLOR_PROPERTIES = {
    "color": "primary",
    "background-color": "neutral",
    "background": "neutral",
    "border-color": "accent",
    "border": "accent",
    "border-top-color": "accent",
    "border-bottom-color": "accent",
    "border-left-color": "accent",
    "border-right-color": "accent",
    "outline-color": "accent",
    "box-shadow": "accent",
    "text-decoration-color": "accent",
}

# Typography properties to extract
TYPOGRAPHY_PROPERTIES = ["font-family", "font-size", "font-weight", "line-height"]

# Heading selectors to match
HEADING_SELECTORS = ["h1", "h2", "h3", "h4", "h5", "h6"]

# Spacing properties
SPACING_PROPERTIES = ["margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
                      "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
                      "gap", "row-gap", "column-gap"]


def parse_color_value(value):
    """Extract individual color values from a CSS property value."""
    colors = []
    # Hex colors
    hex_matches = re.findall(r'#[0-9a-fA-F]{3,8}', value)
    colors.extend(hex_matches)
    # RGB/RGBA
    rgb_matches = re.findall(r'rgba?\([^)]+\)', value)
    colors.extend(rgb_matches)
    # HSL/HSLA
    hsl_matches = re.findall(r'hsla?\([^)]+\)', value)
    colors.extend(hsl_matches)
    # Named colors (skip common non-color keywords)
    skip = {"none", "inherit", "initial", "unset", "transparent", "currentcolor",
            "auto", "normal", "bold", "italic", "solid", "dotted", "dashed",
            "inset", "outset", "ridge", "groove", "hidden", "scroll", "fixed",
            "local", "repeat", "no-repeat", "cover", "contain", "center",
            "top", "bottom", "left", "right", "both", "ease", "linear"}
    return colors


def normalize_selector(selector_text):
    """Extract the base element or class from a selector for categorization."""
    selector_text = selector_text.strip()
    # Remove pseudo-classes and pseudo-elements
    base = re.split(r':{1,2}', selector_text)[0].strip()
    # Get the last part of a compound selector
    parts = re.split(r'[\s>+~]+', base)
    return parts[-1].strip() if parts else base


def get_heading_level(selector_text):
    """Return heading level (h1-h6) if the selector targets a heading, else None."""
    normalized = normalize_selector(selector_text)
    for h in HEADING_SELECTORS:
        if normalized == h or normalized.startswith(h + ".") or normalized.startswith(h + "["):
            return h
    return None


def is_body_selector(selector_text):
    """Check if the selector targets body-level text."""
    normalized = normalize_selector(selector_text)
    return normalized in ("body", "p", "html", ".entry-content", "main", "article")


def extract_custom_properties(css_text):
    """Extract all CSS custom properties (variables) from :root declarations."""
    custom_props = {}
    # Match :root blocks
    root_pattern = r':root\s*\{([^}]+)\}'
    for match in re.finditer(root_pattern, css_text):
        block = match.group(1)
        for prop_match in re.finditer(r'(--[\w-]+)\s*:\s*([^;]+)', block):
            name = prop_match.group(1).strip()
            value = prop_match.group(2).strip()
            custom_props[name] = value
    return custom_props


def extract_breakpoints(css_text):
    """Extract media query breakpoints from CSS."""
    breakpoints = set()
    for match in re.finditer(r'@media[^{]*\(\s*(?:min|max)-width\s*:\s*(\d+)\s*px', css_text):
        breakpoints.add(int(match.group(1)))
    return sorted(breakpoints)


def extract_design_tokens_from_css(css_text):
    """Parse CSS text and extract structured design tokens."""
    colors = defaultdict(list)
    typography = {}
    spacing_values = set()
    layout = {"maxWidth": None, "breakpoints": []}
    components = []

    # Parse with cssutils for structured access
    sheet = cssutils.parseString(css_text)

    for rule in sheet:
        if rule.type != rule.STYLE_RULE:
            continue

        selector = rule.selectorText
        properties = {}
        prop_count = 0

        for prop in rule.style:
            name = prop.name
            value = prop.value
            properties[name] = value
            prop_count += 1

            # Extract colors
            if name in COLOR_PROPERTIES:
                color_values = parse_color_value(value)
                category = COLOR_PROPERTIES[name]
                for cv in color_values:
                    # Avoid duplicates for same value+property combo
                    existing = [c for c in colors[category]
                                if c["value"] == cv and c["property"] == name]
                    if existing:
                        if selector not in existing[0]["selectors"]:
                            existing[0]["selectors"].append(selector)
                    else:
                        colors[category].append({
                            "value": cv,
                            "property": name,
                            "selectors": [selector],
                        })

            # Extract typography for headings and body
            heading = get_heading_level(selector)
            if heading and name in TYPOGRAPHY_PROPERTIES:
                if heading not in typography:
                    typography[heading] = {}
                key = name.replace("-", "")
                # Convert CSS property names to camelCase
                camel_map = {
                    "fontfamily": "fontFamily",
                    "fontsize": "fontSize",
                    "fontweight": "fontWeight",
                    "lineheight": "lineHeight",
                }
                key = camel_map.get(key, key)
                typography[heading][key] = value

            if is_body_selector(selector) and name in TYPOGRAPHY_PROPERTIES:
                if "body" not in typography:
                    typography["body"] = {}
                key = name.replace("-", "")
                camel_map = {
                    "fontfamily": "fontFamily",
                    "fontsize": "fontSize",
                    "fontweight": "fontWeight",
                    "lineheight": "lineHeight",
                }
                key = camel_map.get(key, key)
                # Only set if not already set (first match wins for body)
                if key not in typography["body"]:
                    typography["body"][key] = value

            # Extract spacing values
            if name in SPACING_PROPERTIES:
                # Split compound values like "10px 20px"
                for part in value.split():
                    part = part.strip()
                    if re.match(r'^-?\d+(\.\d+)?(px|rem|em|%)$', part):
                        spacing_values.add(part)

            # Extract max-width for layout
            if name == "max-width" and re.match(r'^\d+(\.\d+)?(px|rem|em)$', value):
                current = layout["maxWidth"]
                if current is None or value > current:
                    layout["maxWidth"] = value

        # Identify components (class-based selectors with 3+ declarations)
        if prop_count >= 3 and "." in selector:
            # Only include class-based selectors, not pure element selectors
            component = {
                "selector": selector,
                "purpose": "auto-detected",
                "properties": properties,
                "usedInHtml": False,
            }
            components.append(component)

    # Extract custom properties from raw text
    custom_properties = extract_custom_properties(css_text)

    # Extract breakpoints from raw text
    layout["breakpoints"] = extract_breakpoints(css_text)

    # Sort spacing values by numeric component
    def sort_key(val):
        num = re.match(r'^-?(\d+(\.\d+)?)', val)
        return float(num.group(1)) if num else 0

    sorted_spacing = sorted(spacing_values, key=sort_key)

    return {
        "colors": dict(colors),
        "typography": typography,
        "spacing": {"values": sorted_spacing},
        "layout": layout,
        "customProperties": custom_properties,
        "components": components,
    }


def extract_computed_styles(url):
    """Use Playwright to load a page and extract computed styles for key elements."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Warning: playwright not installed, skipping computed style extraction")
        print("  Install with: pip install playwright && playwright install")
        return None

    print(f"Loading {url} for computed style extraction...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error loading page: {e}")
            browser.close()
            return None

        print("Extracting computed styles...")
        computed = page.evaluate("""() => {
            const selectors = {
                h1: 'h1', h2: 'h2', h3: 'h3', h4: 'h4', h5: 'h5', h6: 'h6',
                body: 'body', p: 'p',
            };
            const props = ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight',
                           'color', 'backgroundColor', 'maxWidth'];

            const results = {};
            for (const [name, sel] of Object.entries(selectors)) {
                const el = document.querySelector(sel);
                if (!el) continue;
                const style = window.getComputedStyle(el);
                const values = {};
                for (const prop of props) {
                    const val = style[prop];
                    if (val) values[prop] = val;
                }
                results[name] = values;
            }
            return results;
        }""")

        browser.close()

    return computed


def merge_computed_styles(design_system, computed):
    """Merge computed styles into the design system, preferring computed values."""
    if not computed:
        return design_system

    typography_props = ["fontFamily", "fontSize", "fontWeight", "lineHeight"]

    for element, styles in computed.items():
        if element in HEADING_SELECTORS or element in ("body", "p"):
            key = element if element != "p" else "body"
            if key not in design_system["typography"]:
                design_system["typography"][key] = {}
            for prop in typography_props:
                if prop in styles:
                    design_system["typography"][key][prop] = styles[prop]

    return design_system


def collect_html_classes(html_dir):
    """Scan HTML files and return a set of all CSS classes used."""
    html_path = Path(html_dir)
    classes = set()

    html_files = list(html_path.glob("**/*.html")) + list(html_path.glob("**/*.htm"))
    print(f"Scanning {len(html_files)} HTML files for used classes...")

    for html_file in html_files:
        try:
            soup = BeautifulSoup(
                html_file.read_text(encoding="utf-8", errors="replace"),
                "html.parser"
            )
        except Exception as e:
            print(f"  Warning: Could not parse {html_file.name}: {e}")
            continue

        for tag in soup.find_all(True):
            for cls in tag.get("class", []):
                classes.add(cls)

    print(f"  Found {len(classes)} unique classes in HTML files")
    return classes


def mark_used_components(design_system, html_classes):
    """Mark components as usedInHtml if their selector classes appear in the HTML."""
    used_count = 0
    for component in design_system["components"]:
        selector = component["selector"]
        # Extract class names from the selector
        selector_classes = re.findall(r'\.([a-zA-Z_][\w-]*)', selector)
        if any(cls in html_classes for cls in selector_classes):
            component["usedInHtml"] = True
            used_count += 1

    print(f"  {used_count} of {len(design_system['components'])} components are used in HTML")
    return design_system


def print_summary(design_system):
    """Print a human-readable summary of the design system to stdout."""
    print("\n--- Design System Summary ---\n")

    # Colors
    total_colors = sum(len(v) for v in design_system["colors"].values())
    print(f"Colors ({total_colors} total):")
    for category, entries in sorted(design_system["colors"].items()):
        values = sorted(set(e["value"] for e in entries))
        display = ", ".join(values[:8])
        if len(values) > 8:
            display += f" (+{len(values) - 8} more)"
        print(f"  {category}: {display}")

    # Typography
    print(f"\nTypography ({len(design_system['typography'])} definitions):")
    for element in ["h1", "h2", "h3", "h4", "h5", "h6", "body"]:
        if element in design_system["typography"]:
            props = design_system["typography"][element]
            parts = []
            if "fontFamily" in props:
                parts.append(props["fontFamily"][:40])
            if "fontSize" in props:
                parts.append(props["fontSize"])
            if "fontWeight" in props:
                parts.append(f"weight={props['fontWeight']}")
            if "lineHeight" in props:
                parts.append(f"lh={props['lineHeight']}")
            print(f"  {element}: {', '.join(parts)}")

    # Spacing
    spacing = design_system["spacing"]["values"]
    if spacing:
        display = ", ".join(spacing[:10])
        if len(spacing) > 10:
            display += f" (+{len(spacing) - 10} more)"
        print(f"\nSpacing ({len(spacing)} values): {display}")

    # Layout
    layout = design_system["layout"]
    if layout["maxWidth"]:
        print(f"\nLayout: max-width={layout['maxWidth']}")
    if layout["breakpoints"]:
        print(f"  Breakpoints: {', '.join(str(b) + 'px' for b in layout['breakpoints'])}")

    # Custom properties
    custom = design_system["customProperties"]
    if custom:
        print(f"\nCustom Properties ({len(custom)}):")
        for name, value in sorted(custom.items())[:15]:
            print(f"  {name}: {value}")
        if len(custom) > 15:
            print(f"  ... and {len(custom) - 15} more")

    # Components
    components = design_system["components"]
    if components:
        used = sum(1 for c in components if c["usedInHtml"])
        print(f"\nComponents ({len(components)} total, {used} used in HTML):")
        for comp in components[:10]:
            marker = " [USED]" if comp["usedInHtml"] else ""
            prop_count = len(comp["properties"])
            print(f"  {comp['selector']} ({prop_count} properties){marker}")
        if len(components) > 10:
            print(f"  ... and {len(components) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Parse CSS into structured design tokens JSON. Extracts colors, typography, "
            "spacing, layout, custom properties, and component patterns."
        )
    )
    parser.add_argument(
        "--css", required=True,
        help="Path to CSS file to analyze (required)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output JSON file path for the design system (e.g., design-system.json)"
    )
    parser.add_argument(
        "--url",
        help="Target URL - use Playwright to extract rendered computed styles for more accurate values"
    )
    parser.add_argument(
        "--html-dir",
        help="Directory of HTML files - cross-reference which CSS classes are actually used"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.css):
        print(f"Error: CSS file not found: {args.css}")
        sys.exit(1)

    if args.html_dir and not os.path.isdir(args.html_dir):
        print(f"Error: HTML directory not found: {args.html_dir}")
        sys.exit(1)

    # Read CSS file
    css_path = Path(args.css)
    css_text = css_path.read_text(encoding="utf-8", errors="replace")
    print(f"Parsing CSS: {css_path} ({len(css_text)} bytes)")

    # Extract design tokens from CSS
    design_system = extract_design_tokens_from_css(css_text)

    # Optionally extract computed styles via Playwright
    if args.url:
        computed = extract_computed_styles(args.url)
        if computed:
            design_system = merge_computed_styles(design_system, computed)
            print("  Merged computed styles into design system")

    # Optionally cross-reference with HTML files
    if args.html_dir:
        html_classes = collect_html_classes(args.html_dir)
        design_system = mark_used_components(design_system, html_classes)

    # Write output JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(design_system, f, indent=2)
    print(f"\nDesign system saved to: {output_path}")

    # Print human-readable summary
    print_summary(design_system)

    print("\nDone.")


if __name__ == "__main__":
    main()
