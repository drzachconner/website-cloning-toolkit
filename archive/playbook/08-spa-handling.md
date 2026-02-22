# Phase 8: SPA Handling

Single Page Applications (SPAs) present unique challenges for website cloning. Unlike traditional server-rendered sites where each URL returns complete HTML, SPAs render content client-side using JavaScript frameworks. The initial HTML is a near-empty shell, and the actual page content is constructed in the browser by React, Vue, Angular, or similar frameworks.

This guide covers identifying SPAs, extracting their content reliably, handling framework-specific artifacts, and deciding when to clone the SPA architecture versus capturing its rendered output.

## Identifying SPAs

### Quick Detection Methods

**View source vs. rendered DOM:** Right-click the page and choose "View Page Source." If the `<body>` contains mostly empty `<div>` tags (like `<div id="root"></div>` or `<div id="app"></div>`) with no visible content, it is an SPA. Compare against DevTools Elements panel -- if the Elements panel shows full content but View Source does not, the content is JavaScript-rendered.

**Network tab indicators:** Open DevTools Network tab, reload the page, and filter by "XHR" or "Fetch." SPAs typically make multiple API calls after the initial page load to fetch content data (usually JSON).

**Framework fingerprints:**

| Framework | HTML Indicators | Global Objects |
|---|---|---|
| React | `<div id="root">` or `<div id="__next">` | `window.__NEXT_DATA__`, `window.__REACT_DEVTOOLS_GLOBAL_HOOK__` |
| Next.js | `<div id="__next">`, `<script id="__NEXT_DATA__">` | `window.__NEXT_DATA__` |
| Vue | `<div id="app">`, `data-v-*` attributes | `window.__VUE__`, `window.__NUXT__` |
| Nuxt | `<div id="__nuxt">`, `<div id="__layout">` | `window.__NUXT__`, `window.$nuxt` |
| Angular | `<app-root>`, `_ngcontent-*` attributes | `window.ng` |
| Svelte | `<div id="svelte">` | -- |
| Gatsby | `<div id="___gatsby">` | `window.___gatsby` |

**JavaScript console check:** In the DevTools Console, run:

```javascript
// React
!!document.querySelector('[data-reactroot]') || !!document.getElementById('__next')

// Vue
!!document.querySelector('[data-v-]') || !!window.__VUE__

// Angular
!!document.querySelector('[_ngcontent]') || !!window.ng
```

### Checking from a Script

Use Playwright to detect the framework programmatically:

```python
def detect_spa_framework(page):
    """Detect which SPA framework a page uses."""
    return page.evaluate("""() => {
        const frameworks = [];

        // React / Next.js
        if (document.getElementById('__next') || document.querySelector('[data-reactroot]')) {
            frameworks.push('react');
        }
        if (window.__NEXT_DATA__) {
            frameworks.push('nextjs');
        }

        // Vue / Nuxt
        if (document.querySelector('[data-v-]') || window.__VUE__) {
            frameworks.push('vue');
        }
        if (window.__NUXT__ || document.getElementById('__nuxt')) {
            frameworks.push('nuxt');
        }

        // Angular
        if (document.querySelector('[_ngcontent]') || window.ng) {
            frameworks.push('angular');
        }

        // Gatsby
        if (document.getElementById('___gatsby') || window.___gatsby) {
            frameworks.push('gatsby');
        }

        // Svelte
        if (document.querySelector('[class*="svelte-"]')) {
            frameworks.push('svelte');
        }

        return frameworks.length > 0 ? frameworks : ['unknown-or-ssr'];
    }""")
```

## Playwright Wait Strategies

SPAs load content asynchronously. The default Playwright `wait_until="load"` fires when the initial HTML shell loads -- before JavaScript has rendered any content. You need explicit wait strategies.

### Wait Strategy Options

**`networkidle`** (recommended default): Waits until there have been no network requests for 500ms. Works well for most SPAs because content renders after API calls complete.

```python
page.goto(url, wait_until="networkidle", timeout=60000)
```

**Caveat:** Some SPAs have persistent WebSocket connections, analytics pings, or polling that prevent `networkidle` from ever resolving. Set a reasonable timeout and fall back to `domcontentloaded` + explicit waits.

**`domcontentloaded` + element wait**: Wait for the DOM to be ready, then wait for a specific content element to appear. More reliable for SPAs with persistent connections.

```python
page.goto(url, wait_until="domcontentloaded", timeout=30000)
# Wait for the main content to render
page.wait_for_selector(".main-content", state="visible", timeout=15000)
```

**Custom wait function**: For complex loading patterns (lazy-loaded images, infinite scroll, skeleton screens):

```python
page.goto(url, wait_until="domcontentloaded", timeout=30000)

# Wait until skeleton screens are gone and real content appears
page.wait_for_function("""() => {
    const skeletons = document.querySelectorAll('.skeleton, [class*="loading"]');
    const content = document.querySelector('h1, article, .entry-content');
    return skeletons.length === 0 && content !== null;
}""", timeout=15000)
```

**Multiple sequential waits**: For pages with staggered loading (hero first, then cards, then sidebar):

```python
page.goto(url, wait_until="domcontentloaded", timeout=30000)
page.wait_for_selector("h1", state="visible", timeout=10000)
page.wait_for_selector(".card-grid", state="visible", timeout=10000)
# Give images and lazy-loaded content a moment
page.wait_for_timeout(2000)
```

### Timeout Strategy

Always set explicit timeouts and handle failures gracefully:

```python
try:
    page.goto(url, wait_until="networkidle", timeout=30000)
except TimeoutError:
    print(f"  networkidle timeout, falling back to domcontentloaded")
    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(5000)  # Give JS extra time
```

## Route Extraction

SPAs use client-side routing, so crawling links with traditional tools misses most pages. Here are strategies for discovering all routes.

### Method 1: Sitemap

Many modern SPAs (especially Next.js and Nuxt) generate sitemaps at build time. Check `/sitemap.xml` first:

```python
import requests
from bs4 import BeautifulSoup

def get_sitemap_urls(base_url):
    """Extract URLs from sitemap.xml."""
    urls = []
    sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
    resp = requests.get(sitemap_url, timeout=15)
    if resp.status_code != 200:
        return urls

    soup = BeautifulSoup(resp.text, "xml")

    # Handle sitemap index (multiple sitemaps)
    for sitemap in soup.find_all("sitemap"):
        loc = sitemap.find("loc")
        if loc:
            urls.extend(get_sitemap_urls(loc.text))

    # Handle regular sitemap
    for url in soup.find_all("url"):
        loc = url.find("loc")
        if loc:
            urls.append(loc.text)

    return urls
```

### Method 2: Intercept the Router

For React Router, Vue Router, or Angular Router, you can extract the route definitions from the JavaScript bundle:

```python
def extract_routes_from_bundle(page):
    """Attempt to extract route paths from the SPA's router."""
    return page.evaluate("""() => {
        const routes = [];

        // Next.js: __NEXT_DATA__ contains page manifest
        if (window.__NEXT_DATA__) {
            const pages = window.__NEXT_DATA__.props?.pageProps;
            if (pages) routes.push('(check __NEXT_DATA__)');
        }

        // Nuxt: window.__NUXT__ contains route info
        if (window.__NUXT__?.routePath) {
            routes.push(window.__NUXT__.routePath);
        }

        // Scan all <a> tags for internal links
        const links = document.querySelectorAll('a[href]');
        const origin = window.location.origin;
        for (const link of links) {
            const href = link.getAttribute('href');
            if (href && (href.startsWith('/') || href.startsWith(origin))) {
                const path = href.replace(origin, '');
                if (path && !routes.includes(path)) {
                    routes.push(path);
                }
            }
        }

        return routes;
    }""")
```

### Method 3: Crawl with Playwright

The most reliable approach: use Playwright to visit pages, extract links, and follow them recursively:

```python
def crawl_spa(start_url, max_pages=100):
    """Crawl an SPA by following internal links with Playwright."""
    from urllib.parse import urlparse, urljoin

    visited = set()
    to_visit = [start_url]
    base = urlparse(start_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue

            visited.add(url)
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Extract all internal links
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => href.startsWith(window.location.origin));
            }""")

            for link in links:
                parsed = urlparse(link)
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean not in visited and clean not in to_visit:
                    to_visit.append(clean)

        browser.close()

    return sorted(visited)
```

### Method 4: Navigation/Footer Links

As a quick-and-dirty approach, inspect the navigation menu and footer for links. Most sites expose their key pages through navigation even if they use client-side routing.

## CSS-in-JS Handling

SPAs commonly use CSS-in-JS libraries (styled-components, Emotion, CSS Modules) that generate styles at runtime. This creates challenges for CSS extraction.

### styled-components / Emotion

These libraries inject `<style>` tags into the `<head>` at runtime. The class names are auto-generated hashes (e.g., `.css-1a2b3c`, `.sc-bdVTJa`).

**Extraction strategy:**

```python
def extract_runtime_styles(page):
    """Extract all style tags injected by CSS-in-JS libraries."""
    return page.evaluate("""() => {
        const styles = [];

        // Collect all <style> tags
        for (const style of document.querySelectorAll('style')) {
            if (style.textContent.trim()) {
                styles.push(style.textContent);
            }
        }

        // Also collect from adoptedStyleSheets (if supported)
        if (document.adoptedStyleSheets) {
            for (const sheet of document.adoptedStyleSheets) {
                for (const rule of sheet.cssRules) {
                    styles.push(rule.cssText);
                }
            }
        }

        return styles.join('\\n');
    }""")
```

**Key insight:** For cloning purposes, you rarely need the CSS-in-JS class names. Instead, extract the *computed styles* from elements (using `extract-design-system.py`) and map them to your target classes. The generated class names are meaningless for cloning.

### CSS Modules

CSS Modules append hash suffixes to class names (e.g., `.heading_abc123`). The original class name is preserved as a prefix.

**Extraction strategy:** Strip the hash suffix to recover the semantic class name:

```python
import re

def strip_css_module_hash(class_name):
    """Remove CSS Module hash suffix from a class name."""
    # Pattern: name_hash or name__hash
    return re.sub(r'[_-][a-zA-Z0-9]{5,}$', '', class_name)
```

## Hydration Artifact Cleanup

When you capture an SPA's rendered HTML, it contains framework-specific attributes and data that are meaningless for a static clone. Remove these artifacts during conversion.

### React / Next.js Artifacts

```python
def clean_react_artifacts(soup):
    """Remove React/Next.js framework artifacts from HTML."""
    # Remove data-reactroot, data-reactid attributes
    for tag in soup.find_all(True):
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr.startswith("data-react") or attr.startswith("data-rh"):
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    # Remove __next wrapper if present (keep its children)
    next_div = soup.find("div", id="__next")
    if next_div:
        next_div.unwrap()

    # Remove Next.js data script
    for script in soup.find_all("script", id="__NEXT_DATA__"):
        script.decompose()

    # Remove Next.js build manifest scripts
    for script in soup.find_all("script"):
        src = script.get("src", "")
        if "_next/" in src or "_buildManifest" in src or "_ssgManifest" in src:
            script.decompose()

    # Remove CSS Module hash suffixes from class names
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        if classes:
            cleaned = [re.sub(r'__[a-zA-Z0-9_]{5,}$', '', cls) for cls in classes]
            tag["class"] = cleaned

    return soup
```

### Vue / Nuxt Artifacts

```python
def clean_vue_artifacts(soup):
    """Remove Vue/Nuxt framework artifacts from HTML."""
    # Remove data-v-* scoped style attributes
    for tag in soup.find_all(True):
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr.startswith("data-v-"):
                attrs_to_remove.append(attr)
            if attr == "data-server-rendered":
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    # Remove __nuxt and __layout wrappers
    for wrapper_id in ["__nuxt", "__layout"]:
        wrapper = soup.find("div", id=wrapper_id)
        if wrapper:
            wrapper.unwrap()

    # Remove Nuxt state script
    for script in soup.find_all("script"):
        text = script.string or ""
        if "window.__NUXT__" in text or "__NUXT_I18N__" in text:
            script.decompose()

    # Remove _nuxt/ build scripts
    for script in soup.find_all("script"):
        src = script.get("src", "")
        if "_nuxt/" in src:
            script.decompose()

    return soup
```

### Angular Artifacts

```python
def clean_angular_artifacts(soup):
    """Remove Angular framework artifacts from HTML."""
    # Remove _ngcontent-*, _nghost-* attributes
    for tag in soup.find_all(True):
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr.startswith("_ngcontent") or attr.startswith("_nghost"):
                attrs_to_remove.append(attr)
            if attr.startswith("ng-") and attr != "ng-content":
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    # Unwrap <app-root> and other custom Angular elements
    for tag in soup.find_all(re.compile(r'^app-')):
        tag.unwrap()

    # Remove Angular state transfer script
    for script in soup.find_all("script", id="serverApp-state"):
        script.decompose()

    # Remove Angular-specific inline styles (ViewEncapsulation emulation)
    for style in soup.find_all("style"):
        text = style.string or ""
        if "[_ngcontent" in text or "[_nghost" in text:
            style.decompose()

    return soup
```

### Universal Cleanup

Apply these to any SPA-captured HTML:

```python
def clean_spa_artifacts(soup, framework=None):
    """Universal SPA artifact cleanup."""
    # Remove all inline scripts (SPA state, hydration, analytics)
    for script in soup.find_all("script"):
        if not script.get("src"):
            script.decompose()
        elif any(pattern in script.get("src", "") for pattern in
                 ["_next/", "_nuxt/", "runtime.", "polyfills.", "vendor.",
                  "webpack.", "chunk.", "main."]):
            script.decompose()

    # Remove preload/prefetch hints for SPA bundles
    for link in soup.find_all("link", rel=["preload", "prefetch", "modulepreload"]):
        href = link.get("href", "")
        if any(ext in href for ext in [".js", ".mjs", ".chunk."]):
            link.decompose()

    # Framework-specific cleanup
    if framework == "react" or framework == "nextjs":
        clean_react_artifacts(soup)
    elif framework == "vue" or framework == "nuxt":
        clean_vue_artifacts(soup)
    elif framework == "angular":
        clean_angular_artifacts(soup)

    return soup
```

## Framework-Specific Sections

### React / Next.js

**`__NEXT_DATA__`:** Next.js pages include a `<script id="__NEXT_DATA__">` tag containing the page's props as JSON. This is used for hydration and client-side navigation. Remove it entirely for static clones -- it can be hundreds of KB and serves no purpose in the clone.

**CSS Module hashes:** Next.js CSS Modules generate class names like `.styles_heading__x7y8z`. The semantic part is `styles_heading`. When mapping classes, strip the hash suffix.

**Image optimization:** Next.js uses `<img>` tags with `srcSet` and `sizes` attributes plus a wrapper `<span>` for lazy loading. Simplify to plain `<img>` with a single `src` for the clone.

**Link prefetching:** Next.js `<Link>` components generate `<a>` tags with `data-noscript` and prefetch attributes. Clean these to plain `<a href="...">`.

### Vue / Nuxt

**`data-v-*` attributes:** Vue's scoped CSS system adds `data-v-xxxxxxxx` attributes to elements. These are meaningless without the corresponding scoped `<style>` tags. Remove all `data-v-*` attributes.

**Scoped style IDs:** Scoped styles have selectors like `.heading[data-v-abc123]`. When extracting CSS, strip the `[data-v-*]` attribute selectors to get the base rules.

**`__NUXT__` state:** Similar to `__NEXT_DATA__`, Nuxt embeds page state in a `window.__NUXT__` script. Remove it.

**Nuxt payload:** Nuxt 3 uses a `<script type="application/json" id="__NUXT_DATA__">` tag for serialized page data. Remove it.

### Angular

**`_ngcontent-*` and `_nghost-*`:** Angular's ViewEncapsulation.Emulated mode (the default) adds `_ngcontent-xxx-yyy` attributes to every element and `_nghost-xxx-yyy` to component hosts. Remove all of these.

**Component selectors:** Angular components render as custom HTML elements (`<app-header>`, `<app-footer>`, `<feature-card>`). These have no meaning in a static clone. Unwrap them (keep children, remove the custom element wrapper) or replace with semantic HTML (`<header>`, `<footer>`, `<div>`).

**ViewEncapsulation styles:** Angular's emulated encapsulation rewrites CSS selectors to include the `_ngcontent` attributes. Strip these attribute selectors from extracted CSS to get the base rules.

**Zone.js:** Angular includes Zone.js for change detection. Remove any script tags referencing `zone.js`, `polyfills.js`, or `runtime.js`.

## Static Export Strategies

If you have access to the SPA's source code (open-source project or your own site), consider generating a static export rather than scraping the rendered output.

### Next.js Static Export

```bash
# In the Next.js project
npx next build
npx next export
# Output: out/ directory with static HTML files
```

Or in `next.config.js`:
```javascript
module.exports = {
  output: 'export',
};
```

**Limitations:** Dynamic routes require `getStaticPaths`. API routes are not exported. Server-side features (middleware, rewrites) are unavailable.

### Nuxt Static Generation

```bash
# In the Nuxt project
npx nuxt generate
# Output: dist/ directory with static HTML files
```

Or in `nuxt.config.js`:
```javascript
export default {
  target: 'static',
};
```

**Nuxt 3:**
```bash
npx nuxi generate
```

### Angular Prerendering

```bash
# In the Angular project (with Angular Universal)
ng build --configuration production
ng run app:prerender
# Output: dist/browser/ directory with prerendered HTML
```

Or use `@nguniversal/express-engine` for server-side rendering and capture the output.

### Gatsby (Already Static)

Gatsby sites are static by default:
```bash
npx gatsby build
# Output: public/ directory with static HTML files
```

### Advantages of Static Export

- Complete, correct HTML without scraping artifacts
- All routes are generated automatically from the route config
- CSS is already extracted and bundled
- No framework artifacts to clean up
- Images and assets are properly referenced

### When Static Export Is Not Available

If you do not have access to the source code or the framework does not support static export for the routes you need, fall back to Playwright-based scraping with the wait strategies and artifact cleanup described above.

## When NOT to Clone as SPA

Often, the best strategy for cloning an SPA is to ignore the SPA architecture entirely and treat it as a rendered website. Clone the **output**, not the **architecture**.

### Clone the rendered output when:

- You only need the visual design and content, not the interactivity
- The SPA has fewer than 50 unique pages
- The clone will be delivered as static HTML (the most common case)
- The target CMS is not a JavaScript framework
- You do not need client-side navigation or dynamic features

### Clone the SPA architecture when:

- The clone must preserve interactive features (forms, filters, search, dynamic content)
- The project is a migration from one framework to another
- The clone will run as a JavaScript application
- Client-side routing and navigation behavior must be preserved

### The Rendered Output Approach

For most website cloning projects, this is the recommended approach:

1. **Capture** the site using Playwright with `wait_until="networkidle"`
2. **Extract** the rendered HTML from the DOM (not the page source)
3. **Clean** framework artifacts using the cleanup functions above
4. **Extract** computed styles using `extract-design-system.py` and `extract-colors.py`
5. **Build** a static CSS file from the extracted design tokens
6. **Map** elements to your target classes using the class mapping process
7. **Validate** against screenshots as usual

This approach works for any SPA framework and produces clean, portable HTML that can be integrated into any CMS.

```python
# Extract rendered HTML (not page source)
rendered_html = page.evaluate("""() => {
    return document.documentElement.outerHTML;
}""")

# Or extract just the content area
content_html = page.evaluate("""() => {
    const main = document.querySelector('main, article, .content, #content');
    return main ? main.innerHTML : document.body.innerHTML;
}""")
```

## Summary

| Challenge | Strategy |
|---|---|
| Detecting SPA framework | View Source vs. DevTools, `window.__NEXT_DATA__`, `data-v-*` attributes |
| Waiting for content | `networkidle` default, `wait_for_selector` fallback, custom wait functions |
| Discovering routes | Sitemap first, Playwright crawl second, navigation links third |
| Extracting CSS | Capture computed styles, not CSS-in-JS class names |
| Cleaning artifacts | Remove `data-react*`, `data-v-*`, `_ngcontent-*`, framework scripts |
| Static export | Use `next export`, `nuxt generate`, or `ng prerender` when possible |
| General approach | Clone the rendered output, not the SPA architecture |
