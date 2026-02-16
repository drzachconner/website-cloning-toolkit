# Phase 3: Generate Code

Produce initial HTML/CSS that matches the target site's visual design. Choose the approach based on site complexity, output format, and how much manual refinement you expect.

**Prerequisites:** Design tokens from [Phase 2](02-extract-design-system.md), screenshots from [Phase 1](01-capture.md)

## Approach Selection

| Approach | Best For | Output | Fidelity | Effort |
|----------|----------|--------|----------|--------|
| Claude Code direct | Any site, maximum control | HTML/CSS | High | Medium |
| Screenshot-to-code | Quick first draft | HTML/React | Medium | Low |
| v0.dev | React/Next.js projects | React components | Medium | Low |
| Bolt.new | Full-stack prototypes | Full project | Medium-High | Low |
| Lovable | MVP web apps | React app | Medium | Low |
| Firecrawl + Claude | Scrape-to-rebuild pipeline | HTML/CSS | High | Medium |

### Decision Tree

```
Is the target site a single page or a few pages?
  YES -> Screenshot-to-code or Claude Code direct
  NO  -> Is it a batch of similar pages (e.g., product pages, condition pages)?
    YES -> Build one template, then batch convert (Phase 4)
    NO  -> Is it a full web application?
      YES -> v0.dev / Bolt.new / Lovable
      NO  -> Claude Code direct with extracted CSS
```

## Claude Code Direct

The most reliable approach for high-fidelity cloning. Feed Claude the extracted HTML, CSS, and design tokens, and ask it to rebuild.

### Single Page Rebuild

```
Here is the extracted HTML content from a page:
[paste mirror/extracted/page-name-content.html]

Here is the site's CSS (relevant subset):
[paste css/site-clone.css]

Rebuild this as a standalone HTML page that:
1. Uses these exact CSS classes: .entry-content, .bldr_callout, .bldr_notebox, .bldr_cta
2. Links to ../css/site-clone.css
3. Includes Schema.org MedicalWebPage JSON-LD
4. Uses this page shell structure:
   <body class="page layout-one-col">
     <div id="containing_wrap">...
```

### Template Generation

For batch conversion, generate one reference template first:

```
Based on these 5 example pages [paste examples], create a reusable HTML
template with placeholder markers for:
- {{TITLE}} - page title
- {{META_DESCRIPTION}} - meta description
- {{H1_TEXT}} - main heading
- {{HERO_ALT}} - hero image alt text
- {{INTRO_TEXT}} - opening paragraph
- {{BODY_CONTENT}} - main content sections
- {{CONDITION_NAME}} - for CTA personalization
- {{TAGLINE}} - bottom tagline text
```

Save templates to `templates/page-template.html`.

### CSS Subset Creation

When rebuilding, create a focused CSS file rather than using the full original:

```
Here is the full original CSS (3000+ lines):
[paste mirror/raw-css/original.css]

Extract only the classes used in the content area:
.entry-content, .bldr_callout, .bldr_notebox, .bldr_cta, .rounded,
.alignright, .alignleft, .fa-ul, .bordered-section, .bldr_divider,
.column, .one_half, .one_third, .two_thirds, .cb

Include the typography rules for h1-h3, p, a, strong, ul, li.
Include the Google Fonts import for Playfair Display and Mulish.
Do not include nav, footer, sidebar, or utility bar styles.
```

## Screenshot-to-Code

### abi/screenshot-to-code (GitHub)

Open-source tool that converts screenshots to HTML/CSS/React:

```bash
# Clone and run locally
git clone https://github.com/abi/screenshot-to-code
cd screenshot-to-code
# Follow setup instructions in repo

# Or use the hosted version at screenshottocode.com
```

**Best for:** Quick first drafts when you have good screenshots but limited HTML access.

**Limitations:** Output often needs significant cleanup. Works better for simple layouts than complex multi-column designs.

### WebSight (HuggingFace)

HuggingFace Space for screenshot-to-code conversion:

- Upload a screenshot
- Get back HTML/Tailwind output
- Works best for clean, modern designs

**Best for:** Tailwind-based projects or when you want utility-class output.

## AI Platforms

### v0.dev

Vercel's AI tool generates React components from prompts or screenshots:

```
Prompt: "Create a medical conditions page that matches this design:
- Serif heading font (Playfair Display)
- Circular hero image floated right
- Pull quote with left border accent
- Gray CTA box with pink button
- Gold bullet point lists"
```

**Output:** React/Next.js components with Tailwind CSS.

**Best for:** Projects where the final output is React. Less useful for static HTML delivery.

### Bolt.new

Full-stack AI prototyping from StackBlitz:

- Describe the site or paste a screenshot
- Generates a complete project with routing, styling, and deployment
- Can iterate on the design in real time

**Best for:** When you need a full working prototype, not just static pages.

### Lovable

AI-powered MVP builder:

- Describe the product or paste screenshots
- Generates a React web app with routing and basic backend
- Deploys to a preview URL

**Best for:** Product MVPs that need more than static pages.

### Open Lovable

Open-source alternative. Provide a URL and get a React codebase that replicates it:

- Feed it the target URL
- Get back a React project structure
- Iterate with prompts

## Firecrawl + Claude Pipeline

Use Firecrawl to scrape the site into structured markdown, then feed that to Claude for code generation:

```bash
# Step 1: Scrape with Firecrawl (via MCP or API)
# Returns clean markdown of each page

# Step 2: Feed to Claude
```

```
Here is the markdown content scraped from the target site:

[paste firecrawl markdown output]

And here is the CSS design system I extracted:
[paste design tokens]

Generate an HTML page that:
1. Preserves all the content from the markdown
2. Uses the CSS classes and design tokens above
3. Follows this template structure: [paste template]
```

**Best for:** Sites that block direct HTML scraping. Firecrawl handles bot detection, and Claude handles the HTML generation.

## Building the Shared CSS

Regardless of generation approach, you need a shared CSS file. Here is the pattern:

```css
/* css/site-clone.css */

/* Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Mulish:wght@400;600;700&display=swap');

/* Base typography */
body { font-family: 'Mulish', sans-serif; font-size: 16px; color: #333; }
h1, h2 { font-family: 'Playfair Display', serif; color: #333; }
h1 { font-size: 2em; }
h2 { font-size: 1.8em; }
h3 { font-family: 'Mulish', sans-serif; font-size: 1.4em; }

/* Content wrapper */
.entry-content { max-width: 960px; margin: 0 auto; padding: 20px; }

/* Components */
.bldr_callout { font-style: italic; color: #444; font-size: 20px;
                border-left: 3px solid #999; padding-left: 20px; margin: 20px 0; }
.bldr_notebox { background: #f1f1f1; border-radius: 25px; padding: 30px;
                margin: 30px 0; text-align: center; }
.bldr_cta { display: inline-block; background: #ed247c; color: #fff;
            text-transform: uppercase; padding: 12px 30px; text-decoration: none; }
.bldr_cta:hover { background: #feb506; color: #333; }

/* Layout */
.rounded { border-radius: 50%; }
.alignright { float: right; margin: 0 0 15px 25px; }
.cb { clear: both; }
```

## Output Checklist

- [ ] Reference template created in `templates/`
- [ ] Shared CSS file created in `css/`
- [ ] CSS imports correct fonts from Google Fonts
- [ ] Template matches target site's page shell structure
- [ ] At least one page manually verified against screenshot
- [ ] Placeholder images in place for development

## Next Step

With templates and CSS in place, proceed to [Phase 4: Convert & Refine](04-convert-and-refine.md) for batch transformation.
