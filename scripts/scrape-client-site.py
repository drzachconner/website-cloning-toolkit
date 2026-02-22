#!/usr/bin/env python3
"""
Scrape business content from a client's existing website.

Uses Playwright (async) for JS rendering, extracts structured business data
into client-content.json and downloads images locally.

Handles platform-specific patterns:
  - Wix: lazy-loaded images (data-src, wix-image), dynamic content rendering
  - Squarespace: JSON API at /page?format=json, structured collection data
  - WordPress: REST API at /wp-json/wp/v2/, common theme patterns
  - Other: Generic HTML + schema.org extraction

Usage:
    python scripts/scrape-client-site.py --url https://example.com --output ./output/

Requirements:
    pip install playwright beautifulsoup4 httpx lxml
    playwright install chromium
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Error: playwright is required. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

def empty_content() -> dict:
    """Return an empty content structure matching the output schema."""
    return {
        "businessName": "",
        "shortName": "",
        "tagline": "",
        "description": "",
        "phone": "",
        "email": "",
        "address": {
            "street": "",
            "city": "",
            "region": "",
            "postal": "",
            "country": "",
        },
        "hours": [],
        "doctor": {
            "fullName": "",
            "credentials": "",
            "title": "",
            "bio": "",
            "education": "",
        },
        "services": [],
        "testimonials": [],
        "socials": {
            "facebook": "",
            "instagram": "",
            "youtube": "",
            "tiktok": "",
            "linkedin": "",
        },
        "logoUrl": "",
        "heroImageUrl": "",
        "images": [],
        "sourceUrl": "",
        "extractedAt": "",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalize whitespace and strip a string."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def print_step(msg: str):
    """Print a progress step."""
    print(f"  -> {msg}")


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform(html: str, url: str) -> str:
    """Detect whether a site is built on Wix, Squarespace, WordPress, or other."""
    html_lower = html.lower()

    wix_signals = [
        "wix-image", "wixsite.com", "_wix_browser_sess", "wix-dropdown-menu",
        "x-wix-", "static.wixstatic.com", "wixmp-", 'data-mesh-id="', "wix-bg-image",
    ]
    wix_score = sum(1 for sig in wix_signals if sig in html_lower)

    sq_signals = [
        "squarespace", "static1.squarespace.com", "sqs-block", "sqs-layout",
        "sqsp-", '"siteid"', "squarespace-cdn.com", "sqs-slide",
    ]
    sq_score = sum(1 for sig in sq_signals if sig in html_lower)

    wp_signals = [
        "wp-content/", "wp-includes/", "wp-json", "wordpress",
        'name="generator" content="wordpress', "wp-block-", "wp-element",
        "wp-emoji", "/xmlrpc.php",
    ]
    wp_score = sum(1 for sig in wp_signals if sig in html_lower)

    scores = {"wix": wix_score, "squarespace": sq_score, "wordpress": wp_score}
    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return "other"


# ---------------------------------------------------------------------------
# Schema.org JSON-LD extraction
# ---------------------------------------------------------------------------

def extract_jsonld(soup: BeautifulSoup) -> list[dict]:
    """Parse all JSON-LD blocks from the page into a flat list of objects."""
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                # Handle @graph wrapper
                if "@graph" in data:
                    results.extend(data["@graph"])
                else:
                    results.append(data)
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return results


def find_jsonld_by_type(jsonld: list[dict], types: list[str]) -> dict | None:
    """Find the first JSON-LD object matching any of the given @type values."""
    for obj in jsonld:
        obj_type = obj.get("@type", "")
        if isinstance(obj_type, list):
            if any(t in types for t in obj_type):
                return obj
        elif obj_type in types:
            return obj
    return None


# ---------------------------------------------------------------------------
# Content extraction functions
# ---------------------------------------------------------------------------

def extract_business_name(soup: BeautifulSoup, jsonld: list[dict], url: str) -> str:
    """Extract the business name from multiple sources."""
    # JSON-LD
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        name = biz.get("name", "")
        if name:
            return clean_text(name)

    # og:site_name
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return clean_text(og["content"])

    # Title tag (before separator)
    title = soup.find("title")
    if title and title.string:
        text = title.string.strip()
        for sep in [" | ", " - ", " \u2013 ", " \u2014 "]:
            if sep in text:
                return clean_text(text.split(sep)[0])
        return clean_text(text)

    return ""


def derive_short_name(business_name: str) -> str:
    """Derive a short name from the full business name."""
    if not business_name:
        return ""
    # Remove common suffixes
    short = re.sub(
        r"\s*(Chiropractic|Clinic|Center|Centre|Wellness|Health|LLC|Inc|PC|PLLC|PA|P\.?A\.?)\.?$",
        "", business_name, flags=re.I,
    ).strip().rstrip(",")
    # If still long, take first two words
    words = short.split()
    if len(words) > 3:
        short = " ".join(words[:2])
    return short if short else business_name


def extract_tagline(soup: BeautifulSoup) -> str:
    """Extract a tagline or slogan from the page."""
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        content = og["content"].strip()
        if len(content) < 120:
            return clean_text(content)

    for selector in [
        "[class*='tagline']", "[class*='slogan']", "[class*='subtitle']",
        "[class*='hero'] h2", "[class*='hero'] p",
    ]:
        elem = soup.select_one(selector)
        if elem:
            text = clean_text(elem.get_text())
            if 3 < len(text) < 150:
                return text

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return clean_text(meta["content"][:150])

    return ""


def extract_description(soup: BeautifulSoup, jsonld: list[dict]) -> str:
    """Extract the business description."""
    # JSON-LD description
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz and biz.get("description"):
        return clean_text(biz["description"])

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return clean_text(meta["content"])

    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return clean_text(og["content"])

    return ""


def extract_phone(soup: BeautifulSoup, jsonld: list[dict], html: str) -> str:
    """Find a phone number from JSON-LD, links, and text patterns."""
    # JSON-LD
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        phone = biz.get("telephone", "")
        if phone:
            return clean_text(phone)

    # tel: links
    tel_link = soup.find("a", href=re.compile(r"^tel:", re.I))
    if tel_link:
        return tel_link["href"].replace("tel:", "").strip()

    # Regex fallback
    phone_pattern = re.compile(r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
    match = phone_pattern.search(html)
    if match:
        return match.group(1).strip()
    return ""


def extract_email(soup: BeautifulSoup, jsonld: list[dict], html: str) -> str:
    """Find an email address from JSON-LD, mailto links, or text patterns."""
    # JSON-LD
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        email = biz.get("email", "")
        if email:
            return clean_text(email)

    mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
    if mailto:
        return mailto["href"].replace("mailto:", "").split("?")[0].strip()

    email_pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    match = email_pattern.search(html)
    if match:
        return match.group(0)
    return ""


def extract_address(soup: BeautifulSoup, jsonld: list[dict], html: str) -> dict:
    """Extract a street address from JSON-LD or text patterns."""
    address = {"street": "", "city": "", "region": "", "postal": "", "country": ""}

    # JSON-LD
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        addr = biz.get("address", {})
        if isinstance(addr, dict):
            address["street"] = clean_text(addr.get("streetAddress", ""))
            address["city"] = clean_text(addr.get("addressLocality", ""))
            address["region"] = clean_text(addr.get("addressRegion", ""))
            address["postal"] = clean_text(addr.get("postalCode", ""))
            address["country"] = clean_text(addr.get("addressCountry", "US"))
            if address["street"]:
                return address

    # Regex fallback
    addr_pattern = re.compile(
        r"(\d{1,5}\s[\w\s.]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl|Pkwy|Ste|Suite|#)[\w\s.,#-]*)"
        r"[,\s]+([\w\s]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)",
        re.I,
    )
    text = soup.get_text(separator=" ")
    match = addr_pattern.search(text)
    if match:
        address["street"] = clean_text(match.group(1))
        address["city"] = clean_text(match.group(2))
        address["region"] = match.group(3).upper()
        address["postal"] = match.group(4)

    return address


def extract_hours(soup: BeautifulSoup, jsonld: list[dict]) -> list[dict]:
    """Extract business hours as [{days, hours}]."""
    hours = []

    # JSON-LD openingHoursSpecification
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        specs = biz.get("openingHoursSpecification", [])
        if not isinstance(specs, list):
            specs = [specs]
        for spec in specs:
            day = spec.get("dayOfWeek", "")
            if isinstance(day, list):
                day = ", ".join(day)
            opens = spec.get("opens", "")
            closes = spec.get("closes", "")
            if day:
                hours.append({"days": clean_text(day), "hours": f"{opens} - {closes}"})
        if hours:
            return hours

    # Regex fallback
    day_pattern = re.compile(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"[:\s]*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*[-\u2013]\s*"
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)",
        re.I,
    )
    text = soup.get_text(separator="\n")
    for match in day_pattern.finditer(text):
        hours.append({"days": match.group(1), "hours": f"{match.group(2)} - {match.group(3)}"})

    return hours


def extract_social_links(soup: BeautifulSoup, jsonld: list[dict]) -> dict:
    """Extract social media URLs from JSON-LD and anchor tags."""
    socials = {"facebook": "", "instagram": "", "youtube": "", "tiktok": "", "linkedin": ""}

    # JSON-LD sameAs
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        same_as = biz.get("sameAs", [])
        if isinstance(same_as, str):
            same_as = [same_as]
        for url in same_as:
            url_lower = url.lower()
            if "facebook.com" in url_lower and not socials["facebook"]:
                socials["facebook"] = url
            elif "instagram.com" in url_lower and not socials["instagram"]:
                socials["instagram"] = url
            elif ("youtube.com" in url_lower or "youtu.be" in url_lower) and not socials["youtube"]:
                socials["youtube"] = url
            elif "tiktok.com" in url_lower and not socials["tiktok"]:
                socials["tiktok"] = url
            elif "linkedin.com" in url_lower and not socials["linkedin"]:
                socials["linkedin"] = url

    # HTML anchor fallback
    platform_patterns = {
        "facebook": r"facebook\.com",
        "instagram": r"instagram\.com",
        "youtube": r"youtube\.com|youtu\.be",
        "tiktok": r"tiktok\.com",
        "linkedin": r"linkedin\.com",
    }
    for link in soup.find_all("a", href=True):
        href = link["href"]
        for platform, pattern in platform_patterns.items():
            if re.search(pattern, href, re.I) and not socials[platform]:
                socials[platform] = href

    return socials


def extract_logo_url(soup: BeautifulSoup, jsonld: list[dict], base_url: str) -> str:
    """Find the site logo URL."""
    # JSON-LD logo
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService", "Organization", "Dentist", "Physician",
    ])
    if biz:
        logo = biz.get("logo", "")
        if isinstance(logo, dict):
            logo = logo.get("url", "")
        if logo:
            return urljoin(base_url, logo)

    # img with logo-like attributes
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").lower()
        src = img.get("src") or img.get("data-src") or ""
        classes = " ".join(img.get("class", []))
        parent_id = img.parent.get("id", "") if img.parent else ""

        if any(kw in alt for kw in ["logo", "brand"]):
            return urljoin(base_url, src) if src else ""
        if any(kw in classes for kw in ["logo", "site-logo", "brand"]):
            return urljoin(base_url, src) if src else ""
        if "logo" in parent_id.lower():
            return urljoin(base_url, src) if src else ""

    # Wix-specific logo by ID
    for elem in soup.find_all(attrs={"id": re.compile(r"logo", re.I)}):
        img = elem.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                return urljoin(base_url, src)

    # Header image fallback
    header = soup.find("header") or soup.find(attrs={"role": "banner"})
    if header:
        img = header.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                return urljoin(base_url, src)

    return ""


def extract_hero_image(soup: BeautifulSoup, base_url: str) -> str:
    """Find the hero/banner image URL."""
    # Hero section images
    for selector in ["[class*='hero']", "[class*='banner']", "[class*='Hero']", "[class*='Banner']"]:
        section = soup.select_one(selector)
        if section:
            img = section.find("img")
            if img:
                src = img.get("src") or img.get("data-src") or ""
                if src:
                    return urljoin(base_url, src)
            # CSS background images via style attr
            style = section.get("style", "")
            bg_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if bg_match:
                return urljoin(base_url, bg_match.group(1))

    # First large image on page as fallback
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or "logo" in src.lower():
            continue
        width = img.get("width") or img.get("data-width") or ""
        try:
            if int(width) > 600:
                return urljoin(base_url, src)
        except (ValueError, TypeError):
            pass

    return ""


def extract_doctor(soup: BeautifulSoup, jsonld: list[dict], base_url: str) -> dict:
    """Extract the primary doctor/practitioner info."""
    doctor = {"fullName": "", "credentials": "", "title": "", "bio": "", "education": ""}

    # JSON-LD Person/Physician
    person = find_jsonld_by_type(jsonld, ["Person", "Physician"])
    if person:
        doctor["fullName"] = clean_text(person.get("name", ""))
        doctor["credentials"] = clean_text(person.get("honorificSuffix", ""))
        doctor["title"] = clean_text(person.get("jobTitle", ""))
        doctor["bio"] = clean_text(person.get("description", ""))
        education = person.get("hasCredential") or person.get("alumniOf")
        if education:
            if isinstance(education, list):
                doctor["education"] = clean_text(", ".join(
                    e.get("name", str(e)) if isinstance(e, dict) else str(e) for e in education
                ))
            elif isinstance(education, dict):
                doctor["education"] = clean_text(education.get("name", ""))
            elif isinstance(education, str):
                doctor["education"] = clean_text(education)
        if doctor["fullName"]:
            return doctor

    # Also check founder/employee on the business
    biz = find_jsonld_by_type(jsonld, [
        "LocalBusiness", "Chiropractor", "MedicalBusiness", "HealthAndBeautyBusiness",
        "ProfessionalService",
    ])
    if biz:
        for key in ("founder", "employee", "member"):
            person_data = biz.get(key)
            if person_data:
                if isinstance(person_data, list):
                    person_data = person_data[0]
                if isinstance(person_data, dict):
                    doctor["fullName"] = clean_text(person_data.get("name", ""))
                    doctor["credentials"] = clean_text(person_data.get("honorificSuffix", ""))
                    doctor["title"] = clean_text(person_data.get("jobTitle", ""))
                    doctor["bio"] = clean_text(person_data.get("description", ""))
                    if doctor["fullName"]:
                        return doctor

    # HTML-based: look for doctor/team/about sections
    staff_selectors = [
        "[class*='doctor']", "[class*='Doctor']", "[class*='team']", "[class*='Team']",
        "[class*='staff']", "[class*='Staff']", "[class*='bio']", "[class*='Bio']",
        "[class*='about']", "[id*='team']", "[id*='staff']", "[id*='doctor']",
    ]

    for selector in staff_selectors:
        sections = soup.select(selector)
        for section in sections:
            heading = section.find(["h1", "h2", "h3"])
            if not heading:
                continue
            name = clean_text(heading.get_text())
            if not name:
                continue

            # Skip common section headings
            skip_words = [
                "our team", "meet the team", "about us", "staff", "services",
                "testimonials", "reviews", "contact", "hours", "schedule",
            ]
            if any(w in name.lower() for w in skip_words):
                continue

            # Must look like a name (short, or has Dr.)
            is_name_like = "dr." in name.lower() or "dc" in name.lower() or len(name.split()) <= 4
            if not is_name_like:
                continue

            # Parse credentials from name
            credentials = ""
            cred_match = re.search(r",?\s*(D\.?C\.?|DC|M\.?D\.?|DO|NP|PA)$", name)
            if cred_match:
                credentials = cred_match.group(1).replace(".", "")
                name = name[:cred_match.start()].strip().rstrip(",")

            # Bio paragraphs
            paragraphs = section.find_all("p")
            bio_parts = [clean_text(p.get_text()) for p in paragraphs if len(clean_text(p.get_text())) > 30]
            bio = " ".join(bio_parts[:3])

            # Education from bio text
            education = ""
            edu_match = re.search(
                r"(?:graduated|degree|studied|education|university|college)[:\s]*(.*?)(?:\.|$)",
                bio, re.I,
            )
            if edu_match:
                education = clean_text(edu_match.group(1))

            doctor["fullName"] = name
            doctor["credentials"] = credentials
            doctor["bio"] = bio
            doctor["education"] = education
            return doctor

    return doctor


def extract_services(soup: BeautifulSoup, jsonld: list[dict], base_url: str) -> list[dict]:
    """Extract services from JSON-LD and HTML."""
    services = []
    seen_names = set()

    # JSON-LD
    for obj in jsonld:
        obj_type = obj.get("@type", "")
        if isinstance(obj_type, list):
            types = obj_type
        else:
            types = [obj_type]

        if any(t in ("Service", "Product", "Offer") for t in types):
            name = clean_text(obj.get("name", ""))
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                services.append({
                    "name": name,
                    "description": clean_text(obj.get("description", "")),
                    "imageUrl": obj.get("image", ""),
                })

        # hasOfferCatalog
        catalog = obj.get("hasOfferCatalog", {})
        if isinstance(catalog, dict):
            for item in catalog.get("itemListElement", []):
                name = clean_text(item.get("name", ""))
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    services.append({
                        "name": name,
                        "description": clean_text(item.get("description", "")),
                        "imageUrl": item.get("image", ""),
                    })

    # HTML-based service cards
    service_selectors = [
        "[class*='service']", "[class*='Service']", "[id*='service']",
        "[data-testid*='service']", "[class*='offering']", "[class*='treatment']",
    ]
    for selector in service_selectors:
        cards = soup.select(selector)
        for card in cards:
            heading = card.find(["h2", "h3", "h4"])
            if not heading:
                continue
            name = clean_text(heading.get_text())
            if not name or name.lower() in seen_names or len(name) > 100:
                continue
            seen_names.add(name.lower())

            desc_elem = card.find("p")
            desc = clean_text(desc_elem.get_text()) if desc_elem else ""

            img = card.find("img")
            img_url = ""
            if img:
                src = img.get("src") or img.get("data-src") or ""
                img_url = urljoin(base_url, src) if src else ""

            services.append({"name": name, "description": desc, "imageUrl": img_url})

    return services


def extract_testimonials(soup: BeautifulSoup, jsonld: list[dict]) -> list[dict]:
    """Extract testimonials / reviews."""
    testimonials = []
    seen_texts = set()

    # JSON-LD reviews
    for obj in jsonld:
        reviews = obj.get("review", [])
        if not isinstance(reviews, list):
            reviews = [reviews]
        for rev in reviews:
            if not isinstance(rev, dict):
                continue
            author = rev.get("author", {})
            name = ""
            if isinstance(author, dict):
                name = author.get("name", "")
            elif isinstance(author, str):
                name = author
            text = clean_text(rev.get("reviewBody", "") or rev.get("description", ""))
            if text and text not in seen_texts:
                seen_texts.add(text)
                testimonials.append({"name": clean_text(name), "text": text})

    # HTML-based testimonials
    testimonial_selectors = [
        "[class*='testimonial']", "[class*='Testimonial']", "[class*='review']",
        "[class*='Review']", "[id*='testimonial']", "[data-testid*='testimonial']",
        "blockquote",
    ]
    for selector in testimonial_selectors:
        cards = soup.select(selector)
        for card in cards:
            text_elem = card.find("p") or card.find(class_=re.compile(r"text|quote|body", re.I))
            text = clean_text(text_elem.get_text()) if text_elem else clean_text(card.get_text())

            if not text or len(text) < 20 or text in seen_texts:
                continue

            name = ""
            name_elem = card.find(class_=re.compile(r"name|author|client|cite", re.I))
            if name_elem:
                name = clean_text(name_elem.get_text())
            else:
                cite = card.find("cite")
                if cite:
                    name = clean_text(cite.get_text())
                else:
                    strong = card.find(["strong", "b"])
                    if strong:
                        candidate = clean_text(strong.get_text())
                        if len(candidate) < 60:
                            name = candidate

            seen_texts.add(text)
            testimonials.append({"name": name, "text": text})

    return testimonials


def _get_element_context(elem) -> str:
    """Determine the section context for an element by walking up the DOM."""
    for parent in elem.parents:
        if parent.name in ("html", "body", "[document]"):
            break
        classes = " ".join(parent.get("class", []))
        elem_id = parent.get("id", "")
        tag_name = parent.name or ""
        for keyword in ["hero", "banner", "header", "footer", "about", "team",
                        "staff", "doctor", "service", "testimonial", "contact",
                        "gallery", "logo", "nav"]:
            if keyword in classes.lower() or keyword in elem_id.lower() or keyword == tag_name:
                return keyword
        tag_role = parent.get("role", "")
        if tag_role in ("banner", "navigation", "main", "contentinfo"):
            return tag_role
    return ""


def collect_all_images(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Collect all meaningful images from the page with metadata.

    Returns a list of dicts with keys: url, alt, context, width, height, tag.
    """
    seen_urls = set()
    images = []

    def _add_image(url: str, alt: str = "", context: str = "",
                   width: str = "", height: str = ""):
        if url in seen_urls:
            return
        seen_urls.add(url)
        w = 0
        h = 0
        try:
            w = int(width) if width else 0
        except (ValueError, TypeError):
            pass
        try:
            h = int(height) if height else 0
        except (ValueError, TypeError):
            pass
        images.append({
            "url": url,
            "alt": alt,
            "context": context,
            "width": w,
            "height": h,
            "tag": "",
        })

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        full_url = urljoin(base_url, src)
        # Skip tiny tracking pixels, data URIs, SVGs
        if full_url.startswith("data:"):
            continue
        if any(skip in full_url.lower() for skip in [
            "pixel", "tracking", "spacer", "1x1", "blank.gif", ".svg",
        ]):
            continue
        alt = img.get("alt", "") or ""
        w = img.get("width") or img.get("data-width") or ""
        h = img.get("height") or img.get("data-height") or ""
        context = _get_element_context(img)
        _add_image(full_url, alt=alt, context=context, width=str(w), height=str(h))

    # Also check wix-image custom elements
    for wimg in soup.find_all("wix-image"):
        src = wimg.get("data-src") or wimg.get("src") or ""
        if src:
            alt = wimg.get("alt", "") or ""
            _add_image(urljoin(base_url, src), alt=alt, context="wix-image")

    # Background images in style attributes
    for elem in soup.find_all(style=re.compile(r"background")):
        style = elem.get("style", "")
        bg_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
        if bg_match:
            bg_url = bg_match.group(1)
            if not bg_url.startswith("data:"):
                context = _get_element_context(elem)
                _add_image(urljoin(base_url, bg_url), context=context)

    return images


# ---------------------------------------------------------------------------
# Image downloader
# ---------------------------------------------------------------------------

async def download_images(image_list: list, output_dir: Path) -> list[str]:
    """Download images to output_dir/images/ and return list of local paths.

    Accepts either a list of URL strings (backward compat) or a list of image
    metadata dicts (with 'url' key).  Also writes image-manifest.json alongside
    downloaded files mapping local filenames to their metadata.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Normalize to list of dicts
    items: list[dict] = []
    for entry in image_list:
        if isinstance(entry, str):
            items.append({"url": entry, "alt": "", "context": "", "width": 0, "height": 0, "tag": ""})
        elif isinstance(entry, dict):
            items.append(entry)

    downloaded = []
    manifest: dict[str, dict] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        for i, item in enumerate(items):
            url = item.get("url", "")
            if not url:
                continue
            try:
                # Derive filename from URL
                parsed = urlparse(url)
                path_parts = parsed.path.rstrip("/").split("/")
                filename = path_parts[-1] if path_parts[-1] else f"image_{i}"

                # Clean filename
                filename = re.sub(r'[^\w.\-]', '_', filename)
                if not re.search(r'\.(jpg|jpeg|png|gif|webp|avif|svg)$', filename, re.I):
                    filename += ".jpg"

                # Avoid duplicates
                dest = images_dir / filename
                if dest.exists():
                    base, ext = dest.stem, dest.suffix
                    dest = images_dir / f"{base}_{i}{ext}"

                response = await client.get(url)
                if response.status_code == 200 and len(response.content) > 500:
                    dest.write_bytes(response.content)
                    local_name = dest.name
                    downloaded.append(str(dest.relative_to(output_dir)))

                    manifest[local_name] = {
                        "url": url,
                        "alt": item.get("alt", ""),
                        "context": item.get("context", ""),
                        "width": item.get("width", 0),
                        "height": item.get("height", 0),
                        "tag": item.get("tag", ""),
                    }

                    if (i + 1) % 10 == 0:
                        print(f"     Downloaded {i + 1}/{len(items)} images...")
            except Exception:
                continue

    # Write image manifest
    manifest_path = images_dir / "image-manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print_step(f"Wrote image manifest ({len(manifest)} entries) to {manifest_path}")

    return downloaded


# ---------------------------------------------------------------------------
# Platform-specific helpers
# ---------------------------------------------------------------------------

async def scroll_page(page):
    """Scroll through the page to trigger lazy-loaded content."""
    try:
        await page.evaluate("""
            async () => {
                const delay = ms => new Promise(r => setTimeout(r, ms));
                const height = document.body.scrollHeight;
                const step = Math.floor(height / 10);
                for (let i = 0; i <= height; i += step) {
                    window.scrollTo(0, i);
                    await delay(300);
                }
                window.scrollTo(0, 0);
                await delay(500);
            }
        """)
    except Exception:
        pass


async def extract_squarespace_api(page, base_url: str, content: dict):
    """Fetch structured data from Squarespace's JSON API."""
    parsed = urlparse(base_url)
    api_url = f"{parsed.scheme}://{parsed.netloc}/?format=json"

    print_step(f"Trying Squarespace JSON API: {api_url}")
    try:
        response = await page.context.request.get(api_url)
        if response.ok:
            data = await response.json()
            website = data.get("website", {})

            if not content["businessName"] and website.get("siteTitle"):
                content["businessName"] = website["siteTitle"]
            if not content["tagline"] and website.get("siteTagLine"):
                content["tagline"] = website["siteTagLine"]
            if not content["description"] and website.get("siteDescription"):
                content["description"] = website["siteDescription"]
            if not content["logoUrl"] and website.get("logoImageUrl"):
                content["logoUrl"] = website["logoImageUrl"]

            # Social accounts
            for acct in website.get("socialAccounts", []):
                service = acct.get("serviceId", "").lower().replace("-page", "")
                url = acct.get("profileUrl", "")
                if service in content["socials"] and url and not content["socials"][service]:
                    content["socials"][service] = url

            # Location
            location = website.get("location", {})
            if location and not content["address"]["street"]:
                content["address"]["street"] = location.get("addressLine1", "")
                content["address"]["city"] = location.get("addressLine2", "")
                content["address"]["region"] = location.get("region", "")
                content["address"]["postal"] = location.get("postalCode", "")
                content["address"]["country"] = location.get("country", "US")

            print_step("Squarespace JSON API: extracted site-level data")
    except Exception as e:
        print_step(f"Squarespace JSON API failed: {e}")


# ---------------------------------------------------------------------------
# Inner page discovery and scraping
# ---------------------------------------------------------------------------

def discover_inner_pages(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Find links to inner pages likely to have useful content."""
    inner_pages = []
    keywords = [
        "service", "about", "team", "testimonial", "review",
        "meet", "staff", "doctor", "contact",
    ]
    parsed_base = urlparse(base_url)

    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = clean_text(link.get_text()).lower()
        for keyword in keywords:
            if keyword in href.lower() or keyword in text:
                full_url = urljoin(base_url, href)
                parsed_link = urlparse(full_url)
                if parsed_link.netloc == parsed_base.netloc and full_url not in inner_pages and full_url != base_url:
                    inner_pages.append(full_url)
                break

    return inner_pages[:5]


async def scrape_inner_pages(page, inner_pages: list[str], content: dict, jsonld_all: list[dict]):
    """Scrape inner pages to fill in missing content."""
    if not inner_pages:
        return

    print_step(f"Scraping {len(inner_pages)} inner page(s) for additional content...")

    for inner_url in inner_pages:
        print(f"     {inner_url}")
        try:
            await page.goto(inner_url, wait_until="networkidle", timeout=30000)
            await scroll_page(page)
            await page.wait_for_timeout(1000)

            inner_html = await page.content()
            inner_soup = BeautifulSoup(inner_html, "lxml")
            inner_jsonld = extract_jsonld(inner_soup)

            # Merge services
            new_services = extract_services(inner_soup, inner_jsonld, inner_url)
            existing_names = {s["name"].lower() for s in content["services"]}
            for svc in new_services:
                if svc["name"].lower() not in existing_names:
                    content["services"].append(svc)
                    existing_names.add(svc["name"].lower())

            # Merge testimonials
            new_testimonials = extract_testimonials(inner_soup, inner_jsonld)
            existing_texts = {t["text"] for t in content["testimonials"]}
            for t in new_testimonials:
                if t["text"] not in existing_texts:
                    content["testimonials"].append(t)
                    existing_texts.add(t["text"])

            # Doctor if not found yet
            if not content["doctor"]["fullName"]:
                content["doctor"] = extract_doctor(inner_soup, inner_jsonld, inner_url)

            # Address if not found yet
            if not content["address"]["street"]:
                content["address"] = extract_address(inner_soup, inner_jsonld, inner_html)

            # Hours if not found yet
            if not content["hours"]:
                content["hours"] = extract_hours(inner_soup, inner_jsonld)

            # Collect additional images (list of dicts)
            new_images = collect_all_images(inner_soup, inner_url)
            existing_urls = {img["url"] for img in content["images"] if isinstance(img, dict)}
            for img in new_images:
                if img["url"] not in existing_urls:
                    content["images"].append(img)
                    existing_urls.add(img["url"])

        except Exception as e:
            print(f"     Warning: Could not scrape: {e}")
            continue


# ---------------------------------------------------------------------------
# Main extraction orchestrator
# ---------------------------------------------------------------------------

async def extract_content(url: str, output_dir: Path):
    """Main extraction function. Launches Playwright and scrapes the site."""
    content = empty_content()
    content["sourceUrl"] = url
    content["extractedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print(f"Launching browser for: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # Navigate
        print_step("Loading page (waiting for networkidle)...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print_step(f"Warning: Initial load issue: {e}")
            print_step("Retrying with domcontentloaded...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
            except Exception as e2:
                print(f"  ERROR: Could not load page: {e2}")
                await browser.close()
                return content

        # Scroll to trigger lazy-loaded content
        print_step("Scrolling to trigger lazy-loaded content...")
        await scroll_page(page)

        # Get rendered HTML
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # Detect platform
        platform = detect_platform(html, url)
        print_step(f"Detected platform: {platform}")

        # Parse JSON-LD
        jsonld = extract_jsonld(soup)
        if jsonld:
            print_step(f"Found {len(jsonld)} JSON-LD block(s)")

        # Platform-specific extraction
        if platform == "squarespace":
            await extract_squarespace_api(page, url, content)

        if platform == "wix":
            # Re-scroll and re-parse for Wix lazy images
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            jsonld = extract_jsonld(soup)

        # Extract all fields
        print_step("Extracting business name...")
        if not content["businessName"]:
            content["businessName"] = extract_business_name(soup, jsonld, url)
        content["shortName"] = derive_short_name(content["businessName"])

        print_step("Extracting tagline & description...")
        if not content["tagline"]:
            content["tagline"] = extract_tagline(soup)
        if not content["description"]:
            content["description"] = extract_description(soup, jsonld)

        print_step("Extracting phone & email...")
        content["phone"] = extract_phone(soup, jsonld, html)
        content["email"] = extract_email(soup, jsonld, html)

        print_step("Extracting address...")
        if not content["address"]["street"]:
            content["address"] = extract_address(soup, jsonld, html)

        print_step("Extracting hours...")
        content["hours"] = extract_hours(soup, jsonld)

        print_step("Extracting social media links...")
        content["socials"] = extract_social_links(soup, jsonld)

        print_step("Extracting logo URL...")
        if not content["logoUrl"]:
            content["logoUrl"] = extract_logo_url(soup, jsonld, url)

        print_step("Extracting hero image...")
        content["heroImageUrl"] = extract_hero_image(soup, url)

        print_step("Extracting doctor/practitioner info...")
        content["doctor"] = extract_doctor(soup, jsonld, url)

        print_step("Extracting services...")
        content["services"] = extract_services(soup, jsonld, url)

        print_step("Extracting testimonials...")
        content["testimonials"] = extract_testimonials(soup, jsonld)

        print_step("Collecting images...")
        content["images"] = collect_all_images(soup, url)

        # Scrape inner pages for additional content
        inner_pages = discover_inner_pages(soup, url)
        await scrape_inner_pages(page, inner_pages, content, jsonld)

        await browser.close()

    # Post-processing: clean up empty entries
    content["services"] = [s for s in content["services"] if s.get("name")]
    content["testimonials"] = [t for t in content["testimonials"] if t.get("text")]

    # Tag logo and hero images in the images list
    logo_url = content.get("logoUrl", "")
    hero_url = content.get("heroImageUrl", "")
    for img in content["images"]:
        if isinstance(img, dict):
            if logo_url and img["url"] == logo_url:
                img["tag"] = "logo"
            elif hero_url and img["url"] == hero_url:
                img["tag"] = "hero"

    return content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def async_main(url: str, output_dir: Path):
    """Run extraction and save results."""
    content = await extract_content(url, output_dir)

    # Save JSON
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "client-content.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
    print_step(f"Saved {json_path}")

    # Download images
    if content["images"]:
        print_step(f"Downloading {len(content['images'])} images...")
        downloaded = await download_images(content["images"], output_dir)
        print_step(f"Downloaded {len(downloaded)} images to {output_dir / 'images'}")
    else:
        print_step("No images found to download")

    return content


def main():
    parser = argparse.ArgumentParser(
        description="Scrape business content from a client's existing website.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="Target website URL to scrape")
    parser.add_argument("--output", default="./output/", help="Output directory (default: ./output/)")
    args = parser.parse_args()

    output_dir = Path(args.output)

    print("=" * 60)
    print("Client Site Scraper")
    print("=" * 60)
    print(f"  URL:    {args.url}")
    print(f"  Output: {output_dir.resolve()}")
    print("=" * 60)

    content = asyncio.run(async_main(args.url, output_dir))

    print()
    print("=" * 60)
    print("Extraction complete!")
    print("=" * 60)
    print(f"  Business:     {content['businessName'] or '(not found)'}")
    print(f"  Short name:   {content['shortName'] or '(not found)'}")
    print(f"  Phone:        {content['phone'] or '(not found)'}")
    print(f"  Email:        {content['email'] or '(not found)'}")
    addr = content["address"]
    addr_str = ", ".join(
        p for p in [addr["street"], addr["city"], f"{addr['region']} {addr['postal']}".strip()] if p
    )
    print(f"  Address:      {addr_str or '(not found)'}")
    print(f"  Doctor:       {content['doctor']['fullName'] or '(not found)'}")
    print(f"  Services:     {len(content['services'])} found")
    print(f"  Testimonials: {len(content['testimonials'])} found")
    img_count = len(content["images"])
    tagged = sum(1 for img in content["images"] if isinstance(img, dict) and img.get("tag"))
    print(f"  Images:       {img_count} found ({tagged} tagged)")
    print(f"  Output:       {output_dir.resolve()}")
    print("=" * 60)

    if not content["businessName"]:
        print("\nWarning: Could not extract business name. You may need to")
        print("manually edit client-content.json.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
