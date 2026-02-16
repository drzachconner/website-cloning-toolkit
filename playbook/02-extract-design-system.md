# Phase 2: Extract Design System

Analyze the captured site to identify its visual DNA: CSS classes, fonts, colors, spacing, and layout grid. The goal is a documented design token set that drives Phase 3 (code generation) and Phase 4 (conversion).

**Prerequisites:** Captured site in `mirror/` from [Phase 1](01-capture.md)

## Browser Extensions

These tools let you inspect design tokens directly in the browser without reading raw CSS:

| Tool | What It Extracts | Link |
|------|-----------------|------|
| **SnipCSS** | Full CSS for any element, one-click copy | Chrome Web Store |
| **CSS Peeper** | Colors, fonts, spacing in a visual panel | Chrome Web Store |
| **Peek** | Font family, size, weight, line-height | Chrome Web Store |
| **MiroMiro** | Color palette from any page | Chrome Web Store |
| **WhatFont** | Font identification on hover | Chrome Web Store |
| **Website Font Extractor** | Downloads actual font files | Chrome Web Store |

### Recommended Workflow

1. Open the target site in Chrome
2. Use **CSS Peeper** to get a quick overview of colors and fonts
3. Use **SnipCSS** on key elements (hero, CTA, cards, nav) to capture full CSS rules
4. Use **Peek** or **WhatFont** to confirm font families and weights
5. Use **MiroMiro** for the complete color palette

## CSS Class Extraction

### Using extract-css.py

```bash
python scripts/extract-css.py --url "https://targetsite.com" --output css/cloned-styles.css --subset --html-dir mirror/extracted/
```

The script parses the original CSS and extracts class definitions relevant to the content area, filtering out framework/utility classes.

### Manual Extraction Pattern

For sites where the CSS is inlined or spread across multiple files, extract classes from the captured HTML:

```python
from bs4 import BeautifulSoup
import os
import json
from collections import Counter

# Scan all extracted HTML for class usage
class_counter = Counter()
extracted_dir = "mirror/extracted"

for filename in os.listdir(extracted_dir):
    if not filename.endswith(".html"):
        continue
    with open(os.path.join(extracted_dir, filename)) as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup.find_all(True):
        for cls in tag.get("class", []):
            class_counter[cls] += 1

# Print most common classes
for cls, count in class_counter.most_common(50):
    print(f"{cls}: {count}")
```

This tells you which classes actually matter. High-frequency classes are structural (wrappers, grids). Medium-frequency classes are component-level (callouts, CTAs). Low-frequency classes may be page-specific.

### Class Inventory Document

Create a class inventory mapping source classes to their purpose:

```markdown
## Class Inventory

| Source Class | Purpose | Properties |
|-------------|---------|------------|
| `.entry-content` | Main content wrapper | max-width: 960px, margin: auto |
| `.bldr_callout` | Pull quote / callout | italic, border-left: 3px solid #999 |
| `.bldr_notebox` | CTA container box | bg: #f1f1f1, border-radius: 25px |
| `.bldr_cta` | CTA button | bg: #ed247c, color: #fff, uppercase |
| `.rounded` | Circular image | border-radius: 50% |
| `.alignright` | Float right | float: right, margin-left: 20px |
| `.fa-ul` | Gold bullet list | list-style: none, custom markers |
```

## Font Extraction

### Identifying Fonts

```bash
python scripts/extract-fonts.py --url https://targetsite.com --output docs/fonts.md
```

### Manual Font Identification

1. **Inspect element** on headings and body text
2. Note `font-family`, `font-weight`, `font-size`, `line-height`
3. Check for Google Fonts links in `<head>`:

```bash
# Search captured HTML for font imports
grep -r "fonts.googleapis" mirror/
grep -r "@import.*font" mirror/raw-css/
grep -r "font-family" mirror/raw-css/ | sort -u
```

### Font Token Document

```markdown
## Typography

### Headings: Playfair Display (serif)
- H1: 2em, weight 700, color #333
- H2: 1.8em, weight 700, color #333
- H3: 1.4em, Mulish (sans-serif), weight 600, color #333

### Body: Mulish (sans-serif)
- Size: 12pt (16px)
- Weight: 400
- Color: #333
- Line-height: 1.6

### Google Fonts import:
fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Mulish:wght@400;600;700
```

## Color Extraction

### Using extract-colors.py

```bash
python scripts/extract-colors.py --css mirror/raw-css/_style-*.css --output docs/colors.md
```

### Manual Color Extraction

Pull all hex/rgb values from the CSS:

```python
import re

with open("mirror/raw-css/style.css") as f:
    css = f.read()

# Extract hex colors
hex_colors = set(re.findall(r'#[0-9a-fA-F]{3,8}', css))

# Extract rgb/rgba colors
rgb_colors = set(re.findall(r'rgba?\([^)]+\)', css))

print("Hex colors:", sorted(hex_colors))
print("RGB colors:", sorted(rgb_colors))
```

### Color Token Document

```markdown
## Color Palette

### Primary
- Brand pink: #ed247c (CTAs, hover links)
- Brand gold: #ffbe08 (list markers, accents)
- Hover gold: #feb506 (CTA hover state)

### Neutral
- Text: #333
- Strong text: #111
- Callout text: #444
- Border light: #eee
- Border medium: #999
- Background gray: #f1f1f1

### Utility
- Header bar: rgba(216, 19, 104, 1)
- Footer: #111
- White: #fff
```

## Spacing and Layout Grid

### Grid System

Most sites use a max-width container with column-based layouts:

```css
/* Common pattern */
.container { max-width: 960px; margin: 0 auto; }

/* Column classes */
.one_half { width: 48%; float: left; }
.one_half.last { margin-left: 4%; }
.one_third { width: 30%; float: left; }
.two_thirds { width: 63%; float: left; }
```

### Spacing Tokens

Inspect padding/margin patterns across components:

```markdown
## Spacing

- Section gap: 30px (between major content blocks)
- Paragraph gap: 15px (between paragraphs)
- Component padding: 20px-30px (callouts, noteboxes)
- Column gutter: 4% (between side-by-side columns)
- Image margin: 0 0 15px 25px (floated right images)
```

## ExtractCSS.dev (Tailwind Conversion)

If your target output uses Tailwind, paste the original CSS into [ExtractCSS.dev](https://extractcss.dev) to get approximate Tailwind utility classes.

This works best for simple designs. Complex layouts with custom properties will need manual mapping.

## Keep the Full Original CSS

Always keep the complete original CSS file as reference, even after extracting your subset:

```
mirror/
  raw-css/
    _style-1770742603.css   # Full original (never modify)
css/
  site-clone.css             # Your subset/adapted version
docs/
  design-tokens.md           # Extracted tokens
  class-inventory.md         # Class mapping
```

The original CSS is your source of truth when something looks wrong. You will reference it repeatedly during Phase 4 refinement.

## Output Checklist

- [ ] Class inventory document (source class -> purpose -> properties)
- [ ] Font tokens (families, weights, sizes, Google Fonts import URL)
- [ ] Color palette (all hex/rgb values categorized)
- [ ] Spacing tokens (section gaps, padding, margins, gutters)
- [ ] Layout grid (max-width, column percentages)
- [ ] Full original CSS preserved in `mirror/raw-css/`
- [ ] Subset CSS created in `css/` for your pages

## Next Step

With design tokens documented, proceed to [Phase 3: Generate Code](03-generate-code.md).
