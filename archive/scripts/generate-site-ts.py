#!/usr/bin/env python3
"""
Generate a valid TypeScript site.ts from extracted client content JSON.

Takes the output of extract-site-content.py (client-content.json) and produces
a TypeScript file matching the bodymind/talsky site.ts schema used across
chiropractic site projects.

The generated site.ts includes:
  - SITE const with full business data, services, testimonials, FAQs
  - Computed exports: activeSocials, aggregateRating
  - TypeScript `as const` assertion for type safety

Usage:
    python generate-site-ts.py --input client-content.json --output src/data/site.ts --domain example.com
    python generate-site-ts.py --input client-content.json  # uses domain from content

Requirements:
    pip install -r requirements.txt  # only stdlib needed for this script
"""

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path


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
    """Generate a short name / abbreviation from the business name."""
    # Remove common suffixes
    cleaned = re.sub(
        r"\s*(Chiropractic|Chiro|Wellness|Health|Center|Centre|Clinic|Office)\s*$",
        "",
        name,
        flags=re.I,
    ).strip()
    if cleaned:
        return cleaned
    # Fallback: first two words
    words = name.split()
    return " ".join(words[:2]) if len(words) >= 2 else name


def make_schema_id(name: str) -> str:
    """Generate a schema ID from a doctor/person name."""
    # Remove "Dr." prefix and credentials suffix
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

    # Extract prefix
    prefix_match = re.match(r"^(Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+", name, re.I)
    if prefix_match:
        result["honorificPrefix"] = "Dr." if "dr" in prefix_match.group(1).lower() else prefix_match.group(1)
        name = name[prefix_match.end():]

    # Extract suffix/credentials
    suffix_match = re.search(r",?\s*(D\.?C\.?|DC|M\.?D\.?|MD|DO|NP|PA|CACCP|DACNB)\s*$", name, re.I)
    if suffix_match:
        result["honorificSuffix"] = suffix_match.group(1).replace(".", "")
        name = name[: suffix_match.start()].strip().rstrip(",")

    parts = name.split()
    if parts:
        result["firstName"] = parts[0]
        result["lastName"] = " ".join(parts[1:]) if len(parts) > 1 else ""

    return result


def generate_faqs_from_services(business_name: str, services: list, doctor_name: str) -> list:
    """Generate FAQ entries from the services list when none are provided."""
    faqs = []

    # General FAQ
    faqs.append({
        "question": f"What services does {business_name} offer?",
        "answer": (
            f"{business_name} offers a range of chiropractic services including "
            + ", ".join(s["name"] for s in services[:3])
            + (". " if services else ". ")
            + "Contact us to learn more about how we can help you."
        ),
    })

    # Per-service FAQs (up to 3)
    for svc in services[:3]:
        desc = svc.get("description", "")
        if desc:
            faqs.append({
                "question": f"What is {svc['name']}?",
                "answer": desc,
            })

    # Appointment FAQ
    faqs.append({
        "question": f"How do I schedule an appointment with {business_name}?",
        "answer": (
            f"You can schedule an appointment by calling our office or using the online "
            f"booking system on our website. New patients are always welcome."
        ),
    })

    # Insurance FAQ
    faqs.append({
        "question": "Do you accept insurance?",
        "answer": (
            "Please contact our office directly to discuss insurance coverage and "
            "payment options. We strive to make chiropractic care accessible to everyone."
        ),
    })

    return faqs


# ---------------------------------------------------------------------------
# TypeScript generation
# ---------------------------------------------------------------------------

def generate_site_ts(content: dict, domain: str = "") -> str:
    """Generate the full site.ts TypeScript source from content JSON."""

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
    short_name = make_short_name(biz_name)
    tagline = content.get("tagline", "")
    description = content.get("description", "")

    # --- Doctor / founder ---
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
    dr_title = primary_doctor.get("title", "") or f"Chiropractor, {biz_name}"
    dr_schema_id = make_schema_id(dr_full) if dr_full else "doctor"

    # Build display name with prefix
    dr_display = dr_full
    if dr_full and not dr_full.lower().startswith("dr"):
        dr_display = f"Dr. {dr_full}"

    # Expertise from services
    expertise = []
    for svc in content.get("services", []):
        name = svc.get("name", "")
        if name and len(name) < 60:
            expertise.append(name)
    if not expertise:
        expertise = ["Chiropractic Care"]

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

    # --- Hours ---
    hours = content.get("hours", [])

    # --- Socials ---
    socials = content.get("socialMedia", {})

    # --- Images ---
    logo_url = content.get("logoUrl", "/images/logo.webp")
    hero_url = content.get("heroImageUrl", "/images/hero-family.webp")

    # --- Services ---
    services = content.get("services", [])

    # --- Testimonials ---
    testimonials = content.get("testimonials", [])

    # --- FAQs ---
    faqs = generate_faqs_from_services(biz_name, services, dr_display)

    # --- Build the TypeScript source ---
    lines = []

    def w(line: str = ""):
        """Write a line."""
        lines.append(line)

    def ws(text: str):
        """Write a single-quoted TypeScript string value."""
        return f"'{escape_ts_string(text)}'"

    # Header comment
    w("/**")
    w(" * SITE CONFIGURATION")
    w(" *")
    w(f" * Single source of truth for all {biz_name} site data.")
    w(f" * Generated from: {content.get('sourceUrl', 'client-content.json')}")
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
    w(f"  shortName: {ws(short_name)},")
    w(f"  domain: {ws(domain)},")
    w(f"  description: {ws(description)},")
    w(f"  tagline: {ws(tagline)},")
    w(f"  foundingYear: '',")
    w(f"  priceRange: '$$',")
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
    w(f"    education: '',")
    w(f"    image: {ws(dr_image)},")
    w(f"    pageSlug: '/meet-{slugify(dr_parsed['firstName'] or 'doctor')}',")
    w(f"    schemaId: {ws(dr_schema_id)},")
    w("    expertise: [")
    for exp in expertise:
        w(f"      {ws(exp)},")
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
    w(f"    formatted: {ws(addr_formatted)},")
    w("  },")
    w()

    # --- BUSINESS HOURS ---
    w("  // ============================================")
    w("  // BUSINESS HOURS")
    w("  // ============================================")
    w("  hours: {")
    w("    display: [")
    for h in hours:
        w(f"      {ws(h)},")
    w("    ],")
    w("    shortFormat: [],")
    w("    structured: [],")
    w("  },")
    w()

    # --- BOOKING SYSTEM ---
    w("  // ============================================")
    w("  // BOOKING SYSTEM")
    w("  // ============================================")
    w("  booking: {")
    w("    provider: 'jane',")
    w("    url: '',")
    w("    urlWithUtm: '',")
    w("  },")
    w()

    # --- CONTACT FORM ---
    w("  // ============================================")
    w("  // CONTACT FORM")
    w("  // ============================================")
    w("  contactForm: {")
    w("    provider: 'cloudflare-pages',")
    w(f"    recipientEmail: {ws(email)},")
    w("  },")
    w()

    # --- SOCIAL MEDIA ---
    w("  // ============================================")
    w("  // SOCIAL MEDIA")
    w("  // ============================================")
    w("  socials: {")
    for platform in ["facebook", "instagram", "tiktok", "youtube", "linkedin", "twitter", "pinterest"]:
        url = socials.get(platform, "")
        w(f"    {platform}: {ws(url)},")
    w("  },")
    w()

    # --- IMAGES ---
    w("  // ============================================")
    w("  // IMAGES")
    w("  // ============================================")
    w("  images: {")
    w(f"    logo: '/images/logo.webp',")
    w(f"    heroFamily: '/images/hero-family.webp',")
    w(f"    doctorHeadshot: '/images/doctor.webp',")
    w(f"    contactHero: '/images/contact-hero.webp',")
    w(f"    ogImage: '/images/hero-family.webp',")
    w("  },")
    w()

    # --- BRANDING COLORS ---
    w("  // ============================================")
    w("  // BRANDING COLORS (update tailwind.config.js to match)")
    w("  // ============================================")
    w("  colors: {")
    w("    themeColor: '#6383ab',")
    w("    primaryDark: '#002d4e',")
    w("    primary: '#6383ab',")
    w("    primaryLight: '#73b7ce',")
    w("    primaryAccent: '#405e84',")
    w("  },")
    w()

    # --- SERVICES ---
    w("  // ============================================")
    w("  // SERVICES OFFERED")
    w("  // ============================================")
    w("  services: [")
    for i, svc in enumerate(services):
        svc_id = slugify(svc.get("name", f"service-{i+1}"))
        svc_name = svc.get("name", "")
        svc_short = re.sub(
            r"\s*(Chiropractic|Care|Treatment|Therapy|Services?)\s*$", "",
            svc_name, flags=re.I,
        ).strip() or svc_name
        svc_desc = svc.get("description", "")
        svc_img = svc.get("imageUrl", "")
        # Normalize image to local path for the generated site
        if not svc_img or not svc_img.startswith("/"):
            svc_img = f"/images/{svc_id}.webp"

        w("    {")
        w(f"      id: {ws(svc_id)},")
        w(f"      name: {ws(svc_name)},")
        w(f"      shortName: {ws(svc_short)},")
        w(f"      slug: '/{svc_id}',")
        w(f"      image: {ws(svc_img)},")
        w(f"      description: {ws(svc_desc)},")
        w("    },")
    w("  ],")
    w()

    # --- TESTIMONIALS ---
    w("  // ============================================")
    w("  // TESTIMONIALS")
    w("  // ============================================")
    w("  testimonials: [")
    for i, test in enumerate(testimonials):
        w("    {")
        w(f"      id: {i + 1},")
        w(f"      name: {ws(test.get('name', ''))},")
        w(f"      text: {ws(test.get('text', ''))},")
        rating = test.get("rating")
        if rating is not None:
            w(f"      rating: {rating},")
        else:
            w(f"      rating: 5,")
        w("    },")
    w("  ],")
    w()

    # --- FAQS ---
    w("  // ============================================")
    w("  // FAQs (for schema.org FAQPage)")
    w("  // ============================================")
    w("  faqs: [")
    for faq in faqs:
        w("    {")
        w(f"      question: {ws(faq['question'])},")
        w(f"      answer: {ws(faq['answer'])},")
        w("    },")
    w("  ],")
    w()

    # --- CUSTOM COPY OVERRIDES ---
    w("  // ============================================")
    w("  // CUSTOM COPY OVERRIDES")
    w("  // ============================================")
    w("  customCopy: {")
    w("    heroTagline: null,")
    w("    aboutBio: null,")
    w("    footerTagline: null,")
    w("    pages: {")
    w("      home: {")
    w("        heroHeadline: null,")
    w("        heroSubheadline: null,")
    w("      },")
    w("      about: {")
    w("        headline: null,")
    w("      },")
    w("    },")
    w("  },")
    w()

    # --- FEATURE FLAGS ---
    w("  // ============================================")
    w("  // FEATURE FLAGS")
    w("  // ============================================")
    w("  features: {")
    w("    talskyTonal: true,")
    w("    insightScans: true,")
    w("    eventsWorkshops: true,")
    w("    freeGuides: true,")
    w("  },")

    w("} as const;")
    w()

    # --- COMPUTED VALUES ---
    w("// ============================================")
    w("// COMPUTED VALUES (don't modify these)")
    w("// ============================================")
    w()

    # aggregateRating
    if testimonials:
        has_ratings = any(t.get("rating") is not None for t in testimonials)
        if has_ratings:
            w("// Aggregate rating computed from testimonials")
            w("export const aggregateRating = {")
            w("  ratingValue: SITE.testimonials.reduce((sum, t) => sum + t.rating, 0) / SITE.testimonials.length,")
            w("  reviewCount: SITE.testimonials.length,")
            w("  bestRating: 5,")
            w("  worstRating: 1,")
            w("};")
        else:
            w("export const aggregateRating = {")
            w("  ratingValue: 5,")
            w("  reviewCount: SITE.testimonials.length,")
            w("  bestRating: 5,")
            w("  worstRating: 1,")
            w("};")
    else:
        w("export const aggregateRating = {")
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

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a TypeScript site.ts configuration file from extracted client content.\n\n"
            "Reads client-content.json (from extract-site-content.py) and produces a valid\n"
            "TypeScript file matching the bodymind/talsky site.ts schema."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default="client-content.json",
        help="Input JSON file from extract-site-content.py (default: client-content.json)",
    )
    parser.add_argument(
        "--output",
        default="site.ts",
        help="Output TypeScript file path (default: site.ts)",
    )
    parser.add_argument(
        "--domain",
        default="",
        help="Override the domain name (default: extracted from source URL)",
    )
    args = parser.parse_args()

    # Read input JSON
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    print("=" * 60)
    print("Site TypeScript Generator")
    print("=" * 60)
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")
    if args.domain:
        print(f"  Domain: {args.domain}")
    print("=" * 60)

    with open(input_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    print(f"  Loaded content for: {content.get('businessName', '(unknown)')}")
    print(f"  Services:     {len(content.get('services', []))}")
    print(f"  Testimonials: {len(content.get('testimonials', []))}")
    print(f"  Staff:        {len(content.get('staff', []))}")

    # Generate TypeScript
    ts_source = generate_site_ts(content, domain=args.domain)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_source)

    print()
    print(f"Generated: {output_path}")
    print(f"  Lines: {len(ts_source.splitlines())}")
    print(f"  Size:  {len(ts_source):,} bytes")
    print()
    print("Next steps:")
    print(f"  1. Review {output_path} and fill in missing values (foundingYear, booking URL, etc.)")
    print("  2. Update branding colors to match the client's brand")
    print("  3. Replace placeholder image paths with actual images")
    print("  4. Copy to your project: cp site.ts src/data/site.ts")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
