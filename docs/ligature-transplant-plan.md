# Ligature Transplant: JetBrains Mono → Ioskeley Condensed

## Motivation

Iosevka's built-in arrow ligatures visually differ from Berkeley Mono's style. Iosevka only provides predefined ligature variants, none close enough. JetBrains Mono's ligatures are a better match and are transplanted as a post-build step.

Iosevka's ligature customization is limited to:
- Enabling/disabling entire ligation **groups** (e.g., `arrow-r-equal` covers `=>`, `==>`, `===>` together)
- Choosing from predefined visual **variants** via `lig-*` settings in `variants.design`
- No support for per-ligature control or custom glyph shapes through the build plan

## Approach: Full calt Transplant

Rather than surgically transplanting individual ligatures, we replace Iosevka's entire `calt` feature with JetBrains Mono's. This is done by:

1. Building Iosevka with `noLigation = true` (separate build plans: `IoskeleyCondensedJBM`, `IoskeleyCondensedTermJBM`)
2. Copying JBM's complete `calt` feature — all lookups and all referenced glyphs — into the target font

This gives the JBM variant ~141 JetBrains Mono ligatures covering arrows, comparisons, logical operators, comments, and more.

The non-JBM variants (`IoskeleyCondensed`, `IoskeleyCondensedTerm`) retain Iosevka's built-in ligatures unchanged.

## Scope

Full JetBrains Mono ligature set (~153 ligatures), including:

| Category | Examples |
|----------|----------|
| Arrows | `->` `=>` `<-` `<<=` `==>` `<=>` `<==>` |
| Comparison | `==` `!=` `<=` `>=` `===` `!==` |
| Logical | `\|\|` `&&` |
| Comments | `//` `/*` `*/` `<!--` `-->` |
| Other | `::` `..` `...` `??` `?.` `++` `--` `>>>` `<<<` |

## Implementation

### `patch-ligatures.py`

The script performs a full calt transplant in these steps:

1. **Find calt lookups** — locate the `calt` feature in JBM's GSUB and recursively collect all lookup indices it references (chain lookups may reference SingleSubst lookups internally)
2. **Deep copy lookups** — copy all needed lookups from JBM
3. **Collect referenced glyphs** — scan the copied lookups for all glyph names
4. **Copy missing glyphs** — copy any glyph referenced by the lookups that doesn't exist in the target (primarily `.liga` glyphs), scaling from JBM's 600 width to Iosevka's 500 width
5. **Append lookups** — add the copied lookups to the target font's GSUB LookupList
6. **Remap indices** — update internal lookup references (SubstLookupRecord) to reflect the new positions
7. **Create calt feature** — add a new `calt` feature pointing to the transplanted lookups

### Key functions

- `find_calt_lookups()` — BFS to find all transitively referenced lookup indices
- `collect_referenced_glyphs()` — extract glyph names from Coverage, SingleSubst, ChainContextSubst, etc.
- `remap_lookup_indices()` — update SubstLookupRecord references using old→new index mapping
- `transplant_calt()` — orchestrates the full transplant

### Italic handling

The script detects italic fonts via `post.italicAngle` or `OS/2.fsSelection` and applies the corresponding slant transform to transplanted glyphs.

## Build Plans

| Plan | Family Name | Ligation |
|------|-------------|----------|
| `IoskeleyCondensed` | Ioskeley Condensed | Iosevka built-in |
| `IoskeleyCondensedTerm` | Ioskeley Condensed Term | Iosevka built-in |
| `IoskeleyCondensedJBM` | Ioskeley Condensed JBM | JetBrains Mono (transplanted) |
| `IoskeleyCondensedTermJBM` | Ioskeley Condensed Term JBM | JetBrains Mono (transplanted) |

JBM plans use `noLigation = true` so there's no coexistence to manage — the transplanted calt is the only ligature feature.

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

- **CI smoke test**: uharfbuzz verifies core ligatures produce different glyph IDs with `calt` on vs off
- **Local test**: `python tests/test_ligatures.py <patched-font.ttf>`
- Tests a representative set of ligatures: `=>`, `->`, `<-`, `!=`, `==`, `<=`, `>=`, `||`, `&&`, `==>`, `<==`, `<=>`, `<==>`

## References

- [fonttools documentation](https://fonttools.readthedocs.io/)
- [JetBrains Mono source](https://github.com/JetBrains/JetBrainsMono)
- [Iosevka custom build docs](https://github.com/be5invis/Iosevka/blob/main/doc/custom-build.md)
