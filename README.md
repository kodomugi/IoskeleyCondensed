# Ioskeley Condensed

A condensed (width 500) variant of [Ioskeley Mono](https://github.com/ahatem/IoskeleyMono), which is a custom build of [Iosevka](https://github.com/be5invis/Iosevka) that mimics the look and feel of Berkeley Mono.

## Differences from Ioskeley Mono

| | Ioskeley Mono | Ioskeley Condensed |
|---|---|---|
| Width | 600 (standard) | 500 (condensed) |
| Spacing | normal | normal + term |
| Slopes | Upright + Italic | Upright + Oblique |
| Ligatures | Built-in | Built-in, controllable via `calt` |
| cv/ss features | Not exported | Exported |
| Sidebearing (`sb`) | 85 (custom) | Default (CJK friendly) |
| Metric override | Full custom | Custom (without `sb`) |

### Why these changes?

- **Width 500**: Narrower characters, more content per line while maintaining readability.
- **Oblique instead of Italic**: Berkeley Mono's italic style is closer to oblique (slanted upright forms, no glyph substitution).
- **Two spacing variants**: "Ioskeley Condensed" for editors (normal, with wide symbols), "Ioskeley Condensed Term" for terminals (narrowed arrow/geometric symbols).
- **cv/ss exported**: Allows toggling character variants via OpenType features in your editor.
- **Default sidebearing**: Preserves Iosevka's native 2:1 halfwidth/fullwidth ratio, ensuring CJK (Chinese/Japanese/Korean) characters align correctly in terminals and editors when paired with a CJK fallback font. Custom `sb` values break this ratio, causing misaligned columns in mixed-script text.

## Installation

Download from the [Releases](../../releases) page.

| Package | Description |
|---------|-------------|
| `IoskeleyCondensed-TTF-Hinted.zip` | Normal spacing, hinted TTF |
| `IoskeleyCondensed-TTF-Unhinted.zip` | Normal spacing, unhinted TTF |
| `IoskeleyCondensed-Web.zip` | Normal spacing, WOFF2 |
| `IoskeleyCondensedTerm-TTF-Hinted.zip` | Term spacing, hinted TTF |
| `IoskeleyCondensedTerm-TTF-Unhinted.zip` | Term spacing, unhinted TTF |
| `IoskeleyCondensedTerm-Web.zip` | Term spacing, WOFF2 |

**Hinted** is recommended for standard-resolution screens. **Unhinted** is preferred on HiDPI displays.

## Automated Builds

A GitHub Action checks daily for new [Iosevka releases](https://github.com/be5invis/Iosevka/releases). When a new version is detected, the font is automatically rebuilt and published as a GitHub Release.

Builds can also be triggered manually via `workflow_dispatch`.

## License

This project is a derivative of [Iosevka](https://github.com/be5invis/Iosevka) by Belleve Invis, based on the build configuration from [Ioskeley Mono](https://github.com/ahatem/IoskeleyMono) by Ahmed Hatem.

Licensed under the **SIL Open Font License, Version 1.1**. See [LICENSE](LICENSE) for the full text.

Per the OFL, the font name does not use "Iosevka" (reserved font name of the original) or "Berkeley Mono" (commercial trademark).
