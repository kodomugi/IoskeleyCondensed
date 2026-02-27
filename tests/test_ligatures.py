"""Test JBM ligature shaping in a patched font.

Verifies that the full JetBrains Mono calt feature was transplanted correctly
by comparing glyph output with calt enabled vs disabled.

Usage:
    python tests/test_ligatures.py <patched-font.ttf>
"""
import uharfbuzz as hb
import sys

FONT_PATH = sys.argv[1]

with open(FONT_PATH, 'rb') as f:
    fontdata = f.read()

face = hb.Face(fontdata)
hb_font = hb.Font(face)


def shape(text, features=None):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, features or {})
    return [info.codepoint for info in buf.glyph_infos]


def is_ligature(seq):
    """Check if a sequence produces different glyphs with calt on vs off."""
    return shape(seq, {'calt': True}) != shape(seq, {'calt': False})


all_pass = True

# These sequences MUST produce ligatures (core JBM ligatures)
MUST_LIGATE = [
    '=>', '->', '<-', '!=', '==', '<=', '>=',
    '||', '&&', '==>',  '<==', '<=>', '<==>',
]

print('=== Required ligatures (calt on != calt off) ===')
for seq in MUST_LIGATE:
    ok = is_ligature(seq)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    gids_on = shape(seq, {'calt': True})
    gids_off = shape(seq, {'calt': False})
    print(f'  {status} {seq:6s}  on={gids_on}  off={gids_off}')

# Additional sequences to report on (not required to pass)
EXTRA = [
    '=>>', '<<=', '>>=', '<=<', '>=>',
    '<=|', '|=>', '=<<',
    '<-<', '>->', '-<<', '>>-',
    '>>>', '<<<', '++', '--',
    '::', '..', '...', '??', '?.',
    '/**', '*/','<!--', '-->',
]

print()
print('=== Additional ligatures (informational) ===')
liga_count = 0
for seq in EXTRA:
    ok = is_ligature(seq)
    status = 'LIGA' if ok else 'NONE'
    if ok:
        liga_count += 1
    print(f'  {status} {seq:6s}')

print()
print(f'Additional: {liga_count}/{len(EXTRA)} sequences ligate')

# Edge cases: ligatures work in context
print()
print('=== Context tests ===')
for text in ['x => y', 'a -> b', 'if (a != b)']:
    ok = is_ligature(text)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'  {status} "{text}"')

print()
print('ALL PASS' if all_pass else 'SOME FAILURES')
sys.exit(0 if all_pass else 1)
