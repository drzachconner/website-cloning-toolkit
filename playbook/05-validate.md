# Phase 5: Validate

Verify that cloned pages visually match the original site and meet structural quality standards. This phase catches regressions, missing elements, and visual drift.

**Prerequisites:** Converted pages from [Phase 4](04-convert-and-refine.md), original screenshots from [Phase 1](01-capture.md)

## Visual Diff: Screenshot Comparison

The most reliable validation method: compare screenshots of your cloned pages against the original site.

### Using visual-diff.py

```bash
python scripts/visual-diff.py \
  --original mirror/screenshots/ \
  --clone conditions/ \
  --output report/diffs/ \
  --threshold 0.05
```

### Manual Screenshot Comparison

When automated diffing is not set up, compare manually:

1. Open the original screenshot side-by-side with the cloned page
2. Check: heading styles, font rendering, spacing, colors, image placement
3. Flag any visible differences

### Automated Screenshot Capture of Clones

Use Playwright to screenshot your cloned pages for comparison:

```python
#!/usr/bin/env python3
"""Screenshot all cloned pages for visual comparison."""
import os
import glob
from playwright.sync_api import sync_playwright

CONDITIONS_DIR = "conditions"
OUTPUT_DIR = "report/clone-screenshots"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html_files = sorted(glob.glob(os.path.join(CONDITIONS_DIR, "*.html")))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for filepath in html_files:
            filename = os.path.basename(filepath)
            slug = filename.replace(".html", "")

            page = browser.new_page(viewport={"width": 1200, "height": 800})
            page.goto(f"file://{os.path.abspath(filepath)}")
            page.wait_for_timeout(1000)  # Let fonts load

            page.screenshot(
                path=os.path.join(OUTPUT_DIR, f"{slug}.png"),
                full_page=True
            )
            page.close()
            print(f"  Screenshot: {slug}")

        browser.close()

    print(f"\nScreenshots saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
```

### Pixel-Level Diff with Pillow

```python
from PIL import Image, ImageChops
import math

def image_diff(img1_path, img2_path, output_path):
    """Generate a visual diff between two screenshots."""
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)

    # Resize to match (screenshots may differ in height)
    min_width = min(img1.width, img2.width)
    min_height = min(img1.height, img2.height)
    img1 = img1.crop((0, 0, min_width, min_height))
    img2 = img2.crop((0, 0, min_width, min_height))

    # Generate diff image (differences appear as bright pixels)
    diff = ImageChops.difference(img1, img2)
    diff.save(output_path)

    # Calculate similarity score
    stat = list(diff.getdata())
    total_diff = sum(sum(pixel) for pixel in stat)
    max_diff = min_width * min_height * 3 * 255
    similarity = 1 - (total_diff / max_diff)

    return similarity

# Usage
score = image_diff(
    "mirror/screenshots/back-pain.png",
    "report/clone-screenshots/back-pain.png",
    "report/diffs/back-pain-diff.png"
)
print(f"Similarity: {score:.2%}")  # Target: >95%
```

## Responsive Testing

Test at key breakpoints to ensure the layout works across devices:

| Breakpoint | Device | What to Check |
|-----------|--------|---------------|
| 320px | iPhone SE | Text readable, no horizontal scroll, images stack |
| 768px | iPad portrait | Columns may collapse, images resize |
| 1024px | iPad landscape / small desktop | Full layout visible |
| 1440px | Desktop | Max-width container centered, proper margins |

### Automated Responsive Screenshots

```python
BREAKPOINTS = [
    {"name": "mobile", "width": 320, "height": 568},
    {"name": "tablet", "width": 768, "height": 1024},
    {"name": "desktop", "width": 1024, "height": 768},
    {"name": "wide", "width": 1440, "height": 900},
]

for bp in BREAKPOINTS:
    page = browser.new_page(
        viewport={"width": bp["width"], "height": bp["height"]}
    )
    page.goto(f"file://{filepath}")
    page.wait_for_timeout(1000)
    page.screenshot(
        path=f"report/responsive/{slug}-{bp['name']}.png",
        full_page=True
    )
    page.close()
```

## CSS Class Audit

Verify that all target CSS classes are present and correctly applied:

```python
from bs4 import BeautifulSoup
import os
import glob

REQUIRED_CLASSES = [
    "entry-content",
    "bldr_cta",
    "bldr_divider",
]

EXPECTED_CLASSES = [
    "bldr_callout",
    "bldr_notebox",
    "rounded",
    "fa-ul",
]

def audit_page(filepath):
    """Check a page for required and expected CSS classes."""
    with open(filepath) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    filename = os.path.basename(filepath)
    issues = []

    # Check required classes
    for cls in REQUIRED_CLASSES:
        if not soup.find(class_=cls):
            issues.append(f"MISSING required class: .{cls}")

    # Check expected classes (warn, not error)
    for cls in EXPECTED_CLASSES:
        if not soup.find(class_=cls):
            issues.append(f"WARNING: expected class .{cls} not found")

    # Check for exactly one H1
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        issues.append(f"H1 count: {len(h1s)} (expected 1)")

    # Check for no inline styles (except on specific allowed elements)
    style_tags = soup.find_all("style")
    if style_tags:
        issues.append(f"Found {len(style_tags)} inline <style> tags")

    # Check for CTA link
    cta = soup.find("a", class_="bldr_cta")
    if cta and cta.get("href") != "/contact-us/":
        issues.append(f"CTA href: {cta.get('href')} (expected /contact-us/)")

    # Check for favicon
    favicon = soup.find("link", attrs={"rel": "icon"})
    if not favicon:
        issues.append("Missing favicon link")

    # Check for schema markup
    schema = soup.find("script", type="application/ld+json")
    if not schema:
        issues.append("Missing Schema.org JSON-LD")

    return issues

# Run audit across all pages
html_files = sorted(glob.glob("conditions/*.html"))
for filepath in html_files:
    issues = audit_page(filepath)
    if issues:
        print(f"\n{os.path.basename(filepath)}:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"  OK: {os.path.basename(filepath)}")
```

## Font Rendering Comparison

Fonts can look different between the original site and your clone due to loading order, fallbacks, or missing weights.

### Check Font Loading

```html
<!-- Verify Google Fonts link is in <head> -->
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Mulish:wght@400;600;700&display=swap">
```

### Browser DevTools Font Check

1. Open your cloned page in Chrome
2. Inspect a heading element
3. In the Computed tab, check `font-family` -- it should show the loaded font, not a fallback
4. If you see "Times New Roman" or "Arial" instead of "Playfair Display" or "Mulish", the font is not loading

### Common Font Issues

- **Google Fonts link missing or malformed** -- Check the URL includes all needed weights
- **CSS specifies font but never imports it** -- Add the `@import` or `<link>` tag
- **Font weight mismatch** -- If you import weight 400 but CSS uses weight 600, it will use faux bold

## Color Accuracy Check

Compare hex values between original CSS and your clone:

```python
import re

def extract_colors(css_path):
    """Extract all color values from a CSS file."""
    with open(css_path) as f:
        css = f.read()
    hex_colors = set(re.findall(r"#[0-9a-fA-F]{3,8}", css))
    return sorted(hex_colors)

original_colors = extract_colors("mirror/raw-css/original.css")
clone_colors = extract_colors("css/site-clone.css")

print("Original colors:", original_colors)
print("Clone colors:", clone_colors)

# Check for missing colors
missing = set(original_colors) - set(clone_colors)
if missing:
    print(f"Colors in original but not clone: {missing}")
```

Key colors to verify:
- Primary brand color (CTAs, accents)
- Text colors (headings, body, links)
- Background colors (noteboxes, callouts)
- Border colors

## Lighthouse / PageSpeed

Run Lighthouse to check performance parity:

```bash
# CLI
npx lighthouse file:///path/to/conditions/back-pain.html \
  --output json --output-path report/lighthouse-back-pain.json

# Or use Chrome DevTools > Lighthouse tab
```

Key metrics to compare:
- **Performance score** -- Should be equal or better than original (static HTML is usually faster)
- **Accessibility score** -- Check alt tags, heading hierarchy, color contrast
- **SEO score** -- Check meta tags, Schema.org, title tags

## Full QA Checklist

Run this checklist against every page before delivery:

- [ ] No inline `<style>` tags (all styling via shared CSS)
- [ ] No emojis in content
- [ ] No `<nav>` or `<footer>` elements (content-only pages)
- [ ] CSS stylesheet link present
- [ ] Favicon link present
- [ ] Schema.org JSON-LD present and valid
- [ ] `.bldr_cta` links to `/contact-us/`
- [ ] Exactly one `<h1>` per page
- [ ] `.entry-content` wrapper on every page
- [ ] `.bldr_divider` and bottom tagline on every page
- [ ] All educational content from originals preserved
- [ ] Hero image has meaningful alt text
- [ ] Page title and meta description are unique per page
- [ ] Relative paths used for all local assets
- [ ] Font Awesome CDN link present (if using FA icons)
- [ ] No broken images or 404 asset references
- [ ] Page renders correctly at 320px, 768px, 1024px, 1440px

## Validation Report

Generate a summary report:

```markdown
## Validation Report - [Date]

### Pages Audited: 32
### Issues Found: 3
### Visual Diff Score: 96.2% average similarity

| Page | CSS Audit | Schema | Responsive | Visual Diff |
|------|-----------|--------|------------|-------------|
| back-pain.html | PASS | PASS | PASS | 97.1% |
| neck-pain.html | PASS | PASS | WARN (320px) | 95.8% |
| headaches.html | FAIL (missing .bldr_callout) | PASS | PASS | 94.2% |
```

## Next Step

With validation complete, the pages are ready for delivery. See [lessons-from-ve-project.md](lessons-from-ve-project.md) for retrospective notes on the full process.
