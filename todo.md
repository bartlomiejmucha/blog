# TODO

- [x] Self-host Google Fonts. `_includes/head.html` loads Inter, Instrument Serif and JetBrains Mono from `fonts.googleapis.com`, which sends every visitor's IP to Google. Serve the font files from `assets/fonts/` and drop the `fonts.googleapis.com` / `fonts.gstatic.com` preconnects in `_layouts/page.html`.
- [ ] Evaluate Cloudflare Web Analytics, either alongside Google Analytics or as a replacement. It is cookieless, so as a replacement the consent banner (`_includes/cookie-consent.html`, `assets/js/consent.js`) could be removed. Alongside GA it would also count visitors who reject cookies.
- [x] Upgrade the theme from Tailwind v3 to v4. Config moved from `tailwind.config.js` into `_tailwind/input.css`.
