# New Chiropractic Office Website Setup

Complete guide for spinning up a new chiropractic client website from this template. The entire architecture is driven by a single `site.ts` data file, so standing up a new site is primarily a content-replacement exercise.

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Node.js | 18+ | `node -v` to check |
| npm or pnpm | npm 9+ / pnpm 8+ | pnpm preferred for speed |
| Cloudflare account | Free tier works | For Pages hosting |
| Client brand assets | N/A | Logo (SVG or PNG), photos, color palette |
| Client business details | N/A | Address, phone, hours, services, testimonials |

---

## Quick Start

```bash
# 1. Copy this template to a new project directory
cp -r templates/react-template/ ~/Code/new-client-website/
cd ~/Code/new-client-website/

# 2. Initialize git
git init

# 3. Install dependencies
npm install

# 4. Generate or manually create the site data file
#    Option A: Use the generator script (if available)
python scripts/generate-site-ts.py --input client-intake.json --output src/data/site.ts
#    Option B: Copy site.ts.template to src/data/site.ts and fill in manually

# 5. Replace images in public/images/
#    - logo.webp (recommended: 200x60 or SVG)
#    - hero-family.webp (recommended: 1920x1080)
#    - doctor headshot (recommended: 800x800, square crop)
#    - service images (recommended: 800x600 each)
#    - og-image.webp (recommended: 1200x630 for social sharing)

# 6. Update tailwind.config.js with client brand colors (if different from defaults)

# 7. Preview locally
npm run dev

# 8. Deploy to Cloudflare Pages
npm run build
# Then connect repo to Cloudflare Pages dashboard (see Deployment section)
```

---

## Architecture Overview

```
src/
  data/
    site.ts              <-- SINGLE SOURCE OF TRUTH (all content lives here)
  components/
    Header.tsx           <-- Generic, reads from SITE.*
    Footer.tsx
    Hero.tsx
    ServiceCard.tsx
    TestimonialCarousel.tsx
    ContactForm.tsx
    ...
  pages/
    Home.tsx
    About.tsx
    Services.tsx
    Contact.tsx
    ...
  layouts/
    RootLayout.tsx       <-- Shared <head> meta, header, footer wrapper
public/
  images/                <-- All client images go here
  _headers               <-- Cloudflare Pages headers (caching, security)
functions/
  api/
    form-handler.ts      <-- Cloudflare Pages Function for contact form
```

**Key architectural principles:**

1. **Single data file** -- `src/data/site.ts` drives ALL content. No CMS, no database, no external API calls at build time. Components import `SITE` and read fields directly.

2. **Generic components** -- Every component is written to be office-agnostic. They read business name, doctor info, colors, services, etc. from `SITE`. You should never hardcode client-specific text in a component.

3. **Tailwind theming** -- Brand colors are defined in `tailwind.config.js` under `theme.extend.colors`. Components use semantic names like `bg-primary`, `text-primary-dark`, `border-primary-light` instead of raw hex values.

4. **Cloudflare Pages hosting** -- Free SSL, global CDN, automatic deploys from git, serverless functions for the contact form. No server to manage.

---

## Customization Points

### 1. `src/data/site.ts` (Content)

This is the most important file. It contains every piece of client-specific data:

| Section | What to fill in | Example |
|---|---|---|
| Business Identity | name, shortName, domain, description, tagline, foundingYear | `'Body Mind Chiropractic'` |
| Doctor Info | fullName, credentials, bio, education, expertise, certifications | See template for full schema |
| Contact | phone, email, address, geo coordinates | `'+1-248-464-9697'` |
| Business Hours | display format, short format, structured (for schema.org) | `'Monday 9:00 AM - 5:00 PM'` |
| Booking | provider, URL, UTM-tagged URL | Jane App, Calendly, etc. |
| Contact Form | provider, recipient email | `'cloudflare-pages'` |
| Socials | facebook, instagram, tiktok, youtube, linkedin, twitter, pinterest | Full URLs or empty string |
| Images | logo, hero, headshot, service images, OG image | Paths under `/images/` |
| Colors | themeColor, primaryDark, primary, primaryLight, primaryAccent | Hex values |
| Services | id, name, shortName, slug, image, description | One object per service offered |
| Testimonials | name, text, rating, datePublished | From Google Reviews |
| FAQs | question, answer pairs | For FAQ page and schema.org |
| Custom Copy | heroTagline, aboutBio, footerTagline, page-specific overrides | `null` to use defaults |
| Features | Toggle flags for optional sections | `talskyTonal: true` |

**Tip:** Use `site.ts.template` as your starting point. Search for `{{PLACEHOLDER}}` markers and replace them all.

### 2. `tailwind.config.js` (Brand Colors)

Update the color palette to match the client's brand:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'primary-dark': '#002d4e',   // Darkest brand color (nav, footer backgrounds)
        'primary': '#6383ab',         // Main brand color (buttons, links, accents)
        'primary-light': '#73b7ce',   // Light accent (hover states, backgrounds)
        'primary-accent': '#405e84',  // Mid-tone accent (secondary buttons, borders)
      },
    },
  },
  // ...
};
```

**How to extract colors from a client's existing site or brand guide:**

1. Use the browser DevTools color picker on their current site
2. Ask the client for their brand guide PDF
3. Use a tool like [Coolors](https://coolors.co/) to generate a complementary palette from their logo
4. The toolkit's `scripts/extract-colors.py` can pull colors from a scraped site

### 3. `public/images/` (Visual Assets)

Replace all placeholder images with the client's actual assets:

| Image | Recommended Size | Format | Notes |
|---|---|---|---|
| `logo.webp` | 200x60 or SVG | WebP/SVG | Transparent background preferred |
| `hero-family.webp` | 1920x1080 | WebP | Main hero banner image |
| `dr-*.webp` | 800x800 | WebP | Doctor headshot, square crop |
| Service images | 800x600 | WebP | One per service (pediatric, prenatal, etc.) |
| `og-image.webp` | 1200x630 | WebP | Social sharing preview image |
| `contact-hero.webp` | 1920x600 | WebP | Contact page header |

**Image optimization tips:**

- Convert all images to WebP format (use `cwebp` or Squoosh)
- Keep file sizes under 200KB for hero images, under 100KB for everything else
- Use responsive `<img srcset>` where the component supports it
- Cloudflare will additionally apply Polish (automatic image optimization) if enabled

### 4. Fonts (Optional)

The default template uses system fonts or Google Fonts loaded via `<link>` in the HTML head. To change fonts:

1. Choose fonts from Google Fonts
2. Update the `<link>` tag in `index.html`
3. Update `tailwind.config.js` fontFamily:

```js
fontFamily: {
  sans: ['Montserrat', 'system-ui', 'sans-serif'],
  heading: ['Playfair Display', 'serif'],
},
```

---

## Deployment to Cloudflare Pages

### First-Time Setup

1. Push your repo to GitHub (private repo is fine)
2. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) > Workers & Pages > Create
3. Connect your GitHub account and select the repository
4. Configure build settings:
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `/` (or the subdirectory if monorepo)
   - **Node.js version:** `18` (set in Environment Variables > `NODE_VERSION=18`)
5. Add environment variables:
   - `CONTACT_FORM_RECIPIENT` = client's email address
   - Any other `.env` values needed
6. Click "Save and Deploy"

### Custom Domain

1. In Cloudflare Pages project settings > Custom domains
2. Add `www.clientdomain.com` and `clientdomain.com`
3. If the domain is already on Cloudflare DNS, CNAME records are created automatically
4. If the domain is elsewhere, add the CNAME records Cloudflare provides, then transfer DNS to Cloudflare for best performance

### Automatic Deploys

Every push to `main` triggers a new production deploy. Push to other branches to get preview URLs (useful for client review before going live).

### Contact Form Function

The contact form submits to a Cloudflare Pages Function at `/api/form-handler`. This function:

1. Validates the form data
2. Sends an email via Resend (or your configured email provider)
3. Returns a success/error response

Make sure to set the `CONTACT_FORM_RECIPIENT` environment variable in the Cloudflare Pages dashboard. If using Resend, also set `RESEND_API_KEY`.

---

## Common Issues & Troubleshooting

### Build fails with "Cannot find module 'site.ts'"

You forgot to create `src/data/site.ts`. Copy `site.ts.template` to `src/data/site.ts` and fill in the client data.

### Colors not updating after changing tailwind.config.js

Restart the dev server (`npm run dev`). Tailwind needs a restart to pick up config changes. Also verify you are using the semantic class names (`bg-primary`, not `bg-[#6383ab]`).

### Images not showing in production

Make sure images are in `public/images/` (not `src/images/`). Vite serves files from `public/` as static assets at the root path. Double-check that paths in `site.ts` start with `/images/`.

### Contact form returns 500 error

Check the Cloudflare Pages Function logs in the dashboard. Common causes:
- Missing `CONTACT_FORM_RECIPIENT` environment variable
- Missing `RESEND_API_KEY` if using Resend
- Function file not in the correct path (`functions/api/form-handler.ts`)

### Google Maps embed not showing

Verify the `geo.latitude` and `geo.longitude` values in `site.ts` are correct. Use Google Maps to look up the exact coordinates for the office address.

### Schema.org validation errors

Run the site through [Google's Rich Results Test](https://search.google.com/test/rich-results) or [Schema.org Validator](https://validator.schema.org/). Common fixes:
- Ensure `address`, `geo`, `hours`, and `doctor` sections are fully populated
- Ensure `googlePlaceId` is set (look it up via the Google Places API or Maps URL)
- Ensure at least one testimonial has `rating` and `datePublished`

### Lighthouse performance score below 90

- Compress all images to WebP under 200KB
- Ensure fonts are preloaded in `<head>`
- Check for unused CSS/JS bundles
- Enable Cloudflare's Auto Minify and Polish features

### Preview deploy looks different from local

Cloudflare Pages uses the `dist/` output from `npm run build`. Run `npm run build && npm run preview` locally to verify the production build matches your expectations before pushing.

---

## Workflow Summary

```
1. Copy template
2. npm install
3. Fill in site.ts (or generate it)
4. Drop in images
5. Adjust colors in tailwind.config.js
6. npm run dev (preview)
7. Push to GitHub
8. Connect to Cloudflare Pages
9. Set env vars in Cloudflare dashboard
10. Add custom domain
11. Done -- auto-deploys on every push
```

---

## File Reference

| File | Purpose | When to Modify |
|---|---|---|
| `src/data/site.ts` | All client content and config | Every new site |
| `tailwind.config.js` | Brand colors, fonts | Every new site (colors at minimum) |
| `public/images/*` | Client visual assets | Every new site |
| `.env` / `.env.example` | Environment variables | Every new site |
| `functions/api/form-handler.ts` | Contact form backend | Only if changing email provider |
| Component files (`src/components/*`) | UI components | Only for structural changes across all sites |
| Page files (`src/pages/*`) | Page layouts | Only for adding/removing pages |
