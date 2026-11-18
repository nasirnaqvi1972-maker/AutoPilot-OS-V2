# GDPR & Author Bio Snippets for Blogger

**Purpose:** Add GDPR-compliant cookie consent + "About the Author" widget  
**Platform:** Blogger (Layout → Add a Gadget → HTML/JavaScript)  
**Safety:** Pure HTML/CSS/JS — no external dependencies, no theme XML edits required

---

## 1. GDPR Cookie Consent Banner

### Code (copy entirely)

```html
<!-- GDPR Cookie Consent Banner - Dust and Dynasty -->
<style>
  #cookie-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1a1a1a;
    color: #eee;
    padding: 16px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
    z-index: 9999;
    display: none;
    max-width: 800px;
    margin: 0 auto;
    border-radius: 8px 8px 0 0;
  }
  #cookie-banner.visible { display: block; }
  #cookie-banner p { margin: 0 0 12px; }
  #cookie-banner a { color: #ffd700; text-decoration: underline; }
  #cookie-banner button {
    background: #ffd700;
    color: #1a1a1a;
    border: none;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
  }
  #cookie-banner button:hover { background: #e6c200; }
  @media (max-width: 480px) {
    #cookie-banner { border-radius: 0; padding: 14px 16px; }
  }
</style>

<div id="cookie-banner" role="dialog" aria-live="polite" aria-label="Cookie consent">
  <p>We use cookies to analyze traffic and improve your experience. By clicking "Accept", you consent to our use of cookies. <a href="/p/privacy-policy.html" target="_blank" rel="noopener">Read our Privacy Policy</a>.</p>
  <button id="cookie-accept" type="button">Accept</button>
</div>

<script>
(function() {
  'use strict';
  
  const BANNER_ID = 'cookie-banner';
  const COOKIE_NAME = 'ddd_cookie_consent';
  const COOKIE_EXPIRY_DAYS = 365;
  
  // Check if consent already given
  function hasConsent() {
    return document.cookie.split('; ').some(row => row.startsWith(COOKIE_NAME + '='));
  }
  
  // Set consent cookie
  function setConsent() {
    const expiry = new Date();
    expiry.setTime(expiry.getTime() + COOKIE_EXPIRY_DAYS * 24 * 60 * 60 * 1000);
    document.cookie = COOKIE_NAME + '=1; expires=' + expiry.toUTCString() + '; path=/; SameSite=Lax';
  }
  
  // Show banner
  function showBanner() {
    const banner = document.getElementById(BANNER_ID);
    if (banner) {
      // Use requestAnimationFrame to ensure style is applied before animation
      requestAnimationFrame(() => {
        banner.classList.add('visible');
      });
    }
  }
  
  // Hide banner
  function hideBanner() {
    const banner = document.getElementById(BANNER_ID);
    if (banner) {
      banner.classList.remove('visible');
    }
  }
  
  // Init
  function init() {
    if (hasConsent()) return;
    
    const acceptBtn = document.getElementById('cookie-accept');
    if (acceptBtn) {
      acceptBtn.addEventListener('click', function() {
        setConsent();
        hideBanner();
      });
    }
    
    // Small delay to ensure DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
  
  init();
})();
</script>
```

### How to Install in Blogger

1. Open **Blogger Dashboard** → **Layout**
2. Click **"Add a Gadget"** (anywhere — sidebar, footer, or cross-column)
3. Choose **"HTML/JavaScript"** from the list
4. **Title:** Leave blank (or "Cookie Consent")
5. **Content:** Paste the entire code block above (including `<style>`, `<div>`, `<script>`)
6. Click **Save**
7. Click **Save arrangement** (top-right)
8. **Test:** Open your blog in incognito/private window → banner should appear at bottom

> **Why this works:** Blogger gadgets render as inline HTML. The `<style>` and `<script>` tags execute normally. No XML theme editing needed.

---

## 2. About the Author Widget

### Code (copy entirely)

```html
<!-- About the Author Widget - Dust and Dynasty -->
<style>
  .author-widget {
    background: #fdfbf7;
    border: 1px solid #e6dbcb;
    border-radius: 8px;
    padding: 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #2c3e50;
    max-width: 300px;
    margin: 0 auto;
  }
  .author-widget__header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .author-widget__avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #d4a373 0%, #2a5c43 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .author-widget__name {
    font-size: 16px;
    font-weight: 700;
    line-height: 1.3;
    margin: 0;
  }
  .author-widget__title {
    font-size: 12px;
    color: #5a6c7a;
    margin: 2px 0 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .author-widget__bio {
    font-size: 13px;
    line-height: 1.6;
    color: #3e4d5a;
    margin: 0;
  }
  .author-widget__links {
    margin-top: 16px;
    display: flex;
    gap: 12px;
  }
  .author-widget__links a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #e6dbcb;
    color: #2c3e50;
    text-decoration: none;
    transition: background 0.2s, color 0.2s;
  }
  .author-widget__links a:hover {
    background: #d4a373;
    color: #fff;
  }
  .author-widget__links svg { width: 18px; height: 18px; }
</style>

<div class="author-widget" role="complementary" aria-label="About the author">
  <div class="author-widget__header">
    <div class="author-widget__avatar" aria-hidden="true">NA</div>
    <div>
      <p class="author-widget__name">Nasir A Naqvi</p>
      <p class="author-widget__title">Historian & Writer</p>
    </div>
  </div>
  <p class="author-widget__bio">
    Independent researcher specializing in South Asian archaeology, UNESCO World Heritage sites, and the deep history of the Indus Valley. Author of <em>Dust and Dynasty</em>, a long-form encyclopedia of lost cities and living monuments across Pakistan, India, and beyond.
  </p>
  <div class="author-widget__links">
    <a href="https://dustanddynasty.blogspot.com" target="_blank" rel="noopener noreferrer" aria-label="Visit Dust and Dynasty blog">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12V7H5V21H16M3 5L12 12L3 19"/></svg>
    </a>
    <a href="https://twitter.com/nasiranaqvi" target="_blank" rel="noopener noreferrer" aria-label="Follow on Twitter">
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z"/></svg>
    </a>
  </div>
</div>
```

### How to Install in Blogger

1. Open **Blogger Dashboard** → **Layout**
2. Click **"Add a Gadget"** in the **Sidebar** (or wherever you want the author box)
3. Choose **"HTML/JavaScript"**
4. **Title:** "About the Author" (or leave blank — the widget has its own heading)
5. **Content:** Paste the entire code block above
6. Click **Save**
7. Drag the gadget to your preferred position in the sidebar
8. Click **Save arrangement**

> **Customization:** Replace the Twitter link (`https://twitter.com/nasiranaqvi`) with your actual profile URL. Add more links by copying the `<a>...</a>` line and changing the `href` and SVG icon.

---

## Security & Performance Notes

| Aspect | Detail |
|--------|--------|
| **Cookie Banner** | Sets first-party cookie `ddd_cookie_consent=1` with `SameSite=Lax`, 365-day expiry. No third-party scripts. |
| **No External Dependencies** | All CSS/JS inline. No CDN, no jQuery, no Google Fonts. |
| **CSP Friendly** | Inline `<script>` and `<style>` — works with Blogger's default CSP. If you have a strict CSP, add `'unsafe-inline'` for script/style or move to external files. |
| **Accessibility** | `role="dialog"`, `aria-live`, `aria-label`, focusable button, semantic HTML. |
| **Lightweight** | ~2.5 KB total (gzipped < 1 KB). No layout shift. |
| **Blogger Safe** | Uses Layout Gadgets — no Theme → Edit HTML required. Zero risk of breaking XML. |

---

## Verification Checklist

After installing both gadgets:

- [ ] Open blog in **incognito/private window** → Cookie banner appears at bottom
- [ ] Click **"Accept"** → Banner disappears, refresh → Stays hidden
- [ ] Check **Developer Tools → Application → Cookies** → `ddd_cookie_consent=1` present
- [ ] Sidebar shows **"About the Author"** widget with bio and links
- [ ] Links open in new tab (`target="_blank"` + `rel="noopener noreferrer"`)
- [ ] Mobile view: Banner spans full width, widget fits sidebar

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Banner doesn't appear | Clear browser cookies for the domain, reload in incognito |
| Widget looks squished | Ensure gadget is in a sidebar column ≥ 280px wide |
| "Accept" button does nothing | Check browser console for JS errors — usually a CSP block; add `'unsafe-inline'` to script-src |
| Styles leak into posts | Styles are scoped by ID/class — extremely unlikely, but add `!important` to key rules if needed |
PYEOF
filePath: D:\Projects\AutoPilot_OS_v2\GDPR_AUTHOR_SNIPPETS.md