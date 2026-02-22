# Website Cloning Methodology: Overview

A 5-phase approach for replicating the design system, layout, and content structure of an existing website into standalone, portable HTML pages.

This methodology was developed and refined during the [VanEveryChiropractic.com project](lessons-from-ve-project.md), where 44 original condition pages were consolidated into 32 production-ready HTML pages that matched the source site's visual identity.

## The 5 Phases

```
 Phase 1          Phase 2              Phase 3            Phase 4             Phase 5
+----------+    +------------------+  +---------------+  +-----------------+  +-----------+
| CAPTURE  | -> | EXTRACT DESIGN   | -> | GENERATE    | -> | CONVERT &     | -> | VALIDATE |
|          |    | SYSTEM           |  | CODE          |  | REFINE          |  |           |
+----------+    +------------------+  +---------------+  +-----------------+  +-----------+
| Scrape   |    | CSS classes      |  | Screenshot-   |  | Multi-pass      |  | Visual    |
| HTML     |    | Fonts            |  | to-code       |  | HTML transform  |  | diff      |
| Screen-  |    | Colors           |  | AI generation |  | Class mapping   |  | Responsive|
| shots    |    | Spacing/grid     |  | Manual build  |  | Content merge   |  | testing   |
| Assets   |    | Layout patterns  |  |               |  | Metadata        |  | QA check  |
+----------+    +------------------+  +---------------+  +-----------------+  +-----------+
     |                |                      |                   |                   |
     v                v                      v                   v                   v
  mirror/        design-tokens/         templates/          conditions/         report/
  extracted/     reference-css/         drafts/             final HTML          diffs/
  screenshots/                                             archive/
```

## Phase Summaries

### Phase 1: Capture ([01-capture.md](01-capture.md))

Scrape the target site to collect raw HTML, screenshots, and static assets. Use Playwright for JS-rendered content, HTTrack/wget for full mirrors, and Firecrawl for sites that block scrapers. Organize everything into a `mirror/` directory.

**Key output:** `mirror/extracted/` (raw HTML), `mirror/screenshots/`, `mirror/raw-css/`

### Phase 2: Extract Design System ([02-extract-design-system.md](02-extract-design-system.md))

Analyze the captured site to identify CSS classes, fonts, colors, spacing, and layout grid. Use browser extensions (SnipCSS, CSS Peeper) and extraction scripts. Keep the full original CSS as a reference alongside your subset.

**Key output:** Design tokens (fonts, colors, spacing), class inventory, reference CSS file

### Phase 3: Generate Code ([03-generate-code.md](03-generate-code.md))

Produce initial HTML/CSS that matches the target design. Choose between AI platforms (v0.dev, Bolt.new), screenshot-to-code tools, or direct Claude Code generation depending on site complexity.

**Key output:** Template HTML files, shared CSS stylesheet

### Phase 4: Convert & Refine ([04-convert-and-refine.md](04-convert-and-refine.md))

Transform raw or draft HTML into production pages through multi-pass scripts. Map source classes to target classes, preserve metadata (title, description, Schema.org), and auto-generate repeated elements like CTAs and footers.

**Key output:** Final HTML pages in `conditions/` (or equivalent), archived originals

### Phase 5: Validate ([05-validate.md](05-validate.md))

Verify visual fidelity through screenshot comparison, responsive testing at key breakpoints, CSS class audits, and font/color accuracy checks. Run Lighthouse for performance parity.

**Key output:** Visual diff report, QA checklist results

## When to Use Each Approach

| Scenario | Recommended Path |
|----------|-----------------|
| Static marketing site, few pages | Phase 1 -> 2 -> 3 (AI generate) -> 5 |
| JS-heavy SPA | Phase 1 (Playwright) -> 2 -> 3 (manual) -> 4 -> 5 |
| Large batch of similar pages | Phase 1 -> 2 -> 3 (template) -> 4 (batch scripts) -> 5 |
| CMS-hosted site with restricted access | Phase 1 (Firecrawl) -> 2 -> 3 -> 4 -> 5 |
| Quick one-off page clone | Phase 1 -> 3 (screenshot-to-code) -> 5 |

## Directory Structure

A cloned site project should follow this layout:

```
project-root/
  mirror/                     # Phase 1 output
    extracted/                # Raw HTML fragments
    screenshots/              # Full-page screenshots
    raw-css/                  # Original stylesheets
    sitemap.json              # Discovered URLs
  css/                        # Phase 2-3 output
    site-clone.css            # Your subset/adapted CSS
  images/                     # Shared assets
    placeholder-square.svg    # Dev placeholders
    logo.png
    favicon.png
  templates/                  # Phase 3 output
    page-template.html        # Reference template
  conditions/                 # Phase 4 output (or pages/, etc.)
    page-one.html
    page-two.html
    index.html
  archive/                    # Originals before transformation
  scripts/                    # Conversion and utility scripts
    scrape-site.py
    convert-html.py
    visual-diff.py
  docs/
    PRD.md                    # Project requirements
    design-tokens.md          # Extracted design system
```

## Quick-Start Checklist

1. [ ] Set up project directory structure (see above)
2. [ ] Capture target site with Playwright or HTTrack ([Phase 1](01-capture.md))
3. [ ] Screenshot every target page for reference
4. [ ] Extract CSS classes, fonts, and colors ([Phase 2](02-extract-design-system.md))
5. [ ] Generate initial HTML templates ([Phase 3](03-generate-code.md))
6. [ ] Run batch conversion scripts ([Phase 4](04-convert-and-refine.md))
7. [ ] Validate against original screenshots ([Phase 5](05-validate.md))
8. [ ] Archive originals and commit final pages

## Lessons Learned

See [lessons-from-ve-project.md](lessons-from-ve-project.md) for a detailed retrospective from the VanEveryChiropractic.com cloning project, including pitfalls, time-savers, and patterns that emerged across all five phases.
