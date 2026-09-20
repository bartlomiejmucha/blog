# SEO backlog

Notes from the SEO review rounds. Lives in `_notes/` so Jekyll ignores it
(underscore-prefixed directories are never copied to `_site`).

Findings keep their original codes (F1-F9) across sessions. Do not renumber.

---

## Done

- **F2 (og:image) - reverted 2026-09-20.** The `og:image` block in `head.html` is
  commented out and the default card `assets/images/og-default.png` plus
  `site.og_image` were removed. Pages currently emit no `og:image` at all.
- **F7 (analytics).** `google_analytics_id` swapped from the dead `UA-51153105-1`
  to GA4 `G-S2470CXBB6`. The existing gtag.js snippet is already GA4-compatible so
  only the ID changed; Cookiebot's `type="text/plain"` +
  `data-cookieconsent="statistics"` gating is untouched. Verified in a real build.
  The site does NOT use Google Tag Manager - there is no `GTM-` container anywhere.
  gtag.js is merely *served from* googletagmanager.com, which is confusing. The tag
  lives in `blog@theme/_includes/google-analytics.html`, included by
  `_layouts/page.html`, ID from `_config.yml`. Nothing to configure in
  tagmanager.google.com.
  Until this is deployed, GA4 data arrives via a connected site tag bridging the old
  UA tag. Remove that bridge in GA4 once the new tag is confirmed in Realtime.
- **F4 (headings) - structural half.** All 41 posts: zero `h1` in post bodies
  (the layout owns it), zero cases of `h3` before any `h2`. 123 `h2`, 28 `h3`.
  31 posts that jumped h1 -> h3 were demoted to `h2` with deeper levels shifted.
  16 headings were hand-drafted and inserted into the 5 thin-but-real posts
  (autohotkey, unused-assets, session-storage, adaptive-sampling, mediacache).
- **F5 (image CLS).** All 40 markdown images in `_posts` + `_includes/about-me.md`
  carry `{: loading="lazy" width="W" height="H"}` with real on-disk dimensions.
- **F6 (robots.txt).** `Allow: /feed.xml` added above the blanket `Disallow: /`.
- Fixed a `/assets//images/` double-slash path in the 2019-07-11 performance post.
- Resized `posts/035/redis-rps-used-memory.png` 2696x1505 -> 1400x781.
- Added `_tools/scripts/check-images.sh` + pre-commit hook (see "Tooling" below).

## Open

### F1 - No structured data anywhere  (highest value)
No JSON-LD at all. Nothing for `BlogPosting`, `BreadcrumbList`, `WebSite`, `Person`.
This is what drives author/date/breadcrumb display in results. Belongs in
`blog@theme/_includes/head.html`. Also covers `VideoObject` for the video stubs
listed under F4 below - those are video pages and can't win video results without it.

### F2 - remaining: per-post cards, then `summary_large_image`

Decided 2026-08-25: post images stay invisible on the site. `image:` is referenced
in exactly one place in the whole theme - `head.html`, for `og:image`. No layout,
include or listing renders it; `post-summary-no-hero.html` is date + title + tags,
and the hero's latest-article card is text-only. The theme is deliberately
typographic and stays that way. Do not reintroduce thumbnails.

Consequence: `image:` is now purely a social-card field. The 300x225 / 600x500
sizes are legacy thumbnail dimensions from the previous theme and nothing displays
them at any size, so there is no reason to preserve them. Per-post card work means
*replacing* those values with 1200x630, not adding a second set.
`twitter:card` is still hardcoded `summary`, deliberately. Every existing post
image is far too small for a large card - 10 are 300x225, one 460x360, two are
600x500, and only 13 unique images cover the 33 posts that have one. X's hard
minimum for a large card is 300x157, but LinkedIn and Facebook render anything
that small as a thumbnail and Google Discover wants >=1200px wide. Switching the
card type before the images exist makes sharing look worse, not better.

Order of work: re-enable the `og:image` block, produce 1200x630 per-post cards, then flip
to `summary_large_image` - either globally once images are standardised, or gated
on an `image_wide: true` front-matter flag while sizes are mixed.

Posts carrying no `image:` of their own (relevant once `og:image` is re-enabled):

    session-storage, adaptive-sampling, mediacache   (empty `image:` value)
    package-source-mapping, install-xm0, duplicated-names,
    saml-single-logout, run-sitecore-on-a-mac        (no field at all)

### F3 - No modification dates
Zero posts carry `last_modified_at`, so every `<lastmod>` in `sitemap.xml` equals
the publish date - including posts edited since. `head.html` emits no
`article:published_time` / `article:modified_time`.

### F4 - remaining half: 5 thin video stubs
43-77 words each, two sentences plus a `{% include youtube-embed.html %}`.
Headings would be cosmetic; the problem is thin content, not structure.

    2017-07-01  helix-solution-from-scratch            77 words
    2017-08-28  configure-visual-studio-local-publish   47 words
    2017-10-06  helix-serialization-unicorn-40          47 words
    2018-07-28  solrcloud-zookeeper-azure-vpn           43 words
    2019-08-22  taurus-blazemeter-load-tests            49 words

Options: write up what the video shows (best, most work - do the two Helix ones
first, highest search demand); add `VideoObject` JSON-LD (cheap, folds into F1);
or `noindex` them (`head.html` already supports the `noindex` front-matter flag).

### F8 - 70 thin tag pages
All share the template description "Articles tagged X."; several list one post.
Consider `noindex` below a post-count threshold, and hand-written descriptions
for the tags worth ranking.

### Image weight on post 029 (2019-07-11 performance post)
5.8 MB across 8 images; six full-page waterfall screenshots at ~900 KB each.

Measured, so nobody re-litigates this:
- Re-encoding does NOT help. JPEG q60 produced a *larger* file than the original
  (952 KB vs 942 KB). They are already compressed; the weight is pixel count.
- Resizing barely helps: 1885w -> 1400w is only -28% (942 -> 676 KB).
- Resizing the PNG makes it *bigger* (1044 -> 1163 KB); resampling adds noise to
  a screenshot. PNG -> JPEG at 1400w gives 711 KB (-32%).
- `sips` cannot write WebP; no `cwebp` or ImageMagick installed on this machine.

Real problem: at ~3450px tall in a ~700px column these render ~700x1400, so the
text is unreadable at display size no matter what the file weighs.
Fix is to crop to the summary line + waterfall shape, or replace with a table of
the actual before/after numbers and keep the screenshots as links.
Low urgency: all six are below the fold and already lazy, so LCP is unaffected.

### F9 - Self-host fonts (apps subdomain and blog)

Deferred 2026-08-25. Both sites pull webfonts from Google. `apps/index.html`
loads Inter 400/500/600 and Instrument Serif regular+italic;
`blog@theme/_includes/head.html` loads the same two families plus JetBrains Mono
400/500. Both preconnect to `fonts.googleapis.com` and `fonts.gstatic.com`.

Reasons to self-host:
1. Two extra connections on the critical path - a CSS fetch from googleapis,
   then a woff2 fetch from gstatic. `preconnect` softens the handshake but does
   not remove the round trips.
2. No shared-cache benefit any more. Browsers partition the HTTP cache by
   top-level site, so a visitor who already has Inter from another site
   downloads it again here.
3. Google Fonts logs visitor IPs. German courts have ruled that hotlinking it
   without consent breaches GDPR. The blog already runs Cookiebot, so this is
   the site where it matters most.

Work: pull the Latin subset woff2 (~40-60K for the apps set), write `@font-face`
with `font-display: swap` and `unicode-range`, drop the Google stylesheet link
and both `preconnect` tags. Do both sites together - same families, same rules.

---

## Tooling

`_tools/scripts/check-images.sh`, symlinked to `.git/hooks/pre-commit`. Blocks a commit when:
1. an image lacks an IAL with `loading`, `width`, `height`;
2. an image that is the first content element of a post is not `loading="eager"`
   (that position is the LCP element - this is the rule that is easy to forget);
3. an image path does not resolve to a file.

Git never tracks `.git/hooks`, so a fresh clone needs:

    ln -sf ../../_tools/scripts/check-images.sh .git/hooks/pre-commit


## Conventions established

- Headings are written as the question the reader arrived with, not as labels.
  `## Why adaptive sampling drops your AUDIT logs`, not `## Background`.
- Target 2-4 `h2` per post at ~300 words. More than that fragments the page.
- The opening paragraph stays unheaded as the lede; the layout already renders
  `description` above it.
- Body images get `loading="lazy"`; only a first-content-element image gets `eager`.
