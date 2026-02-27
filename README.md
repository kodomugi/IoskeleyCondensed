# Ioskeley Condensed

A condensed (width 500) variant of [Ioskeley Mono](https://github.com/ahatem/IoskeleyMono), which is a custom build of [Iosevka](https://github.com/be5invis/Iosevka) that mimics the look and feel of Berkeley Mono.

## Differences from Ioskeley Mono

| | Ioskeley Mono | Ioskeley Condensed |
|---|---|---|
| Width | 600 (standard) | 500 (condensed) |
| Spacing | normal | normal + term |
| Slopes | Upright + Italic | Upright + Italic |
| Ligatures | Built-in | Built-in (Iosevka) or [full JetBrains Mono ligatures](#ligatures) (JBM variant), controllable via `calt` |
| cv/ss features | Not exported | Exported |
| Sidebearing (`sb`) | 85 (custom) | Default (CJK friendly) |
| Metric override | Full custom | Custom (without `sb`) |

### Why these changes?

- **Width 500**: Narrower characters, more content per line while maintaining readability.
- **Italic**: Uses italic slope for better compatibility with applications that only look for italic fonts. Glyph variants are explicitly pinned, so no unwanted glyph substitution occurs.
- **Two spacing variants**: "Ioskeley Condensed" for editors (normal, with wide symbols), "Ioskeley Condensed Term" for terminals (narrowed arrow/geometric symbols).
- **cv/ss exported**: Allows toggling character variants via OpenType features in your editor.
- **Default sidebearing**: Preserves Iosevka's native 2:1 halfwidth/fullwidth ratio, ensuring CJK (Chinese/Japanese/Korean) characters align correctly in terminals and editors when paired with a CJK fallback font. Custom `sb` values break this ratio, causing misaligned columns in mixed-script text.

## Ligatures

The **JBM** variants (`Ioskeley Condensed JBM`, `Ioskeley Condensed Term JBM`) use JetBrains Mono's full ligature set (~153 ligatures), transplanted via the `calt` OpenType feature. This includes arrows, comparisons, logical operators, comments, and more:

```
=>  ->  <-  ==>  <==  <=>  <==>  ...
==  !=  <=  >=  ===  !==  ...
||  &&  //  /*  */  <!--  -->  ...
::  ..  ...  ??  ?.  ++  --  >>>  <<<  ...
```

The standard variants (`Ioskeley Condensed`, `Ioskeley Condensed Term`) retain Iosevka's built-in ligatures unchanged.

JBM variants use a separate font family name, so both can be installed side by side.

## Installation

Download from the [Releases](../../releases) page.

| Package | Description |
|---------|-------------|
| `IoskeleyCondensed-TTF-Hinted.zip` | Normal spacing, hinted TTF |
| `IoskeleyCondensed-TTF-Unhinted.zip` | Normal spacing, unhinted TTF |
| `IoskeleyCondensed-Web.zip` | Normal spacing, WOFF2 |
| `IoskeleyCondensed-JBM-TTF-Hinted.zip` | Normal spacing, hinted TTF + JBM ligatures (family: "Ioskeley Condensed JBM") |
| `IoskeleyCondensed-JBM-TTF-Unhinted.zip` | Normal spacing, unhinted TTF + JBM ligatures (family: "Ioskeley Condensed JBM") |
| `IoskeleyCondensed-JBM-Web.zip` | Normal spacing, WOFF2 + JBM ligatures (family: "Ioskeley Condensed JBM") |
| `IoskeleyCondensedTerm-TTF-Hinted.zip` | Term spacing, hinted TTF |
| `IoskeleyCondensedTerm-TTF-Unhinted.zip` | Term spacing, unhinted TTF |
| `IoskeleyCondensedTerm-Web.zip` | Term spacing, WOFF2 |
| `IoskeleyCondensedTerm-JBM-TTF-Hinted.zip` | Term spacing, hinted TTF + JBM ligatures (family: "Ioskeley Condensed Term JBM") |
| `IoskeleyCondensedTerm-JBM-TTF-Unhinted.zip` | Term spacing, unhinted TTF + JBM ligatures (family: "Ioskeley Condensed Term JBM") |
| `IoskeleyCondensedTerm-JBM-Web.zip` | Term spacing, WOFF2 + JBM ligatures (family: "Ioskeley Condensed Term JBM") |

**Hinted** is recommended for standard-resolution screens. **Unhinted** is preferred on HiDPI displays.

## Automated Builds

A GitHub Action checks daily for new [Iosevka releases](https://github.com/be5invis/Iosevka/releases). When a new version is detected, the font is automatically rebuilt and published as a GitHub Release.

Builds can also be triggered manually via `workflow_dispatch`.

## License

This project is a derivative of [Iosevka](https://github.com/be5invis/Iosevka) by Belleve Invis, based on the build configuration from [Ioskeley Mono](https://github.com/ahatem/IoskeleyMono) by Ahmed Hatem.

Licensed under the **SIL Open Font License, Version 1.1**. See [LICENSE](LICENSE) for the full text.

Per the OFL, the font name does not use "Iosevka" (reserved font name of the original) or "Berkeley Mono" (commercial trademark).
