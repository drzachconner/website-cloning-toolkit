# Website Cloning Toolkit

Two-step pipeline for creating chiropractic client websites. Scrapes content from a client's existing site (Wix, Squarespace, WordPress, or any site), then generates a full React + Vite + Tailwind site using [bodymind-chiro-website](https://github.com/drzachconner/bodymind-chiro-website) as the template.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Quick Start

```bash
# Install dependencies
pip install -r scripts/requirements.txt
playwright install chromium

# 1. Scrape the client's existing site
python scripts/scrape-client-site.py --url "https://example-chiro.com" --output ./output/client/

# 2. Generate the new site (images are auto-classified and placed)
python scripts/generate-new-site.py --content ./output/client/client-content.json --output ./new-client-site/ --domain newclient.com

# 3. Preview
cd new-client-site
npm install
npm run dev
```

Optionally supply additional images (e.g. professional photos):

```bash
python scripts/generate-new-site.py --content ./output/client/client-content.json --output ./new-client-site/ --local-images ./extra-photos/
```

## What You Get

A complete, production-ready chiropractic website with React 18, TypeScript, Vite, Tailwind CSS, React Router, SEO, Schema.org structured data, AI chatbot, and contact form -- ready to deploy to Cloudflare Pages. All content is driven by a single `src/data/site.ts` file.

Images are automatically classified and placed into site slots (logo, hero, headshot, contact, services) using filename heuristics, scraper metadata, and Pillow-based dimension analysis. Runner-up candidates are saved in `public/images/alternatives/` for easy swapping.
