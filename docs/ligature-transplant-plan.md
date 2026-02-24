# Ligature Transplant: JetBrains Mono → Ioskeley Condensed

## Motivation

Iosevka's built-in arrow ligatures visually differ from Berkeley Mono's style. Iosevka only provides predefined ligature variants, none close enough. JetBrains Mono's arrow ligatures are a better match and are transplanted as a post-build step.

Iosevka's ligature customization is limited to:
- Enabling/disabling entire ligation **groups** (e.g., `arrow-r-equal` covers `=>`, `==>`, `===>` together)
- Choosing from predefined visual **variants** via `lig-*` settings in `variants.design`
- No support for per-ligature control or custom glyph shapes through the build plan

## Scope

17 arrow ligatures transplanted from JetBrains Mono:

| Sequence | JetBrains Mono Glyph Name |
|----------|---------------------------|
| `<==>` | `less_equal_equal_greater.liga` |
| `==>` | `equal_equal_greater.liga` |
| `=>>` | `equal_greater_greater.liga` |
| `<<=` | `less_less_equal.liga` |
| `>>=` | `greater_greater_equal.liga` |
| `<=<` | `less_equal_less.liga` |
| `>=>` | `greater_equal_greater.liga` |
| `<==` | `less_equal_equal.liga` |
| `<=>` | `less_equal_greater.liga` |
| `<=\|` | `less_equal_bar.liga` |
| `\|=>` | `bar_equal_greater.liga` |
| `=<<` | `equal_less_less.liga` |
| `<-<` | `less_hyphen_less.liga` |
| `>->` | `greater_hyphen_greater.liga` |
| `-<<` | `hyphen_less_less.liga` |
| `>>-` | `greater_greater_hyphen.liga` |
| `=>` | `equal_greater.liga` |

## Implementation

### Approach: Full Glyph Replacement via GSUB Chain Lookups

Rather than modifying Iosevka's complex fragment-based ligature system, we:
1. Copy full-width ligature glyphs from JetBrains Mono (scaled from 600 → 500 width)
2. Add new GSUB ChainContextSubst lookups at the beginning of the LookupList
3. Each N-char ligature uses N passes: first N-1 chars → SPC (empty spacer), last char → liga glyph

### Key Components in `patch-ligatures.py`

- **`CHAR_GLYPH`**: Maps characters (`= > < - |`) to glyph names
- **`LIGATURES`**: Declarative list of 17 ligatures, longest first
- **`SubstRegistry`**: Deduplicates SingleSubst lookups (e.g., `equal→SPC` created once)
- **`compute_ignore_rules()`**: Automatically detects substring overlaps between ligatures and generates ignore rules to prevent shorter ligatures from matching inside longer ones
- **`build_ligature_chain_lookups()`**: Generic N-char ligature builder
- **Blocking (seed + propagation)**: Prevents `={m}>{n}` sequences where m+n ≥ 4 from ligating (e.g., `===>`, `==>>`)

### Lookup Structure (~96 total)

| Type | Count | Purpose |
|------|-------|---------|
| SingleSubst | ~24 | char→SPC, char→liga, char→noliga substitutions |
| Blocking seed | 1 | Detect overlong `={m}>{n}` sequences |
| Blocking propagation | 20 | Spread noliga marking to adjacent chars |
| Ligature chains | ~51 | N passes per ligature (4+3×15+2 = 51) |

### Italic Handling

The script detects italic fonts via `post.italicAngle` or `OS/2.fsSelection` and applies the corresponding slant transform to transplanted glyphs.

## Font Metrics

Both fonts use 1000 UPM. Glyphs are horizontally scaled from 600 → 500 width.

| Metric | Iosevka (this project) | JetBrains Mono |
|--------|------------------------|----------------|
| UPM | 1000 | 1000 |
| Width | 500 | 600 |

## Licensing

Both fonts are under **SIL Open Font License 1.1**. Mixing glyphs is permitted as long as:
- The result is distributed under OFL
- Reserved Font Names are not used

## Testing

- **CI smoke test**: uharfbuzz verifies all 17 ligatures produce substituted glyphs
- **Local test**: `tests/test_ligatures.py <patched.ttf> <unpatched.ttf>`
- **Blocking verification**: `===>`, `==>>` must NOT produce arrow liga glyphs (note: `====` will still show Iosevka's built-in equal-chain ligature, which is expected)

## Notes

- Iosevka includes `calt` ligatures by default without an explicit `[ligations]` section in the build plan. Adding `inherits = "default-calt"` is redundant and unnecessary. The patch script hooks into the existing `calt` feature.

## References

- [fonttools documentation](https://fonttools.readthedocs.io/)
- [JetBrains Mono source](https://github.com/JetBrains/JetBrainsMono)
- [Iosevka custom build docs](https://github.com/be5invis/Iosevka/blob/main/doc/custom-build.md)
