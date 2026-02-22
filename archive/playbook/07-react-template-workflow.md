# Phase 7: React Template Workflow

A 4-phase workflow for building chiropractic websites using the React template approach. Instead of pixel-perfect HTML cloning, this method extracts content from an existing site and drops it into a pre-built React template driven by a single `site.ts` configuration file.

This approach is ideal when the goal is a new, modern site -- not a visual replica of the original. The client's existing Wix, Squarespace, or WordPress site provides the *content* (business info, services, testimonials, images), while the React template provides the *design*.

**Prerequisites:** Node.js 18+, Playwright installed (`pip install playwright && playwright install chromium`), access to the client's current website URL.

## When to Use This Workflow

| Scenario | Use React Template? |
|----------|-------------------|
| Client wants a modern redesign, not a clone | Yes |
| Chiropractic office with standard pages (home, about, services, contact) | Yes |
| Client has a Wix/Squarespace site with content to migrate | Yes |
| Client needs pixel-perfect match of existing site | No -- use the [5-phase clone workflow](00-overview.md) |
| Highly custom site with unique layouts per page | No -- manual build |

## Overview

```
 Phase 1              Phase 2              Phase 3               Phase 4
+-----------------+  +-----------------+  +-------------------+  +------------+
| CAPTURE CONTENT | -> | GENERATE       | -> | CUSTOMIZE        | -> | DEPLOY    |
|                 |  | site.ts          |  | TEMPLATE           |  |            |
+-----------------+  +-----------------+  +-------------------+  +------------+
| Scrape text     |  | Map JSON to     |  | Copy template      |  | npm build  |
| Extract images  |  | SITE schema     |  | Drop in site.ts    |  | CF Pages   |
| Collect contact |  | Fill all fields |  | Swap images        |  | Custom DNS |
| Parse services  |  | Validate types  |  | Update colors      |  | Verify     |
+-----------------+  +-----------------+  +-------------------+  +------------+
       |                    |                      |                    |
       v                    v                      v                    v
  client-content.json   src/data/site.ts     Working local dev     Live site
```

---

## Phase 1: Capture Content

Extract the client's business content from their existing website. The goal is a structured `client-content.json` file that contains everything needed to populate `site.ts`.

### What to Extract

| Data | Where to Find It | Notes |
|------|------------------|-------|
| Business name | `<title>`, hero heading, footer | Watch for variations ("Dr. Smith Chiropractic" vs "Smith Chiropractic Center") |
| Doctor name & credentials | About page, bio section | Look for "DC", "Doctor of Chiropractic" |
| Doctor bio | About page | Usually 1-3 paragraphs |
| Phone number | Header, footer, contact page | Extract both display format and E.164 format |
| Email address | Contact page, footer | May be obfuscated with `mailto:` or JavaScript |
| Physical address | Footer, contact page, Google Maps embed | Parse into street, city, state, zip |
| Business hours | Contact page, footer, Google Business Profile | Both display and structured formats |
| Services list | Services/conditions page, navigation menu | Name, short description, any service-specific images |
| Testimonials | Testimonials page, homepage carousel | Name, text, rating if available |
| Social media links | Footer, header icons | Facebook, Instagram, YouTube, TikTok, LinkedIn |
| Logo | Header `<img>`, favicon | Download the highest resolution available |
| Photos | About page, hero sections, service pages | Doctor headshot, office photos, hero images |
| Brand colors | CSS, inline styles, logo colors | Primary, secondary, accent colors |

### Extraction Script Pattern

Use Playwright to scrape the live site, since most Wix and Squarespace sites render content via JavaScript:

```python
#!/usr/bin/env python3
"""Extract business content from a chiropractic website."""
import json
import os
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

TARGET_URL = "https://example-chiro.com"
OUTPUT_FILE = "client-content.json"

def extract_content(page, url):
    """Extract structured content from a single page."""
    page.goto(url, wait_until="networkidle", timeout=30000)

    content = {}

    # Business name from title
    content["title"] = page.title()

    # All text content
    content["headings"] = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('h1, h2, h3'))
            .map(h => ({ tag: h.tagName, text: h.textContent.trim() }));
    }""")

    # Phone numbers
    content["phones"] = page.evaluate("""() => {
        const links = document.querySelectorAll('a[href^="tel:"]');
        return Array.from(links).map(a => ({
            href: a.getAttribute('href'),
            display: a.textContent.trim()
        }));
    }""")

    # Email addresses
    content["emails"] = page.evaluate("""() => {
        const links = document.querySelectorAll('a[href^="mailto:"]');
        return Array.from(links).map(a => ({
            href: a.getAttribute('href').replace('mailto:', ''),
            display: a.textContent.trim()
        }));
    }""")

    # Social media links
    content["socials"] = page.evaluate("""() => {
        const patterns = {
            facebook: /facebook\\.com/,
            instagram: /instagram\\.com/,
            youtube: /youtube\\.com/,
            tiktok: /tiktok\\.com/,
            linkedin: /linkedin\\.com/,
            twitter: /twitter\\.com|x\\.com/,
        };
        const links = document.querySelectorAll('a[href]');
        const found = {};
        for (const link of links) {
            const href = link.getAttribute('href');
            for (const [platform, pattern] of Object.entries(patterns)) {
                if (pattern.test(href) && !found[platform]) {
                    found[platform] = href;
                }
            }
        }
        return found;
    }""")

    # Images (src and alt text)
    content["images"] = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('img'))
            .filter(img => img.src && !img.src.includes('data:image'))
            .map(img => ({
                src: img.src,
                alt: img.alt || '',
                width: img.naturalWidth,
                height: img.naturalHeight,
            }))
            .filter(img => img.width > 100); // Skip tiny icons
    }""")

    # All paragraph text
    content["paragraphs"] = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('p'))
            .map(p => p.textContent.trim())
            .filter(t => t.length > 20);
    }""")

    return content


def main():
    pages_to_scrape = [
        {"slug": "", "label": "home"},
        {"slug": "about", "label": "about"},
        {"slug": "services", "label": "services"},
        {"slug": "contact", "label": "contact"},
        {"slug": "testimonials", "label": "testimonials"},
    ]

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1200, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36"
        )

        for page_info in pages_to_scrape:
            url = f"{TARGET_URL.rstrip('/')}/{page_info['slug']}"
            page = context.new_page()
            try:
                print(f"  Scraping {page_info['label']}... ({url})")
                results[page_info["label"]] = extract_content(page, url)
                print(f"    OK")
            except Exception as e:
                print(f"    ERROR: {e}")
                results[page_info["label"]] = {"error": str(e)}
            finally:
                page.close()

        browser.close()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
```

### Platform-Specific Gotchas

#### Wix Sites

- **Lazy-loaded images:** Wix aggressively lazy-loads images. Scroll the page to the bottom before extracting image URLs, or images will have placeholder `data:` URIs instead of real URLs.

  ```python
  # Scroll to bottom to trigger lazy loading
  page.evaluate("""async () => {
      await new Promise(resolve => {
          let totalHeight = 0;
          const timer = setInterval(() => {
              window.scrollBy(0, 300);
              totalHeight += 300;
              if (totalHeight >= document.body.scrollHeight) {
                  clearInterval(timer);
                  resolve();
              }
          }, 100);
      });
  }""")
  page.wait_for_timeout(2000)  # Wait for images to load
  ```

- **Image URLs:** Wix serves images through `static.wixstatic.com` with transformation parameters in the URL. Strip the transformation suffix to get the original high-resolution image: `https://static.wixstatic.com/media/abc123.jpg` (remove everything after the file extension).

- **Dynamic content containers:** Wix uses deeply nested `<div>` structures with generated class names. Target content by semantic elements (`h1`, `h2`, `p`, `img`) rather than class names.

- **Multiple `<main>` regions:** Some Wix templates split content across multiple sections that are not inside a single `<main>` tag. Use `document.querySelectorAll('section')` and iterate.

#### Squarespace Sites

- **JSON API:** Squarespace exposes page content as JSON at `{page-url}?format=json`. This is often easier to parse than scraping the rendered HTML:

  ```python
  import requests

  url = "https://example-chiro.squarespace.com/about?format=json"
  data = requests.get(url).json()

  # Content is in data['item'] or data['items']
  # Each block has 'type' and structured content
  ```

- **Image URLs:** Squarespace images are served from `images.squarespace-cdn.com`. Append `?format=2500w` to get a high-resolution version.

- **Password-protected sites:** If the Squarespace site has a site-wide password, you need to authenticate first. Use Playwright to fill in the password form before scraping.

- **Blog vs. pages:** Squarespace treats blog posts and pages differently in the JSON API. Blog posts are under `/blog?format=json`, individual pages under `/{slug}?format=json`.

#### WordPress Sites

- **REST API:** WordPress sites often expose content via `/wp-json/wp/v2/pages` and `/wp-json/wp/v2/posts`. Check if the API is enabled before scraping HTML.

- **Yoast SEO data:** If the site uses Yoast, the REST API response includes `yoast_head_json` with structured metadata (title, description, schema.org data) that maps directly to `site.ts` fields.

### Image Download

After extracting image URLs, download them to a local directory:

```python
import requests
import os
from urllib.parse import urlparse

def download_images(image_urls, output_dir="client-images"):
    """Download all extracted images to a local directory."""
    os.makedirs(output_dir, exist_ok=True)

    for i, url in enumerate(image_urls):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                # Generate a clean filename
                parsed = urlparse(url)
                ext = os.path.splitext(parsed.path)[1] or ".jpg"
                filename = f"image-{i:03d}{ext}"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"  Downloaded: {filename} ({len(resp.content)} bytes)")
        except Exception as e:
            print(f"  Failed: {url} - {e}")
```

### Output: client-content.json

The extraction should produce a JSON file with this shape:

```json
{
  "home": {
    "title": "Smith Chiropractic - Rochester Hills, MI",
    "headings": [
      { "tag": "H1", "text": "Welcome to Smith Chiropractic" },
      { "tag": "H2", "text": "Our Services" }
    ],
    "phones": [{ "href": "tel:+12484649697", "display": "(248) 464-9697" }],
    "emails": [{ "href": "info@smithchiro.com", "display": "info@smithchiro.com" }],
    "socials": {
      "facebook": "https://facebook.com/smithchiro",
      "instagram": "https://instagram.com/smithchiro"
    },
    "images": [
      { "src": "https://...", "alt": "Dr. Smith adjusting patient", "width": 800, "height": 600 }
    ],
    "paragraphs": [
      "Dr. Smith has been serving the Rochester Hills community since 2005...",
      "We specialize in gentle, neurologically-focused chiropractic care..."
    ]
  },
  "about": { ... },
  "services": { ... },
  "contact": { ... },
  "testimonials": { ... }
}
```

### Phase 1 Checklist

- [ ] Identify all pages to scrape (home, about, services, contact, testimonials, conditions)
- [ ] Run extraction script with Playwright
- [ ] Scroll all pages to trigger lazy-loaded images (especially Wix)
- [ ] Download all images to `client-images/` directory
- [ ] Verify `client-content.json` has all required data fields
- [ ] Manually fill in any gaps (hours, address details) from Google Business Profile
- [ ] Note any missing content that needs to be requested from the client

---

## Phase 2: Generate site.ts

Transform the extracted `client-content.json` into a valid `site.ts` file that conforms to the bodymind schema.

### The SITE Object Schema

The `site.ts` file exports a single `SITE` constant with these sections:

```typescript
export const SITE = {
  // BUSINESS IDENTITY
  name: string,              // Full business name
  shortName: string,         // Abbreviated name
  domain: string,            // Target domain (no https://)
  description: string,       // SEO meta description (150-160 chars)
  tagline: string,           // Short brand tagline
  foundingYear: string,      // Year established
  priceRange: string,        // "$" | "$$" | "$$$"

  // DOCTOR / PRACTITIONER INFO
  doctor: {
    fullName: string,        // "Dr. Jane Smith"
    firstName: string,
    lastName: string,
    honorificPrefix: string, // "Dr."
    honorificSuffix: string, // "DC"
    credentials: string,     // "DC"
    title: string,           // "Neurologically-Focused Chiropractor"
    bio: string,             // 2-4 sentence bio paragraph
    education: string,       // "Palmer College of Chiropractic"
    image: string,           // "/images/dr-smith.webp"
    pageSlug: string,        // "/meet-dr-smith" or "/about"
    schemaId: string,        // "dr-smith" (for schema.org @id)
    expertise: string[],     // ["NetworkSpinal", "Pediatric Chiropractic", ...]
  },

  // CONTACT INFORMATION
  phone: string,             // E.164 format: "+1-248-464-9697"
  phoneDisplay: string,      // Display format: "(248) 464-9697"
  email: string,

  // PHYSICAL ADDRESS
  address: {
    street: string,
    city: string,
    region: string,          // State abbreviation
    postal: string,
    country: string,         // "US"
    formatted: string,       // Full display string
  },

  // GEOGRAPHIC DATA
  geo: {
    latitude: number,
    longitude: number,
  },

  // BUSINESS HOURS
  hours: {
    display: string[],       // ["Monday 9am-5pm", "Wednesday 9am-5pm"]
    shortFormat: string[],   // ["Mo 09:00-17:00", "We 09:00-17:00"]
    structured: Array<{
      dayOfWeek: string,
      opens: string,
      closes: string,
    }>,
  },

  // BOOKING SYSTEM
  booking: {
    provider: string,        // "jane" | "calendly" | "formspree"
    url: string,
    urlWithUtm: string,
  },

  // CONTACT FORM
  contactForm: {
    provider: string,        // "cloudflare-pages"
    recipientEmail: string,
  },

  // SOCIAL MEDIA
  socials: {
    facebook: string,
    instagram: string,
    tiktok: string,
    youtube: string,
    linkedin: string,
    twitter: string,
  },

  // IMAGES
  images: {
    logo: string,
    heroFamily: string,      // Or heroBanner, heroContent
    doctorHeadshot: string,
    contactHero: string,
    ogImage: string,
  },

  // BRANDING COLORS
  colors: {
    themeColor: string,      // Hex value
    primaryDark: string,
    primary: string,
    primaryLight: string,
    primaryAccent: string,
  },

  // SERVICES
  services: Array<{
    id: string,
    name: string,
    shortName: string,
    slug: string,
    image: string,
    description: string,
  }>,

  // TESTIMONIALS
  testimonials: Array<{
    id: number,
    name: string,
    text: string,
    rating: number,
    datePublished: string,
  }>,

  // FAQs
  faqs: Array<{
    question: string,
    answer: string,
  }>,

  // FEATURE FLAGS
  features: {
    [key: string]: boolean,
  },
} as const;
```

### Mapping client-content.json to site.ts

Work through the extracted content section by section:

**Business identity:** Pull the business name from the homepage `<title>` tag or `<h1>`. Cross-reference with the footer and contact page. The description should be 150-160 characters for SEO.

**Doctor info:** The about page is the primary source. Look for paragraphs starting with "Dr." to find the bio. Education and credentials are often in the bio text or a dedicated section. If credentials are not explicitly listed, check for "DC", "Doctor of Chiropractic", or certifications mentioned in the bio.

**Contact info:** Phone numbers from `tel:` links, email from `mailto:` links. Convert the phone to E.164 format (`+1-XXX-XXX-XXXX`). Parse the address into components -- if it is a single string, use Google Maps to verify and split into street/city/state/zip.

**Services:** Build from the services page headings and descriptions. Each service needs an `id` (kebab-case), a `slug` (URL path), and a description. If the source site does not have dedicated service pages, create brief descriptions from whatever content exists.

**Testimonials:** Extract reviewer name and review text. If ratings are visible (stars), include them. If not, default to `rating: 5` for positive testimonials. Include `datePublished` if available, or use the current date.

**Colors:** Extract from the CSS or inline styles. Use a browser extension like ColorZilla or inspect the computed styles of key elements (headers, buttons, backgrounds). Map to the `colors` object: `primaryDark` is usually the darkest brand color (often navy or dark green for chiropractic sites), `primary` is the main brand color, `primaryLight` is a lighter tint, and `primaryAccent` bridges between dark and light.

**Images:** Rename downloaded images with descriptive names: `logo.webp`, `dr-smith.webp`, `hero-family.webp`, `pediatric-care.webp`. Convert to `.webp` format for performance. All image paths in `site.ts` should start with `/images/`.

### Validation

Before moving to Phase 3, verify the `site.ts` passes TypeScript compilation:

```bash
npx tsc --noEmit src/data/site.ts
```

Check that:

- [ ] No TypeScript errors
- [ ] All required fields are populated (no empty strings for required data)
- [ ] Phone number is valid E.164 format
- [ ] All image paths point to files that exist in `public/images/`
- [ ] Social media URLs are valid (or empty string if not applicable)
- [ ] Colors are valid hex values
- [ ] Services array has at least one entry
- [ ] Testimonials array has at least one entry
- [ ] FAQs array has at least 3 entries
- [ ] `domain` matches the target domain (no `https://` prefix)

### Phase 2 Checklist

- [ ] Map all `client-content.json` fields to `site.ts` schema
- [ ] Write doctor bio (2-4 sentences, factual, professional)
- [ ] Format phone number in both E.164 and display formats
- [ ] Parse address into structured components
- [ ] Convert all images to `.webp` format
- [ ] Assign descriptive filenames to all images
- [ ] Extract and document brand colors
- [ ] Write SEO meta description (150-160 characters)
- [ ] Create at least 3-4 FAQs
- [ ] Validate TypeScript compilation
- [ ] Review all content for accuracy with client

---

## Phase 3: Customize Template

Copy the React template, drop in the client's `site.ts`, configure images and colors, and verify everything works locally.

### Step 1: Copy the Template

```bash
# Create the new project from the template
cp -r templates/react-template/ ~/Code/client-name-website/
cd ~/Code/client-name-website/

# Install dependencies
npm install
```

### Step 2: Drop in site.ts

Replace the template's placeholder `site.ts` with the client-specific version:

```bash
cp /path/to/generated/site.ts src/data/site.ts
```

### Step 3: Add Images

Copy all client images into the public images directory:

```bash
# Copy downloaded and renamed images
cp client-images/*.webp public/images/

# Verify all images referenced in site.ts exist
grep -oP "'/images/[^']+'" src/data/site.ts | tr -d "'" | while read img; do
  if [ ! -f "public${img}" ]; then
    echo "MISSING: public${img}"
  fi
done
```

### Step 4: Update Tailwind Colors

If the client's brand colors differ from the template defaults, update `tailwind.config.js`:

```javascript
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#6383ab',   // Match SITE.colors.primary
          dark: '#002d4e',      // Match SITE.colors.primaryDark
          light: '#73b7ce',     // Match SITE.colors.primaryLight
          accent: '#405e84',    // Match SITE.colors.primaryAccent
        },
      },
    },
  },
};
```

The hex values in `tailwind.config.js` must match the values in `site.ts` `colors` object exactly. If they diverge, the CSS classes will not match the schema.org theme color, causing visual inconsistency.

### Step 5: Test Locally

```bash
npm run dev
```

Open `http://localhost:3000` (or whatever port Vite/Next.js uses) and verify:

- [ ] Homepage loads with correct business name and tagline
- [ ] Doctor photo and bio display correctly on the about page
- [ ] Phone number links work (`tel:` protocol)
- [ ] Email link works (`mailto:` protocol)
- [ ] All navigation links resolve to the correct pages
- [ ] Services section shows all services with correct images
- [ ] Testimonials display with reviewer names
- [ ] Social media icons link to the correct profiles
- [ ] Contact form renders (test submission in production)
- [ ] Colors match the client's brand
- [ ] All images load without broken references
- [ ] Mobile responsive layout works at 375px, 768px, and 1024px

### Common Issues

**Images not loading:** Check that image paths in `site.ts` start with `/images/` and that the files exist in `public/images/`. Paths are case-sensitive.

**Colors look wrong:** Verify the hex values in `tailwind.config.js` match `site.ts`. Run `npm run dev` again after changing Tailwind config -- hot reload does not always pick up config changes.

**TypeScript errors after dropping in site.ts:** The new `site.ts` may have fields that the template components do not expect, or may be missing fields the components require. Check the component imports and adjust `site.ts` to match the expected shape. The `as const` assertion at the end of the `SITE` object is required.

**Booking link not working:** If the client uses a different booking provider than the template default, update the booking URL and ensure the CTA buttons reference `SITE.booking.url` or `SITE.booking.urlWithUtm`.

### Phase 3 Checklist

- [ ] Template copied to new project directory
- [ ] `npm install` completed without errors
- [ ] `site.ts` dropped into `src/data/`
- [ ] All images copied to `public/images/`
- [ ] No missing image references
- [ ] `tailwind.config.js` colors updated
- [ ] `npm run dev` starts without errors
- [ ] All pages render correctly
- [ ] Mobile responsive layout verified
- [ ] All links (phone, email, social, booking) work
- [ ] Git initialized and initial commit made

---

## Phase 4: Deploy

Build the production site, deploy to Cloudflare Pages, configure the custom domain, and verify the live site.

### Step 1: Production Build

```bash
npm run build
```

The build output goes to `dist/` (Vite) or `.next/` (Next.js). Verify:

- No build errors or warnings
- Output size is reasonable (typically under 5MB for a chiropractic site)
- All static assets are included in the build output

### Step 2: Deploy to Cloudflare Pages

#### Option A: Git Integration (Recommended)

```bash
# Push to GitHub
git remote add origin https://github.com/your-org/client-name-website.git
git push -u origin main
```

Then connect the repository to Cloudflare Pages:

1. Go to Cloudflare Dashboard > Pages > Create a project
2. Connect the GitHub repository
3. Set build command: `npm run build`
4. Set build output directory: `dist` (or `out` for Next.js static export)
5. Add any required environment variables
6. Deploy

#### Option B: Direct Upload

```bash
# Install Wrangler if not already installed
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
wrangler pages deploy dist/ --project-name=client-name
```

### Step 3: Configure Custom Domain

1. In Cloudflare Pages project settings, go to "Custom domains"
2. Add the client's domain (e.g., `smithchiro.com` and `www.smithchiro.com`)
3. Cloudflare will provide DNS records to add

If the domain is already on Cloudflare DNS:
- Cloudflare automatically creates the required CNAME records
- SSL certificate is provisioned automatically

If the domain is on an external registrar:
- Add the CNAME record pointing to `client-name.pages.dev`
- Or transfer the domain to Cloudflare for easier management

### Step 4: DNS Configuration

```
Type    Name    Content                         TTL
CNAME   @       client-name.pages.dev           Auto
CNAME   www     client-name.pages.dev           Auto
```

If the domain uses an A record at the apex (some registrars do not support CNAME at root):

```
Type    Name    Content
A       @       192.0.2.1  (Cloudflare Pages IP)
CNAME   www     client-name.pages.dev
```

### Step 5: Post-Deploy Verification

After DNS propagation (usually 5 minutes with Cloudflare, up to 48 hours for external registrars):

- [ ] Site loads at `https://clientdomain.com`
- [ ] Site loads at `https://www.clientdomain.com`
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate is valid (check the padlock icon)
- [ ] All pages load without errors (check browser console)
- [ ] All images load correctly
- [ ] Phone number links work on mobile
- [ ] Contact form submits successfully
- [ ] Booking button links to the correct URL
- [ ] Social media links open in new tab
- [ ] Google PageSpeed Insights score is 90+ on mobile
- [ ] Schema.org structured data is valid (test at schema.org/validate)
- [ ] Open Graph tags work (test at opengraph.xyz)

### Step 6: Search Engine Setup

```bash
# Submit sitemap to Google Search Console
# 1. Verify domain ownership in Google Search Console
# 2. Submit sitemap URL: https://clientdomain.com/sitemap.xml

# If replacing an existing site, set up redirects for any changed URLs
# In Cloudflare Pages _redirects file:
# /old-page  /new-page  301
```

### Step 7: Monitoring

For the first 48 hours after launch:

- Check Cloudflare Analytics for traffic and errors
- Monitor for 404 errors (old URLs that need redirects)
- Verify Google Search Console for crawl errors
- Test the contact form submission pipeline end-to-end
- Confirm the client can receive form submissions at their email

### Phase 4 Checklist

- [ ] `npm run build` completes without errors
- [ ] Deployed to Cloudflare Pages
- [ ] Custom domain configured
- [ ] DNS records pointing to Cloudflare Pages
- [ ] SSL certificate active
- [ ] All pages load at the production URL
- [ ] Contact form works in production
- [ ] Google Search Console set up
- [ ] Sitemap submitted
- [ ] Client notified of go-live
- [ ] 48-hour monitoring window started

---

## Reference Scripts

| Script | Purpose | Phase |
|--------|---------|-------|
| `scripts/scrape-site.py` | General site scraper with Playwright | Phase 1 |
| `scripts/extract-colors.py` | Extract color values from CSS | Phase 1-2 |
| `scripts/extract-fonts.py` | Extract font information | Phase 1-2 |
| Custom content extractor | Extract structured business content | Phase 1 |

## Related Playbook Entries

- [Phase 1: Capture](01-capture.md) -- General scraping strategies (Playwright, Firecrawl, HTTrack)
- [Phase 8: SPA Handling](08-spa-handling.md) -- Handling JavaScript-rendered source sites
- [New Client Onboarding](09-new-client-onboarding.md) -- Full client onboarding checklist from intake to go-live
