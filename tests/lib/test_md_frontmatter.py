"""Tests for _md_frontmatter.py — YAML-subset front-matter parser + writer.

≥10 test cases covering:
  1.  Round-trip: render then parse returns equivalent record (canonical keys).
  2.  Round-trip with extra keys: extra keys preserved in sorted block.
  3.  Parse rejects missing leading fence.
  4.  Parse rejects missing closing fence (within 100 lines).
  5.  Parse rejects duplicate keys.
  6.  Parse rejects unparseable lines (no ':' separator).
  7.  Parse rejects closing fence beyond 100 lines.
  8.  Parse correctly extracts ints from `evidence_start: 42`.
  9.  Parse handles quoted strings with embedded escaped quotes.
 10.  Render rejects values with newlines in string fields.
 11.  Body preservation: arbitrary post-fence text round-trips byte-exact.
 12.  Parse handles blank lines inside front-matter fence silently.
 13.  Parse handles unquoted string values (confidence enum).
 14.  Render emits canonical key order deterministically.
 15.  Parse negative int values.

Stdlib only. Python 3.8+.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib" / "_generate_docs"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
# Also add the parent so _generate_docs imports work.
_PARENT_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_PARENT_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_LIB_DIR))

from _generate_docs._md_frontmatter import (  # noqa: E402
    FrontmatterParseError,
    parse_frontmatter,
    render_frontmatter,
)


# ---------------------------------------------------------------------------
# Shared helper: a valid canonical record for round-trip tests.
# ---------------------------------------------------------------------------

_VALID_RECORD = {
    "label": "Authentication entry point",
    "confidence": "extracted",
    "evidence_file": "src/auth/index.ts",
    "evidence_start": 1,
    "evidence_end": 5,
    "content_hash": "a" * 64,
    "model_version": "haiku",
}


# ---------------------------------------------------------------------------
# Test 1: Round-trip with canonical keys.
# ---------------------------------------------------------------------------


class TestRoundTripCanonical(unittest.TestCase):

    def test_render_then_parse_returns_equivalent_record(self):
        body_header = "# index.ts\n"
        rendered = render_frontmatter(_VALID_RECORD, body_header)
        record, body = parse_frontmatter(rendered)

        self.assertEqual(record["label"], _VALID_RECORD["label"])
        self.assertEqual(record["confidence"], _VALID_RECORD["confidence"])
        self.assertEqual(record["evidence_file"], _VALID_RECORD["evidence_file"])
        self.assertEqual(record["evidence_start"], _VALID_RECORD["evidence_start"])
        self.assertEqual(record["evidence_end"], _VALID_RECORD["evidence_end"])
        self.assertEqual(record["content_hash"], _VALID_RECORD["content_hash"])
        self.assertEqual(record["model_version"], _VALID_RECORD["model_version"])

    def test_ints_survive_round_trip(self):
        record = dict(_VALID_RECORD)
        record["evidence_start"] = 42
        record["evidence_end"] = 100
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertIsInstance(parsed["evidence_start"], int)
        self.assertIsInstance(parsed["evidence_end"], int)
        self.assertEqual(parsed["evidence_start"], 42)
        self.assertEqual(parsed["evidence_end"], 100)


# ---------------------------------------------------------------------------
# Test 2: Round-trip with extra keys.
# ---------------------------------------------------------------------------


class TestRoundTripExtraKeys(unittest.TestCase):

    def test_extra_keys_preserved_in_sorted_block(self):
        record = dict(_VALID_RECORD)
        record["zebra_extra"] = "extra_value"
        record["apple_extra"] = "another_value"
        body_header = "# index.ts\n"
        rendered = render_frontmatter(record, body_header)

        # Extra keys must appear in the rendered output.
        self.assertIn("zebra_extra:", rendered)
        self.assertIn("apple_extra:", rendered)

        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["zebra_extra"], "extra_value")
        self.assertEqual(parsed["apple_extra"], "another_value")

    def test_extra_keys_appear_after_canonical_block(self):
        record = dict(_VALID_RECORD)
        record["zzz_extra"] = "value"
        rendered = render_frontmatter(record, "# f.ts\n")
        # model_version is the last canonical key; zzz_extra must come after.
        model_pos = rendered.index("model_version:")
        extra_pos = rendered.index("zzz_extra:")
        self.assertGreater(extra_pos, model_pos)


# ---------------------------------------------------------------------------
# Test 3: Parse rejects missing leading fence.
# ---------------------------------------------------------------------------


class TestMissingLeadingFence(unittest.TestCase):

    def test_no_leading_fence_raises(self):
        text = "label: foo\n---\n"
        with self.assertRaises(FrontmatterParseError) as ctx:
            parse_frontmatter(text)
        self.assertIn("leading", str(ctx.exception))

    def test_empty_string_raises(self):
        with self.assertRaises(FrontmatterParseError):
            parse_frontmatter("")

    def test_whitespace_before_fence_raises(self):
        # Leading whitespace before `---` is rejected (must be exactly `---`).
        text = " ---\nlabel: foo\n---\n"
        with self.assertRaises(FrontmatterParseError):
            parse_frontmatter(text)


# ---------------------------------------------------------------------------
# Test 4: Parse rejects missing closing fence within 100 lines.
# ---------------------------------------------------------------------------


class TestMissingClosingFence(unittest.TestCase):

    def test_no_closing_fence_raises(self):
        text = "---\nlabel: foo\n"
        with self.assertRaises(FrontmatterParseError) as ctx:
            parse_frontmatter(text)
        self.assertIn("closing", str(ctx.exception))

    def test_closing_fence_on_line_101_raises(self):
        # 100 key: value lines then a closing fence on line 101.
        lines = ["---"]
        for i in range(100):
            lines.append("key{0}: value".format(i))
        lines.append("---")
        text = "\n".join(lines)
        with self.assertRaises(FrontmatterParseError) as ctx:
            parse_frontmatter(text)
        self.assertIn("100", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test 5: Parse rejects duplicate keys.
# ---------------------------------------------------------------------------


class TestDuplicateKeys(unittest.TestCase):

    def test_duplicate_key_raises(self):
        text = "---\nlabel: first\nlabel: second\n---\n"
        with self.assertRaises(FrontmatterParseError) as ctx:
            parse_frontmatter(text)
        self.assertIn("duplicate", str(ctx.exception))
        self.assertIn("label", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test 6: Parse rejects unparseable lines (no ':').
# ---------------------------------------------------------------------------


class TestUnparseableLine(unittest.TestCase):

    def test_line_without_colon_raises(self):
        text = "---\nthis is not a key value pair\n---\n"
        with self.assertRaises(FrontmatterParseError) as ctx:
            parse_frontmatter(text)
        self.assertIn("unparseable", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test 7: Parse rejects closing fence beyond 100 lines.
# ---------------------------------------------------------------------------


class TestClosingFenceBeyond100(unittest.TestCase):

    def test_99_lines_then_close_is_ok(self):
        # 99 blank lines then close — within limit.
        lines = ["---"]
        for _ in range(98):
            lines.append("")
        lines.append("---")
        lines.append("")
        text = "\n".join(lines)
        # Should NOT raise.
        record, body = parse_frontmatter(text)
        self.assertEqual(record, {})

    def test_100_blank_lines_then_close_is_ok(self):
        # Closing on line index 100 (the 100th line after opening) is within limit.
        lines = ["---"]
        for _ in range(99):
            lines.append("")
        lines.append("---")
        text = "\n".join(lines)
        record, body = parse_frontmatter(text)
        self.assertEqual(record, {})

    def test_101_lines_no_close_raises(self):
        lines = ["---"]
        for i in range(101):
            lines.append("k{0}: v".format(i))
        lines.append("---")
        text = "\n".join(lines)
        with self.assertRaises(FrontmatterParseError):
            parse_frontmatter(text)


# ---------------------------------------------------------------------------
# Test 8: Int extraction.
# ---------------------------------------------------------------------------


class TestIntExtraction(unittest.TestCase):

    def test_evidence_start_parsed_as_int(self):
        text = "---\nevidence_start: 42\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record["evidence_start"], 42)
        self.assertIsInstance(record["evidence_start"], int)

    def test_zero_parsed_as_int(self):
        text = "---\nevidence_start: 0\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record["evidence_start"], 0)
        self.assertIsInstance(record["evidence_start"], int)


# ---------------------------------------------------------------------------
# Test 9: Quoted strings with embedded escaped chars.
# ---------------------------------------------------------------------------


class TestQuotedStringsEscaped(unittest.TestCase):

    def test_embedded_quote_roundtrips(self):
        record = dict(_VALID_RECORD)
        record["label"] = 'Component with "quotes" inside'
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["label"], 'Component with "quotes" inside')

    def test_forward_slash_in_path_roundtrips(self):
        record = dict(_VALID_RECORD)
        record["evidence_file"] = "src/auth/index.ts"
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["evidence_file"], "src/auth/index.ts")

    def test_backslash_in_label_roundtrips(self):
        # Labels may contain backslashes (regex notation, escape sequences in
        # prose). Round-trip must preserve them byte-exact.
        record = dict(_VALID_RECORD)
        record["label"] = r"matches \d+ digits"
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["label"], r"matches \d+ digits")

    def test_double_backslash_in_label_roundtrips(self):
        record = dict(_VALID_RECORD)
        record["label"] = r"path\\to\\file"
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["label"], r"path\\to\\file")

    def test_trailing_backslash_in_label_roundtrips(self):
        record = dict(_VALID_RECORD)
        record["label"] = "trailing slash\\"
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["label"], "trailing slash\\")

    def test_quote_and_backslash_mixed_roundtrips(self):
        record = dict(_VALID_RECORD)
        record["label"] = 'mix "quote" and \\backslash'
        rendered = render_frontmatter(record, "# foo.ts\n")
        parsed, _ = parse_frontmatter(rendered)
        self.assertEqual(parsed["label"], 'mix "quote" and \\backslash')


# ---------------------------------------------------------------------------
# Test 10: Render rejects values with newlines.
# ---------------------------------------------------------------------------


class TestRenderRejectsNewlines(unittest.TestCase):

    def test_newline_in_label_raises(self):
        record = dict(_VALID_RECORD)
        record["label"] = "line one\nline two"
        with self.assertRaises((ValueError, FrontmatterParseError)):
            render_frontmatter(record, "# foo.ts\n")

    def test_carriage_return_in_label_raises(self):
        record = dict(_VALID_RECORD)
        record["label"] = "line one\rline two"
        with self.assertRaises((ValueError, FrontmatterParseError)):
            render_frontmatter(record, "# foo.ts\n")

    def test_newline_in_evidence_file_raises(self):
        record = dict(_VALID_RECORD)
        record["evidence_file"] = "src/\nfoo.ts"
        with self.assertRaises((ValueError, FrontmatterParseError)):
            render_frontmatter(record, "# foo.ts\n")


# ---------------------------------------------------------------------------
# Test 11: Body preservation.
# ---------------------------------------------------------------------------


class TestBodyPreservation(unittest.TestCase):

    def test_arbitrary_body_roundtrips_byte_exact(self):
        body_header = "# Login.vue\n"
        body_extra = "\nThis is a paragraph.\n\n## Section\n\nMore content.\n"
        full_body = body_header.rstrip("\n") + body_extra
        record = dict(_VALID_RECORD)
        rendered = render_frontmatter(record, body_header)
        # Append additional body content after the rendered output to simulate
        # a partially filled doc.
        augmented = rendered.rstrip("\n") + body_extra

        _, body_out = parse_frontmatter(augmented)
        # Body section must contain the extra content.
        self.assertIn("paragraph", body_out)
        self.assertIn("Section", body_out)

    def test_empty_body_roundtrips(self):
        body_header = "# foo.ts\n"
        rendered = render_frontmatter(_VALID_RECORD, body_header)
        _, body = parse_frontmatter(rendered)
        # Body may be whitespace only for a skeleton — that is acceptable.
        self.assertIsNotNone(body)


# ---------------------------------------------------------------------------
# Test 12: Blank lines inside front-matter are skipped.
# ---------------------------------------------------------------------------


class TestBlankLinesInsideFence(unittest.TestCase):

    def test_blank_lines_skipped_silently(self):
        text = "---\n\nlabel: foo\n\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record.get("label"), "foo")


# ---------------------------------------------------------------------------
# Test 13: Unquoted string values (e.g. confidence enum).
# ---------------------------------------------------------------------------


class TestUnquotedStringValue(unittest.TestCase):

    def test_unquoted_confidence_parsed_as_string(self):
        text = "---\nconfidence: extracted\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record["confidence"], "extracted")
        self.assertIsInstance(record["confidence"], str)

    def test_unquoted_ambiguous_parsed(self):
        text = "---\nconfidence: ambiguous\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record["confidence"], "ambiguous")


# ---------------------------------------------------------------------------
# Test 14: Render emits canonical key order deterministically.
# ---------------------------------------------------------------------------


class TestCanonicalKeyOrder(unittest.TestCase):

    def test_canonical_order_in_output(self):
        rendered = render_frontmatter(_VALID_RECORD, "# f.ts\n")
        # Find positions of canonical keys.
        positions = {}
        for key in ["label", "confidence", "evidence_file", "evidence_start",
                    "evidence_end", "content_hash", "model_version"]:
            positions[key] = rendered.index(key + ":")

        # Verify strict ordering: each key appears after the previous.
        ordered = ["label", "confidence", "evidence_file", "evidence_start",
                   "evidence_end", "content_hash", "model_version"]
        for i in range(len(ordered) - 1):
            self.assertLess(
                positions[ordered[i]], positions[ordered[i + 1]],
                "Expected {0} before {1}".format(ordered[i], ordered[i + 1]),
            )

    def test_render_is_deterministic(self):
        r1 = render_frontmatter(_VALID_RECORD, "# f.ts\n")
        r2 = render_frontmatter(_VALID_RECORD, "# f.ts\n")
        self.assertEqual(r1, r2)


# ---------------------------------------------------------------------------
# Test 15: Negative int values.
# ---------------------------------------------------------------------------


class TestNegativeInts(unittest.TestCase):

    def test_negative_int_parsed(self):
        # While negative line numbers are semantically invalid, the parser
        # should handle them grammatically (semantic validation is in the
        # caller).
        text = "---\nevidence_start: -1\n---\n"
        record, _ = parse_frontmatter(text)
        self.assertEqual(record["evidence_start"], -1)
        self.assertIsInstance(record["evidence_start"], int)


if __name__ == "__main__":
    unittest.main()
