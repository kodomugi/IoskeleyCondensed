# Local Testing

Test the JBM ligature transplant locally. Everything lives in `tmp/` — no system packages are modified.

## Quick Start

```bash
cd tmp
./test.sh            # full run: clone + build + patch + test (~5-15 min)
./test.sh patch      # re-patch + test only (seconds)
```

## Directory Layout

After a full run, `tmp/` will contain:

```
tmp/
├── test.sh                 # test script (committed)
├── test-build-plans.toml   # minimal build plan (not committed, see below)
├── venv/                   # Python venv (fonttools, uharfbuzz, brotli)
├── iosevka-src/            # Iosevka source + build output
├── jb-mono/                # JetBrains Mono download
└── jb-mono.zip
```

## Test Build Plan

`test-build-plans.toml` is derived from the main `private-build-plans.toml` with these changes:

- `noLigation = true`, `noCvSs = true`, `exportGlyphNames = false`
- Single weight only (e.g. Medium) to speed up builds
- Family name with a "Test" suffix to avoid conflicts with installed fonts

The plan name must be `IoskeleyCondensedJBMTest` (hardcoded in `test.sh`).

## Install Test Fonts

```bash
rm -f ~/.local/share/fonts/IoskeleyCondensedJBMTest*.ttf
cp tmp/iosevka-src/dist/IoskeleyCondensedJBMTest/TTF/*.ttf ~/.local/share/fonts/
fc-cache -fv
```

The family name is set by the `family` field in `test-build-plans.toml`.
Change the name each time to avoid font cache issues.

## Remove Test Fonts

```bash
rm -f ~/.local/share/fonts/IoskeleyCondensedJBMTest*.ttf
fc-cache -fv
```

## Visual Testing

Open `jbm-ligatures.txt` in an editor with the test font and compare against JetBrains Mono to verify ligature appearance.

## Cleanup

```bash
rm -rf tmp/venv tmp/iosevka-src tmp/jb-mono tmp/jb-mono.zip tmp/test-build-plans.toml
```
