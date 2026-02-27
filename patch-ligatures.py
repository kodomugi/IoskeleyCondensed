"""
Patch ligatures from JetBrains Mono into Ioskeley Condensed.

Transplants JetBrains Mono's full calt (ligature) feature into an
Iosevka-built font compiled with noLigation=true. All referenced glyphs
and the complete set of calt lookups are copied from JBM, giving the
target font JBM's entire ligature set (~153 ligatures).

Usage:
    python patch-ligatures.py <iosevka.ttf> <jetbrains-mono.ttf> <output.ttf>
"""

import copy
import math
import sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen


# ---------------------------------------------------------------------------
# Glyph manipulation
# ---------------------------------------------------------------------------

def scale_glyph(glyph, scale_x, scale_y=1.0):
    """Scale a glyph's coordinates (simple or composite)."""
    if glyph.isComposite():
        for comp in glyph.components:
            comp.x = round(comp.x * scale_x)
            if scale_y != 1.0:
                comp.y = round(comp.y * scale_y)
        return
    if glyph.numberOfContours <= 0:
        return
    coords = glyph.coordinates
    new_coords = []
    for x, y in coords:
        new_coords.append((round(x * scale_x), round(y * scale_y)))
    glyph.coordinates = type(coords)(new_coords)
    # Recalculate bounds from actual coordinates (decomposed glyphs
    # may not have xMin/xMax/yMin/yMax set yet)
    xs = [c[0] for c in new_coords]
    ys = [c[1] for c in new_coords]
    glyph.xMin = min(xs)
    glyph.xMax = max(xs)
    glyph.yMin = min(ys)
    glyph.yMax = max(ys)


def apply_italic_slant(glyph, angle_deg):
    """Apply italic slant transform to glyph coordinates (simple or composite)."""
    slant = math.tan(math.radians(angle_deg))
    if glyph.isComposite():
        for comp in glyph.components:
            comp.x = round(comp.x + comp.y * slant)
        return
    if glyph.numberOfContours <= 0:
        return
    coords = glyph.coordinates
    new_coords = []
    for x, y in coords:
        new_coords.append((round(x + y * slant), y))
    glyph.coordinates = type(coords)(new_coords)
    xs = [c[0] for c in new_coords]
    ys = [c[1] for c in new_coords]
    glyph.xMin = min(xs)
    glyph.xMax = max(xs)
    glyph.yMin = min(ys)
    glyph.yMax = max(ys)


def detect_italic_angle(font):
    """Detect if this is an italic font and return the slant angle."""
    post = font.get("post")
    if post and post.italicAngle:
        return -post.italicAngle  # post.italicAngle is negative for italic
    os2 = font.get("OS/2")
    if os2 and (os2.fsSelection & 1):  # bit 0 = italic
        return 11.8  # Iosevka default
    return 0


def _decompose_glyph(font, glyph_name):
    """Flatten a composite glyph into simple outlines using the source font's components."""
    glyph_set = font.getGlyphSet()
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(rec)
    pen = TTGlyphPen(None)
    rec.replay(pen)
    return pen.glyph()


def add_glyph(target_font, glyph_name, source_font, source_glyph_name,
              target_width, source_width, italic_angle=0):
    """Copy a glyph from source font to target font with scaling.

    Composite glyphs are decomposed into simple outlines first, so they
    use JBM's actual drawn shapes instead of referencing the target font's
    (differently shaped) base glyphs.
    """
    src_glyf = source_font["glyf"]
    src_hmtx = source_font["hmtx"]

    src_glyph = src_glyf[source_glyph_name]
    if src_glyph.isComposite():
        new_glyph = _decompose_glyph(source_font, source_glyph_name)
    else:
        new_glyph = copy.deepcopy(src_glyph)

    # Strip TrueType hinting instructions — they reference the source font's
    # CVT/fpgm which differ from the target font, causing garbled rendering.
    new_glyph.program = Program()

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


# ---------------------------------------------------------------------------
# GSUB lookup analysis
# ---------------------------------------------------------------------------

def _unwrap(lookup, subtable):
    """Unwrap Extension subtable to get the actual subtable."""
    if lookup.LookupType == 7 and hasattr(subtable, 'ExtSubTable'):
        return subtable.ExtSubTable
    return subtable


def _collect_refs(subtable, refs):
    """Collect SubstLookupRecord.LookupListIndex from a subtable."""
    # Format 1 rule sets (ChainContextSubst / ContextSubst)
    for rs_attr, rule_attr in [('ChainSubRuleSet', 'ChainSubRule'),
                               ('SubRuleSet', 'SubRule')]:
        for rs in getattr(subtable, rs_attr, None) or []:
            if rs is None:
                continue
            for rule in getattr(rs, rule_attr, []):
                for rec in getattr(rule, 'SubstLookupRecord', []):
                    refs.add(rec.LookupListIndex)

    # Format 2 class sets
    for cs_attr, rule_attr in [('ChainSubClassSet', 'ChainSubClassRule'),
                               ('SubClassSet', 'SubClassRule')]:
        for cs in getattr(subtable, cs_attr, None) or []:
            if cs is None:
                continue
            for rule in getattr(cs, rule_attr, []):
                for rec in getattr(rule, 'SubstLookupRecord', []):
                    refs.add(rec.LookupListIndex)

    # Format 3 inline SubstLookupRecord
    for rec in getattr(subtable, 'SubstLookupRecord', None) or []:
        refs.add(rec.LookupListIndex)


def collect_lookup_refs(lookup):
    """Get all lookup indices referenced by a lookup's SubstLookupRecords."""
    refs = set()
    for st in lookup.SubTable:
        _collect_refs(_unwrap(lookup, st), refs)
    return refs


def find_calt_lookups(gsub):
    """Find calt feature's direct lookup indices and all transitively referenced lookups."""
    calt_direct = []
    for rec in gsub.table.FeatureList.FeatureRecord:
        if rec.FeatureTag == 'calt':
            calt_direct = list(rec.Feature.LookupListIndex)
            break

    if not calt_direct:
        return [], set()

    all_needed = set(calt_direct)
    queue = list(calt_direct)
    while queue:
        idx = queue.pop()
        for ref in collect_lookup_refs(gsub.table.LookupList.Lookup[idx]):
            if ref not in all_needed:
                all_needed.add(ref)
                queue.append(ref)

    return calt_direct, all_needed


# ---------------------------------------------------------------------------
# Glyph name collection from lookups
# ---------------------------------------------------------------------------

def collect_referenced_glyphs(lookups):
    """Collect all glyph names referenced in the given lookups."""
    names = set()
    for lookup in lookups:
        for st in lookup.SubTable:
            _collect_glyph_names(_unwrap(lookup, st), names)
    return names


def _collect_glyph_names(st, names):
    """Collect glyph names from a single subtable."""
    # Coverage
    cov = getattr(st, 'Coverage', None)
    if cov and hasattr(cov, 'glyphs'):
        names.update(cov.glyphs)

    # SingleSubst mapping
    mapping = getattr(st, 'mapping', None)
    if mapping:
        names.update(mapping.keys())
        names.update(mapping.values())

    # LigatureSubst
    ligs = getattr(st, 'ligatures', None)
    if ligs:
        for glyph, lig_list in ligs.items():
            names.add(glyph)
            for lig in lig_list:
                names.update(lig.Component)
                names.add(lig.LigGlyph)

    # ChainContextSubst / ContextSubst Format 1 rules
    for rs_attr, rule_attr in [('ChainSubRuleSet', 'ChainSubRule'),
                               ('SubRuleSet', 'SubRule')]:
        for rs in getattr(st, rs_attr, None) or []:
            if rs is None:
                continue
            for rule in getattr(rs, rule_attr, []):
                for field in ('Backtrack', 'Input', 'LookAhead'):
                    names.update(getattr(rule, field, None) or [])

    # Format 2 ClassDefs
    for attr in ('BacktrackClassDef', 'InputClassDef', 'LookAheadClassDef',
                 'ClassDef'):
        cd = getattr(st, attr, None)
        if cd and hasattr(cd, 'classDefs'):
            names.update(cd.classDefs.keys())

    # Format 3 Coverages
    for attr in ('BacktrackCoverage', 'InputCoverage', 'LookAheadCoverage'):
        for cov in getattr(st, attr, None) or []:
            if hasattr(cov, 'glyphs'):
                names.update(cov.glyphs)


# ---------------------------------------------------------------------------
# Lookup index remapping
# ---------------------------------------------------------------------------

def _remap_refs(subtable, m):
    """Remap SubstLookupRecord.LookupListIndex using mapping m."""
    for rs_attr, rule_attr in [('ChainSubRuleSet', 'ChainSubRule'),
                               ('SubRuleSet', 'SubRule')]:
        for rs in getattr(subtable, rs_attr, None) or []:
            if rs is None:
                continue
            for rule in getattr(rs, rule_attr, []):
                for rec in getattr(rule, 'SubstLookupRecord', []):
                    rec.LookupListIndex = m[rec.LookupListIndex]

    for cs_attr, rule_attr in [('ChainSubClassSet', 'ChainSubClassRule'),
                               ('SubClassSet', 'SubClassRule')]:
        for cs in getattr(subtable, cs_attr, None) or []:
            if cs is None:
                continue
            for rule in getattr(cs, rule_attr, []):
                for rec in getattr(rule, 'SubstLookupRecord', []):
                    rec.LookupListIndex = m[rec.LookupListIndex]

    for rec in getattr(subtable, 'SubstLookupRecord', None) or []:
        rec.LookupListIndex = m[rec.LookupListIndex]


def remap_lookup_indices(lookup, index_map):
    """Remap all SubstLookupRecord indices in a lookup."""
    for st in lookup.SubTable:
        _remap_refs(_unwrap(lookup, st), index_map)


# ---------------------------------------------------------------------------
# Main transplant logic
# ---------------------------------------------------------------------------

def transplant_calt(target, source, target_width, source_width, italic_angle):
    """Transplant the entire calt feature from source to target font."""
    src_gsub = source["GSUB"]

    # 1. Find all lookups needed by calt
    calt_direct, all_needed = find_calt_lookups(src_gsub)
    if not calt_direct:
        print("ERROR: No calt feature found in source font")
        sys.exit(1)

    print(f"  calt: {len(calt_direct)} direct lookups, {len(all_needed)} total (incl. referenced)")

    # 2. Deep copy the needed lookups
    src_lookups = src_gsub.table.LookupList.Lookup
    copied = {}
    for idx in sorted(all_needed):
        copied[idx] = copy.deepcopy(src_lookups[idx])

    # 3. Collect all glyph names referenced by the copied lookups
    all_glyphs = collect_referenced_glyphs(copied.values())

    # 4. Copy missing glyphs from source to target
    #    Composite glyphs are decomposed in add_glyph(), so no need to
    #    resolve component dependencies.
    target_glyph_set = set(target.getGlyphOrder())
    source_glyph_set = set(source.getGlyphOrder())
    missing = all_glyphs - target_glyph_set
    to_copy = sorted(missing & source_glyph_set)
    skipped = sorted(missing - source_glyph_set)

    print(f"  {len(all_glyphs)} unique glyphs referenced, {len(to_copy)} to copy")
    if skipped:
        print(f"  WARNING: {len(skipped)} glyphs not found in source: {skipped[:10]}...")

    for glyph_name in to_copy:
        add_glyph(target, glyph_name, source, glyph_name,
                  target_width, source_width, italic_angle)

    # 5. Append lookups to target's GSUB LookupList, building index mapping
    tgt_gsub = target["GSUB"]
    tgt_lookups = tgt_gsub.table.LookupList.Lookup
    base_idx = len(tgt_lookups)

    index_map = {}
    for i, old_idx in enumerate(sorted(all_needed)):
        new_idx = base_idx + i
        index_map[old_idx] = new_idx
        tgt_lookups.append(copied[old_idx])

    # 6. Remap internal lookup references in the copied lookups
    for old_idx in sorted(all_needed):
        remap_lookup_indices(copied[old_idx], index_map)

    # 7. Create/set calt feature
    new_calt_indices = [index_map[i] for i in calt_direct]

    calt_found = False
    for rec in tgt_gsub.table.FeatureList.FeatureRecord:
        if rec.FeatureTag == 'calt':
            rec.Feature.LookupListIndex = new_calt_indices
            rec.Feature.LookupCount = len(new_calt_indices)
            calt_found = True
            break

    if not calt_found:
        feature = otTables.Feature()
        feature.FeatureParams = None
        feature.LookupListIndex = new_calt_indices
        feature.LookupCount = len(new_calt_indices)

        feature_rec = otTables.FeatureRecord()
        feature_rec.FeatureTag = 'calt'
        feature_rec.Feature = feature

        tgt_gsub.table.FeatureList.FeatureRecord.append(feature_rec)
        calt_idx = len(tgt_gsub.table.FeatureList.FeatureRecord) - 1

        for script_rec in tgt_gsub.table.ScriptList.ScriptRecord:
            if script_rec.Script.DefaultLangSys:
                script_rec.Script.DefaultLangSys.FeatureIndex.append(calt_idx)
            for lang_rec in (script_rec.Script.LangSysRecord or []):
                lang_rec.LangSys.FeatureIndex.append(calt_idx)

    print(f"  Appended {len(index_map)} lookups, calt → {len(new_calt_indices)} lookups")
    return new_calt_indices


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <iosevka.ttf> <jetbrains-mono.ttf> <output.ttf>")
        sys.exit(1)

    target_path = sys.argv[1]
    source_path = sys.argv[2]
    output_path = sys.argv[3]

    print(f"Loading {target_path}...")
    target = TTFont(target_path)
    print(f"Loading {source_path}...")
    source = TTFont(source_path)

    italic_angle = detect_italic_angle(target)
    if italic_angle:
        print(f"Detected italic angle: {italic_angle}°")

    target_width = target["hmtx"]["equal"][0]
    source_width = source["hmtx"]["equal"][0]
    print(f"Target char width: {target_width}")
    print(f"Source char width: {source_width}")

    print("Transplanting calt feature...")
    transplant_calt(target, source, target_width, source_width, italic_angle)

    print(f"Saving {output_path}...")
    target.save(output_path)
    print("Done!")


if __name__ == "__main__":
    main()
