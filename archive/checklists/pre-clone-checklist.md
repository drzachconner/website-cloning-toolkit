# Pre-Clone Checklist

Complete before starting any website clone project.

## Target Analysis

- [ ] Target URL(s) identified and accessible
- [ ] Legal/TOS review complete (cloning is permitted for this use case)
- [ ] Full-page screenshots captured for reference (desktop + mobile)
- [ ] Sitemap.xml located (if available)
- [ ] robots.txt reviewed for scraping restrictions
- [ ] Page count estimated (how many unique pages to clone)

## Design System Discovery

- [ ] CSS source URL(s) identified (check `<link>` tags and `@import` rules)
- [ ] Font families identified (primary heading font, body font)
- [ ] Font loading method noted (Google Fonts, Adobe Fonts, self-hosted)
- [ ] Color palette documented:
  - [ ] Heading color(s)
  - [ ] Body text color
  - [ ] Link color (default + hover)
  - [ ] Button/CTA colors (background, text, hover states)
  - [ ] Background colors (page, sections, cards)
  - [ ] Border/divider colors
- [ ] Layout grid understood:
  - [ ] Max content width
  - [ ] Column system (if any)
  - [ ] Gutters and spacing scale
  - [ ] Breakpoints for responsive behavior
- [ ] Spacing patterns documented (margins, padding, gaps)

## Component Inventory

- [ ] Key page components listed:
  - [ ] Navigation (type: fixed, sticky, hamburger, mega-menu)
  - [ ] Hero/banner sections
  - [ ] Content blocks (text, images, callouts)
  - [ ] Cards or grid layouts
  - [ ] CTA sections
  - [ ] Footer
- [ ] Repeated patterns identified (shared headers/footers, CTA blocks)
- [ ] Interactive elements noted (dropdowns, accordions, tabs, sliders)
- [ ] Third-party widgets identified (contact forms, maps, chat, analytics)
- [ ] Image assets cataloged (logos, icons, decorative elements)

## Technical Assessment

- [ ] Rendering method determined (static HTML, SSR, client-side JS)
- [ ] CMS platform identified (if applicable: WordPress, Wix, Squarespace, custom)
- [ ] CDN or asset hosting identified
- [ ] Authentication required for any pages? (login walls, member content)
- [ ] Anti-bot protection present? (Cloudflare, CAPTCHA, rate limiting)

## Project Setup

- [ ] Output directory created with standard structure
- [ ] MCP servers installed and configured (run `setup-mcp.sh`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Git repository initialized
- [ ] CLAUDE.md created with project-specific conventions
- [ ] Reference screenshots saved to `reference/` directory
