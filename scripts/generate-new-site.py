#!/usr/bin/env python3
"""
Generate a new client site from the bodymind-chiro-website template.

This script does TWO things:
  1. Copies the entire bodymind-chiro-website as a working template
  2. Generates a new src/data/site.ts from client-content.json and replaces it

The generated site.ts matches the bodymind schema exactly field-for-field,
including all computed exports (activeSocials, aggregateRating, janeUrl, etc.)

Usage:
    python scripts/generate-new-site.py --content client-content.json --output ./new-client-site/ --domain newclient.com
    python scripts/generate-new-site.py --content client-content.json --output ./new-client-site/

Requirements:
    Python 3.8+ (stdlib only)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


# ---------------------------------------------------------------------------
# Source template (absolute path to bodymind-chiro-website)
# ---------------------------------------------------------------------------
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "bodymind-chiro-website"

# Directories/files to exclude when copying the template
EXCLUDE_COPY = {".git", "node_modules", "dist", ".env", "admin-backend"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def escape_ts_string(text: str) -> str:
    """Escape a string for use inside TypeScript single quotes."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "")
    return text


def format_phone_display(phone: str) -> str:
    """Convert a phone number to (XXX) XXX-XXXX display format."""
    digits = re.sub(r"[^\d]", "", phone)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def format_phone_e164(phone: str) -> str:
    """Convert a phone number to +1-XXX-XXX-XXXX format."""
    digits = re.sub(r"[^\d]", "", phone)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return phone


def make_short_name(name: str) -> str:
    """Generate a short name from the business name."""
    cleaned = re.sub(
        r"\s*(Chiropractic|Chiro|Wellness|Health|Center|Centre|Clinic|Office)\s*$",
        "", name, flags=re.I,
    ).strip()
    if cleaned:
        return cleaned
    words = name.split()
    return " ".join(words[:2]) if len(words) >= 2 else name


def make_schema_id(name: str) -> str:
    """Generate a schema ID from a doctor/person name."""
    cleaned = re.sub(r"^(Dr\.?\s*)", "", name, flags=re.I)
    cleaned = re.sub(r",?\s*(D\.?C\.?|DC|M\.?D\.?|DO|NP|PA)\s*$", "", cleaned, flags=re.I)
    return slugify(cleaned)


def parse_doctor_name(full_name: str) -> dict:
    """Parse a full name into components."""
    result = {
        "fullName": full_name,
        "firstName": "",
        "lastName": "",
        "honorificPrefix": "",
        "honorificSuffix": "",
    }
    name = full_name.strip()

    prefix_match = re.match(r"^(Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+", name, re.I)
    if prefix_match:
        result["honorificPrefix"] = "Dr." if "dr" in prefix_match.group(1).lower() else prefix_match.group(1)
        name = name[prefix_match.end():]

    suffix_match = re.search(r",?\s*(D\.?C\.?|DC|M\.?D\.?|MD|DO|NP|PA|CACCP|DACNB)\s*$", name, re.I)
    if suffix_match:
        result["honorificSuffix"] = suffix_match.group(1).replace(".", "")
        name = name[:suffix_match.start()].strip().rstrip(",")

    parts = name.split()
    if parts:
        result["firstName"] = parts[0]
        result["lastName"] = " ".join(parts[1:]) if len(parts) > 1 else ""

    return result


def make_package_name(domain: str) -> str:
    """Generate a package.json name from the domain."""
    # e.g. "newclient.com" -> "newclient-website"
    name = domain.split(".")[0] if domain else "client"
    return slugify(name) + "-website"


def make_wrangler_name(domain: str) -> str:
    """Generate a wrangler.toml name from the domain."""
    name = domain.split(".")[0] if domain else "client"
    return slugify(name)


# ---------------------------------------------------------------------------
# Copy template
# ---------------------------------------------------------------------------

def copy_template(output_dir: Path) -> None:
    """Copy the bodymind-chiro-website template to output_dir, excluding specified dirs/files."""
    if not TEMPLATE_DIR.exists():
        print(f"Error: Template directory not found: {TEMPLATE_DIR}")
        sys.exit(1)

    if output_dir.exists():
        print(f"  Output directory already exists: {output_dir}")
        print("  Merging into existing directory...")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    for item in TEMPLATE_DIR.iterdir():
        if item.name in EXCLUDE_COPY:
            continue

        dest = output_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


# ---------------------------------------------------------------------------
# Generate site.ts
# ---------------------------------------------------------------------------

def generate_site_ts(content: dict, domain: str, image_mapping: dict[str, str] | None = None) -> str:
    """Generate the full site.ts TypeScript source matching the bodymind schema exactly.

    If image_mapping is provided, it maps slot names to placed image paths
    (e.g. {"logo": "/images/logo.webp", "heroFamily": "/images/hero-family.webp"}).
    """

    # --- Resolve domain ---
    if not domain:
        source_url = content.get("sourceUrl", "")
        if source_url:
            from urllib.parse import urlparse
            parsed = urlparse(source_url)
            domain = parsed.netloc.replace("www.", "")
        else:
            domain = "example.com"

    # --- Business identity ---
    biz_name = content.get("businessName", "Business Name")
    short_name = content.get("shortName", "") or make_short_name(biz_name)
    tagline = content.get("tagline", "")
    description = content.get("description", "")
    founding_year = content.get("foundingYear", "")
    price_range = content.get("priceRange", "$$")

    # --- Doctor / practitioner ---
    staff = content.get("staff", [])
    primary_doctor = staff[0] if staff else {}
    dr_full = primary_doctor.get("fullName", "")
    dr_parsed = parse_doctor_name(dr_full) if dr_full else {
        "fullName": "", "firstName": "", "lastName": "",
        "honorificPrefix": "Dr.", "honorificSuffix": "DC",
    }
    dr_credentials = primary_doctor.get("credentials", "") or dr_parsed.get("honorificSuffix", "DC")
    dr_bio = primary_doctor.get("bio", "")
    dr_image = primary_doctor.get("imageUrl", "/images/doctor.webp")
    dr_title = primary_doctor.get("title", "") or f"Chiropractor"
    dr_education = primary_doctor.get("education", "")
    dr_education_wikidata = primary_doctor.get("educationWikidata", "")
    dr_schema_id = make_schema_id(dr_full) if dr_full else "doctor"

    # Build display name with prefix
    dr_display = dr_full
    if dr_full and not dr_full.lower().startswith("dr"):
        dr_display = f"Dr. {dr_full}"

    # Page slug
    first_name = dr_parsed.get("firstName", "doctor") or "doctor"
    dr_page_slug = f"/meet-{slugify(first_name)}"

    # Expertise from services or content
    expertise = primary_doctor.get("expertise", [])
    if not expertise:
        for svc in content.get("services", []):
            name = svc.get("name", "")
            if name and len(name) < 60:
                expertise.append(name)
    if not expertise:
        expertise = ["Chiropractic Care"]

    # Certifications
    certifications = primary_doctor.get("certifications", [])
    if not certifications:
        certifications = [{"type": "degree", "name": "Doctor of Chiropractic"}]

    # --- Contact ---
    phone_raw = content.get("phone", "")
    phone_e164 = format_phone_e164(phone_raw) if phone_raw else ""
    phone_display = format_phone_display(phone_raw) if phone_raw else ""
    email = content.get("email", "")

    # --- Address ---
    addr = content.get("address", {})
    addr_street = addr.get("street", "")
    addr_city = addr.get("city", "")
    addr_region = addr.get("region", "")
    addr_postal = addr.get("postal", "")
    addr_country = addr.get("country", "US")
    addr_formatted = addr.get("formatted", "")
    if not addr_formatted and addr_street:
        parts = [addr_street]
        if addr_city:
            parts.append(addr_city)
        if addr_region:
            parts.append(addr_region)
        if addr_postal:
            parts.append(addr_postal)
        addr_formatted = ", ".join(parts)

    # --- Geo ---
    geo = content.get("geo", {})
    latitude = geo.get("latitude", 0.0)
    longitude = geo.get("longitude", 0.0)
    google_place_id = content.get("googlePlaceId", "PLACEHOLDER_NEED_TO_LOOK_UP")

    # --- Hours ---
    hours_raw = content.get("hours", {})
    if isinstance(hours_raw, list):
        # Legacy: just a list of display strings
        hours_display = hours_raw
        hours_short = []
        hours_structured = []
    elif isinstance(hours_raw, dict):
        hours_display = hours_raw.get("display", [])
        hours_short = hours_raw.get("shortFormat", [])
        hours_structured = hours_raw.get("structured", [])
    else:
        hours_display = []
        hours_short = []
        hours_structured = []

    # --- Booking ---
    booking = content.get("booking", {})
    booking_provider = booking.get("provider", "jane")
    booking_url = booking.get("url", "")
    booking_url_utm = booking.get("urlWithUtm", "")
    if booking_url and not booking_url_utm:
        booking_url_utm = f"{booking_url.rstrip('/')}?utm_source=website&utm_medium=cta&utm_campaign=request-appointment"

    # --- Contact form ---
    contact_form = content.get("contactForm", {})
    cf_provider = contact_form.get("provider", "cloudflare-pages")
    cf_email = contact_form.get("recipientEmail", "") or email

    # --- Socials ---
    socials = content.get("socialMedia", content.get("socials", {}))

    # --- Images ---
    # Prefer auto-classified image_mapping, then content dict, then defaults
    _im = image_mapping or {}
    images = content.get("images", {})
    # If images is a list (scraper output), don't try to access as dict
    if isinstance(images, list):
        images = {}
    img_logo = _im.get("logo") or images.get("logo", "/images/logo.webp")
    img_hero = _im.get("heroFamily") or images.get("heroFamily", images.get("heroImageUrl", "/images/hero-family.webp"))
    img_headshot = _im.get("doctorHeadshot") or images.get("doctorHeadshot", dr_image)
    img_contact = _im.get("contactHero") or images.get("contactHero", "/images/contact-hero.webp")
    img_og = _im.get("ogImage") or images.get("ogImage", img_hero)

    # --- Colors ---
    colors = content.get("colors", {})
    color_theme = colors.get("themeColor", "#002d4e")
    color_primary_dark = colors.get("primaryDark", "#002d4e")
    color_primary = colors.get("primary", "#6383ab")
    color_primary_light = colors.get("primaryLight", "#73b7ce")
    color_primary_accent = colors.get("primaryAccent", "#405e84")

    # --- Services ---
    services = content.get("services", [])

    # --- Testimonials ---
    testimonials = content.get("testimonials", [])

    # --- Custom copy ---
    custom_copy = content.get("customCopy", {})

    # --- Features ---
    features = content.get("features", {})

    # -----------------------------------------------------------------------
    # Build TypeScript source
    # -----------------------------------------------------------------------
    lines = []

    def w(line: str = ""):
        lines.append(line)

    def ws(text: str) -> str:
        return f"'{escape_ts_string(str(text))}'"

    # Header
    w("/**")
    w(" * SITE CONFIGURATION")
    w(" *")
    w(" * This is the SINGLE SOURCE OF TRUTH for all office-specific information.")
    w(" * When setting up a new office website, update this file with the new office's details.")
    w(" *")
    w(" * See NEW_OFFICE_SETUP.md for complete instructions.")
    w(" */")
    w()
    w("export const SITE = {")

    # --- BUSINESS IDENTITY ---
    w("  // ============================================")
    w("  // BUSINESS IDENTITY")
    w("  // ============================================")
    w(f"  name: {ws(biz_name)},")
    w(f"  shortName: {ws(short_name)}, // Used for alternate name in schema")
    w(f"  domain: {ws(domain)},")
    w(f"  description: {ws(description)},")
    w(f"  tagline: {ws(tagline)},")
    w(f"  foundingYear: {ws(founding_year)},")
    w(f"  priceRange: {ws(price_range)},")
    w()

    # --- DOCTOR / PRACTITIONER INFO ---
    w("  // ============================================")
    w("  // DOCTOR / PRACTITIONER INFO")
    w("  // ============================================")
    w("  doctor: {")
    w(f"    fullName: {ws(dr_display)},")
    w(f"    firstName: {ws(dr_parsed['firstName'])},")
    w(f"    lastName: {ws(dr_parsed['lastName'])},")
    w(f"    honorificPrefix: {ws(dr_parsed.get('honorificPrefix', 'Dr.'))},")
    w(f"    honorificSuffix: {ws(dr_credentials)},")
    w(f"    credentials: {ws(dr_credentials)},")
    w(f"    title: {ws(dr_title)},")
    w(f"    bio: {ws(dr_bio)},")
    w(f"    education: {ws(dr_education)},")
    if dr_education_wikidata:
        w(f"    educationWikidata: {ws(dr_education_wikidata)},")
    w(f"    image: {ws(dr_image)},")
    w(f"    pageSlug: {ws(dr_page_slug)},")
    w(f"    schemaId: {ws(dr_schema_id)}, // Used for @id in schema.org")
    w("    expertise: [")
    for exp in expertise:
        w(f"      {ws(exp)},")
    w("    ],")
    w("    certifications: [")
    for cert in certifications:
        if isinstance(cert, dict):
            cert_type = cert.get("type", "certification")
            cert_name = cert.get("name", "")
            w("      {")
            w(f"        type: {ws(cert_type)},")
            w(f"        name: {ws(cert_name)},")
            w("      },")
        else:
            w("      {")
            w(f"        type: 'certification',")
            w(f"        name: {ws(str(cert))},")
            w("      },")
    w("    ],")
    w("  },")
    w()

    # --- CONTACT INFORMATION ---
    w("  // ============================================")
    w("  // CONTACT INFORMATION")
    w("  // ============================================")
    w(f"  phone: {ws(phone_e164)},")
    w(f"  phoneDisplay: {ws(phone_display)},")
    w(f"  email: {ws(email)},")
    w()

    # --- PHYSICAL ADDRESS ---
    w("  // ============================================")
    w("  // PHYSICAL ADDRESS")
    w("  // ============================================")
    w("  address: {")
    w(f"    street: {ws(addr_street)},")
    w(f"    city: {ws(addr_city)},")
    w(f"    region: {ws(addr_region)},")
    w(f"    postal: {ws(addr_postal)},")
    w(f"    country: {ws(addr_country)},")
    w(f"    // Full formatted address for display")
    w(f"    formatted: {ws(addr_formatted)},")
    w("  },")
    w()

    # --- GEOGRAPHIC DATA ---
    w("  // ============================================")
    w("  // GEOGRAPHIC DATA (for maps & schema.org)")
    w("  // ============================================")
    w("  geo: {")
    w(f"    latitude: {latitude},")
    w(f"    longitude: {longitude},")
    w("  },")
    w(f"  // Google Maps place ID (for sameAs links in schema)")
    w(f"  googlePlaceId: {ws(google_place_id)},")
    w()

    # --- BUSINESS HOURS ---
    w("  // ============================================")
    w("  // BUSINESS HOURS")
    w("  // ============================================")
    w("  hours: {")
    w("    // Human-readable format for display")
    w("    display: [")
    for h in hours_display:
        w(f"      {ws(h)},")
    w("    ],")
    w("    // Short format for LocalBusiness schema")
    w("    shortFormat: [")
    for h in hours_short:
        w(f"      {ws(h)},")
    w("    ],")
    w("    // Structured format for OpeningHoursSpecification schema")
    w("    structured: [")
    for h in hours_structured:
        if isinstance(h, dict):
            day = h.get("dayOfWeek", "")
            opens = h.get("opens", "09:00")
            closes = h.get("closes", "17:00")
            w(f"      {{ dayOfWeek: {ws(day)}, opens: {ws(opens)}, closes: {ws(closes)} }},")
        else:
            w(f"      {ws(str(h))},")
    w("    ],")
    w("  },")
    w()

    # --- BOOKING SYSTEM ---
    w("  // ============================================")
    w("  // BOOKING SYSTEM")
    w("  // ============================================")
    w("  booking: {")
    w(f"    provider: {ws(booking_provider)}, // 'jane' | 'formspree' | 'calendly' | etc.")
    w(f"    url: {ws(booking_url)},")
    w(f"    urlWithUtm: {ws(booking_url_utm)},")
    w("  },")
    w()

    # Legacy aliases
    w(f"  // Legacy aliases for backwards compatibility (use booking.url/booking.urlWithUtm for new code)")
    w(f"  janeUrl: {ws(booking_url)},")
    w(f"  janeUrlWithUtm: {ws(booking_url_utm)},")
    w()

    # --- CONTACT FORM ---
    w("  // ============================================")
    w("  // CONTACT FORM")
    w("  // ============================================")
    w("  contactForm: {")
    w(f"    // Contact form posts to Cloudflare Pages Function /api/form-handler")
    w(f"    provider: {ws(cf_provider)},")
    w(f"    // Email where form submissions are sent (via Resend)")
    w(f"    recipientEmail: {ws(cf_email)},")
    w("  },")
    w()

    # --- SOCIAL MEDIA ---
    w("  // ============================================")
    w("  // SOCIAL MEDIA")
    w("  // ============================================")
    w("  socials: {")
    for platform in ["facebook", "instagram", "tiktok", "youtube", "linkedin", "twitter", "pinterest"]:
        url = socials.get(platform, "")
        if platform == "linkedin":
            w(f"    {platform}: {ws(url)},")
        else:
            w(f"    {platform}: {ws(url)},")
    w("    // Optional - leave empty string if not applicable")
    w("  },")
    w()

    # --- IMAGES ---
    w("  // ============================================")
    w("  // IMAGES (standardized paths in /public/images/)")
    w("  // ============================================")
    w("  images: {")
    w(f"    logo: {ws(img_logo)},")
    w(f"    heroFamily: {ws(img_hero)},")
    w(f"    doctorHeadshot: {ws(img_headshot)},")
    w(f"    contactHero: {ws(img_contact)},")
    w(f"    ogImage: {ws(img_og)}, // Default Open Graph image")
    w("  },")
    w()

    # --- BRANDING COLORS ---
    w("  // ============================================")
    w("  // BRANDING COLORS (update tailwind.config.js to match)")
    w("  // ============================================")
    w("  colors: {")
    w(f"    themeColor: {ws(color_theme)}, // Primary dark (navy)")
    w(f"    primaryDark: {ws(color_primary_dark)},")
    w(f"    primary: {ws(color_primary)},")
    w(f"    primaryLight: {ws(color_primary_light)},")
    w(f"    primaryAccent: {ws(color_primary_accent)},")
    w("  },")
    w()

    # --- SERVICES ---
    w("  // ============================================")
    w("  // SERVICES OFFERED")
    w("  // ============================================")
    w("  services: [")
    for i, svc in enumerate(services):
        svc_id = svc.get("id", "") or slugify(svc.get("name", f"service-{i+1}"))
        svc_name = svc.get("name", "")
        svc_short = svc.get("shortName", "")
        if not svc_short:
            svc_short = re.sub(
                r"\s*(Chiropractic|Care|Treatment|Therapy|Services?)\s*$", "",
                svc_name, flags=re.I,
            ).strip() or svc_name
        svc_slug = svc.get("slug", f"/{svc_id}")
        svc_img = _im.get(f"service-{svc_id}") or svc.get("image", svc.get("imageUrl", ""))
        if not svc_img or not svc_img.startswith("/"):
            svc_img = f"/images/{svc_id}.webp"
        svc_desc = svc.get("description", "")

        w("    {")
        w(f"      id: {ws(svc_id)},")
        w(f"      name: {ws(svc_name)},")
        w(f"      shortName: {ws(svc_short)},")
        w(f"      slug: {ws(svc_slug)},")
        w(f"      image: {ws(svc_img)},")
        w(f"      description: {ws(svc_desc)},")
        w("    },")
    w("  ],")
    w()

    # --- TESTIMONIALS ---
    w("  // ============================================")
    w("  // TESTIMONIALS (from Google Reviews)")
    w("  // ============================================")
    w("  testimonials: [")
    for i, test in enumerate(testimonials):
        w("    {")
        w(f"      id: {i + 1},")
        w(f"      name: {ws(test.get('name', ''))},")
        w(f"      text: {ws(test.get('text', ''))},")
        rating = test.get("rating", 5)
        w(f"      rating: {rating},")
        date_pub = test.get("datePublished", "")
        if date_pub:
            w(f"      datePublished: {ws(date_pub)},")
        w("    },")
    w("  ],")
    w()

    # --- CUSTOM COPY OVERRIDES ---
    w("  // ============================================")
    w("  // CUSTOM COPY OVERRIDES")
    w("  // Use these to override default template copy.")
    w("  // Set to null to use template defaults.")
    w("  // ============================================")
    w("  customCopy: {")
    hero_tagline = custom_copy.get("heroTagline")
    about_bio = custom_copy.get("aboutBio")
    footer_tagline = custom_copy.get("footerTagline")
    w(f"    // Hero section tagline")
    w(f"    heroTagline: {ws(hero_tagline) if hero_tagline else 'null'},")
    w(f"    // About page doctor bio (uses doctor.bio if null)")
    w(f"    aboutBio: {ws(about_bio) if about_bio else 'null'},")
    w(f"    // Footer tagline")
    w(f"    footerTagline: {ws(footer_tagline) if footer_tagline else 'null'},")
    w("    // Any page-specific overrides")
    w("    pages: {")
    pages = custom_copy.get("pages", {})
    home = pages.get("home", {})
    about = pages.get("about", {})
    w("      home: {")
    home_headline = home.get("heroHeadline")
    home_sub = home.get("heroSubheadline")
    w(f"        heroHeadline: {ws(home_headline) if home_headline else 'null'},")
    w(f"        heroSubheadline: {ws(home_sub) if home_sub else 'null'},")
    w("      },")
    w("      about: {")
    about_headline = about.get("headline")
    w(f"        headline: {ws(about_headline) if about_headline else 'null'},")
    w("      },")
    w("    },")
    w("  },")
    w()

    # --- FEATURE FLAGS ---
    w("  // ============================================")
    w("  // OFFICE-SPECIFIC FEATURES")
    w("  // Enable/disable features based on what the office offers")
    w("  // ============================================")
    w("  features: {")
    w(f"    // Does this office use Talsky Tonal Chiropractic?")
    w(f"    talskyTonal: {'true' if features.get('talskyTonal', True) else 'false'},")
    w(f"    // Does this office offer workshops/events?")
    w(f"    eventsWorkshops: {'true' if features.get('eventsWorkshops', False) else 'false'},")
    w(f"    // Does this office have downloadable guides?")
    w(f"    freeGuides: {'true' if features.get('freeGuides', False) else 'false'},")
    w(f"    // Does this office offer NetworkSpinal?")
    w(f"    networkSpinal: {'true' if features.get('networkSpinal', True) else 'false'},")
    w(f"    // Does this office offer Koren Specific Technique?")
    w(f"    kst: {'true' if features.get('kst', False) else 'false'},")
    w("  },")

    w("} as const;")
    w()

    # --- COMPUTED VALUES ---
    w("// ============================================")
    w("// COMPUTED VALUES (don't modify these)")
    w("// ============================================")
    w()

    # aggregateRating
    w("// Aggregate rating computed from testimonials")
    w("export const aggregateRating = {")
    if testimonials:
        w("  ratingValue: SITE.testimonials.reduce((sum, t) => sum + t.rating, 0) / SITE.testimonials.length,")
        w("  reviewCount: SITE.testimonials.length,")
    else:
        w("  ratingValue: 5,")
        w("  reviewCount: 0,")
    w("  bestRating: 5,")
    w("  worstRating: 1,")
    w("};")
    w()

    # activeSocials
    w("// Get active social links (non-empty)")
    w("export const activeSocials = Object.entries(SITE.socials)")
    w("  .filter(([, url]) => url)")
    w("  .map(([platform, url]) => ({ platform, url }));")
    w()

    # Legacy exports
    w("// Legacy exports for backwards compatibility with existing components")
    w("export const { janeUrl, janeUrlWithUtm } = {")
    w("  janeUrl: SITE.booking.url,")
    w("  janeUrlWithUtm: SITE.booking.urlWithUtm,")
    w("};")
    w()

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Update tailwind.config.js with brand colors
# ---------------------------------------------------------------------------

def update_tailwind_config(output_dir: Path, colors: dict) -> bool:
    """Update tailwind.config.js with brand colors if provided."""
    if not colors:
        return False

    config_path = output_dir / "tailwind.config.js"
    if not config_path.exists():
        return False

    primary = colors.get("primary", "#6383ab")
    primary_dark = colors.get("primaryDark", "#002d4e")
    primary_light = colors.get("primaryLight", "#73b7ce")
    primary_accent = colors.get("primaryAccent", "#405e84")

    new_config = f"""/** @type {{import('tailwindcss').Config}} */
export default {{
  content: ['./index.html', './src/**/*.{{js,ts,jsx,tsx}}'],
  theme: {{
    extend: {{
      colors: {{
        primary: {{
          DEFAULT: '{primary}',
          dark: '{primary_dark}',
          light: '{primary_light}',
          accent: '{primary_accent}',
        }},
      }},
      fontFamily: {{
        sans: ['Open Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        heading: ['Work Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      }},
    }},
  }},
  plugins: [],
}};
"""

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_config)

    return True


# ---------------------------------------------------------------------------
# Update package.json
# ---------------------------------------------------------------------------

def update_package_json(output_dir: Path, domain: str) -> None:
    """Update the package.json name field for the new client."""
    pkg_path = output_dir / "package.json"
    if not pkg_path.exists():
        return

    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    pkg["name"] = make_package_name(domain)

    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(pkg, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Update wrangler.toml
# ---------------------------------------------------------------------------

def update_wrangler_toml(output_dir: Path, domain: str) -> None:
    """Update the wrangler.toml name field for the new client."""
    toml_path = output_dir / "wrangler.toml"
    if not toml_path.exists():
        return

    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_name = make_wrangler_name(domain)
    content = re.sub(r'^name\s*=\s*"[^"]*"', f'name = "{new_name}"', content, flags=re.MULTILINE)

    with open(toml_path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Image classification and placement
# ---------------------------------------------------------------------------

# Site image slots and their target filenames
IMAGE_SLOTS = {
    "logo": "logo.webp",
    "heroFamily": "hero-family.webp",
    "doctorHeadshot": "dr-headshot.webp",
    "contactHero": "contact-hero.webp",
    "ogImage": "og-image.webp",
}

# Filename keywords per category
_SLOT_FILENAME_KEYWORDS = {
    "logo": ["logo", "brand", "icon", "emblem", "mark"],
    "heroFamily": ["hero", "banner", "cover", "header-bg", "main-bg"],
    "doctorHeadshot": ["headshot", "portrait", "doctor", "dr", "staff", "practitioner", "chiropractor"],
    "contactHero": ["contact", "office", "building", "exterior", "location"],
}

# Alt text keywords per category
_SLOT_ALT_KEYWORDS = {
    "logo": ["logo", "brand"],
    "heroFamily": ["hero", "banner", "family", "welcome"],
    "doctorHeadshot": ["doctor", "dr.", "headshot", "portrait", "chiropractor"],
    "contactHero": ["contact", "office", "location", "building"],
}


def _read_image_dimensions(path: Path) -> tuple[int, int]:
    """Read actual image dimensions using Pillow, falling back to (0, 0)."""
    if Image is None:
        return (0, 0)
    try:
        with Image.open(path) as img:
            return img.size  # (width, height)
    except Exception:
        return (0, 0)


def _aspect_ratio(w: int, h: int) -> float:
    """Return width/height ratio, or 0 if invalid."""
    if h <= 0 or w <= 0:
        return 0.0
    return w / h


def classify_image(path: Path, manifest_entry: dict | None = None) -> dict:
    """Classify a single image file, returning scores per slot.

    Returns: {slot_name: score, ...} where higher score = better match.
    """
    scores: dict[str, int] = {slot: 0 for slot in IMAGE_SLOTS}
    fname = path.stem.lower()
    suffix = path.suffix.lower()

    # Read actual dimensions
    w, h = _read_image_dimensions(path)
    ratio = _aspect_ratio(w, h)

    # Manifest metadata
    alt = ""
    context = ""
    tag = ""
    mw, mh = 0, 0
    if manifest_entry:
        alt = (manifest_entry.get("alt") or "").lower()
        context = (manifest_entry.get("context") or "").lower()
        tag = (manifest_entry.get("tag") or "").lower()
        mw = manifest_entry.get("width", 0) or 0
        mh = manifest_entry.get("height", 0) or 0

    # Use actual dimensions if available, else manifest dimensions
    if w == 0 and mw > 0:
        w, h = mw, mh
        ratio = _aspect_ratio(w, h)

    # --- LOGO ---
    # Scraper tag match
    if tag == "logo":
        scores["logo"] += 15
    # Filename keyword
    if any(kw in fname for kw in _SLOT_FILENAME_KEYWORDS["logo"]):
        scores["logo"] += 10
    # Alt text keyword
    if any(kw in alt for kw in _SLOT_ALT_KEYWORDS["logo"]):
        scores["logo"] += 8
    # Context match
    if "logo" in context or "nav" in context or "header" in context:
        scores["logo"] += 5
    # Small PNG is likely a logo
    if suffix == ".png" and 0 < w < 500 and 0 < h < 500:
        scores["logo"] += 3
    # Very small image is likely logo-ish
    if 0 < w < 300 and 0 < h < 300:
        scores["logo"] += 2

    # --- HERO ---
    if tag == "hero":
        scores["heroFamily"] += 15
    if any(kw in fname for kw in _SLOT_FILENAME_KEYWORDS["heroFamily"]):
        scores["heroFamily"] += 10
    if any(kw in alt for kw in _SLOT_ALT_KEYWORDS["heroFamily"]):
        scores["heroFamily"] += 8
    if "hero" in context or "banner" in context:
        scores["heroFamily"] += 5
    # Wide + large = hero candidate
    if ratio > 1.8 and w > 1000:
        scores["heroFamily"] += 5
    elif ratio > 1.4 and w > 800:
        scores["heroFamily"] += 3
    # Large image bonus
    if w > 1200:
        scores["heroFamily"] += 2

    # --- HEADSHOT ---
    if any(kw in fname for kw in _SLOT_FILENAME_KEYWORDS["doctorHeadshot"]):
        scores["doctorHeadshot"] += 10
    if any(kw in alt for kw in _SLOT_ALT_KEYWORDS["doctorHeadshot"]):
        scores["doctorHeadshot"] += 8
    if "about" in context or "team" in context or "staff" in context or "doctor" in context:
        scores["doctorHeadshot"] += 5
    # Near-square + medium size = headshot
    if 0.7 <= ratio <= 1.3 and 200 <= w <= 1000:
        scores["doctorHeadshot"] += 5
    elif 0.6 <= ratio <= 1.4 and 150 <= w <= 1200:
        scores["doctorHeadshot"] += 2

    # --- CONTACT HERO ---
    if any(kw in fname for kw in _SLOT_FILENAME_KEYWORDS["contactHero"]):
        scores["contactHero"] += 10
    if any(kw in alt for kw in _SLOT_ALT_KEYWORDS["contactHero"]):
        scores["contactHero"] += 8
    if "contact" in context:
        scores["contactHero"] += 5
    # Wide landscape photo = contact hero candidate
    if ratio > 1.3 and w > 600:
        scores["contactHero"] += 3

    return scores


def classify_and_map_images(
    scraped_dir: Path | None,
    local_dir: Path | None,
    manifest: dict,
    services: list[dict] | None = None,
) -> dict:
    """Classify all available images and map best candidates to slots.

    Returns: {
        slot_name: {"primary": Path, "alternatives": [Path, ...]},
        ...,
        "_extras": [Path, ...],
        "_service_map": {service_slug: {"primary": Path, "alternatives": [Path]}},
    }
    """
    # Collect all image files
    image_files: list[Path] = []
    if scraped_dir and scraped_dir.exists():
        for f in scraped_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"):
                image_files.append(f)
    if local_dir and local_dir.exists():
        for f in local_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"):
                image_files.append(f)

    if not image_files:
        return {"_extras": [], "_service_map": {}}

    # Score every image for every slot
    image_scores: dict[str, dict[str, int]] = {}  # path_str -> {slot: score}
    for img_path in image_files:
        manifest_entry = manifest.get(img_path.name)
        scores = classify_image(img_path, manifest_entry)
        image_scores[str(img_path)] = scores

    # Assign best image per slot (greedy: highest score first, no double-assignment)
    assigned: set[str] = set()
    result: dict[str, dict] = {}

    for slot in IMAGE_SLOTS:
        # Rank all images by their score for this slot (descending)
        candidates = sorted(
            image_scores.items(),
            key=lambda x: x[1].get(slot, 0),
            reverse=True,
        )
        primary = None
        alternatives = []
        for path_str, scores in candidates:
            if scores.get(slot, 0) <= 0:
                break
            if path_str not in assigned and primary is None:
                primary = Path(path_str)
                assigned.add(path_str)
            elif scores.get(slot, 0) > 0:
                alternatives.append(Path(path_str))
                if len(alternatives) >= 5:
                    break

        if primary:
            result[slot] = {"primary": primary, "alternatives": alternatives}

    # Service image matching
    service_map: dict[str, dict] = {}
    if services:
        for svc in services:
            svc_name = svc.get("name", "")
            svc_id = svc.get("id", "") or slugify(svc_name)
            if not svc_name:
                continue
            svc_keywords = [w.lower() for w in svc_name.split() if len(w) > 2]
            svc_keywords.append(svc_id.lower())

            best_path = None
            best_score = 0
            svc_alts = []

            for img_path in image_files:
                if str(img_path) in assigned:
                    continue
                fname = img_path.stem.lower()
                alt_text = (manifest.get(img_path.name, {}).get("alt") or "").lower()
                score = 0
                for kw in svc_keywords:
                    if kw in fname:
                        score += 10
                    if kw in alt_text:
                        score += 8
                if score > best_score:
                    if best_path:
                        svc_alts.append(best_path)
                    best_path = img_path
                    best_score = score
                elif score > 0:
                    svc_alts.append(img_path)

            if best_path and best_score > 0:
                assigned.add(str(best_path))
                service_map[svc_id] = {"primary": best_path, "alternatives": svc_alts[:3]}

    # Everything else goes to extras
    extras = [Path(p) for p in image_scores if p not in assigned]
    result["_extras"] = extras
    result["_service_map"] = service_map

    return result


def _convert_to_webp(src: Path, dest: Path) -> bool:
    """Convert an image to WebP format using Pillow. Returns True on success."""
    if Image is None:
        # Fallback: just copy the file as-is
        shutil.copy2(src, dest.with_suffix(src.suffix))
        return False
    try:
        with Image.open(src) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=85)
        return True
    except Exception:
        # Fallback: copy as-is with original extension
        fallback = dest.with_suffix(src.suffix)
        shutil.copy2(src, fallback)
        return False


def place_images(
    mapping: dict,
    output_dir: Path,
    services: list[dict] | None = None,
) -> dict[str, str]:
    """Place classified images into the output site's public/images/ directory.

    Returns a dict of {slot_name: "/images/filename"} for use in site.ts.
    """
    images_dir = output_dir / "public" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    alt_dir = images_dir / "alternatives"
    extras_dir = images_dir / "extras"

    placed: dict[str, str] = {}

    # Place primary images per slot
    for slot, target_filename in IMAGE_SLOTS.items():
        if slot not in mapping:
            continue
        entry = mapping[slot]
        src = entry["primary"]
        dest = images_dir / target_filename

        if _convert_to_webp(src, dest):
            placed[slot] = f"/images/{target_filename}"
        else:
            # Fallback: used original extension
            actual_name = target_filename.rsplit(".", 1)[0] + src.suffix
            placed[slot] = f"/images/{actual_name}"

        # Place alternatives
        alternatives = entry.get("alternatives", [])
        if alternatives:
            slot_alt_dir = alt_dir / slot.replace("Family", "").replace("Headshot", "").lower()
            if slot == "heroFamily":
                slot_alt_dir = alt_dir / "hero"
            elif slot == "doctorHeadshot":
                slot_alt_dir = alt_dir / "headshot"
            elif slot == "contactHero":
                slot_alt_dir = alt_dir / "contact"
            elif slot == "ogImage":
                slot_alt_dir = alt_dir / "og"
            else:
                slot_alt_dir = alt_dir / slot

            slot_alt_dir.mkdir(parents=True, exist_ok=True)
            for alt_path in alternatives[:5]:
                shutil.copy2(alt_path, slot_alt_dir / alt_path.name)

    # OG image: copy from hero if not separately assigned
    if "ogImage" not in placed and "heroFamily" in placed:
        hero_src = images_dir / IMAGE_SLOTS["heroFamily"]
        og_dest = images_dir / IMAGE_SLOTS["ogImage"]
        if hero_src.exists():
            shutil.copy2(hero_src, og_dest)
            placed["ogImage"] = f"/images/{IMAGE_SLOTS['ogImage']}"

    # Place service images
    service_map = mapping.get("_service_map", {})
    if service_map:
        for svc_id, entry in service_map.items():
            src = entry["primary"]
            target_name = f"{svc_id}.webp"
            dest = images_dir / target_name
            if _convert_to_webp(src, dest):
                placed[f"service-{svc_id}"] = f"/images/{target_name}"
            else:
                actual_name = f"{svc_id}{src.suffix}"
                placed[f"service-{svc_id}"] = f"/images/{actual_name}"

            svc_alts = entry.get("alternatives", [])
            if svc_alts:
                svc_alt_dir = alt_dir / "services" / svc_id
                svc_alt_dir.mkdir(parents=True, exist_ok=True)
                for alt_path in svc_alts[:3]:
                    shutil.copy2(alt_path, svc_alt_dir / alt_path.name)

    # Place extras
    extras = mapping.get("_extras", [])
    if extras:
        extras_dir.mkdir(parents=True, exist_ok=True)
        for extra_path in extras:
            shutil.copy2(extra_path, extras_dir / extra_path.name)

    return placed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a new client website from the bodymind-chiro-website template.\n\n"
            "Copies the template, generates a new site.ts from client-content.json,\n"
            "and updates configuration files for the new client."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--content",
        required=True,
        help="Path to client-content.json from the scrape/extraction step",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the new client site",
    )
    parser.add_argument(
        "--domain",
        default="",
        help="Override the domain name (default: extracted from client-content.json sourceUrl)",
    )
    parser.add_argument(
        "--local-images",
        default="",
        help="Optional directory of additional images to include in classification",
    )
    args = parser.parse_args()

    content_path = Path(args.content).resolve()
    output_dir = Path(args.output).resolve()
    domain = args.domain
    local_images_dir = Path(args.local_images).resolve() if args.local_images else None

    # Validate input
    if not content_path.exists():
        print(f"Error: Content file not found: {content_path}")
        sys.exit(1)

    if not TEMPLATE_DIR.exists():
        print(f"Error: Template directory not found: {TEMPLATE_DIR}")
        print(f"  Expected at: {TEMPLATE_DIR}")
        sys.exit(1)

    # Load content
    with open(content_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    # Resolve domain
    if not domain:
        source_url = content.get("sourceUrl", "")
        if source_url:
            from urllib.parse import urlparse
            parsed = urlparse(source_url)
            domain = parsed.netloc.replace("www.", "")
        else:
            domain = "example.com"

    biz_name = content.get("businessName", "(unknown)")

    print("=" * 60)
    print("  New Site Generator")
    print("=" * 60)
    print(f"  Business:  {biz_name}")
    print(f"  Domain:    {domain}")
    print(f"  Content:   {content_path}")
    print(f"  Output:    {output_dir}")
    print(f"  Template:  {TEMPLATE_DIR}")
    print("=" * 60)
    print()

    # Step 1: Copy template
    print("[1/7] Copying template...")
    copy_template(output_dir)
    print(f"  Copied template to {output_dir}")

    # Step 2: Update tailwind.config.js if colors provided
    print("[2/7] Updating tailwind.config.js...")
    colors = content.get("colors", {})
    if colors and update_tailwind_config(output_dir, colors):
        print("  Updated with brand colors")
    else:
        print("  No brand colors provided, keeping template defaults")

    # Step 3: Classify and place images
    print("[3/7] Classifying and placing images...")
    scraped_images_dir = content_path.parent / "images"
    manifest = {}
    manifest_path = scraped_images_dir / "image-manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"  Loaded image manifest ({len(manifest)} entries)")

    image_mapping_result = classify_and_map_images(
        scraped_dir=scraped_images_dir if scraped_images_dir.exists() else None,
        local_dir=local_images_dir,
        manifest=manifest,
        services=content.get("services", []),
    )
    placed_images = place_images(image_mapping_result, output_dir, services=content.get("services", []))

    # Print classification summary
    slot_count = sum(1 for k in placed_images if not k.startswith("service-"))
    svc_count = sum(1 for k in placed_images if k.startswith("service-"))
    extras_count = len(image_mapping_result.get("_extras", []))
    print(f"  Placed {slot_count} slot image(s), {svc_count} service image(s)")
    print(f"  {extras_count} unclassified image(s) copied to extras/")

    # Print slot assignment table
    print()
    print("  Image Slot Assignments:")
    print("  " + "-" * 55)
    for slot in IMAGE_SLOTS:
        if slot in placed_images:
            src_name = image_mapping_result[slot]["primary"].name
            alt_count = len(image_mapping_result[slot].get("alternatives", []))
            print(f"    {slot:<18} <- {src_name}  ({alt_count} alt(s))")
        else:
            print(f"    {slot:<18}    (no match - using default)")
    for k, v in sorted(placed_images.items()):
        if k.startswith("service-"):
            svc_id = k.replace("service-", "")
            src_name = image_mapping_result["_service_map"][svc_id]["primary"].name
            print(f"    {k:<18} <- {src_name}")
    print("  " + "-" * 55)
    print()

    # Step 4: Generate site.ts with placed image paths
    print("[4/7] Generating site.ts...")
    ts_source = generate_site_ts(content, domain=domain, image_mapping=placed_images)
    site_ts_path = output_dir / "src" / "data" / "site.ts"
    site_ts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(site_ts_path, "w", encoding="utf-8") as f:
        f.write(ts_source)
    print(f"  Generated {site_ts_path}")
    print(f"    Lines: {len(ts_source.splitlines())}")
    print(f"    Size:  {len(ts_source):,} bytes")

    # Step 5: Update package.json
    print("[5/7] Updating package.json...")
    update_package_json(output_dir, domain)
    print(f"  Set name to: {make_package_name(domain)}")

    # Step 6: Update wrangler.toml
    print("[6/7] Updating wrangler.toml...")
    update_wrangler_toml(output_dir, domain)
    print(f"  Set name to: {make_wrangler_name(domain)}")

    # Step 7: Summary
    print("[7/7] Summary")
    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()
    print(f"  Services:     {len(content.get('services', []))}")
    print(f"  Testimonials: {len(content.get('testimonials', []))}")
    print(f"  Staff:        {len(content.get('staff', []))}")
    print(f"  Images:       {slot_count} slots filled, {svc_count} service images, {extras_count} extras")
    print()
    print("  Next steps:")
    print(f"    1. cd {output_dir}")
    print(f"    2. Review src/data/site.ts and fill in missing values")
    print(f"       - foundingYear, booking URL, googlePlaceId, geo coordinates")
    print(f"       - Verify doctor bio, expertise, certifications")
    print(f"    3. Review auto-placed images in public/images/")
    print(f"       - Swap with alternatives from public/images/alternatives/ if needed")
    print(f"       - Check extras/ for any useful unclassified images")
    print(f"    4. npm install")
    print(f"    5. npm run dev  (to preview locally)")
    print(f"    6. npm run build  (to build for production)")
    print(f"    7. Configure Cloudflare Pages deployment:")
    print(f"       - Create Pages project named: {make_wrangler_name(domain)}")
    print(f"       - Set custom domain: {domain}")
    print(f"       - Add environment variables in Cloudflare dashboard")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
