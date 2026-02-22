# React Template QA Checklist

Pre-delivery quality assurance checklist for chiropractic website projects built with the React template. Every item must pass before handing off to the client.

---

## Build & Performance

- [ ] **`npm run build` completes with zero errors and zero warnings**
  Run `npm run build` from the project root and verify the terminal output shows a successful build with no errors or warnings. If warnings appear (e.g., unused variables, missing dependencies), fix them before proceeding. The final output should show the bundle size summary with no red or yellow text.

- [ ] **Lighthouse performance score >= 90 on mobile**
  Open the deployed staging URL in Chrome, go to DevTools > Lighthouse, select "Mobile" device and check "Performance." Run the audit. The performance score must be 90 or above. Pay attention to Largest Contentful Paint (should be under 2.5s), Cumulative Layout Shift (under 0.1), and Total Blocking Time (under 200ms). If the score is below 90, address the specific recommendations Lighthouse provides (lazy loading images, reducing unused JavaScript, etc.).

- [ ] **All images are WebP format and under 500KB each**
  Open DevTools > Network tab, filter by "Img," and reload the page. Verify every image loads as `.webp` format. Click each image request and check the response size in the Headers or Size column. No single image should exceed 500KB. Hero images should ideally be under 300KB. If any images are PNG/JPG or oversized, convert them using `cwebp` or the project's image optimization script and replace the originals.

---

## Content Accuracy

- [ ] **Business name, phone number, and email are correct across all pages**
  Navigate to every page on the site (Home, About, Services, Contact, and any additional pages). Check the header, footer, and any in-page mentions of the business name, phone number, and email address. Cross-reference each instance against the client's intake form or onboarding document. Verify the phone number uses the correct `tel:` link format (e.g., `<a href="tel:+15551234567">`) and the email uses the correct `mailto:` link. Click both to confirm they trigger the expected action.

- [ ] **Doctor/staff bios are accurate and complete**
  Navigate to the About page (or wherever staff bios are displayed). Verify each team member's name, title/credentials, photo, and bio text matches the content the client provided. Check for spelling errors in names and credentials (e.g., "D.C." vs "DC"). Confirm that staff photos are the correct resolution and not stretched or cropped awkwardly. If the client provided specific credential abbreviations or titles, use those exactly.

- [ ] **Service descriptions match client-provided content**
  Open every service page or service section and compare the displayed text line-by-line against the client's original content document. Check that service names, descriptions, and any listed benefits or techniques are accurate. Verify that no placeholder text (Lorem Ipsum, "Service description here," etc.) remains. Confirm that any service-specific images match the correct service.

- [ ] **Testimonials display correct names and text**
  Locate the testimonials section (typically on the Home page or a dedicated Reviews page). Verify each testimonial's quote text, patient first name (or full name if provided), and any associated star rating matches the client's provided testimonials. Check that quotation marks render correctly and that no testimonial is duplicated or missing. If testimonials rotate in a carousel, click through all slides to verify each one.

---

## Responsive Design

- [ ] **Site renders correctly at 375px (mobile)**
  Open Chrome DevTools, toggle the device toolbar, and set the viewport to 375px wide (iPhone SE/standard mobile). Navigate through every page. Verify that no content overflows horizontally (no horizontal scrollbar), text is readable without zooming (minimum 16px body text), images scale down properly, and all interactive elements (buttons, links, forms) are tappable with adequate touch targets (minimum 44x44px). Check that no elements overlap or get hidden behind other content.

- [ ] **Site renders correctly at 768px (tablet)**
  Set the DevTools viewport to 768px wide (iPad portrait). Navigate through every page. Verify the layout transitions correctly from mobile to tablet breakpoint: the navigation may switch from hamburger to full menu, content columns should reflow appropriately (e.g., 2 columns instead of 1), and images should resize without distortion. Check that there is no awkward whitespace or content that appears too small or too large for this viewport.

- [ ] **Site renders correctly at 1024px+ (desktop)**
  Set the viewport to 1024px, 1280px, and 1440px. Verify the full desktop layout displays correctly at each width: the navigation is fully visible, content is properly centered with reasonable max-width constraints, hero sections span the full width appropriately, and the layout does not break or create excessively wide text lines (aim for 60-80 characters per line for readability). Test at 1920px as well to ensure the design does not look sparse on large monitors.

- [ ] **Mobile CTA bar appears on scroll and all 3 buttons work**
  On a 375px viewport, scroll down past the hero section. A sticky CTA bar should appear at the bottom of the screen containing three buttons (typically: Call, Book, and Directions/Map). Verify that: (1) the bar appears smoothly on scroll and disappears when scrolling back to the top, (2) the Call button triggers the device phone dialer with the correct number, (3) the Book button navigates to the booking URL or opens the scheduling widget, and (4) the Directions button opens Google Maps with the correct business address. Test each button by clicking and confirming the expected behavior.

---

## Functionality

- [ ] **Contact form submits successfully and email is received**
  Navigate to the Contact page and fill out every form field with test data (use a recognizable test name like "QA Test Submission" so it is easy to identify). Submit the form. Verify that: (1) a success message or confirmation screen appears, (2) the form fields clear or the page redirects as expected, (3) a confirmation email is received at the client's designated inbox within 5 minutes, and (4) the email contains all submitted form fields with correct data. Also test validation by submitting with empty required fields and an invalid email format to confirm error messages display correctly.

- [ ] **All external links (social media, booking) open in new tabs**
  Click every external link on the site, including social media icons in the header/footer, booking/scheduling links, Google Maps links, and any third-party review site links. Each must open in a new browser tab (verify `target="_blank"` and `rel="noopener noreferrer"` are present in the HTML). Internal navigation links (Home, About, Services, Contact) should NOT open in new tabs. Use DevTools to inspect link elements if any behavior seems incorrect.

- [ ] **Navigation works on all pages (including mobile hamburger menu)**
  On desktop (1024px+), click every item in the main navigation and verify it routes to the correct page. Check that the active page is visually indicated in the nav (highlighted, underlined, or bold). Then switch to mobile viewport (375px), tap the hamburger icon, and verify the mobile menu opens with a smooth animation. Tap each menu item and confirm it navigates to the correct page and the menu closes afterward. Also verify the menu can be closed by tapping the X/close button or tapping outside the menu overlay.

- [ ] **Schema.org structured data validates (test with Google Rich Results)**
  Copy the staging URL and paste it into the [Google Rich Results Test](https://search.google.com/test/rich-results). Run the test and verify that: (1) no errors are reported, (2) the LocalBusiness schema is detected with correct business name, address, phone number, and business hours, (3) any additional schema types (e.g., MedicalBusiness, Physician) are valid, and (4) warnings are minimal and non-critical. Alternatively, paste the page source into the [Schema.org Validator](https://validator.schema.org/) for a detailed breakdown. Fix any errors before delivery.

---

## Sign-Off

| Check | Status | Notes |
|-------|--------|-------|
| Build clean | | |
| Lighthouse >= 90 | | |
| Images optimized | | |
| Business info correct | | |
| Bios accurate | | |
| Services match | | |
| Testimonials correct | | |
| Mobile 375px | | |
| Tablet 768px | | |
| Desktop 1024px+ | | |
| Mobile CTA bar | | |
| Contact form works | | |
| External links | | |
| Navigation | | |
| Schema.org valid | | |

**Reviewer:** _______________
**Date:** _______________
**Verdict:** [ ] Ready for delivery  [ ] Needs revision
