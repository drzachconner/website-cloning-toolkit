# Phase 4: Convert & Refine

Transform raw or draft HTML into production-ready pages through multi-pass Python scripts. This is where batch conversion happens -- taking the extracted content from Phase 1 and the templates from Phase 3 and producing final pages.

**Prerequisites:** Extracted HTML in `mirror/extracted/`, template from Phase 3, design tokens from Phase 2

## Core Principle: Multi-Pass Processing

Never try to do everything in one script. Each pass handles one concern:

```
Pass 1: Structure    -- Map source HTML structure to target template
Pass 2: Styling      -- Convert source CSS classes to target classes
Pass 3: Layout       -- Fix image floats, columns, clear floats
Pass 4: Components   -- Add CTAs, dividers, taglines, schema markup
Pass 5: Polish       -- Font Awesome icons, spacers, final fixes
```

This approach is more reliable than a single monolithic script because:
- Each pass can be tested independently
- Failures are isolated and easy to debug
- You can re-run a single pass without re-doing everything
- New requirements only affect the relevant pass

## BeautifulSoup for HTML Parsing

Always use BeautifulSoup for HTML manipulation. Never use regex alone for HTML transformations -- it breaks on edge cases.

```python
from bs4 import BeautifulSoup

with open("mirror/extracted/back-pain-content.html") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Safe element manipulation
h1 = soup.find("h1")
callouts = soup.find_all("div", class_="source-callout")
cta_links = soup.find_all("a", class_="source-cta")
```

Use regex for simple string replacements within already-extracted text (class name swaps, attribute changes), but use BeautifulSoup for any structural changes.

## Class Mapping Strategy

Create a mapping from source site classes to your target classes:

```python
CLASS_MAP = {
    "source-callout": "bldr_callout",
    "source-cta-box": "bldr_notebox",
    "source-button": "bldr_cta",
    "source-hero": "rounded alignright",
    "source-list": "fa-ul",
    "source-divider": "bldr_divider",
    "source-quote": "bldr_callout",
}

def map_classes(soup):
    """Replace source classes with target classes."""
    for source_cls, target_cls in CLASS_MAP.items():
        for tag in soup.find_all(class_=source_cls):
            tag["class"] = [c if c != source_cls else target_cls
                           for c in tag.get("class", [])]
    return soup
```

Document the full mapping in `docs/class-inventory.md` so it is clear what each source class becomes.

## Pass 1: Structure (convert-html.py)

The main conversion script that wraps extracted content into the target page template:

```bash
python scripts/convert-html.py --input mirror/extracted/ --output conditions/ --template templates/page-template.html
```

### Core Pattern

```python
#!/usr/bin/env python3
"""Convert extracted HTML fragments into full pages."""
import os
import glob
from bs4 import BeautifulSoup

CONDITIONS_DIR = "conditions"
EXTRACTED_DIR = "mirror/extracted"

def extract_condition_title(soup):
    """Extract the condition name from H1."""
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text()
        # Remove location suffix (customize per project)
        return text.replace(" Care in Royal Oak", "").strip()
    return ""

def convert_page(filepath):
    """Convert a single extracted page to the target template."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    condition_title = extract_condition_title(soup)

    # Extract metadata
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    title_tag = soup.find("title")
    page_title = title_tag.string if title_tag else f"{condition_title} | Site Name"

    # Extract and transform content elements
    elements = []
    for tag in soup.children:
        if tag.name is None:
            continue
        if tag.name == "h1":
            continue  # We rebuild the H1

        # Map source components to target components
        if tag.name == "div" and "source-callout" in tag.get("class", []):
            elements.append(("callout", tag.decode_contents()))
            continue

        if tag.name == "div" and "source-cta" in tag.get("class", []):
            continue  # We rebuild the CTA section

        elements.append(("raw", str(tag)))

    # Build the new page using the target template
    return build_page(page_title, meta_desc, condition_title, elements)

def build_page(title, meta_desc, condition, elements):
    """Assemble the final HTML page."""
    content_parts = [f"<h1>{condition} Care in Royal Oak</h1>"]

    for etype, econtent in elements:
        if etype == "callout":
            content_parts.append(f'<div class="bldr_callout">{econtent}</div>')
        else:
            content_parts.append(econtent)

    # Add standard CTA section
    content_parts.append("""
<div class="bldr_notebox">
<h2>Schedule Today</h2>
<p>Contact our office today to book an appointment.</p>
<p><a href="/contact-us/" class="bldr_cta">CONTACT US</a></p>
</div>""")

    # Add divider and tagline
    content_parts.append('<div class="cb"></div>')
    content_parts.append('<p><img class="bldr_divider" alt="divider" src="../images/divider1.png"></p>')
    content_parts.append(f'<h3 align="center">{condition} Care Royal Oak MI | (248) 616-0900</h3>')

    inner = "\n".join(content_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{meta_desc}">
  <link rel="icon" type="image/png" href="../images/favicon1.png">
  <link rel="stylesheet" href="../css/site-clone.css">
</head>
<body class="page layout-one-col">
  <div id="containing_wrap">
    <div id="wrap">
      <div id="container_wrap">
        <div id="container">
          <div id="content">
            <div class="entry-content cf">
{inner}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""
```

## Pass 2: Styling (fix classes and visual elements)

After structural conversion, fix CSS classes and add visual components:

```python
def fix_lists_to_fa_ul(content):
    """Convert plain <ul> to fa-ul with gold markers."""
    import re

    FA_ICON = '<i class="fas fa-circle fa-2xs" style="color: #ffbe08;"></i> '

    def replace_ul(match):
        ul_content = match.group(0)
        if "fa-ul" in ul_content:
            return ul_content
        ul_content = ul_content.replace("<ul>", '<ul class="fa-ul">', 1)
        ul_content = re.sub(
            r"<li>",
            f'<li style="margin-bottom: 5px;">{FA_ICON}',
            ul_content
        )
        return ul_content

    return re.sub(r"<ul>.*?</ul>", replace_ul, content, flags=re.DOTALL)

def fix_image_structure(content):
    """Wrap hero images in alignment divs."""
    import re
    return re.sub(
        r'<img\s+class="rounded\s+alignright"([^>]*)>',
        r'<div class="alignright"><img class="rounded"\1></div>',
        content
    )
```

## Pass 3: Metadata and Schema

Add Schema.org markup and ensure metadata is correct:

```python
import json

def generate_schema(condition_title, slug, meta_desc):
    """Generate MedicalWebPage schema for a condition page."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "name": f"{condition_title} Care in Royal Oak",
        "description": meta_desc,
        "url": f"https://targetsite.com/{slug}/",
        "publisher": {
            "@type": "MedicalBusiness",
            "name": "Practice Name",
            "telephone": "(248) 616-0900",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Royal Oak",
                "addressRegion": "MI"
            }
        }
    }, indent=2)
```

## Archive Before Transformation

Always archive originals before running conversion:

```bash
# Before first conversion
mkdir -p archive/
cp conditions/*.html archive/

# Or use git
git add conditions/
git commit -m "Archive original pages before conversion"
```

This lets you diff changes and recover content if a conversion script has bugs.

## Batch Processing Pattern

Run conversion across all pages with progress logging:

```python
import glob

if __name__ == "__main__":
    html_files = sorted(glob.glob(os.path.join(CONDITIONS_DIR, "*.html")))

    success = 0
    failed = 0

    for filepath in html_files:
        filename = os.path.basename(filepath)
        print(f"Converting {filename}...")

        try:
            if convert_page(filepath):
                success += 1
                print(f"  OK: {filename}")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  ERROR: {filename}: {e}")

    print(f"\nDone: {success} converted, {failed} failed out of {len(html_files)} files.")
```

## Content Merging

When the source site has duplicate or overlapping pages (e.g., "back-pain" and "back-pain-treatment"), merge them:

1. Identify duplicates by comparing H1 titles and content overlap
2. Pick the richer page as the base
3. Pull unique sections from the secondary page
4. Use human judgment for what to keep -- automated merging loses nuance

In the VE project, 44 original pages were consolidated to 32 because many conditions had duplicate URLs (e.g., "sciatica" and "sciatica-treatment" with overlapping content).

## Placeholder Images

Use SVG placeholders during development to avoid broken images and keep the repo lightweight:

```html
<img class="rounded" src="../images/placeholder-square.svg"
     alt="Back pain chiropractic care" width="425" height="425">
```

A 400x400 SVG placeholder in `images/placeholder-square.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#f0f0f0"/>
  <text x="200" y="200" text-anchor="middle" dy=".3em"
        font-family="sans-serif" font-size="16" fill="#999">
    425 x 425
  </text>
</svg>
```

Replace with real images in the final delivery.

## Relative Paths for Portability

Always use relative paths so pages work when opened locally and when deployed to any domain:

```html
<!-- Good: relative paths -->
<link rel="stylesheet" href="../css/site-clone.css">
<img src="../images/logo.png">

<!-- Bad: absolute paths (breaks when moved) -->
<link rel="stylesheet" href="/css/site-clone.css">
<img src="https://example.com/images/logo.png">
```

## Output Checklist

- [ ] All pages converted to target template structure
- [ ] Source CSS classes mapped to target classes
- [ ] Metadata (title, description) preserved on every page
- [ ] Schema.org JSON-LD present on every page
- [ ] CTA sections generated with correct links
- [ ] Divider and tagline on every page
- [ ] Originals archived before transformation
- [ ] All educational content from originals preserved
- [ ] Exactly one `<h1>` per page
- [ ] No inline `<style>` tags
- [ ] Favicon link present on every page

## Next Step

With pages converted, proceed to [Phase 5: Validate](05-validate.md) for visual and structural verification.
