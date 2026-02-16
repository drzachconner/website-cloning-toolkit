# Recommended MCP Servers for Website Cloning

MCP (Model Context Protocol) servers extend Claude Code with browser automation, scraping, and screenshot capabilities that are essential for high-fidelity website cloning.

## Server Overview

| Priority | Server | Purpose | Install Command |
|----------|--------|---------|-----------------|
| Must-have | Playwright MCP | Browser automation, screenshots, JS rendering | `npx @anthropic-ai/mcp-server-playwright` |
| Must-have | Firecrawl MCP | Web scraping that bypasses 403s | `npx firecrawl-mcp-server` |
| Recommended | Screenshot MCP | Quick full-page captures for Claude Vision | `npx @anthropic-ai/mcp-screenshot` |
| Optional | Browser Use MCP | Complex auth flows, form interactions | See docs.browser-use.com |
| Optional | Crawl4AI MCP | Self-hosted alternative to Firecrawl (free) | See github.com/unclecode/crawl4ai |

---

## Must-Have Servers

### Playwright MCP

**What it does:** Provides full browser automation through Chromium. Navigate pages, wait for JavaScript to render, extract DOM content, take screenshots, and interact with elements.

**When to use it:**
- Scraping JS-rendered sites (SPAs, React, CMS platforms like Vortala/Wix/Squarespace)
- Taking reference screenshots at specific viewport sizes
- Extracting computed CSS values from rendered elements
- Navigating multi-page sites with dynamic content loading

**Why it matters:** Many modern websites render content client-side. Simple HTTP requests return empty shells. Playwright waits for `networkidle` state, ensuring all content and styles are loaded before extraction.

**Best at:** Precise, controllable browser sessions where you need to wait for specific elements, scroll to trigger lazy loading, or capture screenshots at exact breakpoints.

**API keys:** None required.

**Key capabilities:**
- `browser_navigate` - Load a URL with configurable wait conditions
- `browser_screenshot` - Capture full-page or element-specific screenshots
- `browser_evaluate` - Run JavaScript to extract computed styles, DOM structure
- `browser_click` / `browser_type` - Interact with page elements

---

### Firecrawl MCP

**What it does:** Cloud-based web scraping service that handles anti-bot protections, JavaScript rendering, and returns clean markdown or structured HTML.

**When to use it:**
- Sites that block direct requests with 403/429 errors
- Bulk scraping multiple pages quickly
- Extracting clean content without writing custom selectors
- Sites with aggressive Cloudflare or bot protection

**Why it matters:** Many sites actively block scraping. Firecrawl handles rotating proxies, browser fingerprinting, and CAPTCHA challenges automatically. It returns clean, structured content without the noise of ads and navigation.

**Best at:** High-volume content extraction where you need clean text/HTML from many pages without writing per-site parsing logic.

**API keys:** Required. Get one at [firecrawl.dev](https://firecrawl.dev). Free tier includes 500 pages/month.

**Key capabilities:**
- `firecrawl_scrape` - Scrape a single URL, returns markdown or HTML
- `firecrawl_crawl` - Crawl an entire site following links
- `firecrawl_map` - Discover all URLs on a domain
- `firecrawl_extract` - Extract structured data using a schema

---

## Recommended Servers

### Screenshot MCP

**What it does:** Captures full-page screenshots optimized for Claude Vision analysis. Lighter weight than Playwright for screenshot-only workflows.

**When to use it:**
- Quick visual reference captures before starting a clone
- Comparing your clone side-by-side with the original
- Feeding screenshots to Claude Vision for pixel-level fidelity checks
- Capturing responsive layouts at multiple breakpoints

**Why it matters:** Visual comparison is the fastest way to spot design drift. Having reference screenshots at 320px, 768px, 1024px, and 1440px gives you concrete targets to match.

**Best at:** Fast, focused screenshot capture when you don't need full browser interaction capabilities.

**API keys:** None required.

---

## Optional Servers

### Browser Use MCP

**What it does:** AI-powered browser automation that can handle complex multi-step interactions including authentication flows, form submissions, and navigation of dynamic interfaces.

**When to use it:**
- Cloning pages behind authentication (member portals, dashboards)
- Sites requiring form submission to access content
- Complex navigation flows (multi-step wizards, filtered views)
- Sites with cookie consent walls or age gates

**Why it matters:** Some content is only accessible after logging in or completing specific interactions. Browser Use can automate these flows while maintaining session state.

**Best at:** Navigating authenticated or interactive content that requires human-like browser behavior.

**API keys:** Depends on configuration. See [docs.browser-use.com](https://docs.browser-use.com) for setup.

---

### Crawl4AI MCP

**What it does:** Self-hosted web crawling and scraping framework. Open-source alternative to Firecrawl that runs locally with no API limits.

**When to use it:**
- High-volume scraping where Firecrawl's free tier isn't enough
- Projects where data shouldn't leave your machine
- Custom extraction logic with CSS/XPath selectors
- Offline or air-gapped environments

**Why it matters:** No API key required, no rate limits, no costs. If you're scraping hundreds of pages or need complete control over the crawling process, Crawl4AI is the way to go.

**Best at:** Large-scale, self-hosted scraping with full control over the extraction pipeline.

**API keys:** None (self-hosted).

**Setup:** See [github.com/unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) for installation and MCP server configuration.

---

## Server Combinations by Use Case

| Use Case | Recommended Stack |
|----------|-------------------|
| Simple static site | Firecrawl + Screenshot MCP |
| JS-rendered SPA | Playwright + Screenshot MCP |
| Site behind login | Browser Use + Playwright |
| Large site (100+ pages) | Firecrawl or Crawl4AI + Screenshot MCP |
| CMS-hosted (Vortala, Wix) | Playwright + Firecrawl |
| Quick visual audit | Screenshot MCP only |
