# Vavin
#
#   make            fonts, specimen assets, proofs, checks
#   make setup      create .venv and install the toolchain
#   make fonts      build all three families + Latin subsets
#   make specimen   sort dist/ by family, emit woff2, wire up specimen/
#   make serve      serve the specimen at http://localhost:8731
#   make proof      render the PNG proof sheets
#   make check      per-glyph checks on every built font
#   make qa         FontBakery on Vavin AND upstream, diffed
#   make install    install into ~/Library/Fonts (macOS)
#   make ufo        Track B - editable UFO sources
#   make release    rebuild, check, then zip release/Vavin-v1.0.zip
#   make zip        zip what is already in dist/
#   make readme-art regenerate the SVGs in docs/assets/
#   make clean

PY  := .venv/bin/python
PIP := VIRTUAL_ENV=.venv uv pip

.PHONY: all setup fonts measure specimen serve proof widths strokes check qa \
        install uninstall ufo ufo-build release zip readme-art clean distclean

all: fonts specimen proof check

# ---------------------------------------------------------------- toolchain

.venv:
	uv venv --python 3.12 .venv

setup: .venv
	$(PIP) install \
	  "fonttools[ufo,lxml,woff,unicode]" defcon fontParts glyphsLib ufo2ft \
	  fontmake uharfbuzz booleanOperations skia-pathops fontbakery gftools Pillow hyperglot
	@echo "hb-view is needed for the PNG proofs: brew install harfbuzz"

upstream:
	./scripts/00_fetch_upstream.sh

# ------------------------------------------------------------------- build

fonts:
	$(PY) scripts/03_restyle.py --subset

measure:
	$(PY) scripts/01_measure.py

specimen:
	$(PY) scripts/21_specimen.py

serve:
	@echo "→ http://localhost:8731"
	@python3 -m http.server 8731 --directory specimen

# ------------------------------------------------------------------ proofs

proof:
	$(PY) scripts/04_proof.py
	$(PY) scripts/07_hero.py

widths:
	$(PY) scripts/09_variants.py

strokes:
	$(PY) scripts/08_strokes.py

# ------------------------------------------------------------------ checks

check:
	$(PY) scripts/05_verify.py

qa:
	$(PY) scripts/06_qa.py

# ----------------------------------------------------------------- track B

ufo:
	$(PY) scripts/10_track_b.py --convert --restyle

ufo-build:
	$(PY) scripts/10_track_b.py --build

# ----------------------------------------------------------------- install

install:
	@mkdir -p ~/Library/Fonts
	@cp dist/*/ttf/*.ttf ~/Library/Fonts/
	@echo "installed:"
	@ls ~/Library/Fonts/Vavin*.ttf | sed 's|.*/|  |'

uninstall:
	@rm -f ~/Library/Fonts/Vavin*.ttf
	@echo "removed Vavin from ~/Library/Fonts"

# ----------------------------------------------------------------- release


release: fonts specimen check zip

zip:
	$(PY) scripts/20_package.py

readme-art:
	$(PY) docs/assets/make_svgs.py

# ------------------------------------------------------------------- clean

clean:
	rm -rf build dist release documentation/*.png \
	       specimen/fonts specimen/fonts.css

distclean: clean
	rm -rf .venv sources/upstream_*
