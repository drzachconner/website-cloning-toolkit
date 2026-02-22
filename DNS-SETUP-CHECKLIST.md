# DNS Setup Guide

## Domain Strategy (Company-Wide)

| Scenario | Registrar | DNS Management | Notes |
|----------|-----------|----------------|-------|
| **New client sites (future)** | **Porkbun** (Zach's account) | Porkbun API (automated by Claude) | One account, full API access, zero manual DNS work |
| **bodymindchiro.com** | NameCheap (jwjohr) | NameCheap manual | Already transferred here, leave it |
| **cultivatewellnesschiro.com** | Squarespace | Cloudflare DNS | Already live, don't touch |

**Why Porkbun for future sites:**
- Single admin account (Zach's) — no creating per-client registrar accounts
- Full API access — Claude can set all DNS records programmatically via MCP server
- API keys already in vault: `PORKBUN_API_KEY`, `PORKBUN_SECRET_KEY`
- MCP server already configured in Claude Code settings (`mcp-porkbun` wrapper)
- Cheaper than NameCheap for most TLDs

---

## Future Sites: Porkbun (Automated)

### New Client Onboarding Flow

```
Day 1: Transfer domain to Porkbun (~$10, 5 min to initiate)
        ↓ capture existing DNS records with dig commands below
        ↓ start building site on pages.dev preview URL
Days 1-7: Build site, deploy to CLIENT-PROJECT.pages.dev
Day 7: Transfer completes → Claude sets DNS via Porkbun API (< 1 min)
Day 7: Site live on custom domain ✓
```

If registering a new domain (client doesn't have one yet): buy at Porkbun directly — instant, no transfer wait.

### Capture Existing DNS Before Transfer

```bash
dig CLIENT-DOMAIN.com MX +short          # Email routing
dig CLIENT-DOMAIN.com TXT +short         # SPF, DMARC, site verification
dig _dmarc.CLIENT-DOMAIN.com TXT +short  # DMARC policy
dig CLIENT-DOMAIN.com A +short           # Current hosting
dig www.CLIENT-DOMAIN.com CNAME +short   # Current www
```

### DNS Records (Claude Sets via API)

Claude uses the Porkbun MCP server to create these records automatically:

**Website:**
- CNAME `www` → `CLIENT-PROJECT.pages.dev`
- URL forward `@` → `https://www.CLIENT-DOMAIN.com` (301)

**Email (Google Workspace — skip if not applicable):**
- MX `@` → `aspmx.l.google.com` (priority 10)
- MX `@` → `alt1.aspmx.l.google.com` (priority 20)
- MX `@` → `alt2.aspmx.l.google.com` (priority 30)
- MX `@` → `alt3.aspmx.l.google.com` (priority 40)
- MX `@` → `alt4.aspmx.l.google.com` (priority 50)

**TXT Records:**
- TXT `@` → `v=spf1 include:_spf.google.com ~all`
- TXT `_dmarc` → `v=DMARC1; p=none;`
- TXT `@` → Google site verification (per-client, check Google Search Console)
- CNAME for Resend DKIM (per-client, check Resend dashboard → domain settings)

### Verify

```bash
dig www.CLIENT-DOMAIN.com CNAME +short   # Should show pages.dev
dig CLIENT-DOMAIN.com MX +short          # Should show Google MX
dig CLIENT-DOMAIN.com TXT +short         # Should show SPF
curl -sI https://www.CLIENT-DOMAIN.com | head -5  # Should show 200
```

Then browser-test: site loads, SSL padlock, contact form, chatbot, email delivery.

---

## Legacy: NameCheap Manual Setup (bodymindchiro.com only)

This section documents the manual process used for bodymindchiro.com. Keep for reference but use Porkbun API for all future sites.

### Step 1: Open Domain Management

Go to: **https://ap.www.namecheap.com/domains/domaincontrolpanel/CLIENT-DOMAIN.com/domain**

Or: NameCheap Dashboard → Domain List → click **"Manage"** next to the domain.

### Step 2: Switch Nameservers to NameCheap BasicDNS

> **Gotcha for transferred domains:** Domains transferred from Wix/Squarespace/GoDaddy arrive with **"Custom DNS"** still pointing to the old registrar's nameservers (e.g., `ns2.wixdns.net`). These are stale and will eventually stop working.

In the **NAMESERVERS** section:
1. Click the dropdown that says **"Custom DNS"**
2. Change it to **"Namecheap BasicDNS"**
3. Click the **green checkmark** to save

A banner says "DNS server update may take up to 48 hours" — usually takes 5-30 min.

### Step 3: Go to Advanced DNS Tab

Click the **"Advanced DNS"** tab at the top (next to Domain, Products, Sharing & Transfer).

### Step 4: Delete Default Records

Remove any parking page records NameCheap auto-created (A record and CNAME pointing to parking page). Delete all of them.

### Step 5: Add Website Records (Host Records section)

Click **"Add New Record"** for each:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| **CNAME** | `www` | `CLIENT-PAGES-PROJECT.pages.dev` | Automatic |
| **URL Redirect Record** | `@` | `https://www.CLIENT-DOMAIN.com` | Permanent (301) |

> **Note:** "URL Redirect Record" is a special type in the dropdown — set Host to `@`, paste the full https URL. Make sure it's **Permanent (301)** not Temporary.

### Step 6: Add TXT Records (Host Records section)

| Type | Host | Value | TTL |
|------|------|-------|-----|
| **TXT** | `@` | `v=spf1 include:_spf.google.com ~all` | Automatic |
| **TXT** | `_dmarc` | `v=DMARC1; p=none;` | Automatic |
| **TXT** | `@` | `google-site-verification=...` (per-client) | Automatic |

> **Gotcha:** Make sure DMARC host is `_dmarc`, NOT `@`. Easy to miss.

### Step 7: Add MX Records (MAIL SETTINGS section)

> **Gotcha:** MX records are NOT in the Host Records type dropdown. Scroll down on the Advanced DNS page to the **"MAIL SETTINGS"** section. Change the dropdown from **"No Email Service"** to **"Custom MX"**. This opens a separate MX records table.

| Host | Value | Priority |
|------|-------|----------|
| `@` | `aspmx.l.google.com` | 10 |
| `@` | `alt1.aspmx.l.google.com` | 20 |
| `@` | `alt2.aspmx.l.google.com` | 30 |
| `@` | `alt3.aspmx.l.google.com` | 40 |
| `@` | `alt4.aspmx.l.google.com` | 50 |

### Step 8: Verify

1. `https://www.CLIENT-DOMAIN.com` — site loads
2. `https://CLIENT-DOMAIN.com` — redirects to www
3. Padlock icon (SSL)
4. Contact form works
5. Chatbot works
6. Email delivery works (send test to client's Google Workspace)

---

## Quick Reference: Current Sites

| Site | Domain | Registrar | DNS Provider | Pages Project | Status |
|------|--------|-----------|--------------|---------------|--------|
| Body Mind Chiro | bodymindchiro.com | NameCheap (jwjohr) | NameCheap | `bodymind-chiro` | DNS setup in progress |
| Cultivate Wellness | cultivatewellnesschiro.com | Squarespace | Cloudflare | `cultivate-wellness-chiro` | Live |
| Talsky Tonal | TBD | Porkbun (Zach) | Porkbun API | TBD | In development |
