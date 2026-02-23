# Chiropractic Site Template — Shared vs Customized

> Defines what's shared across all client sites vs what's customized per-client.
> Used by `generate-new-site.py` and for manual onboarding of new chiro clients.

---

## Shared Components (identical across all sites)

These files are copied verbatim from the template and require zero per-client changes:

### React Components
| Component | Path | Purpose |
|-----------|------|---------|
| AnimateOnScroll | `src/components/AnimateOnScroll.tsx` | Scroll-triggered animations |
| AuthorByline | `src/components/AuthorByline.tsx` | Author attribution block |
| Breadcrumbs | `src/components/Breadcrumbs.tsx` | Navigation breadcrumbs |
| CTABanner | `src/components/CTABanner.tsx` | Call-to-action banner |
| ChatbotWidget | `src/components/ChatbotWidget.tsx` | AI chatbot (consumes SITE data) |
| ContactForm | `src/components/ContactForm.tsx` | Contact form (posts to /api/form-handler) |
| ErrorBoundary | `src/components/ErrorBoundary.tsx` | Error boundary wrapper |
| FloatingReviewWidget | `src/components/FloatingReviewWidget.tsx` | Google review prompt |
| Footer | `src/components/Footer.tsx` | Site footer (consumes SITE data) |
| Header | `src/components/Header.tsx` | Navigation header (consumes SITE navLinks) |
| Hero | `src/components/Hero.tsx` | Hero section template |
| JsonLd | `src/components/JsonLd.tsx` | Schema.org JSON-LD renderer |
| MobileCTA | `src/components/MobileCTA.tsx` | Mobile sticky CTA bar |
| Seo | `src/components/Seo.tsx` | Meta tags + Open Graph |
| StatsBar | `src/components/StatsBar.tsx` | Stats/metrics display |
| TestimonialSlider | `src/components/TestimonialSlider.tsx` | Testimonial marquee carousel |
| AdminRedirect | `src/components/AdminRedirect.tsx` | Redirects /admin to agent.drzach.ai |

### Condition System
| File | Purpose |
|------|---------|
| `src/data/conditions.ts` | 48 condition definitions (shared across all chiro sites) |
| `src/pages/conditions/ConditionIndex.tsx` | Conditions listing page |
| `src/pages/conditions/ConditionPage.tsx` | Individual condition template |
| `src/pages/conditions/ConditionPageWrapper.tsx` | Route wrapper with lazy loading |
| `src/components/conditions/ConditionHero.tsx` | Condition page hero |
| `src/components/conditions/ConditionTemplate.tsx` | Condition page layout |

### Utility Libraries
| File | Purpose |
|------|---------|
| `src/lib/schema.ts` | Schema.org JSON-LD generators (consumes SITE) |
| `src/lib/breadcrumbs.ts` | Breadcrumb JSON-LD helper |
| `src/lib/analytics.ts` | AI traffic tracking |
| `src/lib/render-inline-links.tsx` | Markdown link parser for React |
| `src/lib/rate-limit.ts` | In-memory IP rate limiter |

### Shared Pages
| Page | Path | Notes |
|------|------|-------|
| Privacy | `src/pages/Privacy.tsx` | Standard privacy policy |
| Thanks | `src/pages/Thanks.tsx` | Form submission confirmation |
| ThankYouSubmission | `src/pages/ThankYouSubmission.tsx` | Guide download confirmation |
| NotFound | `src/pages/NotFound.tsx` | 404 page |
| AnswerHub | `src/pages/AnswerHub.tsx` | FAQ page (consumes SITE.faqs if present) |

### Infrastructure
| File | Purpose |
|------|---------|
| `src/App.tsx` | Router + layout (routes adjust per site) |
| `src/main.tsx` | Entry point |
| `tailwind.config.js` | Tailwind config (colors customized per site) |
| `vite.config.ts` | Vite build config |
| `wrangler.toml` | Cloudflare Pages config (name customized) |
| `.github/workflows/deploy.yml` | GitHub Actions → Cloudflare Pages |
| `package.json` | Dependencies (identical across sites) |
| `tsconfig.json` | TypeScript config |

---

## Customized via site.ts (no code changes needed)

The `src/data/site.ts` file is the **single source of truth** for all per-client data. Every shared component reads from `SITE.*` — updating this one file customizes the entire site.

### SITE Object Structure

```typescript
SITE = {
  // Business Identity
  name: string,              // "BodyMind Chiropractic"
  shortName: string,         // "BodyMind Chiro"
  domain: string,            // "bodymindchiro.com"
  description: string,       // SEO meta description
  tagline: string,           // "Your Health and Happiness"
  foundingYear: string,      // "1998"
  priceRange: string,        // "$$"

  // Doctor / Practitioner
  doctor: {
    fullName: string,        // "Dr. John Johr"
    firstName: string,
    lastName: string,
    honorificPrefix: string, // "Dr."
    honorificSuffix: string, // "DC"
    credentials: string,
    title: string,           // "Neurologically-Focused Chiropractor"
    bio: string,             // Full bio paragraph
    education: string,       // "Life University College of Chiropractic"
    educationWikidata: string,
    image: string,           // "/images/dr-john.webp"
    pageSlug: string,        // "/meet-dr-john"
    schemaId: string,        // "dr-john"
    expertise: string[],     // ["Talsky Tonal", "NetworkSpinal", ...]
    certifications: Array<{ type: string, name: string }>,
  },

  // Contact
  phone: string,             // "+1-248-464-9697"
  phoneDisplay: string,      // "(248) 464-9697"
  email: string,

  // Address
  address: {
    street: string,
    city: string,
    region: string,          // State abbreviation
    postal: string,
    country: string,         // "US"
    formatted: string,       // Full display string
  },

  // Geo (for maps + schema.org)
  geo: { latitude: number, longitude: number },
  googlePlaceId: string,

  // Hours
  hours: {
    display: string[],       // ["Monday 9am-5pm", ...]
    shortFormat: string[],   // ["Mo 09:00-17:00", ...]
    structured: Array<{ dayOfWeek: string, opens: string, closes: string }>,
  },

  // Booking
  booking: {
    provider: string,        // "jane" | "calendly" | etc.
    url: string,
    urlWithUtm: string,
  },

  // Contact Form
  contactForm: {
    provider: string,        // "cloudflare-pages"
    recipientEmail: string,
  },

  // Social Media (empty string = omitted from UI)
  socials: {
    facebook: string,
    instagram: string,
    tiktok: string,
    youtube: string,
    linkedin: string,
    twitter: string,
    pinterest: string,
  },

  // Images
  images: {
    logo: string,
    heroFamily: string,
    doctorHeadshot: string,
    contactHero: string,
    ogImage: string,
  },

  // Brand Colors (must also update tailwind.config.js)
  colors: {
    themeColor: string,      // Primary dark hex
    primaryDark: string,
    primary: string,
    primaryLight: string,
    primaryAccent: string,
  },

  // Services (array of service objects)
  services: Array<{
    id: string,
    name: string,
    shortName: string,
    description: string,
    icon: string,
    link: string,
  }>,

  // Testimonials
  testimonials: Array<{
    id: number,
    name: string,
    text: string,
    rating: number,
  }>,
}
```

---

## Per-Site Pages (doctor/technique specific)

These pages exist on every site but contain doctor-specific content:

| Page | Template Path | What Changes |
|------|--------------|--------------|
| Home | `src/pages/Home.tsx` | Hero images, copy, featured services |
| About Us | `src/pages/AboutUs.tsx` | Practice story, team description |
| Meet Dr. X | `src/pages/MeetDrJohn.tsx` | Renamed per doctor, bio content from SITE |
| New Patient Center | `src/pages/NewPatientCenter.tsx` | Office-specific intake info, images |
| Contact | `src/pages/Contact.tsx` | Uses SITE address/phone/email |
| Schedule Appointment | `src/pages/ScheduleAppointment.tsx` | Embeds booking URL from SITE |

### Technique Pages (conditional — only generated if doctor uses the technique)

| Technique | Path | Generate If |
|-----------|------|-------------|
| Talsky Tonal | `src/pages/TalskyTonal.tsx` | Doctor uses Talsky Tonal |
| KST | `src/pages/KST.tsx` | Doctor uses Koren Specific Technique |
| NetworkSpinal | (not yet built) | Doctor uses NetworkSpinal |

### Specialty Pages (conditional — based on services offered)

| Page | Path | Generate If |
|------|------|-------------|
| Pediatric | `src/pages/Pediatric.tsx` | Services include pediatric |
| Prenatal | `src/pages/Prenatal.tsx` | Services include prenatal |
| Family | `src/pages/Family.tsx` | Services include family |
| Events/Workshops | `src/pages/EventsWorkshops.tsx` | Client runs workshops |

### Guide Pages (conditional — based on feature flags)

| Page | Path | Generate If |
|------|------|-------------|
| Free Guides Hub | `src/pages/FreeGuidesForParents.tsx` | Client offers downloadable guides |
| Individual Guide | `src/pages/RHKNGuide.tsx` etc. | Per-guide landing pages |

---

## Per-Site Config (deploy-time customization)

| File | What to Customize |
|------|------------------|
| `wrangler.toml` | `name` field (Cloudflare Pages project name) |
| `index.html` | `<title>`, `<meta>` description, theme-color, OG tags |
| `tailwind.config.js` | Brand color values under `colors.primary-*` |
| `public/_headers` | CSP `connect-src` (add client's agent backend URL if different) |
| `public/robots.txt` | Sitemap URL, Host URL |
| `public/sitemap.xml` | All page URLs with client's domain |
| `public/llms.txt` | Business name, domain, description for AI discoverability |
| `.github/workflows/deploy.yml` | Cloudflare Pages project name in deploy step |

---

## Per-Site Backend (system prompt + branding)

| File | What to Customize |
|------|------------------|
| `functions/api/chat.ts` | System prompt: doctor name, techniques, specialties, phone number, booking URL |
| `functions/api/form-handler.ts` | Email template: practice name, branding colors in HTML email |
| `ADMIN_PANEL_PROMPT.md` | Agent backend system prompt for admin panel |

### Cloudflare Pages Environment Variables (set in dashboard per site)

| Variable | Value Source |
|----------|-------------|
| `OPENAI_API_KEY` | Client's OpenAI account |
| `RESEND_API_KEY` | Client's Resend account |
| `BREVO_API_KEY` | Client's Brevo account |
| `NOTIFICATION_EMAIL` | Doctor's email address |
| `BREVO_LIST_ID` | Created during onboarding |

---

## Onboarding Questionnaire

Everything needed from a new client to generate a complete site:

### Business Identity
- [ ] Practice name (full)
- [ ] Practice short name
- [ ] Desired domain (e.g., `examplechiro.com`)
- [ ] Practice description (1-2 sentences for SEO)
- [ ] Tagline / motto
- [ ] Founding year
- [ ] Price range (`$`, `$$`, `$$$`)

### Doctor / Practitioner
- [ ] Full name with credentials (e.g., "Dr. Jane Smith, DC")
- [ ] First name, last name
- [ ] Professional title (e.g., "Neurologically-Focused Chiropractor")
- [ ] Bio paragraph (150-300 words)
- [ ] Education institution
- [ ] Headshot photo (high-res, will be converted to WebP)
- [ ] List of expertise / specialties
- [ ] Certifications (degree, certification names)

### Contact Information
- [ ] Phone number (with area code)
- [ ] Email address
- [ ] Street address (street, city, state, zip)
- [ ] Google Place ID (for maps integration)
- [ ] Latitude / longitude (auto-derived from address)

### Business Hours
- [ ] Days open and hours (e.g., "Mon 9am-5pm, Wed 9am-5pm, Fri 9am-5pm")
- [ ] Or "by appointment" for flexible scheduling

### Booking System
- [ ] Booking provider (JaneApp, Calendly, ChiroTouch, etc.)
- [ ] Booking URL

### Branding
- [ ] Logo file (SVG or high-res PNG, will be converted to WebP)
- [ ] Hero image (family/office photo)
- [ ] 4 brand colors:
  - Primary Dark (navy/deep — buttons, headers)
  - Primary (mid-tone — body accents)
  - Primary Light (sky/soft — hover backgrounds)
  - Primary Accent (medium — hover states)
- [ ] Font preferences (or use default Inter/system fonts)

### Social Media (leave blank if not applicable)
- [ ] Facebook page URL
- [ ] Instagram profile URL
- [ ] TikTok profile URL
- [ ] YouTube channel URL
- [ ] LinkedIn profile URL

### Services Offered
- [ ] Which specialties? (check all that apply)
  - Pediatric Chiropractic
  - Prenatal Chiropractic
  - Family Chiropractic
  - Other: _______________
- [ ] Custom service descriptions? (or use template defaults)

### Techniques
- [ ] Which techniques does the doctor use? (generates technique pages)
  - Talsky Tonal Chiropractic
  - NetworkSpinal
  - Koren Specific Technique (KST)
  - Other: _______________

### Features (optional)
- [ ] Enable events/workshops page?
- [ ] Enable free downloadable guides?
  - If yes: guide titles, PDF files, and brief descriptions
- [ ] Enable AnswerHub FAQ page?

### Testimonials
- [ ] 3-5 Google reviews:
  - Reviewer name
  - Review text
  - Star rating (1-5)

### AI Chatbot Context
- [ ] Doctor's approach / philosophy (2-3 sentences)
- [ ] Unique selling points
- [ ] Common patient questions and preferred answers
- [ ] Any topics the chatbot should NOT discuss

### Email Setup (completed during onboarding)
- [ ] Resend account created (API key)
- [ ] Brevo account created (API key + list ID)
- [ ] Sending domain verified in Resend (`forms@clientdomain.com`)

### Conditions
- [ ] Use default 48 conditions? (recommended)
- [ ] Or customize subset: _______________

---

## Site Generation Workflow

```
1. Client fills out Onboarding Questionnaire
   ↓
2. Run generate-new-site.py with questionnaire data
   ↓
3. Script copies template → populates site.ts → places images
   ↓
4. Manual review:
   - Check auto-placed images
   - Review generated site.ts
   - Customize technique pages if needed
   - Adjust Home page copy
   ↓
5. Set up infrastructure:
   - Create GitHub repo
   - Create Cloudflare Pages project
   - Register/transfer domain at Porkbun
   - Set DNS via Porkbun API (see DNS-SETUP-CHECKLIST.md)
   - Set env vars in Cloudflare Pages dashboard
   ↓
6. Push to GitHub → auto-deploys via GitHub Actions
   ↓
7. Configure admin panel at agent.drzach.ai/admin/{project-id}
   ↓
8. Client handoff: verify live site, chatbot, contact form
```
