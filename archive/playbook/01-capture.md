# Phase 1: Capture

Scrape the target website to collect raw HTML, full-page screenshots, and static assets. This phase produces the source-of-truth mirror that all subsequent phases reference.

**Prerequisites:** Python 3.10+, Playwright installed (`pip install playwright && playwright install chromium`)

## Strategy Selection

| Method | Best For | Handles JS? | Handles 403s? |
|--------|----------|-------------|---------------|
| Playwright | JS-rendered SPAs, dynamic content | Yes | No |
| Firecrawl MCP | Sites blocking scrapers, Cloudflare | Yes | Yes |
| HTTrack | Static sites, full mirror with assets | No | No |
| SiteSucker | macOS users, quick visual mirrors | Partial | No |
| wget | Simple static pages, CI pipelines | No | No |

Start with Playwright for most modern sites. Fall back to Firecrawl if you hit 403 errors or bot detection.

## Playwright Scraping

Playwright renders the full page including JavaScript, which is essential for sites built on frameworks like React, Vue, or CMS platforms that inject content dynamically.

### Basic Usage

```bash
python scripts/scrape-site.py --url https://example.com --output mirror/
```

### Script Pattern

The core scraping pattern extracts `.entry-content` (or any target selector) from each page:

```python
#!/usr/bin/env python3
"""Scrape site pages using Playwright."""
import json
import os
from playwright.sync_api import sync_playwright

BASE_URL = "https://targetsite.com"
OUTPUT_DIR = "mirror/extracted"

SLUGS = [
    "page-one",
    "page-two",
    "about-us",
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1200, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36"
        )

        for slug in SLUGS:
            url = f"{BASE_URL}/{slug}/"
            page = context.new_page()
            try:
                response = page.goto(url, wait_until="networkidle", timeout=15000)
                status = response.status if response else 0

                if status == 200:
                    # Extract the main content element
                    content = page.evaluate("""() => {
                        const el = document.querySelector('.entry-content');
                        if (!el) return null;
                        return el.innerHTML;
                    }""")

                    if content and len(content) > 100:
                        filepath = os.path.join(OUTPUT_DIR, f"{slug}-content.html")
                        with open(filepath, "w") as f:
                            f.write(content)
                        results[slug] = {"status": 200, "has_content": True}
                        print(f"  OK: {slug} ({len(content)} chars)")
                    else:
                        results[slug] = {"status": 200, "has_content": False}
                        print(f"  NO CONTENT: {slug}")
                else:
                    results[slug] = {"status": status, "has_content": False}
                    print(f"  HTTP {status}: {slug}")
            except Exception as e:
                results[slug] = {"status": 0, "error": str(e)}
                print(f"  ERROR: {slug} - {e}")
            finally:
                page.close()

        browser.close()

    # Write summary
    with open(os.path.join(OUTPUT_DIR, "_summary.json"), "w") as f:
        json.dump(results, f, indent=2)

    found = sum(1 for r in results.values() if r.get("has_content"))
    print(f"\nFound {found} pages out of {len(SLUGS)} URLs tried")

if __name__ == "__main__":
    main()
```

### Key Playwright Settings

- **`wait_until="networkidle"`** -- Waits for all network requests to settle. Critical for JS-rendered content that loads after initial page load.
- **`timeout=15000`** -- 15-second timeout prevents hanging on slow pages without cutting off legitimate loads.
- **`viewport={"width": 1200, "height": 800}`** -- Desktop viewport captures the full layout. Change for mobile captures.
- **User agent** -- Set a realistic user agent string to avoid basic bot detection.

## Screenshot Capture

Take full-page screenshots of every page for visual reference during validation.

```python
# Add to scraping loop after content extraction:
screenshot_dir = "mirror/screenshots"
os.makedirs(screenshot_dir, exist_ok=True)

page.screenshot(
    path=os.path.join(screenshot_dir, f"{slug}.png"),
    full_page=True
)
```

Screenshots serve double duty:
1. Visual reference while building templates (Phase 3)
2. Comparison baseline during validation (Phase 5)

## Two-Phase URL Discovery

Most sites have more pages than you initially expect. Use a two-phase approach:

### Phase A: Known/guessed URLs

Start with URLs you can see in navigation, footer links, or guess from patterns:

```python
SLUGS = [
    "back-pain",
    "neck-pain",
    "headaches",
    # ... initial list
]
```

### Phase B: Sitemap discovery

After the first scrape, check for additional pages via sitemap:

```bash
# Check for sitemap
curl -s https://targetsite.com/sitemap.xml | head -50
curl -s https://targetsite.com/robots.txt | grep -i sitemap
```

Create a second scrape script for newly discovered URLs:

```python
ADDITIONAL_SLUGS = [
    "eczema",
    "stress",
    "frozen-shoulders",
    # ... discovered from sitemap
]
```

Merge results into the existing `_summary.json`:

```python
summary_path = os.path.join(OUTPUT_DIR, "_summary.json")
if os.path.exists(summary_path):
    with open(summary_path) as f:
        existing = json.load(f)
    existing.update(results)
    results = existing
```

## Firecrawl MCP (for blocked sites)

When Playwright gets 403 errors or hits Cloudflare/bot protection, use Firecrawl through its MCP server:

```bash
# Firecrawl can bypass most bot detection
# Use the firecrawl_scrape tool from the MCP server
# It returns markdown-formatted content
```

Firecrawl returns content as markdown, which you can then convert back to HTML or feed directly to Claude for code generation (see [Phase 3](03-generate-code.md)).

## HTTrack / wget (Full Mirror)

For static sites where you want a complete local copy including all assets:

```bash
# HTTrack - full mirror with linked assets
httrack "https://targetsite.com" -O mirror/full-site \
  --ext-depth=1 \
  --max-rate=50000

# wget - simpler but effective
wget --mirror \
  --convert-links \
  --adjust-extension \
  --page-requisites \
  --no-parent \
  -P mirror/wget \
  https://targetsite.com/
```

## SiteSucker (macOS)

SiteSucker is a macOS app that mirrors sites with a GUI. Useful for quick visual mirrors where you need all linked assets (images, CSS, JS). Export the mirror to `mirror/sitesuck/`.

This is how the VE project originally captured the full site structure and CSS files from `doc.vortala.com`.

## Output Directory Structure

After capture, your `mirror/` directory should look like:

```
mirror/
  extracted/              # Raw HTML fragments per page
    back-pain-content.html
    neck-pain-content.html
    _summary.json         # Scrape results log
  screenshots/            # Full-page PNGs
    back-pain.png
    neck-pain.png
  raw-css/                # Original stylesheets
    _style-1770742603.css
  full-site/              # HTTrack mirror (optional)
```

## Capture Checklist

- [ ] Identify all target URLs (navigation, sitemap, guessing)
- [ ] Run Playwright scrape with `networkidle` wait strategy
- [ ] Screenshot every page at desktop viewport
- [ ] Check for additional pages via sitemap.xml
- [ ] Run second-pass scrape for discovered URLs
- [ ] Download original CSS files into `mirror/raw-css/`
- [ ] Verify `_summary.json` shows all expected pages
- [ ] Spot-check 3-5 extracted HTML files for completeness

## Next Step

With raw HTML and screenshots captured, proceed to [Phase 2: Extract Design System](02-extract-design-system.md).
