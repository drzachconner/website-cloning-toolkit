#!/usr/bin/env python3
"""Extract and combine CSS from a website, optionally subsetting to used rules only."""

import argparse
import json
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


# ---------------------------------------------------------------------------
# Tailwind CSS mapping (activated with --tailwind flag)
# ---------------------------------------------------------------------------

# Maps CSS property+value pairs to Tailwind utility classes.
# Each entry: (property, value_or_pattern) -> tailwind_class
# Use None as value to match any value for that property.
TAILWIND_EXACT_MAP = {
    # Display
    ("display", "flex"): "flex",
    ("display", "inline-flex"): "inline-flex",
    ("display", "grid"): "grid",
    ("display", "inline-grid"): "inline-grid",
    ("display", "block"): "block",
    ("display", "inline-block"): "inline-block",
    ("display", "inline"): "inline",
    ("display", "none"): "hidden",
    ("display", "table"): "table",
    # Position
    ("position", "relative"): "relative",
    ("position", "absolute"): "absolute",
    ("position", "fixed"): "fixed",
    ("position", "sticky"): "sticky",
    ("position", "static"): "static",
    # Flex
    ("flex-direction", "column"): "flex-col",
    ("flex-direction", "column-reverse"): "flex-col-reverse",
    ("flex-direction", "row"): "flex-row",
    ("flex-direction", "row-reverse"): "flex-row-reverse",
    ("flex-wrap", "wrap"): "flex-wrap",
    ("flex-wrap", "nowrap"): "flex-nowrap",
    ("flex-wrap", "wrap-reverse"): "flex-wrap-reverse",
    ("flex-grow", "1"): "grow",
    ("flex-grow", "0"): "grow-0",
    ("flex-shrink", "1"): "shrink",
    ("flex-shrink", "0"): "shrink-0",
    # Alignment
    ("justify-content", "center"): "justify-center",
    ("justify-content", "flex-start"): "justify-start",
    ("justify-content", "flex-end"): "justify-end",
    ("justify-content", "space-between"): "justify-between",
    ("justify-content", "space-around"): "justify-around",
    ("justify-content", "space-evenly"): "justify-evenly",
    ("align-items", "center"): "items-center",
    ("align-items", "flex-start"): "items-start",
    ("align-items", "flex-end"): "items-end",
    ("align-items", "stretch"): "items-stretch",
    ("align-items", "baseline"): "items-baseline",
    ("align-self", "auto"): "self-auto",
    ("align-self", "center"): "self-center",
    ("align-self", "flex-start"): "self-start",
    ("align-self", "flex-end"): "self-end",
    ("align-self", "stretch"): "self-stretch",
    # Text
    ("text-align", "center"): "text-center",
    ("text-align", "left"): "text-left",
    ("text-align", "right"): "text-right",
    ("text-align", "justify"): "text-justify",
    ("text-decoration", "underline"): "underline",
    ("text-decoration", "line-through"): "line-through",
    ("text-decoration", "none"): "no-underline",
    ("text-transform", "uppercase"): "uppercase",
    ("text-transform", "lowercase"): "lowercase",
    ("text-transform", "capitalize"): "capitalize",
    ("text-transform", "none"): "normal-case",
    ("font-style", "italic"): "italic",
    ("font-style", "normal"): "not-italic",
    ("white-space", "nowrap"): "whitespace-nowrap",
    ("white-space", "pre"): "whitespace-pre",
    ("white-space", "pre-wrap"): "whitespace-pre-wrap",
    ("white-space", "normal"): "whitespace-normal",
    ("word-break", "break-all"): "break-all",
    ("overflow-wrap", "break-word"): "break-words",
    # Font weight
    ("font-weight", "100"): "font-thin",
    ("font-weight", "200"): "font-extralight",
    ("font-weight", "300"): "font-light",
    ("font-weight", "400"): "font-normal",
    ("font-weight", "500"): "font-medium",
    ("font-weight", "600"): "font-semibold",
    ("font-weight", "700"): "font-bold",
    ("font-weight", "800"): "font-extrabold",
    ("font-weight", "900"): "font-black",
    ("font-weight", "bold"): "font-bold",
    ("font-weight", "normal"): "font-normal",
    # Width / Height
    ("width", "100%"): "w-full",
    ("width", "auto"): "w-auto",
    ("width", "100vw"): "w-screen",
    ("width", "fit-content"): "w-fit",
    ("width", "min-content"): "w-min",
    ("width", "max-content"): "w-max",
    ("height", "100%"): "h-full",
    ("height", "auto"): "h-auto",
    ("height", "100vh"): "h-screen",
    ("height", "fit-content"): "h-fit",
    ("min-height", "100vh"): "min-h-screen",
    ("min-width", "100%"): "min-w-full",
    ("max-width", "100%"): "max-w-full",
    ("max-width", "none"): "max-w-none",
    # Overflow
    ("overflow", "hidden"): "overflow-hidden",
    ("overflow", "auto"): "overflow-auto",
    ("overflow", "scroll"): "overflow-scroll",
    ("overflow", "visible"): "overflow-visible",
    ("overflow-x", "hidden"): "overflow-x-hidden",
    ("overflow-x", "auto"): "overflow-x-auto",
    ("overflow-y", "hidden"): "overflow-y-hidden",
    ("overflow-y", "auto"): "overflow-y-auto",
    # Border
    ("border-style", "solid"): "border-solid",
    ("border-style", "dashed"): "border-dashed",
    ("border-style", "dotted"): "border-dotted",
    ("border-style", "none"): "border-none",
    ("border-radius", "9999px"): "rounded-full",
    ("border-radius", "0"): "rounded-none",
    ("border-radius", "0px"): "rounded-none",
    # Visibility / Opacity
    ("visibility", "hidden"): "invisible",
    ("visibility", "visible"): "visible",
    ("opacity", "0"): "opacity-0",
    ("opacity", "1"): "opacity-100",
    # Cursor
    ("cursor", "pointer"): "cursor-pointer",
    ("cursor", "not-allowed"): "cursor-not-allowed",
    ("cursor", "default"): "cursor-default",
    # Misc
    ("list-style-type", "none"): "list-none",
    ("list-style-type", "disc"): "list-disc",
    ("list-style-type", "decimal"): "list-decimal",
    ("object-fit", "cover"): "object-cover",
    ("object-fit", "contain"): "object-contain",
    ("object-fit", "fill"): "object-fill",
    ("pointer-events", "none"): "pointer-events-none",
    ("pointer-events", "auto"): "pointer-events-auto",
    ("box-sizing", "border-box"): "box-border",
    ("box-sizing", "content-box"): "box-content",
}

# Spacing scale: px value -> Tailwind spacing unit
TAILWIND_SPACING = {
    "0": "0",
    "0px": "0",
    "1px": "px",
    "0.125rem": "0.5",
    "2px": "0.5",
    "0.25rem": "1",
    "4px": "1",
    "0.375rem": "1.5",
    "6px": "1.5",
    "0.5rem": "2",
    "8px": "2",
    "0.625rem": "2.5",
    "10px": "2.5",
    "0.75rem": "3",
    "12px": "3",
    "0.875rem": "3.5",
    "14px": "3.5",
    "1rem": "4",
    "16px": "4",
    "1.25rem": "5",
    "20px": "5",
    "1.5rem": "6",
    "24px": "6",
    "1.75rem": "7",
    "28px": "7",
    "2rem": "8",
    "32px": "8",
    "2.25rem": "9",
    "36px": "9",
    "2.5rem": "10",
    "40px": "10",
    "2.75rem": "11",
    "44px": "11",
    "3rem": "12",
    "48px": "12",
    "3.5rem": "14",
    "56px": "14",
    "4rem": "16",
    "64px": "16",
    "5rem": "20",
    "80px": "20",
    "6rem": "24",
    "96px": "24",
}

# Tailwind default color palette (subset for nearest-match)
TAILWIND_COLORS = {
    "slate-50": "#f8fafc", "slate-100": "#f1f5f9", "slate-200": "#e2e8f0",
    "slate-300": "#cbd5e1", "slate-400": "#94a3b8", "slate-500": "#64748b",
    "slate-600": "#475569", "slate-700": "#334155", "slate-800": "#1e293b",
    "slate-900": "#0f172a", "slate-950": "#020617",
    "gray-50": "#f9fafb", "gray-100": "#f3f4f6", "gray-200": "#e5e7eb",
    "gray-300": "#d1d5db", "gray-400": "#9ca3af", "gray-500": "#6b7280",
    "gray-600": "#4b5563", "gray-700": "#374151", "gray-800": "#1f2937",
    "gray-900": "#111827", "gray-950": "#030712",
    "red-50": "#fef2f2", "red-100": "#fee2e2", "red-200": "#fecaca",
    "red-300": "#fca5a5", "red-400": "#f87171", "red-500": "#ef4444",
    "red-600": "#dc2626", "red-700": "#b91c1c", "red-800": "#991b1b",
    "red-900": "#7f1d1d", "red-950": "#450a0a",
    "orange-50": "#fff7ed", "orange-100": "#ffedd5", "orange-200": "#fed7aa",
    "orange-300": "#fdba74", "orange-400": "#fb923c", "orange-500": "#f97316",
    "orange-600": "#ea580c", "orange-700": "#c2410c", "orange-800": "#9a3412",
    "orange-900": "#7c2d12", "orange-950": "#431407",
    "yellow-50": "#fefce8", "yellow-100": "#fef9c3", "yellow-200": "#fef08a",
    "yellow-300": "#fde047", "yellow-400": "#facc15", "yellow-500": "#eab308",
    "yellow-600": "#ca8a04", "yellow-700": "#a16207", "yellow-800": "#854d0e",
    "yellow-900": "#713f12", "yellow-950": "#422006",
    "green-50": "#f0fdf4", "green-100": "#dcfce7", "green-200": "#bbf7d0",
    "green-300": "#86efac", "green-400": "#4ade80", "green-500": "#22c55e",
    "green-600": "#16a34a", "green-700": "#15803d", "green-800": "#166534",
    "green-900": "#14532d", "green-950": "#052e16",
    "blue-50": "#eff6ff", "blue-100": "#dbeafe", "blue-200": "#bfdbfe",
    "blue-300": "#93c5fd", "blue-400": "#60a5fa", "blue-500": "#3b82f6",
    "blue-600": "#2563eb", "blue-700": "#1d4ed8", "blue-800": "#1e40af",
    "blue-900": "#1e3a8a", "blue-950": "#172554",
    "indigo-50": "#eef2ff", "indigo-100": "#e0e7ff", "indigo-200": "#c7d2fe",
    "indigo-300": "#a5b4fc", "indigo-400": "#818cf8", "indigo-500": "#6366f1",
    "indigo-600": "#4f46e5", "indigo-700": "#4338ca", "indigo-800": "#3730a3",
    "indigo-900": "#312e81", "indigo-950": "#1e1b4e",
    "purple-50": "#faf5ff", "purple-100": "#f3e8ff", "purple-200": "#e9d5ff",
    "purple-300": "#d8b4fe", "purple-400": "#c084fc", "purple-500": "#a855f7",
    "purple-600": "#9333ea", "purple-700": "#7e22ce", "purple-800": "#6b21a8",
    "purple-900": "#581c87", "purple-950": "#3b0764",
    "pink-50": "#fdf2f8", "pink-100": "#fce7f3", "pink-200": "#fbcfe8",
    "pink-300": "#f9a8d4", "pink-400": "#f472b6", "pink-500": "#ec4899",
    "pink-600": "#db2777", "pink-700": "#be185d", "pink-800": "#9d174d",
    "pink-900": "#831843", "pink-950": "#500724",
    "white": "#ffffff",
    "black": "#000000",
    "transparent": "transparent",
}


def _hex_to_rgb(hex_str):
    """Convert a hex color string to (r, g, b) tuple."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) < 6:
        return None
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b)
    except ValueError:
        return None


def _rgb_str_to_tuple(rgb_str):
    """Parse rgb(r, g, b) or rgba(r, g, b, a) to (r, g, b)."""
    match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', rgb_str)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def _color_distance(c1, c2):
    """Simple Euclidean distance between two RGB tuples."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def nearest_tailwind_color(color_value):
    """Find the closest Tailwind color name for a CSS color value.

    Returns (tailwind_name, hex_value, distance).
    """
    color_value = color_value.strip().lower()

    # Parse the input color to RGB
    if color_value.startswith("#"):
        input_rgb = _hex_to_rgb(color_value)
    elif color_value.startswith("rgb"):
        input_rgb = _rgb_str_to_tuple(color_value)
    else:
        return None

    if input_rgb is None:
        return None

    best_name = None
    best_hex = None
    best_dist = float("inf")

    for name, hex_val in TAILWIND_COLORS.items():
        tw_rgb = _hex_to_rgb(hex_val)
        if tw_rgb is None:
            continue
        dist = _color_distance(input_rgb, tw_rgb)
        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_hex = hex_val

    return (best_name, best_hex, best_dist)


def _map_spacing_property(prop, value):
    """Map a spacing CSS property+value to a Tailwind class.

    Returns (tailwind_class, confidence) or None.
    """
    value = value.strip().rstrip("!important").strip()

    # Special case: margin: 0 auto -> mx-auto
    if prop == "margin" and value in ("0 auto", "0px auto", "auto"):
        if value == "auto":
            return ("m-auto", "exact")
        return ("mx-auto", "exact")

    # Determine the Tailwind prefix
    prefix_map = {
        "margin": "m", "margin-top": "mt", "margin-right": "mr",
        "margin-bottom": "mb", "margin-left": "ml",
        "padding": "p", "padding-top": "pt", "padding-right": "pr",
        "padding-bottom": "pb", "padding-left": "pl",
        "gap": "gap", "row-gap": "gap-y", "column-gap": "gap-x",
        "top": "top", "right": "right", "bottom": "bottom", "left": "left",
    }

    prefix = prefix_map.get(prop)
    if not prefix:
        return None

    # Single value
    tw_unit = TAILWIND_SPACING.get(value)
    if tw_unit is not None:
        return (f"{prefix}-{tw_unit}", "exact")

    # Negative values
    if value.startswith("-"):
        pos_val = value[1:]
        tw_unit = TAILWIND_SPACING.get(pos_val)
        if tw_unit is not None:
            return (f"-{prefix}-{tw_unit}", "exact")

    return None


def _map_font_size(value):
    """Map font-size value to Tailwind text-* class."""
    value = value.strip().rstrip("!important").strip()
    size_map = {
        "0.75rem": "text-xs", "12px": "text-xs",
        "0.875rem": "text-sm", "14px": "text-sm",
        "1rem": "text-base", "16px": "text-base",
        "1.125rem": "text-lg", "18px": "text-lg",
        "1.25rem": "text-xl", "20px": "text-xl",
        "1.5rem": "text-2xl", "24px": "text-2xl",
        "1.875rem": "text-3xl", "30px": "text-3xl",
        "2.25rem": "text-4xl", "36px": "text-4xl",
        "3rem": "text-5xl", "48px": "text-5xl",
        "3.75rem": "text-6xl", "60px": "text-6xl",
        "4.5rem": "text-7xl", "72px": "text-7xl",
        "6rem": "text-8xl", "96px": "text-8xl",
        "8rem": "text-9xl", "128px": "text-9xl",
    }
    return size_map.get(value)


def _map_border_radius(value):
    """Map border-radius value to Tailwind rounded-* class."""
    value = value.strip().rstrip("!important").strip()
    radius_map = {
        "0": "rounded-none", "0px": "rounded-none",
        "0.125rem": "rounded-sm", "2px": "rounded-sm",
        "0.25rem": "rounded", "4px": "rounded",
        "0.375rem": "rounded-md", "6px": "rounded-md",
        "0.5rem": "rounded-lg", "8px": "rounded-lg",
        "0.75rem": "rounded-xl", "12px": "rounded-xl",
        "1rem": "rounded-2xl", "16px": "rounded-2xl",
        "1.5rem": "rounded-3xl", "24px": "rounded-3xl",
        "9999px": "rounded-full",
        "50%": "rounded-full",
    }
    return radius_map.get(value)


def _map_border_width(value):
    """Map border-width value to Tailwind border-* class."""
    value = value.strip().rstrip("!important").strip()
    width_map = {
        "0": "border-0", "0px": "border-0",
        "1px": "border",
        "2px": "border-2",
        "4px": "border-4",
        "8px": "border-8",
    }
    return width_map.get(value)


def _map_max_width(value):
    """Map max-width to Tailwind max-w-* class."""
    value = value.strip().rstrip("!important").strip()
    mw_map = {
        "100%": "max-w-full",
        "none": "max-w-none",
        "0": "max-w-0", "0px": "max-w-0",
        "20rem": "max-w-xs", "320px": "max-w-xs",
        "24rem": "max-w-sm", "384px": "max-w-sm",
        "28rem": "max-w-md", "448px": "max-w-md",
        "32rem": "max-w-lg", "512px": "max-w-lg",
        "36rem": "max-w-xl", "576px": "max-w-xl",
        "42rem": "max-w-2xl", "672px": "max-w-2xl",
        "48rem": "max-w-3xl", "768px": "max-w-3xl",
        "56rem": "max-w-4xl", "896px": "max-w-4xl",
        "64rem": "max-w-5xl", "1024px": "max-w-5xl",
        "72rem": "max-w-6xl", "1152px": "max-w-6xl",
        "80rem": "max-w-7xl", "1280px": "max-w-7xl",
        "65ch": "max-w-prose",
    }
    return mw_map.get(value)


def _map_z_index(value):
    """Map z-index to Tailwind z-* class."""
    value = value.strip().rstrip("!important").strip()
    z_map = {"0": "z-0", "10": "z-10", "20": "z-20", "30": "z-30",
             "40": "z-40", "50": "z-50", "auto": "z-auto"}
    return z_map.get(value)


def generate_tailwind_mapping(css_text):
    """Parse CSS rules and generate Tailwind utility class mappings.

    Returns (mappings_list, config_dict) where:
      - mappings_list: list of per-selector mapping dicts
      - config_dict: extracted design tokens for tailwind.config.js
    """
    sheet = cssutils.parseString(css_text)

    mappings = []
    all_colors = {}
    all_fonts = {}

    for rule in sheet:
        if rule.type != rule.STYLE_RULE:
            continue

        selector = rule.selectorText
        tw_classes = []
        unmapped = []

        for prop in rule.style:
            prop_name = prop.name
            prop_value = prop.value.strip()
            clean_value = prop_value.rstrip("!important").strip()

            # 1. Check exact map
            key = (prop_name, clean_value)
            if key in TAILWIND_EXACT_MAP:
                tw_classes.append({"class": TAILWIND_EXACT_MAP[key], "confidence": "exact"})
                continue

            # 2. Spacing properties
            spacing_result = _map_spacing_property(prop_name, clean_value)
            if spacing_result:
                tw_classes.append({"class": spacing_result[0], "confidence": spacing_result[1]})
                continue

            # 3. Font size
            if prop_name == "font-size":
                tw = _map_font_size(clean_value)
                if tw:
                    tw_classes.append({"class": tw, "confidence": "exact"})
                    continue

            # 4. Border radius
            if prop_name == "border-radius":
                tw = _map_border_radius(clean_value)
                if tw:
                    tw_classes.append({"class": tw, "confidence": "exact"})
                    continue

            # 5. Border width
            if prop_name in ("border-width", "border-top-width", "border-right-width",
                             "border-bottom-width", "border-left-width"):
                tw = _map_border_width(clean_value)
                if tw:
                    tw_classes.append({"class": tw, "confidence": "exact"})
                    continue

            # 6. Max-width
            if prop_name == "max-width":
                tw = _map_max_width(clean_value)
                if tw:
                    tw_classes.append({"class": tw, "confidence": "exact"})
                    continue

            # 7. Z-index
            if prop_name == "z-index":
                tw = _map_z_index(clean_value)
                if tw:
                    tw_classes.append({"class": tw, "confidence": "exact"})
                    continue

            # 8. Color properties
            if prop_name in ("color", "background-color", "border-color",
                             "border-top-color", "border-right-color",
                             "border-bottom-color", "border-left-color",
                             "outline-color", "text-decoration-color"):
                result = nearest_tailwind_color(clean_value)
                if result:
                    tw_name, tw_hex, dist = result
                    color_prefix_map = {
                        "color": "text",
                        "background-color": "bg",
                        "border-color": "border",
                        "border-top-color": "border-t",
                        "border-right-color": "border-r",
                        "border-bottom-color": "border-b",
                        "border-left-color": "border-l",
                        "outline-color": "outline",
                        "text-decoration-color": "decoration",
                    }
                    prefix = color_prefix_map.get(prop_name, "text")
                    tw_class = f"{prefix}-{tw_name}"
                    confidence = "exact" if dist < 1.0 else "approximate"
                    tw_classes.append({"class": tw_class, "confidence": confidence})

                    # Track for config
                    all_colors[clean_value] = tw_name
                    continue

            # 9. Font family -- track for config, can't map to utility directly
            if prop_name == "font-family":
                families = [f.strip().strip("'\"") for f in clean_value.split(",")]
                if families:
                    primary = families[0].lower().replace(" ", "-")
                    all_fonts[primary] = families
                    tw_classes.append({"class": f"font-{primary}", "confidence": "approximate"})
                    continue

            # 10. Not mappable
            unmapped.append(f"{prop_name}: {clean_value}")

        # Determine overall confidence
        if not tw_classes and not unmapped:
            continue

        confidences = [c["confidence"] for c in tw_classes]
        if not tw_classes:
            overall = "manual"
        elif "approximate" in confidences or unmapped:
            overall = "approximate"
        elif all(c == "exact" for c in confidences) and not unmapped:
            overall = "exact"
        else:
            overall = "approximate"

        mappings.append({
            "selector": selector,
            "tailwindClasses": " ".join(c["class"] for c in tw_classes),
            "confidence": overall,
            "unmapped": unmapped if unmapped else [],
        })

    # Build config
    config = {
        "colors": {},
        "fontFamily": {},
        "spacing": {},
    }

    # Deduplicate colors: group by hex -> tailwind name
    seen_colors = {}
    for css_val, tw_name in all_colors.items():
        hex_val = css_val
        if css_val.startswith("rgb"):
            rgb = _rgb_str_to_tuple(css_val)
            if rgb:
                hex_val = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        # Use a simple name like "primary", "secondary" etc. for custom colors
        # For now, store by the original hex
        if hex_val not in seen_colors:
            seen_colors[hex_val] = tw_name

    for hex_val, name in seen_colors.items():
        # If it's far from a Tailwind default, mark as custom
        config["colors"][name] = hex_val

    for font_key, font_list in all_fonts.items():
        config["fontFamily"][font_key] = font_list

    return mappings, config


def generate_tailwind_config_stub(config):
    """Generate a tailwind.config.js string from extracted tokens."""
    lines = ["/** @type {import('tailwindcss').Config} */"]
    lines.append("module.exports = {")
    lines.append("  content: ['./**/*.html'],")
    lines.append("  theme: {")
    lines.append("    extend: {")

    # Colors
    if config.get("colors"):
        lines.append("      colors: {")
        for name, value in sorted(config["colors"].items()):
            lines.append(f"        '{name}': '{value}',")
        lines.append("      },")

    # Font families
    if config.get("fontFamily"):
        lines.append("      fontFamily: {")
        for name, families in sorted(config["fontFamily"].items()):
            family_str = ", ".join(f"'{f}'" for f in families)
            lines.append(f"        '{name}': [{family_str}],")
        lines.append("      },")

    # Spacing
    if config.get("spacing"):
        lines.append("      spacing: {")
        for name, value in sorted(config["spacing"].items()):
            lines.append(f"        '{name}': '{value}',")
        lines.append("      },")

    lines.append("    },")
    lines.append("  },")
    lines.append("  plugins: [],")
    lines.append("};")

    return "\n".join(lines) + "\n"


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
    parser.add_argument(
        "--tailwind", action="store_true",
        help="Generate Tailwind CSS utility class mappings from the extracted CSS"
    )
    parser.add_argument(
        "--tailwind-output", default="tailwind-mapping.json",
        help="Output path for the Tailwind mapping JSON (default: tailwind-mapping.json)"
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

    # Tailwind mapping generation (only when --tailwind flag is passed)
    if args.tailwind:
        print("\n--- Tailwind CSS Mapping ---")
        tw_mappings, tw_config = generate_tailwind_mapping(combined)

        exact = sum(1 for m in tw_mappings if m["confidence"] == "exact")
        approx = sum(1 for m in tw_mappings if m["confidence"] == "approximate")
        manual = sum(1 for m in tw_mappings if m["confidence"] == "manual")
        print(f"  Mapped {len(tw_mappings)} selector(s): "
              f"{exact} exact, {approx} approximate, {manual} manual review")

        total_unmapped = sum(len(m["unmapped"]) for m in tw_mappings)
        if total_unmapped:
            print(f"  {total_unmapped} propert(ies) flagged for manual review")

        tw_output = {
            "mappings": tw_mappings,
            "config": tw_config,
        }

        tw_output_path = Path(args.tailwind_output)
        tw_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tw_output_path, "w") as f:
            json.dump(tw_output, f, indent=2)
        print(f"  Tailwind mapping saved to: {tw_output_path}")

        # Generate tailwind.config.js stub
        config_path = tw_output_path.parent / "tailwind.config.js"
        config_content = generate_tailwind_config_stub(tw_config)
        config_path.write_text(config_content, encoding="utf-8")
        print(f"  Tailwind config stub saved to: {config_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
