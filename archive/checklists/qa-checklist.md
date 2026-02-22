# Final QA Checklist

Complete before delivering cloned pages. Every item must pass.

---

## HTML Quality

- [ ] Valid HTML5 (passes [W3C Validator](https://validator.w3.org/) with no errors)
- [ ] DOCTYPE declaration present on every page
- [ ] `<html lang="en">` attribute set
- [ ] `<meta charset="UTF-8">` present
- [ ] `<meta name="viewport">` present with responsive settings
- [ ] Exactly one `<h1>` per page
- [ ] Heading hierarchy is logical (no skipped levels)
- [ ] No unclosed tags or malformed HTML
- [ ] Semantic HTML5 elements used where appropriate

## CSS Quality

- [ ] No inline `<style>` tags (all styling via external CSS classes)
- [ ] No inline `style=""` attributes on elements
- [ ] All CSS loaded via `<link>` tags
- [ ] CSS classes are descriptive and consistent
- [ ] No unused CSS bloating the stylesheet
- [ ] No `!important` overrides (unless matching original)
- [ ] CSS custom properties used for theme values (colors, fonts, spacing)

## Assets

- [ ] All images load successfully (no 404s in network tab)
- [ ] All CSS files load successfully
- [ ] All fonts load successfully
- [ ] Relative paths used throughout (no absolute localhost URLs)
- [ ] No references to original domain's assets (self-contained)
- [ ] Image file sizes are optimized (no uncompressed 5MB PNGs)
- [ ] Favicon is present and loads correctly

## Metadata

- [ ] `<title>` tag present and descriptive on every page
- [ ] `<meta name="description">` present on every page
- [ ] Open Graph tags present (og:title, og:description, og:image)
- [ ] Structured data present if applicable (Schema.org JSON-LD)
- [ ] Canonical URL set if pages will be indexed

## Performance

- [ ] Lighthouse performance score within 10% of original
- [ ] No render-blocking resources that could be deferred
- [ ] Images have width/height attributes (prevents layout shift)
- [ ] CSS is minified for production (or can be easily minified)
- [ ] No unnecessary JavaScript loaded
- [ ] Page weight is reasonable (< 3MB total including assets)
- [ ] First Contentful Paint under 2 seconds on broadband

## Accessibility

- [ ] All images have meaningful `alt` attributes
- [ ] Color contrast meets WCAG AA (4.5:1 for body text, 3:1 for large text)
- [ ] Interactive elements are keyboard navigable
- [ ] Focus indicators are visible
- [ ] Form inputs have associated `<label>` elements
- [ ] ARIA attributes used correctly (if present)
- [ ] Page is navigable with screen reader
- [ ] No text embedded in images without alt text

## Cross-Browser Testing

- [ ] Chrome (latest) - renders correctly
- [ ] Firefox (latest) - renders correctly
- [ ] Safari (latest) - renders correctly
- [ ] Edge (latest) - renders correctly
- [ ] Mobile Chrome (iOS/Android) - renders correctly
- [ ] Mobile Safari (iOS) - renders correctly

## Functional Testing

- [ ] All internal links work (no broken links)
- [ ] All external links open in new tab (if intended)
- [ ] CTA buttons link to correct destinations
- [ ] Anchor links scroll to correct sections
- [ ] No JavaScript console errors
- [ ] No mixed content warnings (HTTP/HTTPS)
- [ ] Forms submit correctly (if applicable)
- [ ] No Lorem Ipsum or placeholder text remaining

## File Organization

- [ ] Consistent file naming (lowercase, hyphens, no spaces)
- [ ] Logical directory structure
- [ ] No orphaned files (every file is referenced somewhere)
- [ ] No duplicate files
- [ ] README or index file explains the structure
- [ ] Git repository is clean (no uncommitted changes)

---

## Sign-Off

| Check | Status | Notes |
|-------|--------|-------|
| HTML valid | | |
| CSS external only | | |
| All assets load | | |
| Metadata complete | | |
| Performance OK | | |
| Accessibility OK | | |
| Cross-browser OK | | |
| All links work | | |
| Files organized | | |

**Reviewer:** _______________
**Date:** _______________
**Verdict:** [ ] Ready for delivery  [ ] Needs revision
