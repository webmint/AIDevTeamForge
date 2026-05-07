"""Tests for _sourcemap.py — Source Map V3 single-source consumer.

Test cases:
  1.  VLQ decode: single zero ('A' → [0]).
  2.  VLQ decode: signed-zero from sign-bit-only ('B' → [0]).
  3.  VLQ decode: known quad 'AAAA' → [0,0,0,0].
  4.  VLQ decode: signed negative ('D' → [-1]).
  5.  VLQ decode: multi-char continuation ('+H' → [127]).
  6.  VLQ decode: invalid base64 char rejected.
  7.  VLQ decode: unterminated continuation rejected.
  8.  parse_sourcemap: minimal valid map (one segment).
  9.  parse_sourcemap: rejects non-JSON.
 10.  parse_sourcemap: rejects wrong version.
 11.  parse_sourcemap: rejects missing/empty sources.
 12.  parse_sourcemap: rejects multi-source maps (sources length > 1).
 13.  parse_sourcemap: rejects sourcesContent length mismatch.
 14.  parse_sourcemap: rejects bad base64 char in mappings.
 15.  apply_mapping: happy path on first segment.
 16.  apply_mapping: header offset (leading semicolons) resolves correctly.
 17.  apply_mapping: gen_line beyond mappings raises.
 18.  apply_mapping: gen-col-only segment raises.
 19.  apply_mapping: column before first segment on line raises.
 20.  apply_mapping: chooses largest segment with gen_col <= query_col.
 21.  apply_mapping: invalid gen_line < 1 raises.
 22.  Round-trip via real vue-to-ts output (tiny.vue.ts.map fixture).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib" / "_generate_docs"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _sourcemap import (  # noqa: E402
    MalformedSourceMapError,
    MappingNotFoundError,
    _decode_vlq,
    apply_mapping,
    parse_sourcemap,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sourcemap"


def _build_map(
    sources=None,
    mappings="",
    sources_content=None,
    version=3,
    omit_sources=False,
):
    payload = {"version": version, "names": [], "mappings": mappings}
    if not omit_sources:
        payload["sources"] = sources if sources is not None else ["x.vue"]
    if sources_content is not None:
        payload["sourcesContent"] = sources_content
    return json.dumps(payload)


class VlqDecodeTests(unittest.TestCase):
    def test_single_zero(self):
        self.assertEqual(_decode_vlq("A"), [0])

    def test_signed_zero_from_sign_bit_only(self):
        # 'B' = 1 → cont=0, value=1, sign=1, magnitude=0 → -0 == 0
        self.assertEqual(_decode_vlq("B"), [0])

    def test_known_quad_AAAA(self):
        self.assertEqual(_decode_vlq("AAAA"), [0, 0, 0, 0])

    def test_signed_negative_one(self):
        # 'D' = 3 → cont=0, value=3, sign=1, magnitude=1 → -1
        self.assertEqual(_decode_vlq("D"), [-1])

    def test_multi_char_continuation(self):
        # '+' = 62 → cont=1, low5=30; 'H' = 7 → cont=0, val=7
        # combined value = (7 << 5) | 30 = 254; sign=0, mag=127 → 127
        self.assertEqual(_decode_vlq("+H"), [127])

    def test_rejects_invalid_base64(self):
        with self.assertRaises(MalformedSourceMapError):
            _decode_vlq("@")

    def test_rejects_unterminated_continuation(self):
        # '+' alone has continuation bit set; no follow-up digit
        with self.assertRaises(MalformedSourceMapError):
            _decode_vlq("+")


class ParseSourceMapTests(unittest.TestCase):
    def test_minimal_valid(self):
        sm = parse_sourcemap(_build_map(mappings="AAAA"))
        self.assertEqual(sm.version, 3)
        self.assertEqual(sm.sources, ["x.vue"])
        self.assertEqual(len(sm._decoded_lines), 1)
        self.assertEqual(len(sm._decoded_lines[0]), 1)

    def test_rejects_non_json(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap("not json at all")

    def test_rejects_wrong_version(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap(_build_map(version=2))

    def test_rejects_missing_sources(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap(_build_map(omit_sources=True))

    def test_rejects_empty_sources(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap(_build_map(sources=[]))

    def test_rejects_multi_source(self):
        with self.assertRaises(MalformedSourceMapError) as cm:
            parse_sourcemap(_build_map(sources=["a.vue", "b.vue"]))
        self.assertIn("multi-source", str(cm.exception))

    def test_rejects_sources_content_length_mismatch(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap(
                _build_map(sources=["a.vue"], sources_content=["a", "b"])
            )

    def test_rejects_bad_base64_in_mappings(self):
        with self.assertRaises(MalformedSourceMapError):
            parse_sourcemap(_build_map(mappings="@"))


class ApplyMappingTests(unittest.TestCase):
    def test_happy_path_first_segment(self):
        # AACA: genCol 0, srcIdx 0, origLine +1 (0-based 1), origCol 0
        sm = parse_sourcemap(_build_map(mappings="AACA"))
        path, line, col = apply_mapping(sm, 1, 1)
        self.assertEqual(path, "x.vue")
        self.assertEqual(line, 2)
        self.assertEqual(col, 1)

    def test_header_offset_with_leading_semicolons(self):
        # 7 leading semicolons → 7 empty lines, then AAKA on line 8
        # AAKA = [0, 0, 5, 0] → origLine 5 (0-based) = 6 (1-based)
        sm = parse_sourcemap(_build_map(mappings=";;;;;;;AAKA"))
        path, line, col = apply_mapping(sm, 8, 1)
        self.assertEqual(line, 6)
        self.assertEqual(col, 1)

    def test_line_beyond_mappings_raises(self):
        sm = parse_sourcemap(_build_map(mappings="AAAA"))
        with self.assertRaises(MappingNotFoundError):
            apply_mapping(sm, 5, 1)

    def test_gen_col_only_segment_raises(self):
        # 'C' = 2 → mag 1, sign 0 → 1. fields=[1] (1-field), gen_col=1, no orig.
        sm = parse_sourcemap(_build_map(mappings="C"))
        with self.assertRaises(MappingNotFoundError):
            apply_mapping(sm, 1, 2)

    def test_col_before_first_segment_raises(self):
        # ";KACA" → line 1 empty, line 2 segment at gen_col 5
        sm = parse_sourcemap(_build_map(mappings=";KACA"))
        with self.assertRaises(MappingNotFoundError):
            apply_mapping(sm, 2, 1)

    def test_chooses_largest_seg_le_query_col(self):
        # AACA = [0,0,1,0] → seg1 at genCol 0, origLine 1
        # GACA = [3,0,1,0] → seg2 at genCol 3, origLine 2
        sm = parse_sourcemap(_build_map(mappings="AACA,GACA"))
        path, line, col = apply_mapping(sm, 1, 4)  # col_idx=3 hits seg2
        self.assertEqual(line, 3)
        self.assertEqual(col, 1)

    def test_invalid_gen_line_below_one_raises(self):
        sm = parse_sourcemap(_build_map(mappings="AAAA"))
        with self.assertRaises(MappingNotFoundError):
            apply_mapping(sm, 0, 1)


class RealProducerRoundTripTests(unittest.TestCase):
    """Round-trip via real vue-to-ts.mjs output (committed fixture).

    Producer: src/devforge/lib/vue-to-ts.mjs run on tiny.vue. Header in
    tiny.vue.ts is 7 lines, so the first mapped generated line is 8 — the
    `import { ref } from 'vue';` line — which must resolve back to tiny.vue
    line 6 (the same import in the original SFC).
    """

    def setUp(self):
        self.map_path = FIXTURE_DIR / "tiny.vue.ts.map"
        self.assertTrue(
            self.map_path.exists(),
            f"missing fixture: {self.map_path}",
        )

    def test_first_import_resolves_to_original_line_6(self):
        sm = parse_sourcemap(self.map_path.read_text(encoding="utf-8"))
        self.assertEqual(sm.sources, ["tiny.vue"])
        self.assertIsNotNone(sm.sources_content)
        path, line, col = apply_mapping(sm, 8, 1)
        self.assertEqual(path, "tiny.vue")
        self.assertEqual(line, 6)
        self.assertEqual(col, 1)
        # Sanity: the resolved line in sourcesContent is the import we expect.
        original_lines = sm.sources_content[0].splitlines()
        self.assertEqual(
            original_lines[line - 1],
            "import { ref } from 'vue';",
        )


if __name__ == "__main__":
    unittest.main()
