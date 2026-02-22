# Visual Fidelity Checklist

Verify your clone matches the original at each breakpoint. Compare side-by-side using reference screenshots.

Test at these viewport widths: **320px**, **768px**, **1024px**, **1440px**

---

## Typography

- [ ] Font family matches at all heading levels (h1-h6)
- [ ] Font family matches for body text
- [ ] Font family matches for navigation and UI elements
- [ ] Font weights match (regular, bold, light variants)
- [ ] Font sizes match at each heading level (within 1px)
- [ ] Line heights match (within 2px)
- [ ] Letter spacing matches (if non-default)
- [ ] Text transforms match (uppercase, capitalize)
- [ ] Font style matches (italic where used)
- [ ] Web fonts load correctly (no FOUT/FOIT issues)

## Colors

- [ ] Heading text color matches (within +/-2 hex values)
- [ ] Body text color matches
- [ ] Link color matches (default state)
- [ ] Link hover color matches
- [ ] Link visited color matches (if distinct)
- [ ] Button background color matches
- [ ] Button text color matches
- [ ] Button hover state colors match
- [ ] Page background color matches
- [ ] Section background colors match
- [ ] Card/box background colors match
- [ ] Border colors match
- [ ] Divider/separator colors match
- [ ] Footer background and text colors match
- [ ] Navigation background and text colors match

## Spacing

- [ ] Content area max-width matches
- [ ] Section padding matches (top, bottom)
- [ ] Paragraph margins match
- [ ] Heading margins match (above and below)
- [ ] Card/component internal padding matches
- [ ] Gap between grid/flex items matches
- [ ] Navigation item spacing matches
- [ ] Footer section spacing matches
- [ ] Button padding matches (internal)
- [ ] List item spacing matches

## Layout

- [ ] Overall page structure matches (header, content, footer positioning)
- [ ] Column widths match at desktop breakpoint
- [ ] Column stacking is correct at mobile breakpoint
- [ ] Float behavior matches (text wrapping around images)
- [ ] Flex/grid alignment matches (center, space-between, etc.)
- [ ] Sidebar positioning matches (if applicable)
- [ ] Sticky/fixed elements behave correctly
- [ ] Content centering matches
- [ ] Clear/clearfix behavior matches (no float leaks)
- [ ] Z-index stacking order matches (overlapping elements)

## Images

- [ ] Hero/banner images display at correct size
- [ ] Image aspect ratios match
- [ ] Image border-radius matches (rounded, circular)
- [ ] Image alignment matches (left, right, center)
- [ ] Decorative images and dividers present
- [ ] Logo displays at correct size
- [ ] Favicon is present and correct
- [ ] Alt text is present on all images
- [ ] Lazy loading works (if original uses it)
- [ ] Placeholder/fallback images display correctly

## Interactive Elements

- [ ] Hover states match on links and buttons
- [ ] Focus states present for accessibility
- [ ] Dropdown menus appear correctly (if applicable)
- [ ] Accordion open/close animation matches (if applicable)
- [ ] Tab switching works correctly (if applicable)
- [ ] Scroll behavior matches (smooth scroll, anchor links)
- [ ] Form input styling matches (borders, focus states)
- [ ] Cursor styles match (pointer on clickable elements)

## Responsive Behavior

### At 320px (Mobile)
- [ ] Navigation collapses appropriately
- [ ] Content is single-column
- [ ] Images scale down without overflow
- [ ] Text remains readable (no tiny fonts)
- [ ] Touch targets are adequate size (44px minimum)
- [ ] No horizontal scrollbar

### At 768px (Tablet)
- [ ] Column layout adjusts correctly
- [ ] Navigation style matches (may differ from desktop)
- [ ] Image sizing is appropriate
- [ ] Spacing adjusts proportionally

### At 1024px (Small Desktop)
- [ ] Full desktop layout renders
- [ ] All columns visible
- [ ] Navigation fully expanded (if applicable)

### At 1440px (Large Desktop)
- [ ] Content doesn't stretch beyond max-width
- [ ] Centering is maintained
- [ ] No awkward gaps or spacing at wide viewports

---

## Scoring Guide

For each section, assign a fidelity score:

| Score | Meaning |
|-------|---------|
| 5/5 | Pixel-perfect match |
| 4/5 | Minor differences only visible on close inspection |
| 3/5 | Noticeable differences but same visual impression |
| 2/5 | Significant divergence from original |
| 1/5 | Barely resembles the original |

**Target:** 4/5 or higher in all sections before delivery.
