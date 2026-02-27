#!/bin/bash
# Local test for JBM ligature transplant.
# Builds a minimal Iosevka font (noLigation), patches it with JBM's calt,
# and verifies ligatures work.
#
# Usage:
#   cd tmp && ./test.sh          # full run (clone + build + patch + test)
#   cd tmp && ./test.sh patch    # skip clone/build, re-patch + test only
#
# Everything stays inside tmp/ — no system packages are modified.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$SCRIPT_DIR/venv/bin/python3"
PLAN=IoskeleyCondensedJBMTest
DIST="$SCRIPT_DIR/iosevka-src/dist/$PLAN/TTF"

# ---------- venv ----------
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "==> Creating Python venv..."
    python3 -m venv "$SCRIPT_DIR/venv"
    "$SCRIPT_DIR/venv/bin/pip" install -q fonttools brotli uharfbuzz
fi

skip_build=false
[[ "${1:-}" == "patch" ]] && skip_build=true

if ! $skip_build; then
    # ---------- Iosevka ----------
    if [ ! -d "$SCRIPT_DIR/iosevka-src" ]; then
        echo "==> Fetching latest Iosevka version..."
        IOSEVKA_VERSION=$(curl -s https://api.github.com/repos/be5invis/Iosevka/releases/latest \
            | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
        echo "    Iosevka $IOSEVKA_VERSION"
        git clone --depth 1 --branch "$IOSEVKA_VERSION" \
            https://github.com/be5invis/Iosevka.git "$SCRIPT_DIR/iosevka-src"
    fi

    echo "==> Building $PLAN (TTF only, Medium + Medium Italic, term)..."
    cp "$SCRIPT_DIR/test-build-plans.toml" "$SCRIPT_DIR/iosevka-src/private-build-plans.toml"
    cd "$SCRIPT_DIR/iosevka-src"
    npm install --silent 2>/dev/null
    npm run build -- ttf::$PLAN
    cd "$SCRIPT_DIR"

    # ---------- JetBrains Mono ----------
    if [ ! -d "$SCRIPT_DIR/jb-mono" ]; then
        echo "==> Downloading JetBrains Mono..."
        JB_VERSION=$(curl -s https://api.github.com/repos/JetBrains/JetBrainsMono/releases/latest \
            | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
        echo "    JetBrains Mono $JB_VERSION"
        curl -sL "https://github.com/JetBrains/JetBrainsMono/releases/download/${JB_VERSION}/JetBrainsMono-${JB_VERSION#v}.zip" \
            -o "$SCRIPT_DIR/jb-mono.zip"
        unzip -q "$SCRIPT_DIR/jb-mono.zip" -d "$SCRIPT_DIR/jb-mono"
    fi
fi

# ---------- Patch ----------
echo "==> Patching ligatures..."
for ttf in "$DIST"/*.ttf; do
    suffix=$(basename "$ttf" .ttf | sed "s/^${PLAN}-//")
    jb_file="$SCRIPT_DIR/jb-mono/fonts/ttf/JetBrainsMono-${suffix}.ttf"
    if [ ! -f "$jb_file" ]; then
        echo "ERROR: No matching JBM file for $suffix"
        exit 1
    fi
    echo "  $(basename "$ttf") <- $(basename "$jb_file")"
    "$PYTHON" "$PROJECT_DIR/patch-ligatures.py" "$ttf" "$jb_file" "$ttf"
done

# ---------- Test ----------
echo ""
echo "==> Running ligature tests..."
"$PYTHON" "$PROJECT_DIR/tests/test_ligatures.py" "$DIST/${PLAN}-Medium.ttf"

echo ""
echo "==> Patched fonts:"
ls -lh "$DIST"/*.ttf
echo ""
echo "Install with:  cp $DIST/*.ttf ~/.local/share/fonts/ && fc-cache"
echo "Family name:   $(grep '^family' "$SCRIPT_DIR/test-build-plans.toml" | head -1 | sed 's/.*"\(.*\)"/\1/')"
