"""
Patch ligatures from JetBrains Mono into Ioskeley Condensed.

This script transplants 17 ligature glyphs from JetBrains Mono into an
Iosevka-built font. For sequences with 3+ equals/greaters (===>), ligatures
are blocked so they render as plain text (matching Berkeley Mono behavior).

Usage:
    python patch-ligatures.py <iosevka.ttf> <jetbrains-mono.ttf> <output.ttf>
"""

import copy
import math
import sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables


CHAR_GLYPH = {
    '=': 'equal', '>': 'greater', '<': 'less',
    '-': 'hyphen', '|': 'bar',
}

# JetBrains Mono ligature definitions (longest first for correct overlap handling):
LIGATURES = [
    # 4-char
    ("<==>", "less_equal_equal_greater.liga"),
    # 3-char
    ("==>",  "equal_equal_greater.liga"),
    ("=>>",  "equal_greater_greater.liga"),
    ("<<=",  "less_less_equal.liga"),
    (">>=",  "greater_greater_equal.liga"),
    ("<=<",  "less_equal_less.liga"),
    (">=>",  "greater_equal_greater.liga"),
    ("<==",  "less_equal_equal.liga"),
    ("<=>",  "less_equal_greater.liga"),
    ("<=|",  "less_equal_bar.liga"),
    ("|=>",  "bar_equal_greater.liga"),
    ("=<<",  "equal_less_less.liga"),
    ("<-<",  "less_hyphen_less.liga"),
    (">->",  "greater_hyphen_greater.liga"),
    ("-<<",  "hyphen_less_less.liga"),
    (">>-",  "greater_greater_hyphen.liga"),
    # 2-char (shortest match last)
    ("=>",   "equal_greater.liga"),
]


class SubstRegistry:
    """Deduplicates SingleSubst lookups — each unique (from, to) pair is created once."""

    def __init__(self, add_fn):
        self._map = {}
        self._add = add_fn

    def get(self, from_glyph, to_glyph):
        key = (from_glyph, to_glyph)
        if key not in self._map:
            self._map[key] = self._add(_make_single_subst({from_glyph: to_glyph}))
        return self._map[key]


def compute_ignore_rules(seq, all_ligatures):
    """Return ignore rules that prevent seq from matching inside longer sequences."""
    rules = []
    for other_seq, _ in all_ligatures:
        if len(other_seq) <= len(seq):
            continue
        for i in range(len(other_seq) - len(seq) + 1):
            if other_seq[i:i + len(seq)] == seq:
                backtrack = [CHAR_GLYPH[c] for c in reversed(other_seq[:i])]
                # i+1 (not i+len(seq)): lookahead is relative to the first
                # char (pass 0's coverage glyph), so it must include the
                # rest of seq's chars as well as the extra chars.
                lookahead = [CHAR_GLYPH[c] for c in other_seq[i + 1:]]
                if backtrack or lookahead:
                    rules.append(build_ignore_rule(
                        backtrack=backtrack or None,
                        lookahead=lookahead or None,
                    ))
    return rules


def build_ligature_chain_lookups(seq, liga_glyph, ignore_rules, registry, add_fn):
    """Build chain lookups for an N-char ligature.

    For c0 c1 ... c(N-1):
      Pass 1: c0' [c1 c2 ... c(N-1)] → SPC  (with ignore rules prepended)
      Pass k (2..N-1): [SPC×(k-1)] ck-1' [ck ... c(N-1)] → SPC
      Pass N: [SPC×(N-1)] c(N-1)' → liga_glyph

    Returns list of lookup indices.
    """
    n = len(seq)
    indices = []

    for k in range(n):
        char = seq[k]
        glyph = CHAR_GLYPH[char]

        if k < n - 1:
            subst_idx = registry.get(glyph, "SPC")
        else:
            subst_idx = registry.get(glyph, liga_glyph)

        backtrack = ["SPC"] * k if k > 0 else None
        lookahead_chars = seq[k + 1:]
        lookahead = [CHAR_GLYPH[c] for c in lookahead_chars] if lookahead_chars else None

        rules = []
        if k == 0:
            rules.extend(ignore_rules)

        rules.append(build_subst_rule(
            backtrack=backtrack,
            lookahead=lookahead,
            subst_records=[make_subst_record(0, subst_idx)],
        ))

        rs = otTables.ChainSubRuleSet()
        rs.ChainSubRule = rules
        rs.ChainSubRuleCount = len(rules)

        idx = add_fn(_make_chain_lookup([glyph], [rs]))
        indices.append(idx)

    return indices


def scale_glyph(glyph, scale_x, scale_y=1.0):
    """Scale a simple glyph's coordinates."""
    if glyph.numberOfContours <= 0:
        return
    coords = glyph.coordinates
    new_coords = []
    for x, y in coords:
        new_coords.append((round(x * scale_x), round(y * scale_y)))
    glyph.coordinates = type(coords)(new_coords)
    glyph.xMin = round(glyph.xMin * scale_x)
    glyph.xMax = round(glyph.xMax * scale_x)
    if scale_y != 1.0:
        glyph.yMin = round(glyph.yMin * scale_y)
        glyph.yMax = round(glyph.yMax * scale_y)


def apply_italic_slant(glyph, angle_deg):
    """Apply italic slant transform to glyph coordinates."""
    if glyph.numberOfContours <= 0:
        return
    slant = math.tan(math.radians(angle_deg))
    coords = glyph.coordinates
    new_coords = []
    for x, y in coords:
        new_coords.append((round(x + y * slant), y))
    glyph.coordinates = type(coords)(new_coords)
    xs = [c[0] for c in new_coords]
    glyph.xMin = min(xs)
    glyph.xMax = max(xs)


def detect_italic_angle(font):
    """Detect if this is an italic font and return the slant angle."""
    post = font.get("post")
    if post and post.italicAngle:
        return -post.italicAngle  # post.italicAngle is negative for italic
    os2 = font.get("OS/2")
    if os2 and (os2.fsSelection & 1):  # bit 0 = italic
        return 11.8  # Iosevka default
    return 0


def add_glyph(target_font, glyph_name, source_font, source_glyph_name,
              target_width, source_width, italic_angle=0):
    """Copy a glyph from source font to target font with scaling."""
    src_glyf = source_font["glyf"]
    src_hmtx = source_font["hmtx"]

    src_glyph = src_glyf[source_glyph_name]
    new_glyph = copy.deepcopy(src_glyph)

    scale_x = target_width / source_width
    scale_glyph(new_glyph, scale_x)

    if italic_angle > 0:
        apply_italic_slant(new_glyph, italic_angle)

    target_glyf = target_font["glyf"]
    target_hmtx = target_font["hmtx"]

    target_glyf.glyphs[glyph_name] = new_glyph

    src_width_val, src_lsb = src_hmtx[source_glyph_name]
    new_lsb = round(src_lsb * scale_x)
    target_hmtx[glyph_name] = (target_width, new_lsb)

    glyph_order = target_font.getGlyphOrder()
    if glyph_name not in glyph_order:
        target_font.setGlyphOrder(glyph_order + [glyph_name])


def ensure_spc_glyph(font):
    """Ensure the font has a SPC glyph (space-width empty glyph for ligature padding)."""
    glyph_order = font.getGlyphOrder()
    if "SPC" in glyph_order:
        return

    hmtx = font["hmtx"]
    char_width = hmtx["equal"][0]  # should be 500

    from fontTools.ttLib.tables._g_l_y_f import Glyph
    glyf = font["glyf"]
    spc = Glyph()
    spc.numberOfContours = 0
    glyf.glyphs["SPC"] = spc
    hmtx["SPC"] = (char_width, 0)

    font.setGlyphOrder(glyph_order + ["SPC"])


def ensure_noliga_glyphs(font):
    """Create .noliga variants of all characters used in ligatures.

    Used to block Iosevka's built-in calt lookups from matching sequences
    that should not ligate (e.g. ===>).
    """
    glyph_order = font.getGlyphOrder()
    glyf = font["glyf"]
    hmtx = font["hmtx"]

    new_glyphs = []
    for base in CHAR_GLYPH.values():
        noliga = f"{base}.noliga"
        if noliga not in glyph_order:
            glyf.glyphs[noliga] = copy.deepcopy(glyf[base])
            hmtx[noliga] = hmtx[base]
            new_glyphs.append(noliga)

    if new_glyphs:
        font.setGlyphOrder(glyph_order + new_glyphs)


def build_ignore_rule(backtrack=None, lookahead=None):
    """Build a ChainSubRule that blocks substitution (SubstCount=0)."""
    rule = otTables.ChainSubRule()
    rule.BacktrackGlyphCount = len(backtrack) if backtrack else 0
    rule.Backtrack = backtrack or []
    rule.GlyphCount = 1
    rule.Input = []
    rule.LookAheadGlyphCount = len(lookahead) if lookahead else 0
    rule.LookAhead = lookahead or []
    rule.SubstCount = 0
    rule.SubstLookupRecord = []
    return rule


def build_subst_rule(backtrack=None, input_extra=None, lookahead=None,
                     subst_records=None):
    """Build a ChainSubRule that triggers substitution."""
    rule = otTables.ChainSubRule()
    rule.BacktrackGlyphCount = len(backtrack) if backtrack else 0
    rule.Backtrack = backtrack or []
    input_glyphs = input_extra or []
    rule.GlyphCount = 1 + len(input_glyphs)
    rule.Input = input_glyphs
    rule.LookAheadGlyphCount = len(lookahead) if lookahead else 0
    rule.LookAhead = lookahead or []
    rule.SubstCount = len(subst_records) if subst_records else 0
    rule.SubstLookupRecord = subst_records or []
    return rule


def make_subst_record(seq_index, lookup_index):
    """Create a SubstLookupRecord."""
    rec = otTables.SubstLookupRecord()
    rec.SequenceIndex = seq_index
    rec.LookupListIndex = lookup_index
    return rec


def _make_single_subst(mapping):
    """Create a SingleSubst lookup object (not yet added to GSUB)."""
    lookup = otTables.Lookup()
    lookup.LookupType = 1
    lookup.LookupFlag = 0
    subtable = otTables.SingleSubst()
    subtable.mapping = mapping
    lookup.SubTable = [subtable]
    lookup.SubTableCount = 1
    return lookup


def _make_chain_lookup(coverage_glyphs, rule_sets):
    """Create a ChainContextSubst lookup object (not yet added to GSUB)."""
    chain = otTables.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    st = otTables.ChainContextSubst()
    st.Format = 1
    cov = otTables.Coverage()
    cov.glyphs = coverage_glyphs
    st.Coverage = cov
    st.ChainSubRuleSet = rule_sets
    st.ChainSubRuleSetCount = len(rule_sets)
    chain.SubTable = [st]
    chain.SubTableCount = 1
    return chain


def _shift_gsub_lookup_refs(gsub, offset, skip_first_n=0):
    """Shift all lookup index references in GSUB by offset.

    skip_first_n: don't shift references inside the first N lookups
    (those are our newly inserted lookups with correct local indices).
    """
    # Shift Feature LookupListIndex
    for rec in gsub.table.FeatureList.FeatureRecord:
        rec.Feature.LookupListIndex = [
            i + offset for i in rec.Feature.LookupListIndex
        ]

    # Shift internal references in existing lookups (skip our new ones)
    for lookup in gsub.table.LookupList.Lookup[skip_first_n:]:
        for st in lookup.SubTable:
            actual_st = st
            # Unwrap Extension lookups
            if lookup.LookupType == 7 and hasattr(st, 'ExtSubTable'):
                actual_st = st.ExtSubTable
            _shift_subtable_refs(actual_st, offset)


def _shift_subtable_refs(subtable, offset):
    """Shift SubstLookupRecord references in a single subtable."""
    # ChainContextSubst Format 1
    if hasattr(subtable, 'ChainSubRuleSet') and subtable.ChainSubRuleSet:
        for rs in subtable.ChainSubRuleSet:
            if rs is None:
                continue
            for rule in rs.ChainSubRule:
                if hasattr(rule, 'SubstLookupRecord'):
                    for rec in rule.SubstLookupRecord:
                        rec.LookupListIndex += offset

    # ChainContextSubst Format 2
    if hasattr(subtable, 'ChainSubClassSet') and subtable.ChainSubClassSet:
        for cs in subtable.ChainSubClassSet:
            if cs is None:
                continue
            for rule in cs.ChainSubClassRule:
                if hasattr(rule, 'SubstLookupRecord'):
                    for rec in rule.SubstLookupRecord:
                        rec.LookupListIndex += offset

    # ChainContextSubst/ContextSubst Format 3 (inline SubstLookupRecord)
    if hasattr(subtable, 'SubstLookupRecord') and subtable.SubstLookupRecord:
        for rec in subtable.SubstLookupRecord:
            rec.LookupListIndex += offset

    # ContextSubst Format 1
    if hasattr(subtable, 'SubRuleSet') and subtable.SubRuleSet:
        for rs in subtable.SubRuleSet:
            if rs is None:
                continue
            for rule in rs.SubRule:
                if hasattr(rule, 'SubstLookupRecord'):
                    for rec in rule.SubstLookupRecord:
                        rec.LookupListIndex += offset

    # ContextSubst Format 2
    if hasattr(subtable, 'SubClassSet') and subtable.SubClassSet:
        for cs in subtable.SubClassSet:
            if cs is None:
                continue
            for rule in cs.SubClassRule:
                if hasattr(rule, 'SubstLookupRecord'):
                    for rec in rule.SubstLookupRecord:
                        rec.LookupListIndex += offset


def add_ligature_lookups(font):
    """Add GSUB lookups for all 17 ligatures.

    Inserts lookups at the BEGINNING of the LookupList so they get
    low indices and execute before Iosevka's built-in calt lookups
    (HarfBuzz processes lookups in index order).
    """
    gsub = font["GSUB"]

    # --- Build all lookups locally first ---
    new_lookups = []

    def add_local(lookup_obj):
        idx = len(new_lookups)
        new_lookups.append(lookup_obj)
        return idx

    registry = SubstRegistry(add_local)

    # --- Blocking: seed + propagation (handles ANY length of ={m}>{n}) ---
    # For any ={m}>{n} sequence where m+n >= 4, convert ALL characters
    # to noliga versions so Iosevka's ==, >>, => lookups won't match.
    PROPAGATION_PASSES = 20

    subst_eq_noliga = registry.get("equal", "equal.noliga")
    subst_gt_noliga = registry.get("greater", "greater.noliga")

    # Seed lookup: 3 rules covering all bad patterns
    seed_rules = []
    # Rule 1: [= =] =' [>]  — for m>=3 (===>+)
    seed_rules.append(build_subst_rule(
        backtrack=["equal", "equal"],
        lookahead=["greater"],
        subst_records=[make_subst_record(0, subst_eq_noliga)],
    ))
    # Rule 2: [=] =' [> >]  — for m>=2, n>=2 (==>>+)
    seed_rules.append(build_subst_rule(
        backtrack=["equal"],
        lookahead=["greater", "greater"],
        subst_records=[make_subst_record(0, subst_eq_noliga)],
    ))
    # Rule 3: =' [> > >]  — for m=1, n>=3 (=>>>+)
    seed_rules.append(build_subst_rule(
        lookahead=["greater", "greater", "greater"],
        subst_records=[make_subst_record(0, subst_eq_noliga)],
    ))
    seed_rs = otTables.ChainSubRuleSet()
    seed_rs.ChainSubRule = seed_rules
    seed_rs.ChainSubRuleCount = len(seed_rules)
    chain_seed = add_local(_make_chain_lookup(["equal"], [seed_rs]))

    # Propagation lookups
    chain_props = []
    for _ in range(PROPAGATION_PASSES):
        eq_prop_rules = []
        eq_prop_rules.append(build_subst_rule(
            lookahead=["equal.noliga"],
            subst_records=[make_subst_record(0, subst_eq_noliga)],
        ))
        eq_prop_rules.append(build_subst_rule(
            lookahead=["greater.noliga"],
            subst_records=[make_subst_record(0, subst_eq_noliga)],
        ))
        eq_prop_rs = otTables.ChainSubRuleSet()
        eq_prop_rs.ChainSubRule = eq_prop_rules
        eq_prop_rs.ChainSubRuleCount = len(eq_prop_rules)

        gt_prop_rules = []
        gt_prop_rules.append(build_subst_rule(
            backtrack=["equal.noliga"],
            subst_records=[make_subst_record(0, subst_gt_noliga)],
        ))
        gt_prop_rules.append(build_subst_rule(
            backtrack=["greater.noliga"],
            subst_records=[make_subst_record(0, subst_gt_noliga)],
        ))
        gt_prop_rs = otTables.ChainSubRuleSet()
        gt_prop_rs.ChainSubRule = gt_prop_rules
        gt_prop_rs.ChainSubRuleCount = len(gt_prop_rules)

        chain_props.append(add_local(
            _make_chain_lookup(["equal", "greater"], [eq_prop_rs, gt_prop_rs])
        ))

    print(f"  Blocking: 1 seed + {PROPAGATION_PASSES} propagation lookups")

    # --- Build chain lookups for each ligature ---
    all_chain_indices = []
    for seq, liga_glyph in LIGATURES:
        ignore_rules = compute_ignore_rules(seq, LIGATURES)
        indices = build_ligature_chain_lookups(
            seq, liga_glyph, ignore_rules, registry, add_local,
        )
        all_chain_indices.extend(indices)
        print(f"  {seq}: {len(indices)} passes, {len(ignore_rules)} ignore rules")

    # --- Insert lookups at beginning of LookupList ---
    n = len(new_lookups)
    print(f"  Inserting {n} lookups at beginning of LookupList...")

    # Shift all existing references by n
    _shift_gsub_lookup_refs(gsub, n)

    # Insert our lookups at the beginning
    gsub.table.LookupList.Lookup = new_lookups + gsub.table.LookupList.Lookup

    # --- Add chain lookup indices to calt feature ---
    chain_indices = [
        chain_seed,
        *chain_props,
        *all_chain_indices,
    ]

    for rec in gsub.table.FeatureList.FeatureRecord:
        if rec.FeatureTag == "calt":
            existing = list(rec.Feature.LookupListIndex)
            rec.Feature.LookupListIndex = chain_indices + existing
            rec.Feature.LookupCount = len(rec.Feature.LookupListIndex)
            break

    return chain_indices


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <iosevka.ttf> <jetbrains-mono.ttf> <output.ttf>")
        sys.exit(1)

    iosevka_path = sys.argv[1]
    jb_path = sys.argv[2]
    output_path = sys.argv[3]

    print(f"Loading {iosevka_path}...")
    iosevka = TTFont(iosevka_path)
    print(f"Loading {jb_path}...")
    jb = TTFont(jb_path)

    # Detect italic
    italic_angle = detect_italic_angle(iosevka)
    if italic_angle:
        print(f"Detected italic angle: {italic_angle}°")

    # Get character widths
    iosevka_char_width = iosevka["hmtx"]["equal"][0]  # 500
    jb_char_width = jb["hmtx"]["equal"][0]  # 600
    print(f"Iosevka char width: {iosevka_char_width}")
    print(f"JetBrains Mono char width: {jb_char_width}")

    # Ensure helper glyphs exist
    ensure_spc_glyph(iosevka)
    ensure_noliga_glyphs(iosevka)

    # Copy ligature glyphs
    for seq, glyph_name in LIGATURES:
        print(f"Copying {seq} ({glyph_name})...")
        add_glyph(
            iosevka, glyph_name, jb, glyph_name,
            target_width=iosevka_char_width,
            source_width=jb_char_width,
            italic_angle=italic_angle,
        )

    # Add GSUB lookups
    print("Adding GSUB lookups...")
    new_indices = add_ligature_lookups(iosevka)
    print(f"Added {len(new_indices)} chain lookups to calt feature")

    # Save
    print(f"Saving {output_path}...")
    iosevka.save(output_path)
    print("Done!")


if __name__ == "__main__":
    main()
