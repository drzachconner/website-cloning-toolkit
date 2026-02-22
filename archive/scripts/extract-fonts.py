#!/usr/bin/env python3
"""Extract font files and Google Fonts references from a website's CSS."""

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


FONT_EXTENSIONS = (".woff2", ".woff", ".ttf", ".otf", ".eot")

GOOGLE_FONTS_CSS_URL = "https://fonts.googleapis.com/css2"


def fetch_url(url, timeout=30):
    """Fetch URL content with error handling."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        print(f"  Warning: Could not fetch {url}: {e}")
        return None


def discover_css_and_font_links(page_url):
    """Find CSS URLs and Google Fonts links from the page."""
    resp = fetch_url(page_url)
    if not resp:
        return [], []

    soup = BeautifulSoup(resp.text, "html.parser")
    css_urls = []
    google_fonts_urls = []

    for link in soup.find_all("link"):
        href = link.get("href", "")
        rel = " ".join(link.get("rel", []))

        if "stylesheet" in rel:
            absolute = urljoin(page_url, href)
            if "fonts.googleapis.com" in absolute:
                google_fonts_urls.append(absolute)
            else:
                css_urls.append(absolute)

    for style in soup.find_all("style"):
        text = style.string or ""
        for match in re.finditer(r'@import\s+url\(["\']?([^"\')]+)["\']?\)', text):
            absolute = urljoin(page_url, match.group(1))
            if "fonts.googleapis.com" in absolute:
                google_fonts_urls.append(absolute)
            else:
                css_urls.append(absolute)

    return css_urls, google_fonts_urls


def extract_font_face_declarations(css_text, base_url):
    """Parse @font-face blocks from CSS text and extract font URLs."""
    fonts = []
    pattern = r'@font-face\s*\{([^}]+)\}'

    for match in re.finditer(pattern, css_text):
        block = match.group(1)

        family_match = re.search(r'font-family\s*:\s*["\']?([^"\';\n]+)', block)
        family = family_match.group(1).strip() if family_match else "Unknown"

        weight_match = re.search(r'font-weight\s*:\s*([^;\n]+)', block)
        weight = weight_match.group(1).strip() if weight_match else "400"

        style_match = re.search(r'font-style\s*:\s*([^;\n]+)', block)
        style = style_match.group(1).strip() if style_match else "normal"

        urls = []
        for url_match in re.finditer(r'url\(["\']?([^"\')]+)["\']?\)', block):
            font_url = url_match.group(1)
            absolute = urljoin(base_url, font_url)
            urls.append(absolute)

        if urls:
            fonts.append({
                "family": family,
                "weight": weight,
                "style": style,
                "urls": urls,
            })

    return fonts


def parse_google_fonts_families(google_url):
    """Extract font family names from a Google Fonts CSS URL."""
    families = []
    parsed = urlparse(google_url)
    query = parsed.query

    for match in re.finditer(r'family=([^&]+)', query):
        raw = match.group(1)
        for part in raw.split("|"):
            name = part.split(":")[0].replace("+", " ")
            families.append(name)

    return families


def download_google_fonts_css(google_urls):
    """Download the CSS from Google Fonts URLs to find @font-face declarations."""
    all_fonts = []

    for url in google_urls:
        resp = fetch_url(url)
        if resp:
            fonts = extract_font_face_declarations(resp.text, url)
            all_fonts.extend(fonts)

    return all_fonts


def download_font_file(url, output_dir):
    """Download a font file and return the local filename."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)

    if not any(filename.lower().endswith(ext) for ext in FONT_EXTENSIONS):
        ext = ".woff2"
        filename = filename.split("?")[0]
        if not any(filename.lower().endswith(e) for e in FONT_EXTENSIONS):
            filename += ext

    output_path = Path(output_dir) / filename
    if output_path.exists():
        base = output_path.stem
        suffix = output_path.suffix
        counter = 1
        while output_path.exists():
            output_path = Path(output_dir) / f"{base}_{counter}{suffix}"
            counter += 1

    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        output_path.write_bytes(resp.content)
        return output_path.name
    except requests.RequestException as e:
        print(f"    Warning: Could not download {url}: {e}")
        return None


def generate_font_face_css(downloaded_fonts):
    """Generate local @font-face CSS snippet for downloaded fonts."""
    blocks = []
    for font in downloaded_fonts:
        local_files = font.get("local_files", [])
        if not local_files:
            continue

        src_parts = []
        for f in local_files:
            ext = Path(f).suffix.lstrip(".")
            fmt_map = {
                "woff2": "woff2",
                "woff": "woff",
                "ttf": "truetype",
                "otf": "opentype",
                "eot": "embedded-opentype",
            }
            fmt = fmt_map.get(ext, ext)
            src_parts.append(f"url('{f}') format('{fmt}')")

        src = ",\n       ".join(src_parts)
        block = (
            f"@font-face {{\n"
            f"  font-family: '{font['family']}';\n"
            f"  font-weight: {font['weight']};\n"
            f"  font-style: {font['style']};\n"
            f"  src: {src};\n"
            f"  font-display: swap;\n"
            f"}}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(
        description="Extract font files and Google Fonts references from a website's CSS."
    )
    parser.add_argument(
        "--url", required=True, help="Target page URL to scan for fonts"
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for downloaded font files"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {args.url} for fonts...")
    css_urls, google_fonts_urls = discover_css_and_font_links(args.url)

    all_fonts = []

    # Process regular CSS files for @font-face
    if css_urls:
        print(f"\nFound {len(css_urls)} CSS file(s), scanning for @font-face...")
        for css_url in css_urls:
            resp = fetch_url(css_url)
            if resp:
                fonts = extract_font_face_declarations(resp.text, css_url)
                all_fonts.extend(fonts)

    # Process Google Fonts
    google_families = []
    if google_fonts_urls:
        print(f"\nFound {len(google_fonts_urls)} Google Fonts link(s)")
        for gurl in google_fonts_urls:
            families = parse_google_fonts_families(gurl)
            google_families.extend(families)
            print(f"  Families: {', '.join(families)}")

        google_fonts = download_google_fonts_css(google_fonts_urls)
        all_fonts.extend(google_fonts)

    if not all_fonts and not google_families:
        print("\nNo fonts discovered.")
        sys.exit(0)

    # Download font files
    print(f"\nDiscovered {len(all_fonts)} @font-face declaration(s)")
    downloaded = 0
    for font in all_fonts:
        font["local_files"] = []
        for url in font["urls"]:
            print(f"  Downloading: {os.path.basename(urlparse(url).path)}")
            local_name = download_font_file(url, output_dir)
            if local_name:
                font["local_files"].append(local_name)
                downloaded += 1

    # Generate local @font-face CSS
    local_css = generate_font_face_css(all_fonts)
    if local_css:
        css_path = output_dir / "fonts.css"
        css_path.write_text(local_css, encoding="utf-8")
        print(f"\nLocal @font-face CSS saved to: {css_path}")

    # Summary
    print("\n--- Font Summary ---")
    seen_families = set()
    for font in all_fonts:
        key = f"{font['family']} ({font['weight']}, {font['style']})"
        if key not in seen_families:
            seen_families.add(key)
            local = ", ".join(font.get("local_files", [])) or "(not downloaded)"
            print(f"  {key} -> {local}")

    if google_families:
        for fam in sorted(set(google_families)):
            if not any(fam in s for s in seen_families):
                print(f"  {fam} (Google Fonts, no @font-face found in CSS response)")

    print(f"\nTotal: {len(seen_families)} font variants, {downloaded} files downloaded")
    print("Done.")


if __name__ == "__main__":
    main()
