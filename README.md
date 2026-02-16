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
# 1. Capture: scrape the target site with screenshots
python scripts/scrape-site.py --url "https://example.com" --output mirror/ --screenshots --sitemap

# 2. Extract: pull out the CSS design system
python scripts/extract-css.py --url "https://example.com" --output css/cloned-styles.css
python scripts/extract-design-system.py --css css/cloned-styles.css --output design-system.json

# 3. Convert: transform source HTML to target layout
python scripts/convert-html.py --input archive/ --output pages/ --config class-mapping.json --template templates/page-template.html

# 4. Validate: run QA checks
python scripts/qa-check.py --pages pages/
```

## Directory Structure

```
website-cloning-toolkit/
  CLAUDE.md                      # Claude Code instructions (start here)
  README.md                      # This file
  LICENSE                        # MIT License

  playbook/                      # Step-by-step phase guides
    00-overview.md
    01-capture.md
    02-extract-design-system.md
    03-generate-code.md
    04-convert-and-refine.md
    05-validate.md
    06-class-mapping.md
    08-spa-handling.md
    lessons-from-ve-project.md

  scripts/                       # Python CLI tools
    requirements.txt
    scrape-site.py
    extract-css.py
    extract-colors.py
    extract-fonts.py
    extract-design-system.py
    convert-html.py
    visual-diff.py
    qa-check.py
    a11y-check.py
    run-pipeline.py

  templates/                     # Starter project templates
    static-site/                 # Plain HTML/CSS clone
    react-clone/                 # React/Next.js clone

  checklists/                    # QA and process checklists
    qa-checklist.md
    fidelity-checklist.md
    pre-clone-checklist.md

  mcp-config/                    # MCP server configurations
    claude-mcp-settings.json
    recommended-servers.md
    setup-mcp.sh

  examples/                      # Real-world case studies
    ve-chiropractic/             # VanEveryChiropractic.com (32 pages)
```

## Playbook Overview

The playbook is the heart of the toolkit. Each phase builds on the previous one.

| Phase | Guide | What It Does |
|---|---|---|
| 1 | [Capture](playbook/01-capture.md) | Scrape the target site's HTML, CSS, images, and screenshots |
| 2 | [Extract Design System](playbook/02-extract-design-system.md) | Parse CSS into colors, fonts, spacing, and component classes |
| 3 | [Generate Code](playbook/03-generate-code.md) | Produce initial HTML using the extracted design system |
| 4 | [Convert & Refine](playbook/04-convert-and-refine.md) | Multi-pass refinement until pixel-perfect |
| 5 | [Validate](playbook/05-validate.md) | Automated QA checks and visual comparison |
| -- | [Class Mapping](playbook/06-class-mapping.md) | How to document source-to-target class translations |
| -- | [Lessons Learned](playbook/lessons-from-ve-project.md) | Hard-won wisdom from real cloning projects |

## Scripts Reference

| Script | Purpose | Key Flags |
|---|---|---|
| `scrape-site.py` | Scrape site HTML and optional screenshots | `--url`, `--urls-file`, `--output`, `--sitemap`, `--screenshots`, `--selector` |
| `extract-css.py` | Download and subset a site's CSS | `--url`, `--output`, `--subset`, `--html-dir` |
| `extract-colors.py` | Extract color values from CSS | `--css`, `--output` |
| `extract-fonts.py` | Extract font information from a site | `--url`, `--output` |
| `extract-design-system.py` | Parse CSS into structured design tokens | `--css`, `--output` |
| `convert-html.py` | Batch-convert HTML with class mapping | `--input`, `--output`, `--config`, `--template` |
| `visual-diff.py` | Compare screenshots and generate diff report | `--original`, `--clone`, `--output`, `--threshold` |
| `qa-check.py` | Automated QA against checklist | `--pages`, `--checklist`, `--fix` |

See `CLAUDE.md` for detailed usage examples of each script.

## MCP Server Recommendations

For faster and more reliable operations, configure these MCP servers in Claude Code:

| Server | Best For | Config |
|---|---|---|
| **Playwright MCP** | Screenshots, JS-rendered pages, visual testing | `mcp-config/claude-mcp-settings.json` |
| **Firecrawl MCP** | Bulk site crawling, clean HTML extraction | `mcp-config/claude-mcp-settings.json` |

See `mcp-config/recommended-servers.md` for setup guidance and `mcp-config/setup-mcp.sh` for automated installation.

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
