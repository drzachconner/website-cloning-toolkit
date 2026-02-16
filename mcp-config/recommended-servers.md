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

**What it does:** Open-source web crawling and scraping framework with built-in browser automation. Runs locally with no API limits and supports JS-rendered pages out of the box via its integrated Playwright-based browser engine.

**When to use it:**
- High-volume scraping where Firecrawl's free tier isn't enough
- JS-rendered pages (SPAs, dynamic content) that need a real browser to extract content
- Projects where data shouldn't leave your machine
- Custom extraction logic with CSS/XPath selectors
- Offline or air-gapped environments

**Why it matters:** No API key required, no rate limits, no costs. Crawl4AI uses a headless browser internally, making it excellent for JS-rendered pages that return empty shells with simple HTTP requests. If you're scraping hundreds of pages or need complete control over the crawling process, Crawl4AI is the way to go.

**Best at:** Large-scale, self-hosted scraping of JS-rendered sites with full control over the extraction pipeline.

**API keys:** None (self-hosted).

**MCP configuration:**
```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "uvx",
      "args": ["crawl4ai-mcp"]
    }
  }
}
```

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

---

## Troubleshooting

Common issues when setting up and using MCP servers for website cloning.

### MCP server not starting

**Symptoms:** Server fails to launch, "command not found" errors, or timeouts during initialization.

**Fixes:**
- **Check Node.js version:** Most MCP servers require Node.js 18+. Run `node --version` to verify. If outdated, install the latest LTS from [nodejs.org](https://nodejs.org).
- **Clear npx cache:** Stale cached packages can cause startup failures. Run `npx clear-npx-cache` or manually delete the npx cache directory (`~/.npm/_npx/`).
- **Check for global conflicts:** If you have the MCP server package installed globally, it may conflict with the npx version. Uninstall the global version with `npm uninstall -g <package>`.
- **Verbose logging:** Run the MCP server command directly in a terminal to see full error output before configuring it in Claude Code.

### Playwright not installed

**Symptoms:** "Executable doesn't exist" errors, "browserType.launch: Browser is not installed" messages.

**Fixes:**
- **Install browser binaries:** Playwright requires separate browser binary downloads. Run:
  ```bash
  npx playwright install chromium
  ```
- **System dependencies (Linux):** On Linux, Playwright needs system libraries. Run:
  ```bash
  npx playwright install-deps chromium
  ```
- **Verify installation:** Test that Playwright works with:
  ```bash
  python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); p.stop(); print('OK')"
  ```

### Firecrawl rate limits

**Symptoms:** 429 (Too Many Requests) responses, "rate limit exceeded" errors, incomplete crawl results.

**Fixes:**
- **Use an API key:** The free tier without an API key has aggressive rate limits. Sign up at [firecrawl.dev](https://firecrawl.dev) for 500 free pages/month.
- **Implement backoff:** When scripting against Firecrawl, add exponential backoff between requests. Start with 1-second delays, doubling on each 429 response up to 30 seconds.
- **Batch strategically:** Use `firecrawl_crawl` for whole-site crawls instead of calling `firecrawl_scrape` on each page individually. The crawl endpoint handles rate limiting internally.
- **Use Crawl4AI as fallback:** If you consistently hit Firecrawl limits, switch to Crawl4AI for unlimited self-hosted scraping.

### Connection refused errors

**Symptoms:** "ECONNREFUSED" errors, "Connection refused" on localhost ports, MCP server appears to start but Claude Code cannot connect.

**Fixes:**
- **Check port conflicts:** Another process may be using the same port. Run `lsof -i :<port>` (macOS/Linux) or `netstat -ano | findstr :<port>` (Windows) to identify conflicts.
- **Firewall/antivirus:** Some security software blocks local server connections. Temporarily disable or add an exception for the MCP server process.
- **Restart the MCP server:** Kill any orphaned MCP server processes and restart Claude Code. Stale processes from crashed sessions can hold ports open.
- **Check stdio vs. HTTP mode:** Some MCP servers communicate via stdio (stdin/stdout) rather than HTTP. Ensure your configuration matches the server's expected transport mode. Playwright MCP and Firecrawl MCP use stdio by default.
