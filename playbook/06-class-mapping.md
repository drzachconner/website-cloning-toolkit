# Phase 6: Class Mapping

CSS class mapping is the core technique for making cloned pages match the target site. It bridges the gap between your source content (scraped HTML, CMS exports, or AI-generated drafts) and the target site's actual class names and styling conventions.

This guide covers the full process: discovering the target site's classes, documenting them, automating the mapping, and validating the result.

**Prerequisites:** Mirrored HTML from Phase 1, extracted CSS from Phase 2, at least one reference template from Phase 3.

## What Class Mapping Is

When you clone a site, the source HTML rarely uses the same CSS class names as the target site. The source might have `.callout-box` where the target uses `.bldr_callout`. The source might wrap content in `.page-body` where the target expects `.entry-content.cf`.

Class mapping is the systematic process of:
1. Identifying every CSS class the target site uses on its content pages
2. Documenting what each class does visually (its purpose and key CSS properties)
3. Creating a translation table from your source classes to the target classes
4. Applying that translation programmatically across all pages

The mapping is not just a mechanical find-and-replace. It encodes *visual intent*: "this element should look like a pull-quote" becomes "apply `.bldr_callout` which renders as italic text with a 3px left border."

## Why It Matters

Without accurate class mapping:
- Pages render with default browser styles instead of the target site's design
- Components (CTAs, callouts, cards) appear as unstyled divs
- The web team cannot extract content into the CMS because the class names do not match
- Visual QA fails on every page, requiring manual fixes that do not scale

With a thorough mapping:
- Every page matches the target site's visual design automatically
- Batch processing works reliably across dozens or hundreds of pages
- The web team can extract `.entry-content` directly into the CMS
- Visual QA passes on first run for most pages

## The Discovery Process

### Step 1: Inspect the Target Site

Open the target site in Chrome DevTools and examine the content area of a representative page. Ignore navigation, header, footer, and sidebar -- focus only on the main content div.

Right-click on each visual component and note:
- The element type (`div`, `p`, `a`, `ul`, etc.)
- The CSS classes applied
- Which classes carry the visual styling vs. which are structural wrappers

```
Target page: https://example.com/services/back-pain/

Content wrapper:  <div class="entry-content cf">
Pull-quote:       <div class="bldr_callout">
CTA box:          <div class="bldr_notebox">
CTA button:       <a class="bldr_cta">
Hero image:       <img class="rounded alignright">
Divider:          <img class="bldr_divider">
Gold bullet list: <ul class="fa-ul">
Two columns:      <div class="column one_half">
```

### Step 2: Analyze the Mirrored HTML

If you captured the site in Phase 1, the mirrored HTML files contain the actual class names. Search across all mirrored files for unique class names:

```bash
# Extract all class names from mirrored HTML
grep -oP 'class="[^"]*"' mirror/extracted/*.html | \
  tr '"' '\n' | grep -v '^class=$' | tr ' ' '\n' | \
  sort | uniq -c | sort -rn | head -40
```

This gives you a frequency-sorted list. The most common classes are usually the ones that matter (content wrappers, component classes).

### Step 3: Trace CSS Rules

For each class you identified, find its CSS rules in the extracted stylesheet:

```bash
# Find all rules for a specific class
grep -A5 '\.bldr_callout' mirror/css/style.css
```

Document the key visual properties: colors, borders, padding, font styles, positioning. These properties define the class's visual purpose and help you match source elements to target classes.

### Step 4: Examine Your Source Content

Look at the HTML you are converting (CMS exports, AI-generated drafts, or scraped content from a different site). Identify the classes and structures it uses for the same visual purposes:

```
Source page: archive/back-pain.html

Content wrapper:  <div class="page-content">
Pull-quote:       <blockquote class="highlight">
CTA box:          <div class="action-box">
CTA button:       <a class="btn btn-primary">
Hero image:       <img class="feature-image float-right">
```

### Step 5: Build the Mapping Table

Match source classes to target classes by visual purpose:

| Source Class | Target Class | Visual Purpose | Key CSS Properties |
|---|---|---|---|
| `.page-content` | `.entry-content.cf` | Main content wrapper | max-width, margin auto, clearfix |
| `.highlight` | `.bldr_callout` | Pull-quote callout | italic, border-left 3px solid #999 |
| `.action-box` | `.bldr_notebox` | CTA container | #f1f1f1 bg, border-radius 8px, padding 20px |
| `.btn.btn-primary` | `.bldr_cta` | CTA button | #ed247c bg, white text, padding 10px 20px |
| `.feature-image.float-right` | `.rounded.alignright` | Hero image | border-radius 8px, float right, margin-left 20px |

## JSON Format for Class Maps

The `convert-html.py` script reads class mappings from a JSON config file. The config supports class renaming, element removal, page shell wrapping, and asset path rewriting.

### Basic Class Map

```json
{
  "class_map": {
    "page-content": "entry-content cf",
    "highlight": "bldr_callout",
    "action-box": "bldr_notebox",
    "btn btn-primary": "bldr_cta",
    "feature-image float-right": "rounded alignright",
    "bullet-list": "fa-ul"
  },
  "remove_elements": ["nav", "footer", "script", "noscript", ".sidebar"],
  "asset_base": "../images/"
}
```

### Full Config with Page Shell

```json
{
  "class_map": {
    "highlight": "bldr_callout",
    "action-box": "bldr_notebox",
    "btn-primary": "bldr_cta"
  },
  "remove_elements": ["nav", "footer", "script", "noscript"],
  "page_shell": "<div class='entry-content cf'>{{content}}</div>",
  "asset_base": "../images/"
}
```

### Multi-Class Mapping

When a source element has multiple classes that should all be renamed:

```json
{
  "class_map": {
    "col-6": "column one_half",
    "col-8": "column two_thirds",
    "col-4": "column one_third",
    "img-rounded": "rounded",
    "float-right": "alignright",
    "float-left": "alignleft"
  }
}
```

### Removing Classes

Map a class to an empty string to remove it without replacing:

```json
{
  "class_map": {
    "wp-block-paragraph": "",
    "has-text-color": "",
    "legacy-widget": ""
  }
}
```

## CLAUDE.md Format

For projects using Claude Code, document the class mapping directly in the project's CLAUDE.md. This gives Claude context during every edit without needing to load a separate file.

```markdown
## CSS Classes (matching target site)

### Content Structure
- `.entry-content.cf` -- Main content wrapper (max-width: 780px, margin: 0 auto)
- `.cb` -- Clear-both div (clear: both, used between floated sections)

### Components
- `.bldr_callout` -- Italic pull-quote with left border (font-style: italic, border-left: 3px solid #999, padding-left: 15px)
- `.bldr_notebox` -- Gray rounded CTA box (background: #f1f1f1, border-radius: 8px, padding: 20px)
- `.bldr_cta` -- Pink CTA button (background: #ed247c, color: #fff, padding: 10px 20px, text-decoration: none)
- `.bldr_divider` -- Decorative divider image (display: block, margin: 20px auto)

### Images
- `.rounded` -- Border-radius on images (border-radius: 8px)
- `.alignright` -- Float right with left margin (float: right, margin: 0 0 10px 20px)
- `.alignleft` -- Float left with right margin (float: left, margin: 0 20px 10px 0)

### Layout
- `.column.one_half` -- 50% width column (width: 48%, float: left)
- `.column.two_thirds` -- 66% width column (width: 65%, float: left)
- `.column.one_third` -- 33% width column (width: 31%, float: left)

### Lists
- `.fa-ul` -- Font Awesome unordered list (list-style: none, padding-left: 2em)

### Wrapper IDs
- `#containing_wrap` -- Outermost page wrapper
- `#wrap` -- Secondary wrapper
- `#container_wrap` -- Content area wrapper
- `#container` -- Inner container
- `#content` -- Content column
```

This format gives Claude everything it needs: the class name, its visual purpose, and the key CSS properties that define its appearance.

## Automated Mapping with convert-html.py

The `convert-html.py` script applies class mappings in batch:

```bash
python scripts/convert-html.py \
  --input archive/ \
  --output pages/ \
  --config class-mapping.json \
  --template templates/page-template.html
```

The script runs four passes:
1. **Structure pass** -- Wraps content in the page shell if configured
2. **Class pass** -- Renames CSS classes per the mapping
3. **Asset pass** -- Rewrites image and CSS paths to relative paths
4. **Cleanup pass** -- Removes unwanted elements (nav, footer, scripts)

Always archive originals before running conversion:

```bash
cp -r archive/ archive-backup/
git add archive/ && git commit -m "Archive originals before class mapping"
```

## Common Patterns

### Wrapper Classes

Every site has a main content wrapper. Identifying it is critical because this is what the web team extracts for CMS integration.

Common wrapper class names:
- `.entry-content` (WordPress/Vortala)
- `.article-body` (news sites)
- `.page-content` (generic CMS)
- `.main-content` (custom sites)
- `#content` (ID-based)

The wrapper often has a companion clearfix class (`.cf`, `.clearfix`, `.overflow-hidden`).

### Component Classes

Components are the reusable visual blocks within the content area. Map them by visual purpose, not by name similarity:

| Visual Purpose | Common Source Names | Common Target Names |
|---|---|---|
| Pull-quote / callout | `.quote`, `.blockquote`, `.highlight` | `.bldr_callout`, `.wp-block-quote` |
| CTA box | `.cta-box`, `.action-box`, `.promo` | `.bldr_notebox`, `.wp-block-group` |
| CTA button | `.btn`, `.button`, `.cta` | `.bldr_cta`, `.wp-block-button__link` |
| Card | `.card`, `.feature-box`, `.panel` | `.bordered-section`, `.wp-block-column` |
| Divider | `.separator`, `.hr`, `.divider` | `.bldr_divider`, `.wp-block-separator` |

### Utility Classes

Utility classes handle single-purpose styling: floats, alignment, spacing. They often need one-to-one mapping:

```json
{
  "class_map": {
    "text-center": "text-center",
    "text-right": "text-right",
    "float-left": "alignleft",
    "float-right": "alignright",
    "clearfix": "cf",
    "mb-4": "",
    "mt-3": ""
  }
}
```

Note: framework-specific spacing classes (Bootstrap's `mb-4`, `mt-3`) often have no direct equivalent. Remove them and let the target CSS handle spacing.

### State Classes

State classes handle hover, active, focus, and responsive states. These typically do not need mapping because they are managed by the target site's CSS. If your clone includes interactive elements, verify the target CSS covers the same states.

## Handling CSS-in-JS Source Sites

Sites built with styled-components, Emotion, or CSS Modules generate class names like `.css-1a2b3c` or `.styles_heading__x7y8z`. These are not human-readable and change on every build.

**Strategy:** Ignore the generated class names entirely. Instead:

1. Identify elements by their tag type and position in the DOM tree
2. Extract the computed styles (using `extract-colors.py` and `extract-design-system.py`)
3. Map elements to target classes based on their visual appearance, not their class names
4. In the conversion script, select elements by tag and context rather than class

```python
# Instead of mapping by class name:
# "css-1a2b3c" -> "bldr_callout"  # This breaks on next build

# Map by element context:
for blockquote in soup.find_all("blockquote"):
    blockquote["class"] = ["bldr_callout"]

for div in soup.find_all("div", attrs={"data-testid": "cta-box"}):
    div["class"] = ["bldr_notebox"]
```

## Handling Tailwind Source Sites

Sites built with Tailwind use many utility classes per element (`class="flex items-center justify-between p-4 bg-white rounded-lg shadow-md"`). Mapping each utility class individually is impractical.

**Strategy:**

1. Use `extract-css.py --tailwind` to generate a mapping from the source CSS to Tailwind utilities
2. For the clone, collapse utility classes into semantic target classes
3. Map compound utility sets to single target classes:

```json
{
  "class_map_compound": [
    {
      "source_pattern": "bg-gray-100 rounded-lg p-6",
      "target": "bldr_notebox",
      "notes": "Gray CTA box"
    },
    {
      "source_pattern": "italic border-l-4 border-gray-400 pl-4",
      "target": "bldr_callout",
      "notes": "Pull-quote"
    }
  ]
}
```

This requires custom handling in your conversion script since the standard class map works one-to-one.

## Validation

### Completeness Check

After creating the mapping, verify every class in the source HTML is accounted for:

```bash
# Extract all classes from source HTML
grep -oP 'class="[^"]*"' archive/*.html | tr '"' '\n' | \
  grep -v '^class=$' | tr ' ' '\n' | sort -u > source-classes.txt

# Extract all mapped classes from config
python3 -c "
import json
config = json.load(open('class-mapping.json'))
for cls in sorted(config.get('class_map', {}).keys()):
    print(cls)
" > mapped-classes.txt

# Find unmapped classes
comm -23 source-classes.txt mapped-classes.txt
```

Any unmapped classes should be either:
- Added to the mapping
- Added to `remove_elements` if they belong to unwanted sections
- Confirmed as irrelevant (framework internals, analytics hooks, etc.)

### Visual Validation

After applying the mapping, compare every page against the target site screenshots:

```bash
python scripts/visual-diff.py \
  --original screenshots/target/ \
  --clone screenshots/clone/ \
  --output diff-report/ \
  --threshold 95
```

Pages below the similarity threshold likely have class mapping gaps. Check the diff images for patterns:
- **Missing backgrounds**: A component class was not mapped
- **Wrong fonts**: The content wrapper class was not mapped (inherits font styles)
- **Broken layout**: Float/alignment classes were not mapped
- **Unstyled lists**: List class (`.fa-ul`) was not mapped

### Automated QA

Run the QA checker to catch structural issues caused by incorrect mapping:

```bash
python scripts/qa-check.py --pages pages/ --checklist checklists/qa-checklist.md
```

Key checks for class mapping:
- Content wrapper class matches target site
- No inline `<style>` tags (all styling via shared CSS with correct classes)
- All images use the correct alignment classes
- CTA buttons have the correct class for styling

## Real-World Example: VE Chiropractic

The VanEveryChiropractic.com project cloned 32 condition pages from a Vortala CMS site. Here is the actual class mapping used.

### Source Site (Vortala CMS)

The content area used these classes:

| Class | Purpose | CSS Properties |
|---|---|---|
| `.entry-content.cf` | Content wrapper | max-width, clearfix |
| `.bldr_callout` | Italic pull-quote | font-style: italic, border-left: 3px solid #999 |
| `.bldr_notebox` | Gray CTA box | background: #f1f1f1, border-radius: 8px |
| `.bldr_cta` | Pink CTA button | background: #ed247c, color: #fff |
| `.rounded` | Image border-radius | border-radius: 8px |
| `.alignright` | Float right | float: right, margin: 0 0 10px 20px |
| `.fa-ul` | Gold bullet list | list-style: none, custom markers |
| `.bldr_divider` | Decorative divider | display: block, margin: 20px auto |
| `.column.one_half` | 50% column | width: 48%, float: left |
| `.bordered-section` | Bordered block | border: 1px solid #ddd, padding: 15px |

### Mapping Applied

Since the source content was scraped directly from the target site, most classes were already correct. The mapping focused on:

1. Ensuring the page shell (`#containing_wrap > #wrap > #container_wrap > #container > #content`) was reproduced exactly
2. Cleaning up scraped artifacts (duplicate classes, empty spans, stray scripts)
3. Standardizing image paths to relative (`../images/`)
4. Adding missing components (dividers, taglines) that were outside the scraped content area

### Subset CSS

The original Vortala CSS was 3000+ lines. The subset for condition pages was approximately 200 lines, containing only the rules for the classes listed above plus typography, color, and spacing defaults.

## Next Step

With class mappings documented and applied, proceed to [Phase 4: Convert & Refine](04-convert-and-refine.md) for multi-pass HTML conversion, or directly to [Phase 5: Validate](05-validate.md) if pages are already converted.
