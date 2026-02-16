# Website Cloning Toolkit

A repeatable, AI-assisted workflow for cloning any website's design system and producing pixel-accurate HTML/CSS reproductions. Built for use with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and refined through a real-world project cloning 32 pages from VanEveryChiropractic.com.

## Features

- **5-phase playbook**: Capture, Extract, Generate, Refine, Validate -- each phase has a dedicated guide in `playbook/`
- **Python CLI scripts**: Mirror sites, capture screenshots, extract CSS, convert HTML, and run QA checks
- **MCP server integration**: Optional Playwright and Firecrawl MCP configs for faster scraping and screenshot capture
- **Class mapping system**: Structured approach to documenting source-to-target CSS class translations
- **Automated QA**: Checklist-driven validation that catches missing assets, broken links, and structural issues
- **Claude Code native**: The `CLAUDE.md` file teaches Claude Code to execute the full workflow autonomously when given a URL

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- A modern browser (for Playwright-based screenshots)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (recommended)

### Install

```bash
git clone https://github.com/drzachconner/website-cloning-toolkit.git
cd website-cloning-toolkit
pip install -r scripts/requirements.txt
playwright install chromium
```

### Basic Usage

**With Claude Code** (recommended):

1. Open the project in Claude Code
2. Tell Claude: *"Clone the design of https://example.com/page"*
3. Claude reads `CLAUDE.md` and follows the 5-phase workflow automatically

**Manual workflow**:

```bash
# 1. Capture: mirror the target site
python scripts/mirror_site.py --url "https://example.com" --output mirror/

# 2. Capture: take reference screenshots
python scripts/screenshot_pages.py --url "https://example.com/page" --output screenshots/

# 3. Extract: pull out the CSS design system
python scripts/extract_css.py --url "https://example.com" --output css/cloned-styles.css
python scripts/extract_design_system.py --css css/cloned-styles.css --output design-system.json

# 4. Convert: transform source HTML to target layout
python scripts/convert_html.py --input archive/ --template templates/page-template.html --output pages/

# 5. Validate: run QA checks
python scripts/qa_check.py --pages pages/
```

## Directory Structure

```
website-cloning-toolkit/
  CLAUDE.md                      # Claude Code instructions (start here)
  README.md                      # This file
  LICENSE                        # MIT License

  playbook/                      # Step-by-step phase guides
    01-capture.md
    02-extract-design-system.md
    03-generate-code.md
    04-convert-refine.md
    05-validate.md
    06-class-mapping.md
    07-lessons-learned.md

  scripts/                       # Python CLI tools
    requirements.txt
    mirror_site.py
    screenshot_pages.py
    extract_css.py
    extract_design_system.py
    convert_html.py
    qa_check.py

  templates/                     # Starter project templates
    static-site/                 # Plain HTML/CSS clone
    react-clone/                 # React/Next.js clone

  checklists/                    # QA and process checklists
    qa-checklist.md
    pre-launch.md

  mcp-config/                    # MCP server configurations
    playwright.json
    firecrawl.json

  examples/                      # Real-world case studies
    ve-chiropractic/             # VanEveryChiropractic.com (32 pages)
```

## Playbook Overview

The playbook is the heart of the toolkit. Each phase builds on the previous one.

| Phase | Guide | What It Does |
|---|---|---|
| 1 | [Capture](playbook/01-capture.md) | Mirror the target site's HTML, CSS, images, and screenshots |
| 2 | [Extract Design System](playbook/02-extract-design-system.md) | Parse CSS into colors, fonts, spacing, and component classes |
| 3 | [Generate Code](playbook/03-generate-code.md) | Produce initial HTML using the extracted design system |
| 4 | [Convert & Refine](playbook/04-convert-refine.md) | Multi-pass refinement until pixel-perfect |
| 5 | [Validate](playbook/05-validate.md) | Automated QA checks and visual comparison |
| -- | [Class Mapping](playbook/06-class-mapping.md) | How to document source-to-target class translations |
| -- | [Lessons Learned](playbook/07-lessons-learned.md) | Hard-won wisdom from real cloning projects |

## Scripts Reference

| Script | Purpose | Key Flags |
|---|---|---|
| `mirror_site.py` | Download site HTML and static assets | `--url`, `--output`, `--depth` |
| `screenshot_pages.py` | Capture full-page screenshots via Playwright | `--url`, `--output`, `--width` |
| `extract_css.py` | Download and subset a site's CSS | `--url`, `--output`, `--selectors` |
| `extract_design_system.py` | Parse CSS into structured design tokens | `--css`, `--output` |
| `convert_html.py` | Batch-convert HTML with class mapping | `--input`, `--template`, `--output`, `--class-map` |
| `qa_check.py` | Automated QA against checklist | `--pages`, `--checklist`, `--fix` |

See `CLAUDE.md` for detailed usage examples of each script.

## MCP Server Recommendations

For faster and more reliable operations, configure these MCP servers in Claude Code:

| Server | Best For | Config |
|---|---|---|
| **Playwright MCP** | Screenshots, JS-rendered pages, visual testing | `mcp-config/playwright.json` |
| **Firecrawl MCP** | Bulk site crawling, clean HTML extraction | `mcp-config/firecrawl.json` |

MCP servers are optional. The Python scripts handle the same tasks without MCP, just with more manual setup.

## Case Study: VanEveryChiropractic.com

The `examples/ve-chiropractic/` directory contains artifacts from the project that inspired this toolkit:

- Cloned 32 condition pages matching the original site's layout exactly
- Extracted a 729KB production CSS file down to a focused subset
- Used multi-pass HTML conversion with BeautifulSoup
- Produced pages that work standalone or drop directly into the site's CMS

See the [VE Conditions Pages repo](https://github.com/drzachconner/Conditions-HTML-Pages-from-VE-to-Repurpose) for the full project.

## License

MIT License. See [LICENSE](LICENSE) for details.
