# Hello Programming World — Jekyll theme

The theme for [bartlomiejmucha.com](https://www.bartlomiejmucha.com). It lives on the `theme`
branch of this repository and is pulled into the site by the content branch (`pages`) through:

```yaml
# _config.yml on the pages branch
remote_theme: bartlomiejmucha/blog@theme
plugins:
  - jekyll-remote-theme
```

Styling is Tailwind utilities in the templates, plus hand-written CSS in `_sass/blog.scss` for
long-form article typography and code highlighting.

## Rebuild the CSS after changing classes

**`assets/css/tailwind.css` is a build artefact and is committed to the repository.** It contains
only the utility classes Tailwind found in the templates when it last ran. If you add or change a
Tailwind class in `_layouts`, `_includes` or `assets/js/theme.js` and do not rebuild, that class
will simply not exist in the stylesheet and the change will not show up on the site.

```bash
./script/build-css.sh          # one-off build
./script/build-css.sh --watch  # rebuild while you edit
```

The script needs the standalone Tailwind CLI, which requires no Node install. Download
`tailwindcss-macos-arm64` from the [Tailwind releases page](https://github.com/tailwindlabs/tailwindcss/releases),
put it on your `PATH` as `tailwindcss`, or point `TAILWIND_BIN` at it:

```bash
TAILWIND_BIN=~/bin/tailwindcss ./script/build-css.sh
```

Classes that only ever appear in JavaScript at runtime — the table-of-contents scroll-spy and the
back-to-top button — are listed in the `safelist` in `tailwind.config.js`. Add to that list if you
introduce more.

### Why not the Tailwind CDN

An earlier version loaded `cdn.tailwindcss.com`, which generates the CSS in the browser after the
page has already painted. That produced a visible flash of unstyled HTML on every page load. The
precompiled stylesheet avoids it and is far smaller than the CDN runtime.

## Preview locally without deploying

`remote_theme` only resolves on GitHub Pages, so for a local preview point Jekyll at both branches
at once: clone the content branch, then symlink the theme directories into it and drop
`remote_theme` from its config.

```bash
git clone -b pages https://github.com/bartlomiejmucha/blog blog-pages
git clone -b theme https://github.com/bartlomiejmucha/blog blog-theme

cd blog-pages
sed -i '' '/remote_theme/d; /jekyll-remote-theme/d' _config.yml   # local preview only, do not commit

rm -rf _layouts _sass assets/css assets/js
ln -s ../blog-theme/_layouts   _layouts
ln -s ../blog-theme/_sass      _sass
ln -s ../blog-theme/assets/css assets/css
ln -s ../blog-theme/assets/js  assets/js
ln -s ../../blog-theme/_includes/*.html _includes/

jekyll serve --watch
```

GitHub Pages builds with Jekyll 3.9, so pin that locally to catch anything that would break in
production.

## Layout

| Path | What it is |
|---|---|
| `_layouts/page.html` | Site shell: head, header, hero on the home page, content column, sidebar, footer |
| `_layouts/post.html` | Article: meta line, title, body, tags, author box, related posts |
| `_layouts/tag.html` | Posts for one tag |
| `_includes/head.html` | Meta tags, Open Graph, fonts, stylesheets |
| `_includes/hero.html` | Home page headline — **the copy is hardcoded here** |
| `_includes/toc.html` | Sidebar shown on articles; the list itself is built by JavaScript |
| `_includes/recent-posts.html` | Featured post plus the archive grouped by year |
| `_sass/blog.scss` | Article typography, Rouge syntax colours, fallbacks for legacy markup |
| `assets/js/theme.js` | Reading progress, table of contents, read time, back to top |

Includes keep the names the content branch already uses, so the two branches can be updated
independently.

## Conventions

- Tag links are built from `site.tags_url`, which defaults to `/en/blog/tags/`. A site whose tag
  hub lives elsewhere overrides it in `_config.yml`. Either way the site must provide that hub
  page plus one `layout: tag` stub per tag.
- `layout: page` wraps the page body in `.prose` so plain Markdown gets article typography.
  A page that ships its own Tailwind markup should set `no_prose: true` in its front matter to
  opt out — otherwise `.prose` link and list styling overrides it.
- Colours are `ink` (`#0a0a0a`) and `paper` (`#f6f5f2`); define new ones in `tailwind.config.js`
  rather than as arbitrary hex values in the templates.
- Fonts: Inter for text, Instrument Serif for italic accents, JetBrains Mono for code.
- Article headings come from post Markdown. Both `##` and `###` are picked up by the table of
  contents.
- The theme carries no `assets/images/logo.png`; branding is the wordmark in `_includes/header.html`.
