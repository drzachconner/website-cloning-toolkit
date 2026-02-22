# DNS Setup Checklist (NameCheap)

Use this for every new client site. Takes ~5 minutes.

## Prerequisites
- Domain registered at NameCheap (login: use `vault-get NAMECHEAP_USERNAME`)
- Cloudflare Pages project created with custom domain added

## Step 1: Open NameCheap DNS Manager

Go to: `https://ap.www.namecheap.com/domains/domaincontrolpanel/CLIENT-DOMAIN.com/domain`

Make sure **Nameservers** is set to **"Namecheap BasicDNS"** (not Custom DNS).

Click the **"Advanced DNS"** tab.

## Step 2: Delete Default Records

Remove any parking page records NameCheap auto-created (usually an A record and CNAME pointing to a parking page).

## Step 3: Add Website Records

| Type | Host | Value |
|------|------|-------|
| **CNAME** | `www` | `CLIENT-PAGES-PROJECT.pages.dev` |
| **URL Redirect (301)** | `@` | `https://www.CLIENT-DOMAIN.com` |

## Step 4: Add Email Records (Google Workspace)

| Type | Host | Value | Priority |
|------|------|-------|----------|
| **MX** | `@` | `aspmx.l.google.com` | 10 |
| **MX** | `@` | `alt1.aspmx.l.google.com` | 20 |
| **MX** | `@` | `alt2.aspmx.l.google.com` | 30 |
| **MX** | `@` | `alt3.aspmx.l.google.com` | 40 |
| **MX** | `@` | `alt4.aspmx.l.google.com` | 50 |

Skip this step if client doesn't use Google Workspace email.

## Step 5: Add TXT Records

| Type | Host | Value |
|------|------|-------|
| **TXT** | `@` | `v=spf1 include:_spf.google.com ~all` |
| **TXT** | `_dmarc` | `v=DMARC1; p=none;` |

Add Google site verification and Resend DKIM if applicable (these are per-client — check Resend dashboard for the DKIM CNAME).

## Step 6: Verify (wait 5-30 min)

1. Open `https://www.CLIENT-DOMAIN.com` — site should load
2. Open `https://CLIENT-DOMAIN.com` — should redirect to www
3. Check for padlock (SSL)
4. Test contact form
5. Test chatbot

## Quick Reference: Current Sites

| Site | Domain | Pages Project | Status |
|------|--------|---------------|--------|
| Body Mind Chiro | bodymindchiro.com | `bodymind-chiro` | DNS setup pending |
| Cultivate Wellness | cultivatewellnesschiro.com | `cultivate-wellness-chiro` | Live |
| Talsky Tonal | TBD | TBD | In development |
