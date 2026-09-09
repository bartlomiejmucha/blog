# Builds a zip of the static site for manual upload to Cloudflare Workers.
#
#   make          same as `make zip`
#   make dist     stage the shippable files in dist/
#   make zip      stage, then write site.zip
#   make clean    remove dist/ and site.zip
#
# `dist` runs the Tailwind build first, so the CSS is never stale.

.PHONY: all css dist zip clean

all: zip

css:
	./build.sh

dist: css
	rm -rf dist
	mkdir -p dist
	cp index.html styles.css custom.css dist/
	cp -R images dist/

zip: dist
	rm -f site.zip
	cd dist && zip -qr ../site.zip . -x '.DS_Store' -x '*/.DS_Store'
	@echo "site.zip → $$(du -h site.zip | cut -f1), $$(unzip -l site.zip | tail -1 | awk '{print $$2}') files"

clean:
	rm -rf dist site.zip
