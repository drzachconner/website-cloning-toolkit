#!/usr/bin/env python3
"""
Extract business content from Wix/Squarespace chiropractic websites.

Scrapes structured business data (NOT design) from JS-rendered sites using
Playwright. Outputs a clean JSON file suitable for feeding into
generate-site-ts.py to produce a valid site.ts configuration.

Handles platform-specific patterns:
  - Wix: lazy-loaded images (data-src, wix-image), dynamic content rendering
  - Squarespace: JSON API at /page?format=json, structured collection data

Usage:
    python extract-site-content.py --url https://example.com --output client-content.json
    python extract-site-content.py --url https://example.com --platform wix --output client-content.json

Requirements:
    pip install playwright beautifulsoup4 requests lxml
    playwright install chromium
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright
    import asyncio
except ImportError:
    print("Error: playwright is required. Install with: pip install playwright && playwright install")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def detect_platform(html: str, url: str) -> str:
    """Detect whether a site is built on Wix, Squarespace, or unknown."""
    html_lower = html.lower()

    # Wix indicators
    wix_signals = [
        "wix-image",
        "wixsite.com",
        "_wix_browser_sess",
        "wix-dropdown-menu",
        "x-wix-",
        "static.wixstatic.com",
        "wixmp-",
        'data-mesh-id="',
        "wix-bg-image",
    ]
    wix_score = sum(1 for sig in wix_signals if sig in html_lower)

    # Squarespace indicators
    sq_signals = [
        "squarespace",
        "static1.squarespace.com",
        "sqs-block",
        "sqs-layout",
        "sqsp-",
        '"siteId"',
        "squarespace-cdn.com",
        "sqs-slide",
    ]
    sq_score = sum(1 for sig in sq_signals if sig in html_lower)

    if wix_score >= 2:
        return "wix"
    elif sq_score >= 2:
        return "squarespace"
    return "unknown"


# ---------------------------------------------------------------------------
# Content schema
# ---------------------------------------------------------------------------

def empty_content() -> dict:
    """Return an empty content structure matching the output schema."""
    return {
        "businessName": "",
        "tagline": "",
        "description": "",
        "phone": "",
        "email": "",
        "address": {
            "street": "",
            "city": "",
            "region": "",
            "postal": "",
            "country": "US",
            "formatted": "",
        },
        "hours": [],
        "services": [],
        "testimonials": [],
        "staff": [],
        "socialMedia": {
            "facebook": "",
            "instagram": "",
            "tiktok": "",
            "youtube": "",
            "linkedin": "",
            "twitter": "",
            "pinterest": "",
        },
        "logoUrl": "",
        "heroImageUrl": "",
        "sourceUrl": "",
        "platform": "",
        "extractedAt": "",
    }


# ---------------------------------------------------------------------------
# Generic extraction helpers
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalize whitespace and strip a string."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_phone(soup: BeautifulSoup, html: str) -> str:
    """Find a phone number from links and text patterns."""
    # tel: links
    tel_link = soup.find("a", href=re.compile(r"^tel:", re.I))
    if tel_link:
        raw = tel_link["href"].replace("tel:", "").strip()
        return raw

    # Common phone patterns in text
    phone_pattern = re.compile(
        r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"
    )
    match = phone_pattern.search(html)
    if match:
        return match.group(1).strip()
    return ""


def extract_email(soup: BeautifulSoup, html: str) -> str:
    """Find an email address from mailto links or text patterns."""
    mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
    if mailto:
        return mailto["href"].replace("mailto:", "").split("?")[0].strip()

    email_pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    match = email_pattern.search(html)
    if match:
        return match.group(0)
    return ""


def extract_social_links(soup: BeautifulSoup) -> dict:
    """Extract social media URLs from anchor tags."""
    socials = {
        "facebook": "",
        "instagram": "",
        "tiktok": "",
        "youtube": "",
        "linkedin": "",
        "twitter": "",
        "pinterest": "",
    }

    platform_patterns = {
        "facebook": r"facebook\.com",
        "instagram": r"instagram\.com",
        "tiktok": r"tiktok\.com",
        "youtube": r"youtube\.com|youtu\.be",
        "linkedin": r"linkedin\.com",
        "twitter": r"(twitter\.com|x\.com)",
        "pinterest": r"pinterest\.com",
    }

    for link in soup.find_all("a", href=True):
        href = link["href"]
        for platform, pattern in platform_patterns.items():
            if re.search(pattern, href, re.I) and not socials[platform]:
                socials[platform] = href
    return socials


def extract_address(soup: BeautifulSoup, html: str) -> dict:
    """Attempt to extract a street address from the page."""
    address = {
        "street": "",
        "city": "",
        "region": "",
        "postal": "",
        "country": "US",
        "formatted": "",
    }

    # Schema.org microdata / JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            addr = data.get("address") or {}
            if isinstance(addr, dict):
                address["street"] = addr.get("streetAddress", "")
                address["city"] = addr.get("addressLocality", "")
                address["region"] = addr.get("addressRegion", "")
                address["postal"] = addr.get("postalCode", "")
                address["country"] = addr.get("addressCountry", "US")
                if address["street"]:
                    parts = [p for p in [address["street"], address["city"],
                             f'{address["region"]} {address["postal"]}'] if p.strip()]
                    address["formatted"] = ", ".join(parts)
                    return address
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # Common address pattern: number + street, city, STATE ZIP
    addr_pattern = re.compile(
        r"(\d{1,5}\s[\w\s.]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl|Pkwy|Ste|Suite|#)[\w\s.,#-]*)"
        r"[,\s]+"
        r"([\w\s]+)[,\s]+"
        r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)",
        re.I,
    )
    text = soup.get_text(separator=" ")
    match = addr_pattern.search(text)
    if match:
        address["street"] = clean_text(match.group(1))
        address["city"] = clean_text(match.group(2))
        address["region"] = match.group(3).upper()
        address["postal"] = match.group(4)
        address["formatted"] = f"{address['street']}, {address['city']}, {address['region']} {address['postal']}"

    return address


def extract_hours(soup: BeautifulSoup) -> list:
    """Extract business hours from common patterns."""
    hours = []

    # Schema.org JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            opening = data.get("openingHoursSpecification", [])
            if opening:
                for spec in opening:
                    day = spec.get("dayOfWeek", "")
                    if isinstance(day, list):
                        day = ", ".join(day)
                    opens = spec.get("opens", "")
                    closes = spec.get("closes", "")
                    if day:
                        hours.append(f"{day}: {opens} - {closes}")
                if hours:
                    return hours
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # Look for elements containing day names near time patterns
    day_pattern = re.compile(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"[:\s]*"
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\s*[-\u2013]\s*"
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)",
        re.I,
    )
    text = soup.get_text(separator="\n")
    for match in day_pattern.finditer(text):
        hours.append(f"{match.group(1)}: {match.group(2)} - {match.group(3)}")

    return hours


def extract_logo_url(soup: BeautifulSoup, base_url: str) -> str:
    """Find the site logo URL."""
    # Wix logo patterns
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").lower()
        src = img.get("src") or img.get("data-src") or ""
        classes = " ".join(img.get("class", []))
        parent_id = ""
        if img.parent:
            parent_id = img.parent.get("id", "")

        if any(kw in alt for kw in ["logo", "brand"]):
            return urljoin(base_url, src) if src else ""
        if any(kw in classes for kw in ["logo", "site-logo", "brand"]):
            return urljoin(base_url, src) if src else ""
        if "logo" in parent_id.lower():
            return urljoin(base_url, src) if src else ""

    # WixImage elements with logo in id
    for elem in soup.find_all(attrs={"id": re.compile(r"logo", re.I)}):
        img = elem.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                return urljoin(base_url, src)

    # Header images as fallback
    header = soup.find("header") or soup.find(attrs={"role": "banner"})
    if header:
        img = header.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                return urljoin(base_url, src)

    return ""


def extract_business_name(soup: BeautifulSoup, url: str) -> str:
    """Extract the business name from multiple sources."""
    # Schema.org JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            name = data.get("name", "")
            if name:
                return clean_text(name)
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # og:site_name meta tag
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return clean_text(og["content"])

    # Title tag (before the | or - separator)
    title = soup.find("title")
    if title and title.string:
        text = title.string.strip()
        for sep in [" | ", " - ", " \u2013 ", " \u2014 "]:
            if sep in text:
                return clean_text(text.split(sep)[0])
        return clean_text(text)

    return ""


def extract_tagline(soup: BeautifulSoup) -> str:
    """Extract a tagline or slogan from the page."""
    # og:description often has the tagline
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        content = og["content"].strip()
        # Short descriptions are likely taglines
        if len(content) < 120:
            return clean_text(content)

    # Look for common tagline containers
    for selector in [
        "[class*='tagline']",
        "[class*='slogan']",
        "[class*='subtitle']",
        "[class*='hero'] h2",
        "[class*='hero'] p",
    ]:
        elem = soup.select_one(selector)
        if elem:
            text = clean_text(elem.get_text())
            if 3 < len(text) < 150:
                return text

    # Meta description as fallback
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return clean_text(meta["content"][:150])

    return ""


def extract_description(soup: BeautifulSoup) -> str:
    """Extract the business description."""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return clean_text(meta["content"])

    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return clean_text(og["content"])

    return ""


# ---------------------------------------------------------------------------
# Services extraction
# ---------------------------------------------------------------------------

def extract_services(soup: BeautifulSoup, base_url: str) -> list:
    """Extract services from the page."""
    services = []
    seen_names = set()

    # Schema.org JSON-LD services
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") in ("Service", "Product", "Offer"):
                        name = clean_text(item.get("name", ""))
                        if name and name.lower() not in seen_names:
                            seen_names.add(name.lower())
                            services.append({
                                "name": name,
                                "description": clean_text(item.get("description", "")),
                                "imageUrl": item.get("image", ""),
                            })
            elif isinstance(data, dict):
                offers = data.get("hasOfferCatalog", {}).get("itemListElement", [])
                for item in offers:
                    name = clean_text(item.get("name", ""))
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        services.append({
                            "name": name,
                            "description": clean_text(item.get("description", "")),
                            "imageUrl": item.get("image", ""),
                        })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # Look for service-like sections in HTML
    service_selectors = [
        "[class*='service']",
        "[class*='Service']",
        "[id*='service']",
        "[data-testid*='service']",
        "[class*='offering']",
        "[class*='treatment']",
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

            services.append({
                "name": name,
                "description": desc,
                "imageUrl": img_url,
            })

    return services


# ---------------------------------------------------------------------------
# Testimonials extraction
# ---------------------------------------------------------------------------

def extract_testimonials(soup: BeautifulSoup) -> list:
    """Extract testimonials / reviews from the page."""
    testimonials = []
    seen_texts = set()

    # Schema.org reviews
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            reviews = data.get("review", [])
            if not isinstance(reviews, list):
                reviews = [reviews]
            for rev in reviews:
                name = ""
                author = rev.get("author", {})
                if isinstance(author, dict):
                    name = author.get("name", "")
                elif isinstance(author, str):
                    name = author
                text = clean_text(rev.get("reviewBody", "") or rev.get("description", ""))
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    testimonials.append({
                        "name": clean_text(name),
                        "text": text,
                        "rating": rev.get("reviewRating", {}).get("ratingValue"),
                    })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # HTML-based testimonials
    testimonial_selectors = [
        "[class*='testimonial']",
        "[class*='Testimonial']",
        "[class*='review']",
        "[class*='Review']",
        "[id*='testimonial']",
        "[data-testid*='testimonial']",
        "blockquote",
    ]

    for selector in testimonial_selectors:
        cards = soup.select(selector)
        for card in cards:
            # Find quote text
            text_elem = card.find("p") or card.find(class_=re.compile(r"text|quote|body", re.I))
            if not text_elem:
                text = clean_text(card.get_text())
            else:
                text = clean_text(text_elem.get_text())

            if not text or len(text) < 20 or text in seen_texts:
                continue

            # Find author name
            name = ""
            name_elem = card.find(class_=re.compile(r"name|author|client|cite", re.I))
            if name_elem:
                name = clean_text(name_elem.get_text())
            else:
                cite = card.find("cite")
                if cite:
                    name = clean_text(cite.get_text())
                else:
                    # Look for a short bold or strong element
                    strong = card.find(["strong", "b"])
                    if strong:
                        candidate = clean_text(strong.get_text())
                        if len(candidate) < 60:
                            name = candidate

            seen_texts.add(text)
            testimonials.append({
                "name": name,
                "text": text,
                "rating": None,
            })

    return testimonials


# ---------------------------------------------------------------------------
# Staff / doctor bio extraction
# ---------------------------------------------------------------------------

def extract_staff(soup: BeautifulSoup, base_url: str) -> list:
    """Extract doctor or staff bios."""
    staff = []
    seen_names = set()

    # Schema.org Person data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("Person", "Physician"):
                    name = clean_text(item.get("name", ""))
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        staff.append({
                            "fullName": name,
                            "title": clean_text(item.get("jobTitle", "")),
                            "bio": clean_text(item.get("description", "")),
                            "imageUrl": item.get("image", ""),
                            "credentials": item.get("honorificSuffix", ""),
                        })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    # HTML-based staff sections
    staff_selectors = [
        "[class*='team']",
        "[class*='Team']",
        "[class*='staff']",
        "[class*='Staff']",
        "[class*='doctor']",
        "[class*='Doctor']",
        "[class*='bio']",
        "[class*='Bio']",
        "[class*='about']",
        "[id*='team']",
        "[id*='staff']",
        "[id*='doctor']",
    ]

    for selector in staff_selectors:
        sections = soup.select(selector)
        for section in sections:
            heading = section.find(["h1", "h2", "h3"])
            if not heading:
                continue
            name = clean_text(heading.get_text())

            # Filter out non-name headings
            if not name or name.lower() in seen_names:
                continue
            # Heuristic: names typically contain "Dr." or are short
            is_name_like = (
                "dr." in name.lower()
                or "dc" in name.lower()
                or len(name.split()) <= 4
            )
            # Skip common section headings
            skip_words = ["our team", "meet the team", "about us", "staff", "services",
                          "testimonials", "reviews", "contact", "hours", "schedule"]
            if any(w in name.lower() for w in skip_words):
                continue

            if not is_name_like:
                continue

            seen_names.add(name.lower())

            # Bio text
            paragraphs = section.find_all("p")
            bio_parts = []
            for p in paragraphs:
                t = clean_text(p.get_text())
                if t and len(t) > 30:
                    bio_parts.append(t)
            bio = " ".join(bio_parts[:3])  # Take up to 3 paragraphs

            # Image
            img = section.find("img")
            img_url = ""
            if img:
                src = img.get("src") or img.get("data-src") or ""
                img_url = urljoin(base_url, src) if src else ""

            # Credentials from name
            credentials = ""
            cred_match = re.search(r",?\s*(D\.?C\.?|DC|M\.?D\.?|DO|NP|PA)$", name)
            if cred_match:
                credentials = cred_match.group(1).replace(".", "")
                name = name[: cred_match.start()].strip().rstrip(",")

            staff.append({
                "fullName": name,
                "title": "",
                "bio": bio,
                "imageUrl": img_url,
                "credentials": credentials,
            })

    return staff


# ---------------------------------------------------------------------------
# Wix-specific extraction
# ---------------------------------------------------------------------------

async def extract_wix_images(page, soup: BeautifulSoup, base_url: str) -> dict:
    """Handle Wix lazy-loaded images."""
    images = {"logo": "", "hero": ""}

    # Wix images use data-src or wix-image custom elements
    # Scroll to trigger lazy loading
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
    except Exception:
        pass

    # Re-parse after lazy load trigger
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    # Find hero image (typically the first large image or background)
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or "logo" in src.lower():
            continue
        # Wix image URLs from static.wixstatic.com
        if "wixstatic.com" in src or "wixmp-" in src:
            # Prefer larger images (hero candidates)
            width = img.get("width") or img.get("data-width") or ""
            try:
                if int(width) > 600:
                    images["hero"] = urljoin(base_url, src)
                    break
            except (ValueError, TypeError):
                pass
            if not images["hero"]:
                images["hero"] = urljoin(base_url, src)

    # Also check for bg-image wix patterns
    for elem in soup.find_all(attrs={"data-bg": True}):
        bg = elem["data-bg"]
        if bg and not images["hero"]:
            images["hero"] = urljoin(base_url, bg)

    # wow-image / wix-image custom elements
    for wimg in soup.find_all("wix-image"):
        src = wimg.get("data-src") or wimg.get("src") or ""
        if src and not images["hero"]:
            images["hero"] = urljoin(base_url, src)

    return images


# ---------------------------------------------------------------------------
# Squarespace-specific extraction
# ---------------------------------------------------------------------------

async def extract_squarespace_data(page, base_url: str) -> dict:
    """Fetch structured data from Squarespace's JSON API."""
    sq_data = {}
    parsed = urlparse(base_url)
    api_url = f"{parsed.scheme}://{parsed.netloc}/?format=json"

    print(f"  Attempting Squarespace JSON API: {api_url}")
    try:
        response = await page.context.request.get(api_url)
        if response.ok:
            data = await response.json()
            sq_data["raw"] = data

            # Extract site-level info
            website = data.get("website", {})
            sq_data["businessName"] = website.get("siteTitle", "")
            sq_data["tagline"] = website.get("siteTagLine", "")
            sq_data["description"] = website.get("siteDescription", "")
            sq_data["logoUrl"] = website.get("logoImageUrl", "")

            # Social links from Squarespace config
            social_accounts = website.get("socialAccounts", [])
            socials = {}
            for acct in social_accounts:
                service = acct.get("serviceId", "").lower()
                url = acct.get("profileUrl", "")
                if service and url:
                    socials[service] = url
            sq_data["socials"] = socials

            # Location info
            location = data.get("website", {}).get("location", {})
            if location:
                sq_data["address"] = {
                    "street": location.get("addressLine1", ""),
                    "city": location.get("addressLine2", ""),  # Often city, state zip
                    "region": location.get("region", ""),
                    "postal": location.get("postalCode", ""),
                    "country": location.get("country", "US"),
                }

            print("  Squarespace JSON API: extracted site-level data")
        else:
            print(f"  Squarespace JSON API returned status {response.status}")
    except Exception as e:
        print(f"  Squarespace JSON API failed: {e}")

    # Try individual page JSON endpoints
    try:
        pages_to_try = ["about", "services", "testimonials", "team", "contact"]
        for page_slug in pages_to_try:
            page_api = f"{parsed.scheme}://{parsed.netloc}/{page_slug}?format=json"
            try:
                resp = await page.context.request.get(page_api)
                if resp.ok:
                    page_data = await resp.json()
                    sq_data[f"page_{page_slug}"] = page_data
                    print(f"  Squarespace page API: got /{page_slug}")
            except Exception:
                continue
    except Exception:
        pass

    return sq_data


# ---------------------------------------------------------------------------
# Main extraction orchestrator
# ---------------------------------------------------------------------------

async def extract_content(url: str, platform: str = "auto", output: str = "client-content.json"):
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

        # Navigate and wait for JS rendering
        print("  Loading page (waiting for networkidle)...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"  Warning: Initial load issue: {e}")
            print("  Retrying with domcontentloaded...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
            except Exception as e2:
                print(f"  Error: Could not load page: {e2}")
                await browser.close()
                return content

        # Scroll down to trigger lazy loading
        print("  Scrolling to trigger lazy-loaded content...")
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

        # Get rendered HTML
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # Detect platform
        if platform == "auto":
            platform = detect_platform(html, url)
        content["platform"] = platform
        print(f"  Detected platform: {platform}")

        # --- Platform-specific extraction ---
        sq_data = {}
        if platform == "squarespace":
            sq_data = await extract_squarespace_data(page, url)
            if sq_data.get("businessName"):
                content["businessName"] = sq_data["businessName"]
            if sq_data.get("tagline"):
                content["tagline"] = sq_data["tagline"]
            if sq_data.get("description"):
                content["description"] = sq_data["description"]
            if sq_data.get("logoUrl"):
                content["logoUrl"] = sq_data["logoUrl"]
            if sq_data.get("socials"):
                for platform_key, social_url in sq_data["socials"].items():
                    mapped = platform_key.replace("facebook-page", "facebook")
                    if mapped in content["socialMedia"]:
                        content["socialMedia"][mapped] = social_url
            if sq_data.get("address"):
                for key, val in sq_data["address"].items():
                    if val:
                        content["address"][key] = val

        if platform == "wix":
            wix_images = await extract_wix_images(page, soup, url)
            if wix_images.get("hero"):
                content["heroImageUrl"] = wix_images["hero"]

        # --- Generic extraction (fills in anything not set by platform-specific) ---
        print("  Extracting business name...")
        if not content["businessName"]:
            content["businessName"] = extract_business_name(soup, url)

        print("  Extracting tagline & description...")
        if not content["tagline"]:
            content["tagline"] = extract_tagline(soup)
        if not content["description"]:
            content["description"] = extract_description(soup)

        print("  Extracting phone & email...")
        content["phone"] = extract_phone(soup, html)
        content["email"] = extract_email(soup, html)

        print("  Extracting address...")
        if not content["address"]["street"]:
            content["address"] = extract_address(soup, html)

        print("  Extracting hours...")
        content["hours"] = extract_hours(soup)

        print("  Extracting social media links...")
        generic_socials = extract_social_links(soup)
        for key, val in generic_socials.items():
            if val and not content["socialMedia"].get(key):
                content["socialMedia"][key] = val

        print("  Extracting logo URL...")
        if not content["logoUrl"]:
            content["logoUrl"] = extract_logo_url(soup, url)

        print("  Extracting services...")
        content["services"] = extract_services(soup, url)

        print("  Extracting testimonials...")
        content["testimonials"] = extract_testimonials(soup)

        print("  Extracting staff/doctor bios...")
        content["staff"] = extract_staff(soup, url)

        # --- Navigate to inner pages for more data ---
        inner_pages = []

        # Try to discover services/about/testimonials pages
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = clean_text(link.get_text()).lower()
            for keyword in ["service", "about", "team", "testimonial", "review",
                            "meet", "staff", "doctor", "contact"]:
                if keyword in href.lower() or keyword in text:
                    full_url = urljoin(url, href)
                    parsed_link = urlparse(full_url)
                    parsed_base = urlparse(url)
                    if parsed_link.netloc == parsed_base.netloc and full_url not in inner_pages:
                        inner_pages.append(full_url)
                    break

        # Scrape up to 5 inner pages for additional content
        inner_pages = inner_pages[:5]
        if inner_pages:
            print(f"  Scraping {len(inner_pages)} inner page(s) for additional content...")

        for inner_url in inner_pages:
            print(f"    -> {inner_url}")
            try:
                await page.goto(inner_url, wait_until="networkidle", timeout=30000)

                # Scroll for lazy loading
                await page.evaluate("""
                    async () => {
                        const delay = ms => new Promise(r => setTimeout(r, ms));
                        const height = document.body.scrollHeight;
                        const step = Math.floor(height / 5);
                        for (let i = 0; i <= height; i += step) {
                            window.scrollTo(0, i);
                            await delay(200);
                        }
                        window.scrollTo(0, 0);
                    }
                """)
                await page.wait_for_timeout(1000)

                inner_html = await page.content()
                inner_soup = BeautifulSoup(inner_html, "lxml")

                # Merge services
                new_services = extract_services(inner_soup, inner_url)
                existing_names = {s["name"].lower() for s in content["services"]}
                for svc in new_services:
                    if svc["name"].lower() not in existing_names:
                        content["services"].append(svc)
                        existing_names.add(svc["name"].lower())

                # Merge testimonials
                new_testimonials = extract_testimonials(inner_soup)
                existing_texts = {t["text"] for t in content["testimonials"]}
                for t in new_testimonials:
                    if t["text"] not in existing_texts:
                        content["testimonials"].append(t)
                        existing_texts.add(t["text"])

                # Merge staff
                new_staff = extract_staff(inner_soup, inner_url)
                existing_staff_names = {s["fullName"].lower() for s in content["staff"]}
                for s in new_staff:
                    if s["fullName"].lower() not in existing_staff_names:
                        content["staff"].append(s)
                        existing_staff_names.add(s["fullName"].lower())

                # Update address if not found yet
                if not content["address"]["street"]:
                    content["address"] = extract_address(inner_soup, inner_html)

                # Update hours if not found yet
                if not content["hours"]:
                    content["hours"] = extract_hours(inner_soup)

            except Exception as e:
                print(f"    Warning: Could not scrape inner page: {e}")
                continue

        await browser.close()

    # --- Post-processing ---
    # Remove empty services/testimonials/staff
    content["services"] = [s for s in content["services"] if s.get("name")]
    content["testimonials"] = [t for t in content["testimonials"] if t.get("text")]
    content["staff"] = [s for s in content["staff"] if s.get("fullName")]

    # Build formatted address if parts exist but formatted is empty
    if content["address"]["street"] and not content["address"]["formatted"]:
        parts = [content["address"]["street"]]
        if content["address"]["city"]:
            parts.append(content["address"]["city"])
        if content["address"]["region"] or content["address"]["postal"]:
            parts.append(f'{content["address"]["region"]} {content["address"]["postal"]}'.strip())
        content["address"]["formatted"] = ", ".join(parts)

    return content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract business content from Wix/Squarespace chiropractic websites.\n"
            "Outputs a structured JSON file for use with generate-site-ts.py."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Target website URL to extract content from",
    )
    parser.add_argument(
        "--output",
        default="client-content.json",
        help="Output JSON file path (default: client-content.json)",
    )
    parser.add_argument(
        "--platform",
        choices=["auto", "wix", "squarespace"],
        default="auto",
        help="Website platform (default: auto-detect)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Site Content Extractor")
    print("=" * 60)
    print(f"  URL:      {args.url}")
    print(f"  Output:   {args.output}")
    print(f"  Platform: {args.platform}")
    print("=" * 60)

    content = asyncio.run(extract_content(args.url, args.platform, args.output))

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("Extraction complete!")
    print("=" * 60)
    print(f"  Business:     {content['businessName'] or '(not found)'}")
    print(f"  Phone:        {content['phone'] or '(not found)'}")
    print(f"  Email:        {content['email'] or '(not found)'}")
    print(f"  Address:      {content['address']['formatted'] or '(not found)'}")
    print(f"  Services:     {len(content['services'])} found")
    print(f"  Testimonials: {len(content['testimonials'])} found")
    print(f"  Staff/Drs:    {len(content['staff'])} found")
    print(f"  Platform:     {content['platform']}")
    print(f"  Output:       {output_path}")
    print("=" * 60)

    if not content["businessName"]:
        print("\nWarning: Could not extract business name. You may need to")
        print("manually edit client-content.json before running generate-site-ts.py.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
