# Website Cloning Toolkit - Claude Code Configuration

## Project Overview

This toolkit provides a repeatable, AI-assisted workflow for cloning any website's design system and producing pixel-accurate HTML/CSS reproductions. Given a target URL, Claude Code follows a 5-phase process: capture the site, extract its design system, generate initial code, refine through multi-pass conversion, and validate the output against the original.

The toolkit was built from hard-won lessons cloning VanEveryChiropractic.com's condition pages (32 HTML files matching the original site's layout exactly). Those patterns are encoded here so any website can be cloned with the same rigor.

## Website Cloning Workflow

### Phase 1: Capture

**Goal**: Scrape the target site's HTML, CSS, images, and fonts. Take full-page screenshots for visual reference.

**Steps**:
1. Create a project directory: `mkdir -p project-name/{mirror,screenshots,archive,css,images,pages,templates}`
2. Mirror the target site's HTML and assets:
   ```bash
   python scripts/mirror_site.py --url "https://example.com" --output mirror/
   ```
3. Capture full-page screenshots of key pages:
   ```bash
   python scripts/screenshot_pages.py --url "https://example.com/page" --output screenshots/
   ```
4. Download the site's CSS files for analysis:
   ```bash
   python scripts/extract_css.py --url "https://example.com" --output mirror/css/
   ```

**Key lesson**: Screenshots are invaluable. They serve as the ground truth throughout every subsequent phase. Always capture them before doing anything else.

**MCP option**: If Playwright MCP or Firecrawl MCP is available, use them instead of the Python scripts for faster, more reliable scraping. See the MCP Servers section below.

### Phase 2: Extract Design System

**Goal**: Analyze the captured CSS to extract colors, fonts, spacing, component patterns, and class names into a structured design-system document.

**Steps**:
1. Parse the site's CSS to extract design tokens:
   ```bash
   python scripts/extract_design_system.py --css mirror/css/style.css --output design-system.json
   ```
2. Document the design system in CLAUDE.md (or a project-specific config) with these sections:
   - **Colors**: All hex values with their usage context (headings, body, links, hover states, backgrounds, borders)
   - **Typography**: Font families, weights, sizes for each heading level and body text
   - **Spacing**: Margins, padding, max-width, line-height
   - **Components**: Each reusable CSS class with its visual purpose (callouts, CTAs, cards, dividers, etc.)
   - **Layout**: Grid/column system, content width, responsive breakpoints

3. Create a class mapping table documenting source site classes and their purposes:

   | Source Class | Purpose | CSS Properties |
   |---|---|---|
   | `.entry-content` | Main content wrapper | max-width, margin auto |
   | `.bldr_callout` | Pull-quote callout | italic, border-left |
   | `.bldr_cta` | CTA button | bg color, text color, hover |

**Key lesson**: Subset the CSS aggressively. A production site's CSS may be 500KB+. Extract only the rules that apply to the pages you are cloning. A 5-10KB subset CSS file is typical.

### Phase 3: Generate Code

**Goal**: Produce initial HTML files that use the extracted design system.

**Approaches (choose one)**:

**A. Screenshot-to-code (AI-assisted)**:
- Feed screenshots to an AI code generator (Claude, screenshot-to-code tools, etc.)
- Use the design system document as context so the AI uses the correct class names
- This gives you a rough first draft quickly

**B. Manual template construction**:
- Build one reference template by hand using the extracted CSS classes
- Save it in `templates/` as the canonical structure
- Use the template as the basis for all pages

**C. Conversion from existing content**:
- If you have existing HTML content (like CMS exports), write a conversion script
- Map old classes to new classes programmatically
- See `scripts/convert_html.py` for the pattern

**Steps**:
1. Create a reference template: `templates/page-template.html`
2. Validate the template against screenshots visually
3. Generate pages from the template, either manually or via script:
   ```bash
   python scripts/convert_html.py --input archive/ --template templates/page-template.html --output pages/
   ```

**Key lesson**: Multi-pass conversion beats monolithic transformation. Do not try to convert everything in a single script run. Instead: rough structure first, then class mapping, then content refinement, then QA fixes.

### Phase 4: Convert & Refine

**Goal**: Iteratively improve the generated HTML until it matches the original site pixel-for-pixel.

**Steps**:
1. **Pass 1 - Structure**: Ensure every page has the correct wrapper elements, heading hierarchy, and section order
2. **Pass 2 - Class mapping**: Replace all placeholder/generic classes with the target site's actual class names
3. **Pass 3 - Content**: Verify all text content is preserved and correctly placed
4. **Pass 4 - Assets**: Confirm all images, icons, and decorative elements are referenced correctly with relative paths
5. **Pass 5 - Polish**: Fix spacing, alignment, and any visual discrepancies found during screenshot comparison

Run the visual diff tool after each pass:
```bash
python scripts/visual_diff.py --original screenshots/page.png --clone pages/page.html --output diff-report/
```

**Key lesson**: Each pass should have a single focus. Trying to fix structure, classes, and content simultaneously leads to regressions.

### Phase 5: Validate

**Goal**: Confirm every page passes the QA checklist and matches the original site visually.

**Steps**:
1. Run the automated QA checker:
   ```bash
   python scripts/qa_check.py --pages pages/ --checklist checklists/qa-checklist.md
   ```
2. Visually compare each page against the original screenshots
3. Walk through the QA checklist manually for edge cases

**QA checklist** (customize per project in `checklists/qa-checklist.md`):
- [ ] No inline `<style>` tags (all styling via shared CSS)
- [ ] External CSS link present on every page
- [ ] Favicon link present on every page
- [ ] Exactly one `<h1>` per page
- [ ] All images use relative paths
- [ ] All links point to correct destinations
- [ ] Content wrapper class matches target site
- [ ] No leftover placeholder text
- [ ] All original content preserved (nothing dropped during conversion)
- [ ] Schema.org structured data present (if applicable)
- [ ] Page renders correctly at target site's max-width
- [ ] No console errors when opened in browser

## MCP Servers

Use MCP (Model Context Protocol) servers when available for faster, more reliable operations.

### Playwright MCP
**When to use**: Screenshots, interactive page scraping, pages that require JavaScript rendering, visual regression testing.
```json
// mcp-config/playwright.json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@anthropic/mcp-playwright"]
    }
  }
}
```
**Capabilities**: Navigate pages, take screenshots, extract rendered HTML (post-JS), interact with elements, wait for dynamic content.

### Firecrawl MCP
**When to use**: Bulk site scraping, extracting clean HTML/markdown from multiple pages, crawling entire site sections.
```json
// mcp-config/firecrawl.json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": { "FIRECRAWL_API_KEY": "<your-key>" }
    }
  }
}
```
**Capabilities**: Crawl entire sites, extract structured content, handle anti-bot measures, return clean markdown.

### Screenshot MCP (or similar)
**When to use**: Automated visual comparison between original site and cloned pages, generating diff reports.

### When to use scripts vs. MCP
| Task | Use Script | Use MCP |
|---|---|---|
| Simple static HTML download | `mirror_site.py` | -- |
| JS-rendered pages | -- | Playwright |
| Full-site crawl (50+ pages) | -- | Firecrawl |
| Screenshots for reference | `screenshot_pages.py` | Playwright |
| CSS extraction | `extract_css.py` | -- |
| Visual diff | `visual_diff.py` | Screenshot MCP |

## Script Usage

All scripts are in `scripts/` and require Python 3.10+. Install dependencies first:
```bash
pip install -r scripts/requirements.txt
```

### mirror_site.py
Download a site's HTML and static assets.
```bash
python scripts/mirror_site.py --url "https://example.com" --output mirror/ --depth 2
```
- `--url`: Target site URL (required)
- `--output`: Output directory (default: `mirror/`)
- `--depth`: Crawl depth for following links (default: 1)
- `--assets`: Also download CSS, JS, images (default: true)

### screenshot_pages.py
Capture full-page screenshots using Playwright.
```bash
python scripts/screenshot_pages.py --url "https://example.com/page" --output screenshots/ --width 1440
```
- `--url`: Page URL or file with URLs (one per line)
- `--output`: Screenshot output directory
- `--width`: Viewport width in pixels (default: 1440)
- `--full-page`: Capture full scrollable page (default: true)

### extract_css.py
Download and subset a site's CSS.
```bash
python scripts/extract_css.py --url "https://example.com" --output css/cloned-styles.css --selectors ".entry-content,.bldr_callout,.bldr_cta"
```
- `--url`: Target site URL (required)
- `--output`: Output CSS file path
- `--selectors`: Comma-separated CSS selectors to keep (optional; keeps all if omitted)

### extract_design_system.py
Parse CSS into a structured design system JSON.
```bash
python scripts/extract_design_system.py --css mirror/css/style.css --output design-system.json
```
- `--css`: Path to CSS file to analyze (required)
- `--output`: Output JSON file path

### convert_html.py
Batch-convert HTML files using class mapping and template structure.
```bash
python scripts/convert_html.py --input archive/ --template templates/page-template.html --output pages/ --class-map class-mapping.json
```
- `--input`: Directory of source HTML files (required)
- `--template`: Reference template for target structure (required)
- `--output`: Output directory for converted files
- `--class-map`: JSON file mapping old classes to new classes (optional)

### qa_check.py
Run automated QA checks against all pages.
```bash
python scripts/qa_check.py --pages pages/ --checklist checklists/qa-checklist.md
```
- `--pages`: Directory of HTML files to check (required)
- `--checklist`: Checklist file with rules (uses default if omitted)
- `--fix`: Attempt to auto-fix common issues (default: false)

## Class Mapping Patterns

Class mapping is the core technique for making cloned pages match the target site. Document mappings in a JSON file or in your project's CLAUDE.md.

### JSON Format
```json
{
  "mappings": [
    {
      "source": ".old-callout",
      "target": ".bldr_callout",
      "notes": "Italic pull-quote with left border"
    },
    {
      "source": ".old-button",
      "target": ".bldr_cta",
      "notes": "Primary CTA button, pink background"
    }
  ],
  "wrapper": {
    "source": ".page-content",
    "target": ".entry-content.cf",
    "notes": "Main content wrapper, extracted for CMS"
  }
}
```

### CLAUDE.md Format
Document mappings directly in the project's CLAUDE.md for Claude Code to reference:
```markdown
## CSS Classes (matching target site)
- `.entry-content.cf` - Main content wrapper
- `.bldr_callout` - Italic quote with left border (3px solid #999)
- `.bldr_notebox` - Gray rounded CTA box (#f1f1f1 bg)
- `.bldr_cta` - Pink CTA button (#ed247c)
```

### Mapping Discovery Process
1. Inspect the target site's HTML using browser DevTools or mirrored HTML
2. Identify every CSS class used in the content area (ignore nav/footer/framework classes)
3. For each class, document: name, visual purpose, key CSS properties
4. Map your source content's classes (or generic tags) to target classes
5. Validate by comparing rendered output against screenshots

## QA Checklist

Customize this checklist per project. Save it in `checklists/qa-checklist.md`.

### Structure
- [ ] Every page has exactly one `<h1>`
- [ ] Content wrapper uses the target site's class name
- [ ] Page shell (body class, wrapper divs) matches target site
- [ ] No orphaned closing tags or malformed HTML

### Styling
- [ ] No inline `<style>` tags -- all styles in shared external CSS
- [ ] No inline `style=""` attributes (unless matching the target site)
- [ ] External CSS `<link>` present in every page's `<head>`
- [ ] Favicon `<link>` present in every page's `<head>`

### Content
- [ ] All original text content preserved (nothing dropped)
- [ ] No placeholder or Lorem Ipsum text remaining
- [ ] Images use correct relative paths
- [ ] All internal links point to valid destinations
- [ ] CTA buttons link to the correct target (e.g., `/contact-us/`)

### Assets
- [ ] All image files exist at referenced paths
- [ ] CSS file exists at referenced path
- [ ] Favicon file exists at referenced path
- [ ] No broken asset references

### SEO & Metadata
- [ ] `<title>` tag present and descriptive
- [ ] `<meta name="description">` present
- [ ] Schema.org structured data present (if applicable)
- [ ] `lang` attribute on `<html>` tag

### Visual
- [ ] Page matches target site screenshot at full width
- [ ] Typography (fonts, sizes, weights) matches target
- [ ] Colors match target (headings, body, links, backgrounds)
- [ ] Spacing and layout match target
- [ ] Component styling matches (callouts, CTAs, cards, dividers)

## Key Lessons (from VE project)

These lessons were learned the hard way during the VanEveryChiropractic.com cloning project. They apply to any website cloning effort.

### 1. Screenshots are your ground truth
Always capture full-page screenshots of the target site before starting any work. Reference them at every phase. When in doubt about how something should look, check the screenshot -- not the CSS documentation.

### 2. Subset CSS aggressively
Production sites ship massive CSS files (500KB+). Do not use the full file. Extract only the rules that apply to the specific pages you are cloning. A 5-10KB subset is typical and much easier to maintain and debug.

### 3. Multi-pass conversion beats monolithic scripts
Never try to do everything in one script run. Break the conversion into focused passes: structure, then classes, then content, then assets, then polish. Each pass has a single concern, making bugs easy to spot and fix.

### 4. Archive originals before any transformation
Always copy original source files into an `archive/` directory before running any conversion. This gives you a clean rollback point and lets you diff against the originals to verify nothing was lost.

### 5. Use relative paths everywhere
All asset references (CSS, images, favicons) should use relative paths (`../css/style.css`, `../images/photo.jpg`). This makes pages work both as standalone files and when embedded into a CMS.

### 6. Document the class mapping thoroughly
The class mapping (source site classes to target site classes) is the most important reference document. Put it in your project's CLAUDE.md so Claude Code can reference it during every edit. Include the visual purpose and key CSS properties for each class.

### 7. Build one perfect template first
Before generating 30+ pages, get one template page pixel-perfect. Validate it against screenshots. Only then use it as the basis for batch generation. Fixing a bug in one template is much easier than fixing it across 30 files.

### 8. The content wrapper is the integration contract
Identify the target site's main content wrapper class (e.g., `.entry-content.cf`). This is the div that the web team will extract for CMS integration. Everything inside it must match the target site's structure exactly. Everything outside it is scaffolding for standalone preview.

### 9. Name files with lowercase and hyphens
Use `back-pain-neck-pain.html`, not `BackPainNeckPain.html` or `back_pain_neck_pain.html`. Lowercase with hyphens is URL-friendly and consistent.

### 10. Automate QA checks
Manual QA does not scale. Write a `qa_check.py` script that validates every page against your checklist. Run it after every batch change. Fix failures immediately before they compound.

## Project Structure

```
website-cloning-toolkit/
  CLAUDE.md                      # This file -- Claude Code instructions
  README.md                      # Project overview and quick-start
  LICENSE                        # MIT License

  playbook/                      # Step-by-step guides for each phase
    01-capture.md                # Phase 1: Site capture
    02-extract-design-system.md  # Phase 2: Design system extraction
    03-generate-code.md          # Phase 3: Initial code generation
    04-convert-refine.md         # Phase 4: Multi-pass refinement
    05-validate.md               # Phase 5: QA and validation
    06-class-mapping.md          # Class mapping reference
    07-lessons-learned.md        # Expanded lessons from real projects

  scripts/                       # Python CLI tools
    requirements.txt             # Python dependencies
    mirror_site.py               # Download site HTML + assets
    screenshot_pages.py          # Capture full-page screenshots
    extract_css.py               # Download and subset CSS
    extract_design_system.py     # Parse CSS into design tokens
    convert_html.py              # Batch HTML conversion
    qa_check.py                  # Automated QA checker

  templates/                     # Starter templates
    static-site/                 # Plain HTML/CSS template
      css/                       # Cloned stylesheet goes here
      images/                    # Cloned assets go here
    react-clone/                 # React/Next.js template
      src/                       # React components

  checklists/                    # QA and process checklists
    qa-checklist.md              # Visual and structural QA
    pre-launch.md                # Pre-delivery verification

  mcp-config/                    # MCP server configurations
    playwright.json              # Playwright MCP config
    firecrawl.json               # Firecrawl MCP config

  examples/                      # Real-world case studies
    ve-chiropractic/             # VanEveryChiropractic.com clone
```

## Git Workflow

- Commit after completing each phase or significant batch of changes
- Use descriptive commit messages: `"Phase 2: Extract VE design system (14 classes, 6 colors)"`
- Keep `archive/` in version control so originals are always recoverable
- The `mirror/`, `screenshots/`, and `diff-report/` directories are gitignored (generated artifacts)
