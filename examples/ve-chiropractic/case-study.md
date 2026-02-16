# Case Study: VanEvery Chiropractic Condition Pages

## Project Overview

**Client:** VanEvery Family Chiropractic (Royal Oak, MI)
**Objective:** Clone 44 condition education pages from VanEveryChiropractic.com and produce 32 standalone HTML files ready for CMS integration on a new platform.
**Source:** Vortala-hosted chiropractic website with JS-rendered content behind a proprietary CMS.

## The Challenge

VanEvery Chiropractic needed to migrate condition-specific educational pages out of their Vortala CMS. The content was:

- **JS-rendered**: Pages loaded empty HTML shells, with content injected via JavaScript after page load. Standard HTTP requests returned blank pages.
- **CSS on a CDN**: Styles were served from `doc.vortala.com` via a hashed, concatenated CSS file (729KB) rather than inline or page-level stylesheets.
- **Template-driven**: All 44 pages shared the same CMS template but with varying content structures (some had columns, callouts, image galleries; others were simple text).
- **Not directly downloadable**: Right-click "Save As" produced broken pages with missing assets and broken paths.

## Approach

### Phase 1: Reconnaissance and Asset Extraction

1. **Playwright scraping** with `networkidle` wait strategy to capture fully-rendered page content. Each page was loaded in a headless Chromium browser, waited for all network requests to settle, then the DOM was extracted.

2. **CSS extraction** from the Vortala CDN. The full 729KB stylesheet was downloaded and analyzed to identify which classes were actually used across the 44 pages. A focused subset was created covering only the relevant component styles.

3. **Asset collection**: Logos, favicons, decorative divider images, and other shared assets were downloaded and organized into a local `images/` directory.

4. **Reference screenshots** captured at desktop viewport width for visual comparison during development.

### Phase 2: Content Analysis and Consolidation

The 44 original pages were analyzed for overlap and redundancy:

- Several conditions had duplicate pages with slightly different titles
- Some topics were closely related and better served as a single comprehensive page
- Content quality varied; some pages were thin while others were substantial

**Decision: Merge 44 pages into 32** (31 condition pages + 1 index page), combining related topics and eliminating redundancy while preserving all unique educational content.

### Phase 3: Conversion Pipeline

A Python conversion script (`convert-to-ve-layout.py`) was built using BeautifulSoup to process each page through multiple passes:

1. **Structure pass**: Extract the `.entry-content` div, strip CMS wrapper elements (nav, footer, sidebar, script tags)
2. **Class mapping pass**: Map Vortala's CSS classes to our defined component classes (`.bldr_callout`, `.bldr_notebox`, `.bldr_cta`, etc.)
3. **Asset path pass**: Rewrite all image `src` attributes to use relative paths pointing to the local `images/` directory
4. **Content cleanup pass**: Remove empty elements, fix malformed HTML, normalize whitespace
5. **Template wrapping pass**: Wrap cleaned content in the standard page shell (head with CSS/favicon links, body wrapper divs, Schema.org JSON-LD)

### Phase 4: Styling and Fidelity

Rather than using the full 729KB Vortala stylesheet, a focused `ve-conditions.css` was created containing only the styles needed for the condition pages. Key design tokens extracted:

| Element | Value |
|---------|-------|
| Heading font | Playfair Display (serif) |
| Body font | Mulish (sans-serif) |
| Heading color | #333 |
| CTA button | #ed247c background, #fff text |
| CTA hover | #feb506 background, #333 text |
| Callout | italic, #444, border-left 3px solid #999 |
| Content max-width | 960px |
| Hero image | 425x425px, border-radius 50% (circular) |

### Phase 5: Quality Assurance

Each page was verified against the QA checklist:
- No inline styles (all CSS class-based)
- No emojis in content
- No CMS artifacts (nav, footer, script tags)
- CSS and favicon links present
- Schema.org MedicalWebPage JSON-LD present
- Single H1 per page
- CTA buttons linking to `/contact-us/`
- Decorative divider and bottom tagline present

## Key Decisions

### Placeholder hero images
Rather than sourcing condition-specific stock photos for all 32 pages (which would slow iteration and require licensing), a single 400x400 SVG placeholder was used. The web team can swap in final images during CMS integration. This kept the focus on content accuracy and layout fidelity.

### Full CSS as reference, subset for production
The complete Vortala CSS was kept in `ve-mirror/` for reference, but a clean subset was written for the actual pages. This reduced stylesheet size by ~95% and made the CSS maintainable and understandable.

### Schema.org MedicalWebPage markup
Each page includes structured data with the condition name, provider information, and content classification. This supports SEO for the health/medical content vertical.

### Page shell wrapping structure
Pages use a specific nesting structure (`#containing_wrap > #wrap > #container_wrap > #container > #content > .entry-content`) that matches VE's CMS layout. The web team extracts just the `.entry-content` div when importing into the new CMS, but the full shell allows standalone preview in a browser.

## Results

- **32 production-ready HTML pages** matching the VanEvery site design
- **1 shared CSS file** (focused subset of original Vortala styles)
- **All educational content preserved** from the original 44 pages
- **Portable and self-contained**: Pages work when opened directly in a browser or imported into a CMS
- **Clean handoff**: Web team can extract `.entry-content` div directly for CMS integration

## Lessons Learned

Detailed lessons are documented in [lessons-from-ve-project.md](../../playbook/lessons-from-ve-project.md). Key takeaways:

1. **Always use `networkidle` wait** when scraping CMS-hosted sites. DOMContentLoaded fires before JS injects the actual content.
2. **Extract the CSS source URL first**, before writing any scraping code. The stylesheet location tells you a lot about the site's architecture.
3. **Merge similar pages early**. Discovered during content review that many pages had overlapping content. Consolidating early saved duplicate work.
4. **Placeholder images accelerate iteration**. Don't block layout work on final image assets.
5. **Keep the full original CSS** even if you create a subset. You'll reference it repeatedly when debugging visual differences.
6. **Multi-pass processing is cleaner than single-pass**. Each pass has a single responsibility, making bugs easier to isolate and fix.
7. **Screenshot comparison is essential**. Side-by-side reference screenshots caught spacing and typography issues that code review missed.

## Timeline

The project was completed iteratively across multiple Claude Code sessions:

1. **Session 1**: Reconnaissance, asset extraction, initial scraping
2. **Session 2**: Conversion script development, first batch of pages
3. **Session 3**: Refinement of CSS classes, component styling
4. **Session 4**: Remaining pages, content consolidation (44 to 32)
5. **Session 5**: QA pass, Schema.org markup, final cleanup

## Tools Used

- **Claude Code** with Playwright MCP for browser automation
- **Python 3** with BeautifulSoup for HTML parsing and transformation
- **CSS analysis** via browser DevTools and manual extraction
- **Git** for version control and iterative development
