#!/usr/bin/env bash
# Fetch the one and only input this project has: EB Garamond, under the OFL.
#
# Nothing else is ever downloaded, and no other font is ever opened. See
# LEGAL.md section 2.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p sources build dist documentation

GF="https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond"

fetch() {
  local remote="$1" local_name="$2"
  printf '  %-34s' "$local_name"
  curl -sSfL --max-time 120 "$GF/$remote" -o "sources/$local_name"
  printf '%s bytes\n' "$(wc -c < "sources/$local_name" | tr -d ' ')"
}

echo "Fetching upstream EB Garamond from Google Fonts (SIL OFL 1.1)"
fetch "EBGaramond%5Bwght%5D.ttf"        "upstream_EBGaramond[wght].ttf"
fetch "EBGaramond-Italic%5Bwght%5D.ttf" "upstream_EBGaramond-Italic[wght].ttf"
fetch "OFL.txt"                         "upstream_OFL.txt"
fetch "METADATA.pb"                     "upstream_METADATA.pb"

echo
echo "Checking the binaries are the ones Vavin 1.0 was built from:"
# Google Fonts updates main in place. A mismatch is not an error, but the
# numbers in the docs were measured on these exact files.
(cd sources && shasum -a 256 -c <<'SUMS') || echo "  !! upstream changed since Vavin 1.0; rebuild and re-measure (scripts/13_facts.py)."
ef9512f92f6d579e5dc75af59a5a4b1b8b47d2eda89e00b954d44520e5369027  upstream_EBGaramond[wght].ttf
bba2c4499c93c9612b90b9825d32b07da52fce2fe57562a1eb6b833553f93c4e  upstream_EBGaramond-Italic[wght].ttf
SUMS

echo
echo "Reserved Font Name check on the upstream licence:"
if grep -q "with Reserved Font Name" sources/upstream_OFL.txt; then
  echo "  !! upstream DOES declare a Reserved Font Name."
  grep -n "with Reserved Font Name" sources/upstream_OFL.txt
  echo "  The derived family name must avoid it. See LEGAL.md section 5."
else
  echo "  none declared (the phrase appears only in the licence definitions)."
  grep -n "Reserved Font Name" sources/upstream_OFL.txt || true
fi

echo
echo "Done. Next: python scripts/03_restyle.py --subset"
