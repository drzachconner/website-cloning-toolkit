# Website Cloning Toolkit

Two-step pipeline for creating new chiropractic client websites. Scrapes content from a client's existing site, then copies bodymind-chiro-website and replaces the content.

## Workflow

### Step 1: Scrape the client's existing site

```bash
python scripts/scrape-client-site.py --url "https://example-chiro.com" --output client-content.json
```

Extracts business name, doctor info, services, testimonials, hours, socials, images, and contact info into a single JSON file. Downloads images to a local `images/` folder. Auto-detects Wix, Squarespace, and WordPress sites. Uses schema.org JSON-LD as primary source, falls back to HTML scraping.

### Step 2: Generate the new site

```bash
python scripts/generate-new-site.py --content client-content.json --output ./new-client-site/ --domain newclient.com
```

Copies the full bodymind-chiro-website template, generates a new `src/data/site.ts` populated with client data, auto-classifies scraped images into site slots (logo, hero, headshot, etc.), and updates `package.json`.

## Template: bodymind-chiro-website

**Location**: `/Users/zachconnermba/Code/bodymind-chiro-website/`

The template is a complete, production-ready site:
- React 18 + TypeScript + Vite 5 + Tailwind CSS 3
- React Router 7 with lazy-loaded pages
- Cloudflare Pages deployment (Pages Functions for contact form + AI chatbot)
- Full SEO: meta tags, Schema.org JSON-LD, sitemap, robots.txt
- Components: Header, Footer, Hero, CTABanner, ContactForm, ChatbotWidget

## What site.ts Drives

`src/data/site.ts` is the single source of truth for ALL content:
- Business identity (name, tagline, description, founding year)
- Doctor/practitioner (name, credentials, bio, education, expertise, certifications)
- Contact info (phone, email, address, geo coordinates)
- Business hours (display, short format, structured for schema)
- Booking system (provider, URL)
- Social media links
- Images (logo, hero, headshot, contact hero, OG image)
- Brand colors
- Services (name, description, slug, image)
- Testimonials (name, text, rating, date)
- Feature flags (talskyTonal, networkSpinal, kst, events, guides)
- Custom copy overrides (hero, about, footer)

Schema.org structured data (`src/lib/schema.ts`) is generated entirely from site.ts.

## Image Auto-Classification

The generator automatically classifies scraped images and places the best candidate in each site slot:

| Slot | Target File | Classification Heuristics |
|------|------------|--------------------------|
| `logo` | `logo.webp` | Scraper tag "logo", filename "logo"/"brand", small PNG |
| `heroFamily` | `hero-family.webp` | Scraper tag "hero", wide aspect ratio + large, filename "hero"/"banner" |
| `doctorHeadshot` | `dr-headshot.webp` | Near-square + medium size, filename "doctor"/"headshot"/"portrait" |
| `contactHero` | `contact-hero.webp` | Filename "contact"/"office", wide landscape photo |
| `ogImage` | `og-image.webp` | Copies from hero if not separately matched |
| `service-{slug}` | `{slug}.webp` | Service name matched to filename/alt text |

Runner-up candidates are saved in `public/images/alternatives/{slot}/` for easy swapping. Unclassified images go to `public/images/extras/`.

To supply additional images (e.g. professional photos not on the old site), use `--local-images`:

```bash
python scripts/generate-new-site.py --content client-content.json --output ./new-site/ --local-images ./extra-photos/
```

## After Generating

```bash
cd ./new-client-site/
npm install
# Review auto-placed images in public/images/
# Swap with alternatives from public/images/alternatives/ if needed
npm run dev        # Preview at localhost:5173
# Deploy to Cloudflare Pages when ready
```

## Script Reference

### scrape-client-site.py

| Arg | Required | Description |
|-----|----------|-------------|
| `--url` | Yes | Client's existing website URL |
| `--output` | No | Output directory (default: `./output/`) |

Outputs `client-content.json` (with image metadata dicts) and an `images/` folder containing downloaded images plus `image-manifest.json` mapping filenames to metadata (URL, alt text, context, dimensions, scraper tags).

### generate-new-site.py

| Arg | Required | Description |
|-----|----------|-------------|
| `--content` | Yes | Path to client-content.json |
| `--output` | Yes | Output directory for the new site |
| `--domain` | No | Client's domain name |
| `--local-images` | No | Directory of additional images to include in classification |

## GSD + Teams Strategy

**Project complexity**: Medium — two-step pipeline (scrape → generate)

**GSD Phase Structure**:

| Phase | Work | Team Approach |
|-------|------|---------------|
| Scraper improvements | `scrape-client-site.py` | Main agent (sequential) |
| Generator improvements | `generate-new-site.py` | Main agent (sequential) |
| New client site generation | Full pipeline run | GSD phases: scrape → generate → customize |
| Multi-client batch | Multiple sites at once | Teams: one teammate per client site |

**Context Management**:
- The two scripts are loosely coupled via `client-content.json` — safe to work on independently
- Template site (bodymind-chiro-website) is a separate repo — changes there affect ALL generated sites
- Multi-client batch work is the primary Teams use case — each teammate generates one client site
- Use `/gsd:resume-work` when resuming multi-session work

## Dependencies

```bash
pip install -r scripts/requirements.txt
playwright install chromium
```

---

## 1. Project Overview

Python-based two-step website cloning pipeline for chiropractic clients. `scrape-client-site.py` scrapes an existing client website and outputs `client-content.json` with all business data and downloaded images. `generate-new-site.py` copies the bodymind-chiro-website React/Vite/Tailwind template and injects the client data to produce a ready-to-deploy site directory. The generated site requires only image review and Cloudflare Pages deployment.

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.11+ |
| Web scraping | Playwright >=1.40.0 (headless Chromium) |
| HTML parsing | BeautifulSoup4 >=4.12.0, lxml >=4.9.0 |
| HTTP client | httpx >=0.25.0 |
| Image processing | Pillow (PIL) >=10.0.0 |
| Data interchange | JSON (`client-content.json`) |
| Template (output) | React 18 + TypeScript + Vite 5 + Tailwind CSS 3 |
| Template deployment | Cloudflare Pages |

Install all dependencies:
```bash
pip install -r scripts/requirements.txt
playwright install chromium
```

## 3. Architecture

Two-step pipeline with a JSON contract between stages:

```
Step 1: scrape-client-site.py
  Input:  --url <existing chiro site URL>
  Output: client-content.json (business data, image metadata)
          images/ (downloaded images + image-manifest.json)

Step 2: generate-new-site.py
  Input:  client-content.json + images/
  Output: new site directory (copy of bodymind-chiro-website template)
          → src/data/site.ts populated with client data
          → public/images/ with auto-classified images
          → public/images/alternatives/{slot}/ runner-ups
          → public/images/extras/ unclassified images
```

**Key design decisions:**
- `client-content.json` is the only coupling between the two scripts — they can be run and improved independently
- Image classification is heuristic (filename + dimensions) — always manual review required
- The bodymind-chiro-website template is the source of truth for all generated sites; changes to it affect every future generation

## 4. Directory Structure

```
website-cloning-toolkit/
├── CLAUDE.md                    # This file
├── README.md                    # User-facing pipeline overview
├── .gitignore
│
├── scripts/
│   ├── scrape-client-site.py    # Step 1: web scraper → client-content.json
│   ├── generate-new-site.py     # Step 2: template copy + data injection
│   └── requirements.txt         # Python dependencies
│
├── output/                      # Default output directory for generated sites
│   └── {client-slug}/           # Generated site directories (gitignored)
│
└── archive/                     # Archived earlier script versions
```

**Template location (external):** `/Users/zachconnermba/Code/bodymind-chiro-website/`

## 5. Development Conventions

- **Python version:** 3.11+
- **Naming:** snake_case for all Python identifiers, filenames, and JSON keys
- **JSON contract:** `client-content.json` is the interface between the two scripts. Any schema changes must be backward-compatible or both scripts updated together
- **No hardcoded paths:** Use `--output` and `--content` CLI args; default to relative paths
- **Image heuristics:** Classification logic lives in `generate-new-site.py` — document any new heuristic rules inline
- **Error handling:** Scraper should degrade gracefully (log missing fields, never crash on a single missing element)
- **Commits:** Conventional commits — `feat:`, `fix:`, `chore:`, `docs:` with `Co-Authored-By: Claude <noreply@anthropic.com>`

## 6. Environment Variables

No secrets or API keys are required to run either pipeline script locally. Playwright runs a local headless Chromium browser — no external API is called during scraping.

If deploy-time automation is added (e.g., auto-deploy generated sites to Cloudflare Pages), the following vault keys would be needed:

| Variable | Purpose | Source |
|----------|---------|--------|
| `CLOUDFLARE_API_TOKEN` | Deploy generated site to Cloudflare Pages | `vault-get CLOUDFLARE_API_TOKEN` |
| `CLOUDFLARE_ACCOUNT_ID` | Identify Cloudflare account | `vault-get CLOUDFLARE_ACCOUNT_ID` |

All secrets are managed in the GPG vault at `~/.secrets/vault.env.gpg`. Never hardcode values in scripts.

## 8. Known Issues

- **Image classification is heuristic:** Auto-classification uses filename patterns and image dimensions. Results vary by source site quality. Always review `public/images/alternatives/{slot}/` after generation and swap in better candidates if needed.
- **CMS detection may miss edge cases:** Wix, Squarespace, and WordPress detection is pattern-based. Unusual themes or custom CMS platforms may fall through to generic HTML scraping, which is less accurate.
- **Schema.org JSON-LD dependency:** The scraper uses schema.org JSON-LD as its primary data source. Sites without structured data produce lower-quality `client-content.json` output requiring more manual cleanup.
- **Generated site.ts requires manual review:** Always review the generated `src/data/site.ts` before deploying — automated data extraction is not 100% accurate.

## 9. Security

- No API keys or secrets are needed for local scraping — Playwright runs entirely locally
- Generated sites inherit the bodymind-chiro-website security posture (CSP headers in `public/_headers`, no credentials in source)
- Per-site Cloudflare tokens and API keys are managed in the GPG vault (`~/.secrets/vault.env.gpg`) and set in the Cloudflare Pages dashboard — never in committed files
- The `output/` directory is gitignored — generated client sites should not be committed to this repo
- Run `secrets-env-auditor` before pushing any changes to either pipeline script

## 10. Subagent Orchestration

| Agent | When to Use |
|-------|-------------|
| `codebase-explorer` | Before modifying either pipeline script — understand data flow and JSON contract between scripts |
| `pre-push-validator` | Before pushing changes to either script |
| `security-scanner` | If adding any network-facing functionality (e.g., auto-deploy API calls) |

## 12. MCP Connections

| Server | Relevance |
|--------|-----------|
| `filesystem` | Read/write local files during pipeline development and output review |

No external MCP servers are needed for local scraping. The pipeline is entirely local: Playwright browser + Python file I/O.

## 13. Completed Work

- **Full two-step pipeline:** `scrape-client-site.py` and `generate-new-site.py` both working end-to-end
- **Image auto-classification:** Heuristic slot assignment (logo, heroFamily, doctorHeadshot, contactHero, ogImage, service images) with alternatives and extras directories
- **CMS detection:** Auto-detects Wix, Squarespace, and WordPress sites; uses schema.org JSON-LD as primary data source
- **`--local-images` flag:** Allows supplementing scraped images with provided professional photos
- **`image-manifest.json`:** Full metadata (URL, alt text, context tags, dimensions) saved alongside downloaded images
- **First client generated:** `output/ttc/` — Tailored Tonal Chiropractic site generated from toolkit

**Next steps:**
- Improve schema.org fallback parsing for sites without structured data
- Add `--dry-run` flag to preview classification without copying files
- Consider adding Cloudflare Pages auto-deploy option post-generation
