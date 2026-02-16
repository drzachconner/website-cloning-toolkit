# Lessons from the VE Project

Raw lessons learned from cloning VanEveryChiropractic.com -- a project that converted 44 original condition pages into 32 production-ready HTML files matching the source site's visual identity.

These lessons informed every phase of the [5-phase methodology](00-overview.md).

## Project Summary

- **Source site:** VanEveryChiropractic.com (Vortala CMS platform)
- **Goal:** Create standalone HTML pages for 32 chiropractic conditions that visually match the existing site
- **Input:** 44 original VEFC_*.html files + live site scraping
- **Output:** 32 final pages in `conditions/` directory, shared CSS, placeholder images
- **CSS source:** `doc.vortala.com/childsites/static/3035/_style-1770742603.css`
- **Fonts:** Playfair Display (headings) + Mulish (body) via Google Fonts
- **Key tools:** Playwright, BeautifulSoup, SiteSucker, Claude Code

## Capture Lessons

### Two-phase scraping is essential

The first scrape (`scrape-ve-pages.py`) used a list of 72 guessed URL slugs and found content on about 44 of them. But a second pass (`scrape-ve-pages-2.py`) using slugs discovered from the sitemap found 23 additional pages with different URL patterns (e.g., `scoliosis-treatment-in-royal-oak` instead of `scoliosis-treatment`).

**Takeaway:** Always check the sitemap after your initial scrape. Sites often have more pages than their navigation reveals, especially when pages have been added over years by different content authors.

### Playwright was essential for JS-rendered content

The VE site runs on the Vortala CMS platform, which renders page content via JavaScript. A simple `requests.get()` returned an empty content div. Playwright with `wait_until="networkidle"` was required to get the actual rendered HTML.

```python
response = page.goto(url, wait_until="networkidle", timeout=15000)
content = page.evaluate("""() => {
    const el = document.querySelector('.entry-content');
    if (!el) return null;
    return el.innerHTML;
}""")
```

**Takeaway:** If `requests` or `wget` returns suspiciously short content, the site likely renders via JS. Switch to Playwright immediately rather than debugging the HTTP approach.

### SiteSucker captured the full asset tree

The initial site mirror was captured using SiteSucker (macOS app), which downloaded the complete site including CSS files hosted on the Vortala CDN (`doc.vortala.com`). This gave us the full original CSS file that became the reference for all design token extraction.

**Takeaway:** For macOS users, SiteSucker is the fastest way to get a complete mirror with all linked assets. It follows CSS and JS includes across domains.

## Design System Lessons

### Subset CSS aggressively

The original Vortala CSS file was 3000+ lines covering navigation, footer, utility bar, admin widgets, and responsive framework. The condition pages only needed about 200 lines of content-area CSS.

Classes that mattered:
- `.entry-content.cf` -- content wrapper
- `.bldr_callout` -- pull quotes
- `.bldr_notebox` -- CTA boxes
- `.bldr_cta` -- CTA buttons
- `.rounded`, `.alignright`, `.alignleft` -- image styling
- `.fa-ul` -- gold bullet lists
- `.bordered-section` -- bordered content blocks
- `.column.one_half`, `.column.two_thirds` -- layout columns

Classes we excluded:
- All `#header`, `#footer`, `#nav`, `#sidebar` rules
- Utility bar (`.utility-bar`)
- Vortala admin widgets
- Print styles
- IE compatibility hacks

**Takeaway:** Start by identifying which CSS classes actually appear in your extracted HTML content. Only include those rules. A focused 200-line CSS file is easier to maintain and debug than carrying 3000 lines of unused rules.

### Keep the full original CSS as reference

Even after creating the subset, we referenced the original file dozens of times to check spacing values, font sizes, hover states, and responsive breakpoints. The original CSS at `ve-mirror/ve-actual-styles.css` was consulted whenever something "looked off."

**Takeaway:** Never delete or modify the original CSS. Keep it in `mirror/raw-css/` as a read-only reference.

## Conversion Lessons

### Multi-pass processing beats monolithic scripts

The VE conversion used four scripts run in sequence:

1. `convert-to-ve-layout.py` -- Structural transformation (source classes -> target classes, template wrapping)
2. `fix-html-to-match-ve.py` -- Visual polish (Font Awesome icons, image structure, list conversion)
3. `fix-layout-structure.py` -- Layout fixes (column wrapping, clear floats, spacers)
4. `add-tabs-and-components.py` -- Component additions (tabbed content, bordered sections)

Each script could be re-run independently when bugs were found. When Pass 3 had a bug, we fixed it and re-ran only Pass 3 and 4, not the entire pipeline.

**Takeaway:** Keep each pass focused on one concern. Test each pass independently. Re-running a single pass is cheap; re-running everything is expensive and error-prone.

### BeautifulSoup for structure, regex for text

BeautifulSoup handled all structural HTML changes (moving elements, changing parent-child relationships, adding/removing tags). Regex handled simple text replacements within already-extracted strings (class name swaps, attribute edits).

Example of correct usage:
```python
# BeautifulSoup for structural changes
hero_img = soup.find("img", class_="ve-hero-image")
intro_p = soup.find("p")
intro_p.insert(0, hero_img)  # Move image inside paragraph

# Regex for simple text swaps
content = content.replace('class="ve-callout"', 'class="bldr_callout"')
```

Example of what NOT to do:
```python
# Never use regex to restructure HTML
content = re.sub(r'<div class="old">(.*?)</div>', r'<section>\1</section>', content)
# This breaks on nested divs, attributes with >, multiline content, etc.
```

### Content merging requires human judgment

44 original pages were consolidated into 32 because many conditions had duplicate URLs. For example:
- `sciatica` and `sciatica-treatment` had ~70% overlapping content
- `headaches-migraines` and `headaches` and `migraines` were three views of the same topic
- `prenatal` and `prenatal-chiropractic` and `pregnancy` covered related but distinct content

Automated deduplication identified the overlaps, but deciding which content to keep, which to merge, and which to discard required reading each page and making editorial decisions.

**Takeaway:** For content-heavy sites with overlapping pages, budget time for manual content review. Automation can identify duplicates, but merging is a human task.

### Archive originals before any transformation

Every conversion pass was run against the `conditions/` directory, modifying files in place. Having the originals in `archive/` (the 44 VEFC_*.html files) meant we could always diff the current state against the source to verify no content was lost.

```bash
# Compare content between original and converted
diff <(python -c "from bs4 import BeautifulSoup; print(BeautifulSoup(open('archive/VEFC_back-pain.html').read(),'html.parser').get_text())") \
     <(python -c "from bs4 import BeautifulSoup; print(BeautifulSoup(open('conditions/back-pain.html').read(),'html.parser').get_text())")
```

**Takeaway:** Always create an archive before running conversion scripts. `git commit` before each pass as well, so you have a per-pass history.

## Template Lessons

### Placeholder images save time

Instead of sourcing real images for 32 pages during development, we used a single `placeholder-square.svg` (400x400) for all hero images. This kept the focus on structural accuracy and avoided broken image links during iteration.

```html
<img class="rounded" src="../images/placeholder-square.svg"
     alt="Back pain chiropractic care" width="425" height="425">
```

**Takeaway:** Use SVG placeholders during development. Replace with real images only in the final delivery step.

### Relative paths for portability

All pages use relative paths (`../css/ve-conditions.css`, `../images/divider1.png`) rather than absolute paths. This means the pages work when:
- Opened locally in a browser from the file system
- Deployed to any subdirectory on any domain
- Previewed in GitHub Pages

**Takeaway:** Use relative paths for everything. Absolute paths (`/css/...`) break when pages are opened via `file://` protocol.

### The page shell matters

The VE site wraps all content in a specific div nesting structure:
```html
<body class="page layout-one-col">
  <div id="containing_wrap">
    <div id="wrap">
      <div id="container_wrap">
        <div id="container">
          <div id="content">
            <div class="entry-content cf">
```

The web team extracts just the `.entry-content` div for CMS integration. Including the full shell means the pages render correctly both standalone and when pasted into the CMS.

**Takeaway:** Replicate the source site's DOM nesting exactly. It often carries CSS rules that affect layout even when the classes seem like empty wrappers.

## Validation Lessons

### Screenshots are invaluable for regression testing

After each conversion pass, taking fresh screenshots and comparing them against the originals caught issues that code review missed: wrong font sizes, missing margins, misaligned columns.

**Takeaway:** Screenshot after every pass. Visual comparison catches what code diffing cannot.

### Schema.org markup for SEO parity

Each condition page includes `MedicalWebPage` Schema.org JSON-LD to maintain the SEO signals the original pages had. This was not visible to users but important for search engine equivalence.

**Takeaway:** Clone the original site's structured data, not just its visual design. Check for JSON-LD, Open Graph tags, and meta descriptions.

## Summary of Patterns

| Pattern | Lesson |
|---------|--------|
| Two-phase URL discovery | Always check sitemap after initial scrape |
| Playwright + networkidle | Required for JS-rendered CMS sites |
| CSS subsetting | Extract only content-area classes |
| Multi-pass scripts | One concern per script, independently re-runnable |
| BeautifulSoup + regex | BS for structure, regex for text only |
| Archive originals | Before any transformation, always |
| Placeholder images | SVG placeholders during development |
| Relative paths | Portability across environments |
| Human content merge | Automation finds duplicates, humans decide |
| Screenshot regression | After every pass, compare visually |
| Schema.org parity | Clone structured data alongside visual design |

## Project Stats

| Metric | Value |
|--------|-------|
| Original pages scraped | 44 |
| Final pages delivered | 32 (31 conditions + 1 index) |
| Conversion scripts written | 4 |
| Scrape scripts written | 2 |
| CSS lines (original) | ~3000 |
| CSS lines (subset) | ~200 |
| Fonts used | 2 (Playfair Display, Mulish) |
| Colors in palette | 8 primary values |
