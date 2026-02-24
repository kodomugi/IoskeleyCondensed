"""Test ligature shaping in a patched font."""
import uharfbuzz as hb
from fontTools.ttLib import TTFont
import sys

FONT_PATH = sys.argv[1]
ORIG_PATH = sys.argv[2]  # unpatched font for glyph count reference

with open(FONT_PATH, 'rb') as f:
    fontdata = f.read()

face = hb.Face(fontdata)
hb_font = hb.Font(face)

# Compute glyph ID ranges for our added glyphs
orig_count = len(TTFont(ORIG_PATH).getGlyphOrder())
# Added order: SPC(1), noliga(5), liga(17)
SPC_GID = orig_count
LIGA_GID_START = orig_count + 6  # after SPC + 5 noliga
LIGA_GID_END = orig_count + 22   # 17 liga glyphs


def shape(text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, {'calt': True})
    return [info.codepoint for info in buf.glyph_infos]


def has_liga(gids):
    return any(LIGA_GID_START <= g <= LIGA_GID_END for g in gids)


def has_spc(gids):
    return any(g == SPC_GID for g in gids)


all_pass = True

print(f'Original glyphs: {orig_count}, SPC={SPC_GID}, liga={LIGA_GID_START}-{LIGA_GID_END}')
print()

print('=== Ligature tests ===')
for seq in ['<==>','==>','=>>','<<=','>>=','<=<','>=>',
            '<==','<=>','<=|','|=>','=<<',
            '<-<','>->','-<<','>>-','=>']:
    gids = shape(seq)
    ok = has_liga(gids) and has_spc(gids)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'  {status} {seq:6s} gids={gids}')

print()
print('=== Blocking tests (no liga glyphs) ===')
for seq in ['===>', '====', '==>>',  '=>>>', '===>>']:
    gids = shape(seq)
    ok = not has_liga(gids)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'  {status} {seq:6s} gids={gids}')

print()
print('=== Edge case tests ===')
for text, should in [('x => y', True), ('<== =>', True)]:
    gids = shape(text)
    ok = has_liga(gids) == should
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'  {status} "{text}" gids={gids}')

print()
print('ALL PASS' if all_pass else 'SOME FAILURES')
sys.exit(0 if all_pass else 1)
