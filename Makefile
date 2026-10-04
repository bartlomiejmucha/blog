# Builds a zip of the static site for manual upload to Cloudflare Workers.
#
#   make          same as `make zip`
#   make dist     stage the shippable files in dist/
#   make zip      stage, then write site.zip
#   make clean    remove dist/ and site.zip
#
# `dist` runs both Tailwind builds first, so the CSS is never stale.

COURSES := courses/llm-from-scratch courses/mlx-swift-inference
SWIFT_COURSE := courses/mlx-swift-inference

.PHONY: all css dist zip clean

all: zip

css:
	./build.sh
	for c in $(COURSES); do $$c/build.sh; done

dist: css
	rm -rf dist
	cp index.html styles.css custom.css dist/ 2>/dev/null || (mkdir -p dist && cp index.html styles.css custom.css dist/)
	for c in $(COURSES); do mkdir -p dist/$$c && cp -R $$c/index.html $$c/lessons $$c/assets dist/$$c/; done
	# The Swift course links to its companion package as a download.
	cd $(SWIFT_COURSE) && zip -qr $(CURDIR)/dist/$(SWIFT_COURSE)/qwenserve-src.zip code \
		-x 'code/DerivedData/*' -x 'code/.build/*' -x 'code/.swiftpm/*' -x '*.profraw' -x '*.DS_Store'

zip: dist
	rm -f site.zip
	cd dist && zip -qr ../site.zip . -x '.DS_Store' -x '*/.DS_Store'
	@echo "site.zip → $$(du -h site.zip | cut -f1), $$(unzip -l site.zip | tail -1 | awk '{print $$2}') files"

clean:
	rm -rf dist site.zip
