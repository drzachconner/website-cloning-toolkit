# Phase 9: New Client Onboarding

A step-by-step checklist for onboarding a new chiropractic client from initial intake through go-live. This guide covers the complete workflow: gathering requirements, extracting content, building the site, getting client approval, and launching.

Use this alongside the [React Template Workflow](07-react-template-workflow.md) for the technical implementation details.

---

## Stage 1: Pre-Work (Client Intake)

Collect all required information before touching any code. Missing information at this stage causes delays in every subsequent stage.

### Client Discovery Call

- [ ] Get the client's **current website URL**
  - If no website exists, skip to "Net-New Site" section below
  - Note the platform (Wix, Squarespace, WordPress, custom) -- this affects the extraction approach
- [ ] Get the client's **desired domain name**
  - Check availability at the registrar if it is a new domain
  - If transferring an existing domain, confirm the client has registrar login access
  - Confirm whether they want `www` and non-`www` to both work
- [ ] Confirm the client's **business information**:
  - [ ] Legal business name (exactly as it should appear on the site)
  - [ ] Doctor/practitioner full name and credentials (DC, etc.)
  - [ ] Office phone number
  - [ ] Office email address
  - [ ] Physical address (street, suite, city, state, ZIP)
  - [ ] Business hours (days, open/close times)
  - [ ] Year established
- [ ] Get the **services list** the client wants displayed
  - Ask them to rank their top 3-5 services in priority order
  - Confirm any services on the current site that should be removed or added
- [ ] Ask about **booking system**
  - Do they use Jane App, Calendly, Acuity, or another scheduling tool?
  - Get the direct booking URL
- [ ] Ask about **testimonials**
  - Do they have Google Reviews they want featured?
  - Any specific testimonials they want highlighted?
  - How many? (Aim for 3-8)
- [ ] Ask about **social media accounts**
  - Facebook, Instagram, YouTube, TikTok, LinkedIn
  - Get exact profile URLs (not just usernames)

### Brand Assets

- [ ] **Logo** -- Request the highest resolution version available
  - Preferred formats: SVG, PNG with transparency, or high-res JPEG
  - Need both full logo and icon/favicon version if available
- [ ] **Photos** -- Collect or confirm availability of:
  - [ ] Doctor/practitioner headshot (professional quality)
  - [ ] Office interior or exterior photo
  - [ ] Hero/banner image
  - [ ] Service-specific images (if available)
  - If professional photos do not exist, plan to use stock photos or generate with AI
- [ ] **Brand colors** -- Ask the client:
  - Do they have a brand guide or style guide?
  - What are their primary brand colors? (Get hex codes if possible)
  - If no brand guide exists, extract colors from their current site or logo

### Domain and Hosting Access

- [ ] Confirm domain registrar (GoDaddy, Namecheap, Google Domains, Cloudflare, etc.)
- [ ] Confirm the client can update DNS records (or will grant you access)
- [ ] If the domain is new, purchase and register it
- [ ] Set up a Cloudflare Pages project for the site

### Pre-Work Checklist Summary

| Item | Status | Notes |
|------|--------|-------|
| Current site URL | | |
| Target domain | | |
| Business name | | |
| Doctor name + credentials | | |
| Phone number | | |
| Email address | | |
| Physical address | | |
| Business hours | | |
| Services list | | |
| Booking URL | | |
| Testimonials | | |
| Social media URLs | | |
| Logo file | | |
| Doctor headshot | | |
| Hero image | | |
| Brand colors | | |
| Domain registrar access | | |

---

## Net-New Site (No Existing Website)

If the client does not have a current website, skip the content extraction phase and build `site.ts` directly from the intake information.

- [ ] Write the doctor bio from scratch (or ask the client to provide one)
- [ ] Write service descriptions (2-3 sentences each)
- [ ] Write 3-4 FAQs relevant to their practice
- [ ] Write the SEO meta description (150-160 characters)
- [ ] Source hero images (stock photo sites or AI-generated)
- [ ] Process the logo (convert to `.webp`, create favicon)
- [ ] Proceed directly to Stage 2, Step 3 (Generate site.ts)

---

## Stage 2: Technical Setup

### Step 1: Content Extraction

If the client has an existing website, extract all usable content.

- [ ] Identify the site platform (Wix, Squarespace, WordPress, custom)
- [ ] Choose extraction strategy:
  - **Wix**: Playwright scraper with scroll-to-load for lazy images (see [Phase 7, Platform Gotchas](07-react-template-workflow.md#platform-specific-gotchas))
  - **Squarespace**: Try JSON API first (`?format=json`), fall back to Playwright
  - **WordPress**: Try REST API first (`/wp-json/wp/v2/pages`), fall back to Playwright
  - **Other**: Playwright with `networkidle` wait strategy
- [ ] Run the content extraction script:
  ```bash
  python scripts/extract-content.py --url "https://client-site.com" --output client-content.json
  ```
- [ ] Download all images from the source site:
  ```bash
  python scripts/download-images.py --json client-content.json --output client-images/
  ```
- [ ] Take screenshots of every page for reference:
  ```bash
  python scripts/scrape-site.py --url "https://client-site.com" --screenshots --output mirror/
  ```

### Step 2: Review and Clean Extracted Content

- [ ] Open `client-content.json` and verify all sections have data
- [ ] Cross-reference extracted text with the live site -- check for:
  - [ ] Truncated paragraphs (common with lazy-loaded content)
  - [ ] Missing sections (popups, modals, accordion content)
  - [ ] Garbled text (encoding issues, HTML entities not decoded)
  - [ ] Duplicate content (same text appearing on multiple pages)
- [ ] Clean up the doctor bio:
  - Remove marketing fluff ("the best chiropractor in town")
  - Keep factual claims (education, years of experience, certifications)
  - Ensure it reads naturally as 2-4 sentences
- [ ] Clean up service descriptions:
  - Each should be 1-3 sentences
  - Focus on what the patient experiences, not technical jargon
- [ ] Clean up testimonials:
  - Remove duplicate testimonials
  - Trim excessively long reviews to the strongest 2-3 sentences
  - Verify reviewer names are appropriate to display (first name + last initial is common)
- [ ] Verify all downloaded images:
  - [ ] Images are high enough resolution (minimum 800px wide for hero images)
  - [ ] No watermarked stock photos
  - [ ] Doctor headshot is professional quality
  - [ ] Logo is clean and crisp

### Step 3: Generate site.ts

- [ ] Create `site.ts` following the [bodymind schema](07-react-template-workflow.md#the-site-object-schema)
- [ ] Fill in all required fields from `client-content.json` and client intake notes
- [ ] Convert all images to `.webp` format:
  ```bash
  for f in client-images/*.{jpg,jpeg,png}; do
    cwebp -q 85 "$f" -o "${f%.*}.webp"
  done
  ```
- [ ] Rename images with descriptive names (`dr-smith.webp`, `hero-family.webp`, etc.)
- [ ] Write FAQs (at least 3-4 questions relevant to the practice)
- [ ] Write the SEO meta description
- [ ] Set feature flags based on what the practice offers
- [ ] Validate TypeScript compilation:
  ```bash
  npx tsc --noEmit src/data/site.ts
  ```

### Step 4: Build the Site

- [ ] Copy the React template to a new project directory:
  ```bash
  cp -r templates/react-template/ ~/Code/client-name-website/
  ```
- [ ] Drop in the client's `site.ts`:
  ```bash
  cp site.ts ~/Code/client-name-website/src/data/site.ts
  ```
- [ ] Copy images to `public/images/`:
  ```bash
  cp client-images/*.webp ~/Code/client-name-website/public/images/
  ```
- [ ] Update `tailwind.config.js` with client's brand colors
- [ ] Install dependencies and start dev server:
  ```bash
  cd ~/Code/client-name-website/
  npm install
  npm run dev
  ```
- [ ] Verify all pages render correctly (see [Phase 7, Phase 3 checklist](07-react-template-workflow.md#phase-3-customize-template))

### Step 5: Set Up Cloudflare Pages Project

- [ ] Create a new GitHub repository for the project
- [ ] Push the code to GitHub
- [ ] Connect the repository to Cloudflare Pages:
  1. Cloudflare Dashboard > Pages > Create a project
  2. Select the GitHub repository
  3. Build command: `npm run build`
  4. Output directory: `dist` (or `out` for Next.js)
- [ ] Verify the deploy preview works at `*.pages.dev`
- [ ] Add any required environment variables in Cloudflare Pages settings

### Step 6: Configure DNS (Staging)

For the staging phase, use the Cloudflare Pages `.pages.dev` subdomain. Do not point the production domain yet.

- [ ] Note the staging URL: `https://client-name.pages.dev`
- [ ] Verify the staging site loads correctly
- [ ] Test all functionality on the staging URL

---

## Stage 3: Content Review

### Step 1: Share Staging URL

- [ ] Send the staging URL to the client
- [ ] Include a brief walkthrough of each page:
  ```
  Hi [Client Name],

  Your new site is ready for review at: https://client-name.pages.dev

  Please review each page:
  - Home: [brief description of what's there]
  - About: [brief description]
  - Services: [brief description]
  - Contact: [brief description]

  Let me know:
  1. Any text that needs to change
  2. Any images you'd like swapped
  3. Any pages or sections you'd like added/removed
  4. Any colors or styling adjustments
  ```
- [ ] Set a review deadline (suggest 3-5 business days)

### Step 2: Collect Feedback

- [ ] Track all feedback items in a checklist:

  | Page | Feedback Item | Status |
  |------|--------------|--------|
  | Home | Change hero heading to "..." | |
  | About | Update bio paragraph 2 | |
  | Services | Add "Prenatal Care" service | |
  | Contact | Hours are wrong for Wednesday | |

- [ ] Clarify any ambiguous feedback before starting revisions
- [ ] If the client requests significant structural changes (new pages, different layout), scope that as a separate revision round

### Step 3: Apply Revisions

- [ ] Update `site.ts` with all text changes
- [ ] Swap any images the client requested
- [ ] Adjust colors or styling if requested
- [ ] Rebuild and verify locally:
  ```bash
  npm run dev
  ```
- [ ] Push changes to trigger a new Cloudflare Pages deploy
- [ ] Send updated staging URL to client for re-review

### Step 4: Final Approval

- [ ] Get explicit written approval from the client (email or message)
  - "The site looks good -- please go ahead and launch."
- [ ] Do not proceed to go-live without written approval
- [ ] If additional revision rounds are needed, repeat Steps 2-4

---

## Stage 4: Go-Live

### Pre-Launch Checklist

Before pointing the production domain:

- [ ] Run `npm run build` one final time -- no errors or warnings
- [ ] All pages load correctly on the staging URL
- [ ] Contact form has been tested end-to-end (submit and confirm email receipt)
- [ ] Booking button links to the correct scheduling URL
- [ ] Phone number `tel:` link works on mobile
- [ ] All images load (no broken references)
- [ ] Schema.org structured data validates (test at [schema.org/validate](https://validator.schema.org/))
- [ ] Open Graph tags work (test at [opengraph.xyz](https://opengraph.xyz))
- [ ] Google PageSpeed Insights score is 90+ on mobile
- [ ] favicon displays correctly in browser tab
- [ ] Client has given written approval

### Step 1: Point DNS to Cloudflare Pages

- [ ] In Cloudflare Pages project settings, add the custom domain(s):
  - `clientdomain.com`
  - `www.clientdomain.com`
- [ ] If the domain is on Cloudflare DNS:
  - Cloudflare creates CNAME records automatically
  - Wait 2-5 minutes for propagation
- [ ] If the domain is on an external registrar:
  - Add CNAME record: `@` -> `client-name.pages.dev`
  - Add CNAME record: `www` -> `client-name.pages.dev`
  - Wait up to 48 hours for propagation (typically 1-4 hours)

### Step 2: Verify SSL Certificate

- [ ] Cloudflare Pages provisions an SSL certificate automatically
- [ ] Verify by visiting `https://clientdomain.com` -- the padlock should show
- [ ] If SSL is not working after 15 minutes:
  - Check that the domain DNS is pointing to Cloudflare
  - Check Cloudflare Pages custom domain status for any error messages
  - Edge certificates can take up to 24 hours to provision

### Step 3: Verify Redirects

- [ ] `http://clientdomain.com` redirects to `https://clientdomain.com`
- [ ] `http://www.clientdomain.com` redirects to `https://clientdomain.com` (or `https://www.clientdomain.com` depending on preference)
- [ ] Old pages from the previous site that no longer exist return a 404 or redirect to the new equivalent:
  ```
  # Add to _redirects file in the project root
  /old-about-page  /about  301
  /old-services    /services  301
  /chiropractic-services  /services  301
  ```

### Step 4: Submit to Google Search Console

- [ ] Go to [Google Search Console](https://search.google.com/search-console/)
- [ ] Add the property `https://clientdomain.com`
- [ ] Verify ownership (DNS TXT record method is recommended with Cloudflare)
- [ ] Submit the sitemap: `https://clientdomain.com/sitemap.xml`
- [ ] If replacing an existing site, check for crawl errors from old URLs
- [ ] Request indexing of the homepage

### Step 5: Post-Launch Notifications

- [ ] Notify the client that the site is live
  ```
  Hi [Client Name],

  Your new website is now live at https://clientdomain.com!

  A few things to know:
  - The site has been submitted to Google for indexing
  - SSL certificate is active (your visitors see the secure padlock)
  - The contact form sends submissions to [email]
  - I'll be monitoring the site for the next 48 hours

  If you notice anything that needs adjusting, let me know.
  ```
- [ ] Share the Google Search Console access with the client (optional)

### Step 6: Monitor for 48 Hours

During the first 48 hours after launch:

- [ ] **Day 1 - Morning:**
  - Check Cloudflare Analytics for any 4xx or 5xx errors
  - Verify all pages still load correctly
  - Test the contact form submission
  - Check mobile rendering on a real device
- [ ] **Day 1 - Evening:**
  - Check for any 404 errors in Cloudflare Analytics (old URLs from search engines)
  - Add redirects for any discovered 404s
  - Verify DNS propagation is complete (try from a different network)
- [ ] **Day 2:**
  - Check Google Search Console for crawl errors
  - Verify the sitemap was processed
  - Check that the SSL certificate is stable
  - Confirm no client-reported issues

---

## Post-Launch Maintenance

After the 48-hour monitoring window:

- [ ] Document the project setup in a README or internal notes:
  - GitHub repo URL
  - Cloudflare Pages project name
  - Domain registrar
  - Client contact email
  - Any special configuration or customizations
- [ ] Set a calendar reminder for 30-day check-in:
  - Are there any content updates needed?
  - Has the client received form submissions successfully?
  - Any new services or testimonials to add?
- [ ] Inform the client how to request future changes:
  - Text/content updates -> update `site.ts` and redeploy
  - New images -> add to `public/images/` and update `site.ts`
  - New pages -> requires template work (scope separately)

---

## Troubleshooting

### DNS Not Propagating

If the site does not load at the custom domain after several hours:

1. Check DNS with `dig clientdomain.com` or [dnschecker.org](https://dnschecker.org)
2. Verify the CNAME record points to `client-name.pages.dev`
3. If using an external registrar, confirm there is no conflicting A record
4. Some registrars do not support CNAME at the root -- use Cloudflare DNS instead

### SSL Certificate Not Provisioning

1. Check Cloudflare Pages custom domain status for error messages
2. Ensure the domain DNS points to Cloudflare (required for automatic SSL)
3. If using an external registrar, the certificate may take up to 24 hours
4. Try removing and re-adding the custom domain in Cloudflare Pages

### Contact Form Not Working

1. Verify the Cloudflare Pages Function `/api/form-handler` is deployed
2. Check the environment variable for the email service API key (e.g., Resend)
3. Check Cloudflare Pages Function logs for errors
4. Test with a simple form submission and check the email delivery service logs

### Build Fails on Cloudflare Pages

1. Check the build log in Cloudflare Pages dashboard
2. Common issues:
   - Node.js version mismatch -- set `NODE_VERSION` environment variable
   - Missing environment variables
   - Dependency resolution errors -- clear cache and rebuild
3. Test the build locally first: `npm run build`

---

## Timeline Estimate

| Stage | Duration | Notes |
|-------|----------|-------|
| Pre-work (client intake) | 1-2 days | Depends on client responsiveness |
| Content extraction | 1-2 hours | Automated with scripts |
| Content review + cleanup | 1-2 hours | Manual review |
| Generate site.ts | 1-2 hours | Including image processing |
| Build + local testing | 1-2 hours | Template customization |
| Client review | 3-5 days | Client's schedule |
| Apply revisions | 1-4 hours | Depends on feedback volume |
| Go-live | 1-2 hours | DNS + verification |
| Monitoring | 48 hours | Passive monitoring |
| **Total** | **5-10 business days** | End-to-end |

---

## Related Playbook Entries

- [React Template Workflow](07-react-template-workflow.md) -- Detailed 4-phase technical workflow
- [Phase 1: Capture](01-capture.md) -- General scraping strategies
- [Phase 8: SPA Handling](08-spa-handling.md) -- Handling JavaScript-rendered source sites
