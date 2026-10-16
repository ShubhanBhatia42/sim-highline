# Short commands for the common jobs. `make help` lists them.
.PHONY: help build test browser verify reproduce lint og links serve clean
help:        ## this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'
build:       ## rebuild dist/ (Explorer, site, static files)
	node scripts/build-static.mjs && node scripts/build-highline.mjs && node scripts/build-site.mjs
lint:        ## syntax of every script, JSON validity, balanced HTML in the built pages
	node scripts/lint.mjs
test:        ## the offline checks (no browser): data, export, site, Python tests
	./scripts/verify-all.sh
browser:     ## every browser test against dist/ (needs `npm ci` and a Chromium)
	npm run test:browser
verify: build lint test browser   ## everything a pull request has to pass
reproduce:   ## rebuild the exploratory numbers from the saved results (about 10 minutes)
	./scripts/reproduce.sh
og:          ## regenerate the share-preview images from the real charts, then rebuild
	node scripts/make-og-images.mjs && node scripts/build-site.mjs
links:       ## check every external link on the built pages (needs a network)
	python3 scripts/check_links.py --site
serve:       ## open the built site at http://localhost:8000/
	python3 -m http.server -d dist
clean:       ## remove generated files
	rm -rf dist
