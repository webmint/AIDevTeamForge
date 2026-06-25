"""Tests for src/devforge/lib/_design/ — the design_helper Phase 2 subpackage.

Real-fixture discipline:
  All tests that exercise the reference parser or spacing extractor use real
  fixture FILES written to a temp directory, then round-tripped through the
  real producer functions.  No hand-authored value strings are used as the
  "expected output" unless they are definitionally derived from the fixture we
  wrote ourselves.

Coverage plan
-------------
_schema.py
  ElementRecord validation:
    - valid MATCH element → no errors
    - valid DEFER-EMPTY element → no errors
    - valid STATIC-PLACEHOLDER element → no errors
    - valid DEVIATE element with reason → no errors
    - DEVIATE element with empty reason → error naming the element
    - invalid disposition string → error
    - unclassified element (disposition="") → error naming the element
    - empty data_ref → error
    - control char in data_ref → error
    - control char in deviate_reason → error

  ManifestContainer / validate_manifest:
    - fully-classified manifest, empty gap-list → empty errors list
    - one unclassified element → error names the element
    - two unclassified elements → two errors
    - non-empty gap-list → error names each token
    - empty reference_html → error
    - DEVIATE element without reason → error

  Serialization round-trip:
    - element_to_dict / element_from_dict → identical data
    - manifest_to_dict / manifest_from_dict → identical data
    - manifest_to_json / manifest_from_json → identical data

_reference.py
  resolve_reference (real fixture HTML + CSS):
    - returns expected element list (data-ref keys, tags, classes)
    - inline_style captured verbatim
    - resolved_values contains rules from <style> block
    - linked stylesheet resolved from disk → rules captured
    - class with no CSS definition → appears in gap_list
    - undefined CSS custom property in inline_style → appears in gap_list
    - undefined CSS custom property referenced in <style> value → appears in gap_list
    - defined class (present in <style>) → NOT in gap_list
    - defined custom property → NOT in gap_list
    - elements without data-ref are NOT in the returned elements list
    - file not found → cmd_resolve_reference returns exit code 2

  cmd_resolve_reference (CLI handler):
    - happy path: emits valid JSON to stdout, exit 0
    - missing --html-path argument: exit 2
    - non-existent file: exit 2

_manifest.py
  init_manifest_from_reference:
    - produces manifest with all elements unclassified
    - gap_list is copied from resolve-reference output
    - reference_html path is copied
    - element count matches reference output

  cmd_init_manifest:
    - happy path: emits valid skeleton manifest JSON, exit 0
    - missing --reference-json: exit 2
    - non-existent file: exit 2
    - malformed JSON: exit 2

  cmd_validate_manifest:
    - fully-classified manifest + empty gap-list → exit 0, valid=true
    - one unclassified element → exit 1, valid=false, error names element
    - non-empty gap-list → exit 1, valid=false, error names token
    - DEVIATE without reason → exit 1
    - missing --manifest-path: exit 2
    - non-existent file: exit 2

  extract_spacing_scale / cmd_extract_spacing_scale:
    - styles.css present with spacing rules → available=true, scale non-empty
    - scale contains px and rem values from the fixture
    - scale does NOT contain non-spacing properties (e.g. color)
    - styles.css absent → available=false, scale=[], source=None, exit 0
    - scale values are sorted (smallest first)

_cli.py / main entry:
  - no subcommand → exit 2
  - unknown subcommand → exits non-zero
  - each verb is reachable via main([verb, ...])

Phase-2 Verify cases (plan 40 Phase 2 verification criteria):
  V1: fully-classified manifest + empty gap-list → exit 0
  V2: one unclassified element → exit non-zero naming the element
  V3: non-empty gap-list → exit non-zero naming the class/token
  V4: resolve-reference on fixture returns expected element list + values
  V5: spacing extraction returns scale when styles.css present
  V6: spacing extraction returns available=false when styles.css absent
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Path setup — make _design importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._schema import (  # noqa: E402
    ElementRecord,
    ManifestContainer,
    DISPOSITION_MATCH,
    DISPOSITION_DEFER_EMPTY,
    DISPOSITION_STATIC_PLACEHOLDER,
    DISPOSITION_DEVIATE,
    DISPOSITION_UNCLASSIFIED,
    VALID_DISPOSITIONS,
    validate_element,
    validate_manifest,
    element_to_dict,
    element_from_dict,
    manifest_to_dict,
    manifest_from_dict,
    manifest_to_json,
    manifest_from_json,
)
from _design._reference import (  # noqa: E402
    resolve_reference,
    cmd_resolve_reference,
    _parse_css_rules,
    _compute_gap_list,
    _extract_rule_blocks,
)
from _design._manifest import (  # noqa: E402
    init_manifest_from_reference,
    cmd_init_manifest,
    cmd_validate_manifest,
    extract_spacing_scale,
    cmd_extract_spacing_scale,
)
from _design._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

# Real reference.html fixture — written to a temp dir and round-tripped.
# Contains:
#   - a data-ref element with a class defined in the <style> block (no gap)
#   - a data-ref element with a class NOT defined anywhere (gap)
#   - a data-ref element with an inline style using var(--defined-token) (no gap)
#   - a data-ref element with an inline style using var(--undefined-token) (gap)
#   - a data-ref element with a linked-stylesheet class (gap because stylesheet
#     is NOT provided in this fixture — tested separately)
#   - a non-data-ref element (should NOT appear in elements list)
#   - a <link rel="stylesheet"> pointing to a file that exists on disk
#     (tested in a second fixture variant)

REFERENCE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <style>
    .defined-class {{
      border: 1px solid #333;
      color: var(--defined-token);
    }}
    :root {{
      --defined-token: #ffffff;
    }}
  </style>
  {stylesheet_link}
</head>
<body>
  <!-- defined class: should NOT be in gap_list -->
  <div data-ref="sidebar" class="defined-class" id="sidebar-root">
    Sidebar content
  </div>

  <!-- undefined class: SHOULD be in gap_list -->
  <section data-ref="header" class="undefined-class-xyz">
    Header
  </section>

  <!-- inline style with defined token: NOT in gap_list -->
  <nav data-ref="nav-bar" style="color: var(--defined-token)">
    Navigation
  </nav>

  <!-- inline style with undefined token: SHOULD be in gap_list -->
  <article data-ref="main-content" style="margin: var(--undefined-token)">
    Main
  </article>

  <!-- no data-ref: should NOT appear in elements list -->
  <footer class="some-footer-class">
    Footer
  </footer>
</body>
</html>
"""

STYLES_CSS_CONTENT = """\
:root {
  --spacing-sm: 4px;
  --spacing-md: 8px;
  --color-bg: #ffffff;
}

.container {
  margin: 16px;
  padding: 8px 4px;
  gap: 1rem;
  color: var(--color-bg);
}

.sidebar {
  padding-top: 0;
  inset: 2rem;
}

/* non-spacing property — should NOT appear in spacing scale */
.button {
  background-color: #ff0000;
  border-radius: 4px;
}
"""

LINKED_CSS_CONTENT = """\
.linked-class {
  border: 2px solid blue;
}
"""


def _write_fixture(tmp_dir, with_stylesheet=False, with_linked_css=False):
    # type: (str, bool, bool) -> str
    """Write reference.html (and optionally styles.css / linked.css) to tmp_dir.
    Returns the path to the reference.html file.
    """
    link_tag = ""
    if with_stylesheet:
        link_tag = '<link rel="stylesheet" href="styles.css">'
        css_path = os.path.join(tmp_dir, "styles.css")
        with open(css_path, "w", encoding="utf-8") as fh:
            fh.write(STYLES_CSS_CONTENT)

    if with_linked_css:
        link_tag = '<link rel="stylesheet" href="linked.css">'
        linked_path = os.path.join(tmp_dir, "linked.css")
        with open(linked_path, "w", encoding="utf-8") as fh:
            fh.write(LINKED_CSS_CONTENT)

    html = REFERENCE_HTML_TEMPLATE.format(stylesheet_link=link_tag)
    html_path = os.path.join(tmp_dir, "reference.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return html_path


def _write_styles_css(tmp_dir):
    # type: (str) -> str
    """Write styles.css and return its path."""
    path = os.path.join(tmp_dir, "styles.css")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(STYLES_CSS_CONTENT)
    return path


def _capture_stdout(fn, *args, **kwargs):
    # type: (callable, ...) -> tuple
    """Run fn, capture stdout, return (exit_code, stdout_text, stderr_text)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = fn(*args, **kwargs)
    finally:
        stdout_text = sys.stdout.getvalue()
        stderr_text = sys.stderr.getvalue()
        sys.stdout = old_out
        sys.stderr = old_err
    return code, stdout_text, stderr_text


def _make_args(**kwargs):
    """Build a simple namespace object."""
    class _NS:
        pass
    ns = _NS()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# Tests: _schema.py — ElementRecord validation
# ---------------------------------------------------------------------------


class TestElementValidation(unittest.TestCase):

    def test_valid_match_element(self):
        rec = ElementRecord("sidebar", DISPOSITION_MATCH)
        self.assertEqual(validate_element(rec), [])

    def test_valid_defer_empty_element(self):
        rec = ElementRecord("main-slot", DISPOSITION_DEFER_EMPTY)
        self.assertEqual(validate_element(rec), [])

    def test_valid_static_placeholder(self):
        rec = ElementRecord("hero-image", DISPOSITION_STATIC_PLACEHOLDER)
        self.assertEqual(validate_element(rec), [])

    def test_valid_deviate_element(self):
        rec = ElementRecord("accent-bar", DISPOSITION_DEVIATE, "accent area is inert")
        self.assertEqual(validate_element(rec), [])

    def test_deviate_empty_reason_is_error(self):
        rec = ElementRecord("accent-bar", DISPOSITION_DEVIATE, "")
        errors = validate_element(rec)
        self.assertTrue(any("deviate_reason is empty" in e for e in errors),
                        "Expected deviate_reason error; got: {0}".format(errors))

    def test_invalid_disposition_string(self):
        rec = ElementRecord("foo", "BOGUS")
        errors = validate_element(rec)
        self.assertTrue(any("invalid disposition" in e for e in errors),
                        "Expected invalid disposition error; got: {0}".format(errors))

    def test_unclassified_element_is_error(self):
        rec = ElementRecord("sidebar", DISPOSITION_UNCLASSIFIED)
        errors = validate_element(rec)
        self.assertTrue(any("unclassified" in e for e in errors),
                        "Expected unclassified error; got: {0}".format(errors))
        # Error message must name the element
        self.assertTrue(any("sidebar" in e for e in errors),
                        "Expected element name in error; got: {0}".format(errors))

    def test_empty_data_ref_is_error(self):
        rec = ElementRecord("", DISPOSITION_MATCH)
        errors = validate_element(rec)
        self.assertTrue(any("data_ref" in e for e in errors),
                        "Expected data_ref error; got: {0}".format(errors))

    def test_whitespace_only_data_ref_is_error(self):
        rec = ElementRecord("   ", DISPOSITION_MATCH)
        errors = validate_element(rec)
        self.assertTrue(any("data_ref" in e for e in errors),
                        "Expected data_ref error; got: {0}".format(errors))

    def test_control_char_in_data_ref(self):
        rec = ElementRecord("side\nbar", DISPOSITION_MATCH)
        errors = validate_element(rec)
        self.assertTrue(any("control" in e for e in errors),
                        "Expected control char error; got: {0}".format(errors))

    def test_control_char_in_deviate_reason(self):
        rec = ElementRecord("foo", DISPOSITION_DEVIATE, "reason\x01here")
        errors = validate_element(rec)
        self.assertTrue(any("control" in e for e in errors),
                        "Expected control char error; got: {0}".format(errors))


# ---------------------------------------------------------------------------
# Tests: _schema.py — ManifestContainer / validate_manifest
# ---------------------------------------------------------------------------


class TestManifestValidation(unittest.TestCase):

    def _make_manifest(self, dispositions, gap_list=None):
        # type: (list, list) -> ManifestContainer
        """Build a manifest from a list of (data_ref, disposition[, reason]) tuples."""
        elements = []
        for item in dispositions:
            if len(item) == 3:
                elements.append(ElementRecord(item[0], item[1], item[2]))
            else:
                elements.append(ElementRecord(item[0], item[1]))
        return ManifestContainer(
            reference_html="design/reference.html",
            elements=elements,
            gap_list=gap_list or [],
        )

    def test_fully_classified_empty_gap_list_is_valid(self):
        m = self._make_manifest([
            ("sidebar", DISPOSITION_MATCH),
            ("header", DISPOSITION_DEFER_EMPTY),
            ("accent", DISPOSITION_DEVIATE, "inert area"),
        ])
        errors = validate_manifest(m)
        self.assertEqual(errors, [], "Expected no errors; got: {0}".format(errors))

    def test_one_unclassified_element_is_error(self):
        # V2: one unclassified element → non-zero naming the element
        m = self._make_manifest([
            ("sidebar", DISPOSITION_MATCH),
            ("header", DISPOSITION_UNCLASSIFIED),
        ])
        errors = validate_manifest(m)
        self.assertTrue(len(errors) >= 1)
        self.assertTrue(any("header" in e for e in errors),
                        "Expected 'header' named in error; got: {0}".format(errors))

    def test_two_unclassified_elements_both_named(self):
        m = self._make_manifest([
            ("el-a", DISPOSITION_UNCLASSIFIED),
            ("el-b", DISPOSITION_UNCLASSIFIED),
        ])
        errors = validate_manifest(m)
        self.assertTrue(any("el-a" in e for e in errors))
        self.assertTrue(any("el-b" in e for e in errors))

    def test_nonempty_gap_list_is_error(self):
        # V3: non-empty gap-list → non-zero naming the token
        m = self._make_manifest(
            [("sidebar", DISPOSITION_MATCH)],
            gap_list=["undefined-class-xyz (no CSS definition found)"],
        )
        errors = validate_manifest(m)
        self.assertTrue(any("undefined-class-xyz" in e for e in errors),
                        "Expected gap-list token in error; got: {0}".format(errors))

    def test_multiple_gap_list_tokens_all_named(self):
        m = self._make_manifest(
            [("sidebar", DISPOSITION_MATCH)],
            gap_list=["token-a (no CSS definition found)", "--token-b (undefined)"],
        )
        errors = validate_manifest(m)
        self.assertTrue(any("token-a" in e for e in errors))
        self.assertTrue(any("token-b" in e for e in errors))

    def test_empty_reference_html_is_error(self):
        m = self._make_manifest([("sidebar", DISPOSITION_MATCH)])
        m.reference_html = ""
        errors = validate_manifest(m)
        self.assertTrue(any("reference_html" in e for e in errors))

    def test_deviate_without_reason_propagates_from_element(self):
        m = self._make_manifest([
            ("accent", DISPOSITION_DEVIATE, ""),
        ])
        errors = validate_manifest(m)
        self.assertTrue(any("deviate_reason is empty" in e for e in errors))


# ---------------------------------------------------------------------------
# Tests: _schema.py — serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization(unittest.TestCase):

    def test_element_roundtrip(self):
        orig = ElementRecord("sidebar", DISPOSITION_MATCH)
        restored = element_from_dict(element_to_dict(orig))
        self.assertEqual(restored.data_ref, "sidebar")
        self.assertEqual(restored.disposition, DISPOSITION_MATCH)
        self.assertEqual(restored.deviate_reason, "")

    def test_element_roundtrip_deviate(self):
        orig = ElementRecord("accent", DISPOSITION_DEVIATE, "inert area")
        restored = element_from_dict(element_to_dict(orig))
        self.assertEqual(restored.data_ref, "accent")
        self.assertEqual(restored.disposition, DISPOSITION_DEVIATE)
        self.assertEqual(restored.deviate_reason, "inert area")

    def test_manifest_roundtrip_dict(self):
        m = ManifestContainer(
            reference_html="design/reference.html",
            elements=[
                ElementRecord("sidebar", DISPOSITION_MATCH),
                ElementRecord("slot-a", DISPOSITION_DEFER_EMPTY),
            ],
            gap_list=["missing-token (undefined)"],
        )
        restored = manifest_from_dict(manifest_to_dict(m))
        self.assertEqual(restored.reference_html, "design/reference.html")
        self.assertEqual(len(restored.elements), 2)
        self.assertEqual(restored.elements[0].data_ref, "sidebar")
        self.assertEqual(restored.gap_list, ["missing-token (undefined)"])

    def test_manifest_roundtrip_json(self):
        m = ManifestContainer(
            reference_html="design/reference.html",
            elements=[ElementRecord("nav", DISPOSITION_STATIC_PLACEHOLDER)],
            gap_list=[],
        )
        restored = manifest_from_json(manifest_to_json(m))
        self.assertEqual(restored.elements[0].disposition, DISPOSITION_STATIC_PLACEHOLDER)
        self.assertEqual(restored.gap_list, [])


# ---------------------------------------------------------------------------
# Tests: _reference.py — resolve_reference with real fixtures
# ---------------------------------------------------------------------------


class TestResolveReference(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._html_path = _write_fixture(self._tmp, with_stylesheet=False)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _result(self):
        return resolve_reference(self._html_path)

    def test_returns_four_data_ref_elements(self):
        # V4: resolve-reference returns expected element list
        result = self._result()
        data_refs = [e["data_ref"] for e in result["elements"]]
        self.assertIn("sidebar", data_refs)
        self.assertIn("header", data_refs)
        self.assertIn("nav-bar", data_refs)
        self.assertIn("main-content", data_refs)

    def test_non_data_ref_element_excluded(self):
        result = self._result()
        data_refs = [e["data_ref"] for e in result["elements"]]
        # The footer has no data-ref so it must NOT appear
        self.assertNotIn("footer", data_refs)
        # No empty data_ref entries
        self.assertFalse(any(r == "" for r in data_refs))

    def test_element_tag_captured(self):
        result = self._result()
        sidebar = next(e for e in result["elements"] if e["data_ref"] == "sidebar")
        self.assertEqual(sidebar["tag"], "div")

    def test_element_id_captured(self):
        result = self._result()
        sidebar = next(e for e in result["elements"] if e["data_ref"] == "sidebar")
        self.assertEqual(sidebar["id"], "sidebar-root")

    def test_element_classes_captured(self):
        result = self._result()
        sidebar = next(e for e in result["elements"] if e["data_ref"] == "sidebar")
        self.assertIn("defined-class", sidebar["classes"])

    def test_inline_style_captured(self):
        result = self._result()
        nav = next(e for e in result["elements"] if e["data_ref"] == "nav-bar")
        self.assertIn("--defined-token", nav["inline_style"])

    def test_style_block_rules_captured(self):
        result = self._result()
        # .defined-class should appear in resolved_values
        keys = list(result["resolved_values"].keys())
        self.assertTrue(
            any("defined-class" in k for k in keys),
            "Expected .defined-class rule in resolved_values; got keys: {0}".format(keys),
        )

    def test_custom_property_defined(self):
        result = self._result()
        self.assertIn("--defined-token", result["custom_properties"])

    def test_undefined_class_in_gap_list(self):
        result = self._result()
        self.assertTrue(
            any("undefined-class-xyz" in g for g in result["gap_list"]),
            "Expected undefined-class-xyz in gap_list; got: {0}".format(result["gap_list"]),
        )

    def test_undefined_token_in_inline_style_in_gap_list(self):
        result = self._result()
        self.assertTrue(
            any("--undefined-token" in g for g in result["gap_list"]),
            "Expected --undefined-token in gap_list; got: {0}".format(result["gap_list"]),
        )

    def test_defined_class_not_in_gap_list(self):
        result = self._result()
        # Use a word-boundary check: the gap entry starts with the class name
        # (e.g. "defined-class (no CSS definition found)") so we check for
        # exactly "defined-class " or "defined-class (" as a prefix, NOT a
        # substring match (which would also hit "undefined-class-xyz ...").
        self.assertFalse(
            any(g.startswith("defined-class ") for g in result["gap_list"]),
            "defined-class should NOT be in gap_list; got: {0}".format(result["gap_list"]),
        )

    def test_defined_custom_property_not_in_gap_list(self):
        result = self._result()
        self.assertFalse(
            any("--defined-token" in g and "undefined" in g for g in result["gap_list"]),
            "--defined-token should NOT be in gap_list; got: {0}".format(result["gap_list"]),
        )

    def test_linked_stylesheet_resolved_when_present(self):
        # Write a fixture with a linked CSS that IS on disk
        html_path = _write_fixture(self._tmp, with_linked_css=True)
        result = resolve_reference(html_path)
        # .linked-class should be in resolved_values
        keys = list(result["resolved_values"].keys())
        self.assertTrue(
            any("linked-class" in k for k in keys),
            "Expected .linked-class from linked.css; got: {0}".format(keys),
        )

    def test_linked_stylesheet_not_on_disk_does_not_crash(self):
        # Create HTML with a stylesheet href pointing to a non-existent file
        html = """<!DOCTYPE html><html><head>
        <link rel="stylesheet" href="nonexistent.css">
        </head><body>
        <div data-ref="el1" class="orphan-class">text</div>
        </body></html>"""
        html_path = os.path.join(self._tmp, "ref_nolink.html")
        with open(html_path, "w") as fh:
            fh.write(html)
        result = resolve_reference(html_path)
        # Should not crash; orphan-class has no definition → gap_list
        self.assertTrue(
            any("orphan-class" in g for g in result["gap_list"]),
            "Expected orphan-class in gap_list; got: {0}".format(result["gap_list"]),
        )

    def test_file_not_found_raises(self):
        with self.assertRaises(OSError):
            resolve_reference("/tmp/nonexistent-reference-12345.html")

    def test_reference_html_key_in_result(self):
        result = self._result()
        self.assertEqual(result["reference_html"], self._html_path)

    def test_F1_var_in_non_data_ref_rule_does_not_create_gap(self):
        """F1: a var(--x) in a rule whose selector does NOT match any data-ref
        element must NOT create a gap entry — only rules that apply to data-ref
        elements are scanned for undefined token references."""
        html = """<!DOCTYPE html><html>
<head>
<style>
  /* .data-ref-class IS used by a data-ref element */
  .data-ref-class { color: red; }
  /* .utility-class is NOT used by any data-ref element;
     its var(--internal-token) must NOT appear in the gap-list */
  .utility-class { margin: var(--internal-token); }
  /* --internal-token is also NOT defined anywhere */
</style>
</head>
<body>
  <div data-ref="el1" class="data-ref-class">content</div>
  <!-- .utility-class is NOT applied to any data-ref element -->
  <span class="utility-class">non-ref span</span>
</body>
</html>"""
        html_path = os.path.join(self._tmp, "ref_f1.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)
        result = resolve_reference(html_path)
        # --internal-token is only referenced in .utility-class, which is NOT
        # applied to any data-ref element → must NOT appear in gap_list
        self.assertFalse(
            any("--internal-token" in g for g in result["gap_list"]),
            "F1: --internal-token from non-data-ref rule should NOT be in gap_list; "
            "got: {0}".format(result["gap_list"]),
        )
        # Sanity: the element itself is still found
        self.assertEqual(len(result["elements"]), 1)
        self.assertEqual(result["elements"][0]["data_ref"], "el1")


class TestCmdResolveReference(unittest.TestCase):
    """CLI handler tests for resolve-reference."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._html_path = _write_fixture(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_happy_path_exit_0_json_stdout(self):
        args = _make_args(html_path=self._html_path)
        code, out, err = _capture_stdout(cmd_resolve_reference, args)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("elements", data)
        self.assertIn("gap_list", data)

    def test_missing_html_path_arg_exit_2(self):
        args = _make_args(html_path=None)
        code, out, err = _capture_stdout(cmd_resolve_reference, args)
        self.assertEqual(code, 2)

    def test_nonexistent_file_exit_2(self):
        args = _make_args(html_path="/tmp/does-not-exist-99999.html")
        code, out, err = _capture_stdout(cmd_resolve_reference, args)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Tests: _manifest.py — init_manifest_from_reference
# ---------------------------------------------------------------------------


class TestInitManifest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._html_path = _write_fixture(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _ref_result(self):
        return resolve_reference(self._html_path)

    def test_elements_all_unclassified(self):
        ref = self._ref_result()
        m = init_manifest_from_reference(ref)
        for elem in m.elements:
            self.assertEqual(
                elem.disposition,
                DISPOSITION_UNCLASSIFIED,
                "Expected unclassified; data_ref={0}".format(elem.data_ref),
            )

    def test_element_count_matches_reference(self):
        ref = self._ref_result()
        m = init_manifest_from_reference(ref)
        self.assertEqual(len(m.elements), len(ref["elements"]))

    def test_gap_list_copied(self):
        ref = self._ref_result()
        m = init_manifest_from_reference(ref)
        self.assertEqual(m.gap_list, ref["gap_list"])

    def test_reference_html_path_copied(self):
        ref = self._ref_result()
        m = init_manifest_from_reference(ref)
        self.assertEqual(m.reference_html, self._html_path)

    def test_data_refs_preserved(self):
        ref = self._ref_result()
        m = init_manifest_from_reference(ref)
        manifest_data_refs = {e.data_ref for e in m.elements}
        ref_data_refs = {e["data_ref"] for e in ref["elements"]}
        self.assertEqual(manifest_data_refs, ref_data_refs)


class TestCmdInitManifest(unittest.TestCase):
    """CLI handler tests for init-manifest."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        # Write resolve-reference output to a JSON file
        html_path = _write_fixture(self._tmp)
        ref_result = resolve_reference(html_path)
        self._ref_json_path = os.path.join(self._tmp, "ref_result.json")
        with open(self._ref_json_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(ref_result, indent=2))
        self._ref_result = ref_result

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_happy_path_exit_0_json_stdout(self):
        args = _make_args(reference_json=self._ref_json_path)
        code, out, err = _capture_stdout(cmd_init_manifest, args)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("elements", data)
        self.assertIn("gap_list", data)
        # All elements must be unclassified
        for elem in data["elements"]:
            self.assertEqual(elem["disposition"], "")

    def test_missing_reference_json_arg_exit_2(self):
        args = _make_args(reference_json=None)
        code, out, err = _capture_stdout(cmd_init_manifest, args)
        self.assertEqual(code, 2)

    def test_nonexistent_file_exit_2(self):
        args = _make_args(reference_json="/tmp/no-such-file-99999.json")
        code, out, err = _capture_stdout(cmd_init_manifest, args)
        self.assertEqual(code, 2)

    def test_malformed_json_exit_2(self):
        bad_path = os.path.join(self._tmp, "bad.json")
        with open(bad_path, "w") as fh:
            fh.write("{invalid json")
        args = _make_args(reference_json=bad_path)
        code, out, err = _capture_stdout(cmd_init_manifest, args)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Tests: _manifest.py — validate-manifest CLI (Phase-2 Verify cases V1-V3)
# ---------------------------------------------------------------------------


class TestCmdValidateManifest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_manifest(self, dispositions, gap_list=None):
        # type: (list, list) -> str
        """Write a manifest JSON file and return its path."""
        elements = []
        for item in dispositions:
            d = {
                "data_ref": item[0],
                "disposition": item[1],
            }
            if len(item) == 3:
                d["deviate_reason"] = item[2]
            elements.append(d)
        manifest = {
            "version": "1",
            "reference_html": "design/reference.html",
            "elements": elements,
            "gap_list": gap_list or [],
        }
        path = os.path.join(self._tmp, "manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, indent=2))
        return path

    def test_V1_fully_classified_empty_gap_list_exit_0(self):
        # V1: fully-classified manifest + empty gap-list → exit 0
        path = self._write_manifest([
            ("sidebar", "MATCH"),
            ("header", "DEFER-EMPTY"),
            ("slot", "STATIC-PLACEHOLDER"),
            ("accent", "DEVIATE", "inert area"),
        ])
        args = _make_args(manifest_path=path)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 0, "Expected exit 0; stderr: {0}".format(err))
        data = json.loads(out)
        self.assertTrue(data["valid"])
        self.assertEqual(data["errors"], [])

    def test_V2_one_unclassified_element_exit_1_names_element(self):
        # V2: one unclassified element → exit non-zero naming the element
        path = self._write_manifest([
            ("sidebar", "MATCH"),
            ("header", ""),           # unclassified
        ])
        args = _make_args(manifest_path=path)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 1, "Expected exit 1; stderr: {0}".format(err))
        data = json.loads(out)
        self.assertFalse(data["valid"])
        self.assertTrue(any("header" in e for e in data["errors"]),
                        "Expected 'header' in errors; got: {0}".format(data["errors"]))

    def test_V3_nonempty_gap_list_exit_1_names_token(self):
        # V3: non-empty gap-list → exit non-zero naming the token
        path = self._write_manifest(
            [("sidebar", "MATCH")],
            gap_list=["unknown-class (no CSS definition found)"],
        )
        args = _make_args(manifest_path=path)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["valid"])
        self.assertTrue(any("unknown-class" in e for e in data["errors"]),
                        "Expected gap token in errors; got: {0}".format(data["errors"]))

    def test_deviate_without_reason_fails(self):
        path = self._write_manifest([("accent", "DEVIATE", "")])
        args = _make_args(manifest_path=path)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["valid"])

    def test_missing_manifest_path_exit_2(self):
        args = _make_args(manifest_path=None)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 2)

    def test_nonexistent_manifest_file_exit_2(self):
        args = _make_args(manifest_path="/tmp/no-manifest-99999.json")
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 2)

    def test_combined_unclassified_and_gap_errors(self):
        path = self._write_manifest(
            [("el-a", ""), ("el-b", "MATCH")],
            gap_list=["stale-token (undefined)"],
        )
        args = _make_args(manifest_path=path)
        code, out, err = _capture_stdout(cmd_validate_manifest, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertTrue(any("el-a" in e for e in data["errors"]))
        self.assertTrue(any("stale-token" in e for e in data["errors"]))


# ---------------------------------------------------------------------------
# Tests: _manifest.py — extract_spacing_scale (V5, V6)
# ---------------------------------------------------------------------------


class TestExtractSpacingScale(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_V5_present_css_returns_available_true_and_scale(self):
        # V5: spacing extraction returns scale when styles.css present
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        self.assertTrue(result["available"])
        self.assertIsInstance(result["scale"], list)
        self.assertGreater(len(result["scale"]), 0)

    def test_V5_scale_contains_px_values(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        # Fixture has 16px, 8px, 4px, 0, 2rem, 1rem
        scale = result["scale"]
        self.assertTrue(any("px" in v or v == "0" for v in scale),
                        "Expected px values in scale; got: {0}".format(scale))

    def test_V5_scale_contains_rem_values(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        scale = result["scale"]
        self.assertTrue(any("rem" in v for v in scale),
                        "Expected rem values in scale; got: {0}".format(scale))

    def test_V5_non_spacing_property_not_in_scale(self):
        # border-radius: 4px appears in the fixture under .button — not a spacing prop
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        # The background-color and border-radius values should NOT pollute the scale
        # (this is a content check — scale values must look like length values, and
        #  we verify 4px ONLY from spacing props, not from border-radius which is
        #  also 4px in the fixture — the value may legitimately appear from padding
        #  so we just check that non-spacing properties don't corrupt the structure)
        self.assertIsInstance(result["scale"], list)
        for v in result["scale"]:
            # Every value in the scale must be a parseable length or "0"
            import re
            self.assertTrue(
                re.match(r"^\d*\.?\d+(px|rem|em|vh|vw|%|fr)$", v) or v == "0",
                "Unexpected scale value: {0}".format(v),
            )

    def test_V5_scale_is_sorted(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        scale = result["scale"]
        self.assertEqual(scale, sorted(scale, key=lambda v: (
            float(__import__("re").match(r"^(\d*\.?\d+)", v).group(1)) if __import__("re").match(r"^(\d*\.?\d+)", v) else 0.0,
            v,
        )), "Scale is not sorted; got: {0}".format(scale))

    def test_V5_source_path_returned(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        self.assertEqual(result["source"], css_path)

    def test_V6_absent_css_available_false(self):
        # V6: spacing extraction returns available=false when styles.css absent (OQ-6)
        absent_path = os.path.join(self._tmp, "nonexistent-styles.css")
        result = extract_spacing_scale(absent_path)
        self.assertFalse(result["available"])
        self.assertEqual(result["scale"], [])
        self.assertIsNone(result["source"])

    def test_V6_absent_css_exit_0(self):
        # Absent CSS must exit 0, not error
        absent_path = os.path.join(self._tmp, "nonexistent-styles.css")
        args = _make_args(css_path=absent_path)
        code, out, err = _capture_stdout(cmd_extract_spacing_scale, args)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["available"])

    def test_cmd_happy_path_exit_0_json(self):
        css_path = _write_styles_css(self._tmp)
        args = _make_args(css_path=css_path)
        code, out, err = _capture_stdout(cmd_extract_spacing_scale, args)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["available"])
        self.assertIn("scale", data)

    def test_cmd_missing_css_path_arg_exit_2(self):
        args = _make_args(css_path=None)
        code, out, err = _capture_stdout(cmd_extract_spacing_scale, args)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Tests: _cli.py — main dispatch
# ---------------------------------------------------------------------------


class TestCLIDispatch(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._html_path = _write_fixture(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_subcommand_exit_2(self):
        code, out, err = _capture_stdout(main, [])
        self.assertEqual(code, 2)

    def test_resolve_reference_via_main(self):
        code, out, err = _capture_stdout(main, ["resolve-reference", "--html-path", self._html_path])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("elements", data)

    def test_init_manifest_via_main(self):
        # First produce the resolve-reference JSON
        ref_result = resolve_reference(self._html_path)
        ref_json_path = os.path.join(self._tmp, "ref.json")
        with open(ref_json_path, "w") as fh:
            fh.write(json.dumps(ref_result))
        code, out, err = _capture_stdout(main, ["init-manifest", "--reference-json", ref_json_path])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("elements", data)

    def test_validate_manifest_via_main_clean(self):
        # Build a fully-classified manifest with no gap-list
        html = "<html><body><div data-ref='el1'></div></body></html>"
        html_path = os.path.join(self._tmp, "simple.html")
        with open(html_path, "w") as fh:
            fh.write(html)
        # Manually produce a manifest with no gap-list (no classes → no gaps)
        manifest = {
            "version": "1",
            "reference_html": html_path,
            "elements": [{"data_ref": "el1", "disposition": "MATCH"}],
            "gap_list": [],
        }
        manifest_path = os.path.join(self._tmp, "m.json")
        with open(manifest_path, "w") as fh:
            fh.write(json.dumps(manifest))
        code, out, err = _capture_stdout(main, ["validate-manifest", "--manifest-path", manifest_path])
        self.assertEqual(code, 0)

    def test_extract_spacing_scale_via_main_absent(self):
        code, out, err = _capture_stdout(
            main,
            ["extract-spacing-scale", "--css-path", "/tmp/no-such-styles-99999.css"],
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["available"])


# ---------------------------------------------------------------------------
# Tests: internal CSS parsing helpers
# ---------------------------------------------------------------------------


class TestCSSParsing(unittest.TestCase):
    """Tests for _parse_css_rules to verify the CSS parser handles edge cases."""

    def test_simple_rule_captured(self):
        css = ".foo { color: red; margin: 4px; }"
        rules, custom_props = _parse_css_rules(css)
        self.assertIn("color", rules.get(".foo", {}))
        self.assertIn("margin", rules.get(".foo", {}))

    def test_custom_property_definition_captured(self):
        css = ":root { --spacing-sm: 4px; --color-bg: #fff; }"
        rules, custom_props = _parse_css_rules(css)
        self.assertIn("--spacing-sm", custom_props)
        self.assertEqual(custom_props["--spacing-sm"], "4px")

    def test_custom_property_not_in_rules(self):
        css = ":root { --spacing-sm: 4px; color: red; }"
        rules, custom_props = _parse_css_rules(css)
        # --spacing-sm should NOT appear as a rule property
        root_decls = rules.get(":root", {})
        self.assertNotIn("--spacing-sm", root_decls)

    def test_multiple_rules(self):
        css = ".a { margin: 1px; } .b { padding: 2px; }"
        rules, custom_props = _parse_css_rules(css)
        self.assertIn("margin", rules.get(".a", {}))
        self.assertIn("padding", rules.get(".b", {}))

    def test_empty_css_yields_empty_dicts(self):
        rules, custom_props = _parse_css_rules("")
        self.assertEqual(rules, {})
        self.assertEqual(custom_props, {})

    def test_undefined_var_in_value_detected_via_gap_list(self):
        # An element uses an undefined var; the gap computation should catch it
        elements = [{"data_ref": "el", "classes": [], "inline_style": "color: var(--missing)"}]
        css = ".foo { border: 1px solid red; }"
        rules, custom_props = _parse_css_rules(css)
        gap = _compute_gap_list(elements, rules, custom_props)
        self.assertTrue(any("--missing" in g for g in gap))

    def test_F2_class_inside_at_media_is_not_a_false_gap(self):
        """F2: a class defined ONLY inside an @media block must be collected by
        _parse_css_rules so that a data-ref element using it does NOT create a
        false gap entry."""
        css = """
@media (max-width: 768px) {
  .media-only-class {
    margin: 8px;
    padding: 4px;
  }
}
"""
        rules, custom_props = _parse_css_rules(css)
        # .media-only-class must appear in the collected rules despite being inside @media
        keys = list(rules.keys())
        self.assertTrue(
            any("media-only-class" in k for k in keys),
            "F2: .media-only-class should be collected from @media block; "
            "got keys: {0}".format(keys),
        )
        # Verify that a data-ref element using this class has NO gap entry
        elements = [{"data_ref": "el-media", "classes": ["media-only-class"], "inline_style": ""}]
        gap = _compute_gap_list(elements, rules, custom_props)
        self.assertFalse(
            any("media-only-class" in g for g in gap),
            "F2: media-only-class should NOT be in gap_list; got: {0}".format(gap),
        )

    def test_F2_at_supports_class_collected(self):
        """F2: @supports blocks are also recursed into."""
        css = """
@supports (display: grid) {
  .grid-class { display: grid; gap: 8px; }
}
"""
        rules, custom_props = _parse_css_rules(css)
        keys = list(rules.keys())
        self.assertTrue(
            any("grid-class" in k for k in keys),
            "F2: .grid-class should be collected from @supports block; "
            "got keys: {0}".format(keys),
        )

    def test_F2_extract_rule_blocks_recurses_at_media(self):
        """Direct test of _extract_rule_blocks to confirm @media recursion."""
        css = "@media screen { .inner { color: red; } } .outer { margin: 4px; }"
        blocks = _extract_rule_blocks(css)
        selectors = [b[0] for b in blocks]
        self.assertTrue(
            any("inner" in s for s in selectors),
            "Expected .inner from @media body; got: {0}".format(selectors),
        )
        self.assertTrue(
            any("outer" in s for s in selectors),
            "Expected .outer at top level; got: {0}".format(selectors),
        )

    def test_F2_spacing_scale_from_at_media_block(self):
        """F2: spacing values defined inside @media blocks are collected by
        extract_spacing_scale (because _parse_spacing_from_css uses _extract_rule_blocks)."""
        import tempfile, os
        tmp = tempfile.mkdtemp()
        try:
            css = """
@media (max-width: 768px) {
  .responsive-container {
    margin: 12px;
    padding: 6px;
  }
}
"""
            css_path = os.path.join(tmp, "styles.css")
            with open(css_path, "w", encoding="utf-8") as fh:
                fh.write(css)
            from _design._manifest import extract_spacing_scale
            result = extract_spacing_scale(css_path)
            self.assertTrue(result["available"])
            self.assertIn("12px", result["scale"],
                          "F2: 12px from @media block should appear in scale; "
                          "got: {0}".format(result["scale"]))
            self.assertIn("6px", result["scale"],
                          "F2: 6px from @media block should appear in scale; "
                          "got: {0}".format(result["scale"]))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# End-to-end round-trip test (the "real producer → real consumer" discipline)
# ---------------------------------------------------------------------------


class TestEndToEndRoundTrip(unittest.TestCase):
    """Real producer round-trip: write fixture → resolve-reference → init-manifest
    → fill dispositions → validate-manifest → exit 0."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_full_pipeline_exit_0_after_classification(self):
        # 1. Write a simple reference.html with no undefined classes/tokens
        html = """<!DOCTYPE html><html>
<head><style>.panel { margin: 8px; }</style></head>
<body>
  <div data-ref="panel-root" class="panel">Content</div>
  <div data-ref="empty-slot" class="panel"><!-- empty --></div>
</body>
</html>"""
        html_path = os.path.join(self._tmp, "reference.html")
        with open(html_path, "w") as fh:
            fh.write(html)

        # 2. Produce resolve-reference output (real producer)
        ref_result = resolve_reference(html_path)

        # V4 check: elements are the two data-ref divs
        data_refs = [e["data_ref"] for e in ref_result["elements"]]
        self.assertIn("panel-root", data_refs)
        self.assertIn("empty-slot", data_refs)

        # gap_list must be empty (both elements use .panel which IS defined)
        self.assertEqual(
            ref_result["gap_list"], [],
            "Expected empty gap_list; got: {0}".format(ref_result["gap_list"]),
        )

        # 3. Produce skeleton manifest (real producer: init_manifest_from_reference)
        skeleton = init_manifest_from_reference(ref_result)
        errors_before = validate_manifest(skeleton)
        # Must fail (all unclassified)
        self.assertTrue(len(errors_before) > 0, "Expected errors before classification")

        # 4. Fill in dispositions
        skeleton.elements[0].disposition = DISPOSITION_MATCH
        skeleton.elements[1].disposition = DISPOSITION_DEFER_EMPTY

        # 5. Validate — must pass now (V1)
        errors_after = validate_manifest(skeleton)
        self.assertEqual(
            errors_after, [],
            "Expected no errors after classification; got: {0}".format(errors_after),
        )

    def test_pipeline_with_gap_list_blocks_until_resolved(self):
        # Fixture with an undefined class — gap_list must block validation
        html = """<!DOCTYPE html><html><body>
          <div data-ref="card" class="undefined-widget-class">Card</div>
        </body></html>"""
        html_path = os.path.join(self._tmp, "reference2.html")
        with open(html_path, "w") as fh:
            fh.write(html)

        ref_result = resolve_reference(html_path)
        self.assertTrue(len(ref_result["gap_list"]) > 0, "Expected non-empty gap_list")

        # V3: even if we classify the element, the gap_list blocks validation
        m = init_manifest_from_reference(ref_result)
        m.elements[0].disposition = DISPOSITION_MATCH

        errors = validate_manifest(m)
        self.assertTrue(len(errors) > 0, "Gap-list should still block validation")
        self.assertTrue(any("undefined-widget-class" in e for e in errors),
                        "Gap token should be named in error; got: {0}".format(errors))


# ---------------------------------------------------------------------------
# Tests: _source.py — parse_design_source
# ---------------------------------------------------------------------------

from _design._source import parse_design_source, cmd_check_design_source  # noqa: E402


class TestParseDesignSource(unittest.TestCase):
    """Unit tests for parse_design_source."""

    # --- scheme recognition ---

    def test_html_scheme_valid(self):
        ds = parse_design_source("html:design/reference.html")
        self.assertEqual(ds.scheme, "html")
        self.assertEqual(ds.target, "design/reference.html")
        self.assertEqual(ds.raw, "html:design/reference.html")
        self.assertTrue(ds.valid)

    def test_figma_scheme_valid(self):
        ds = parse_design_source("figma:https://figma.com/file/abc/Frame?node-id=1:2")
        self.assertEqual(ds.scheme, "figma")
        self.assertTrue(ds.valid)

    def test_figma_target_preserves_full_url(self):
        # The target must keep the full URL including https:// — split on FIRST colon only.
        url = "https://figma.com/file/abc/Frame?node-id=1:2"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.target, url)

    def test_screenshot_scheme_valid(self):
        ds = parse_design_source("screenshot:design/mock.png")
        self.assertEqual(ds.scheme, "screenshot")
        self.assertEqual(ds.target, "design/mock.png")
        self.assertTrue(ds.valid)

    # --- "none" cases ---

    def test_bare_none_lowercase(self):
        ds = parse_design_source("none")
        self.assertEqual(ds.scheme, "none")
        self.assertEqual(ds.target, "")
        self.assertTrue(ds.valid)

    def test_bare_none_uppercase(self):
        ds = parse_design_source("None")
        self.assertEqual(ds.scheme, "none")
        self.assertTrue(ds.valid)

    def test_bare_none_allcaps(self):
        ds = parse_design_source("NONE")
        self.assertEqual(ds.scheme, "none")
        self.assertTrue(ds.valid)

    def test_bare_none_mixed_case(self):
        ds = parse_design_source("NoNe")
        self.assertEqual(ds.scheme, "none")
        self.assertTrue(ds.valid)

    # --- empty / whitespace ---

    def test_empty_string_treated_as_none(self):
        ds = parse_design_source("")
        self.assertEqual(ds.scheme, "none")
        self.assertEqual(ds.target, "")
        self.assertTrue(ds.valid)

    def test_whitespace_only_treated_as_none(self):
        ds = parse_design_source("   ")
        self.assertEqual(ds.scheme, "none")
        self.assertTrue(ds.valid)

    def test_none_with_surrounding_whitespace(self):
        ds = parse_design_source("  none  ")
        self.assertEqual(ds.scheme, "none")
        self.assertTrue(ds.valid)

    # --- invalid / malformed ---

    def test_unknown_scheme_invalid(self):
        ds = parse_design_source("foo:bar")
        self.assertFalse(ds.valid)
        self.assertEqual(ds.raw, "foo:bar")

    def test_figma_empty_target_invalid(self):
        ds = parse_design_source("figma:")
        self.assertFalse(ds.valid)
        self.assertEqual(ds.scheme, "figma")
        self.assertEqual(ds.target, "")

    def test_screenshot_empty_target_invalid(self):
        ds = parse_design_source("screenshot:")
        self.assertFalse(ds.valid)
        self.assertEqual(ds.scheme, "screenshot")

    def test_html_empty_target_invalid(self):
        ds = parse_design_source("html:")
        self.assertFalse(ds.valid)
        self.assertEqual(ds.scheme, "html")

    def test_content_no_colon_not_none_invalid(self):
        # Has content but no colon and is not a "none" variant
        ds = parse_design_source("something-else")
        self.assertFalse(ds.valid)

    def test_raw_always_preserved_on_invalid(self):
        ds = parse_design_source("foo:bar")
        self.assertEqual(ds.raw, "foo:bar")

    def test_raw_preserved_on_valid(self):
        ds = parse_design_source("html:design/reference.html")
        self.assertEqual(ds.raw, "html:design/reference.html")

    # Finding 1: target strip
    def test_html_with_space_after_colon_target_stripped(self):
        # "html: design/reference.html" — space after colon must be stripped.
        ds = parse_design_source("html: design/reference.html")
        self.assertEqual(ds.scheme, "html")
        self.assertEqual(ds.target, "design/reference.html",
                         "target should be stripped; got: {0!r}".format(ds.target))
        self.assertTrue(ds.valid)

    def test_figma_target_preserves_full_url_after_strip(self):
        # strip() is idempotent on a URL with no surrounding whitespace
        url = "https://figma.com/file/abc/Frame?node-id=1:2"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.target, url,
                         "figma URL must be preserved verbatim after strip; got: {0!r}".format(ds.target))

    def test_figma_url_with_multiple_colons(self):
        # Multiple colons in figma URL — only first colon splits scheme/target.
        # The node-id=1:2 part has a colon inside the target.
        url = "https://figma.com/design/XYZ?node-id=0:1&t=abc"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.scheme, "figma")
        self.assertEqual(ds.target, url)
        self.assertTrue(ds.valid)

    # --- "none:" / "none:<x>" must be INVALID (SYNC contract) ---

    def test_none_with_empty_target_colon_is_invalid(self):
        # "none:" — colon present, scheme="none", target="" → invalid
        # SYNC contract: none is valid ONLY as a bare sentinel (no colon).
        ds = parse_design_source("none:")
        self.assertFalse(ds.valid,
                         "none: must be invalid (bare sentinel only, no colon allowed)")
        self.assertEqual(ds.raw, "none:")

    def test_none_with_nonempty_target_is_invalid(self):
        # "none:something" — colon present, scheme="none", target non-empty → invalid
        ds = parse_design_source("none:something")
        self.assertFalse(ds.valid,
                         "none:something must be invalid (bare sentinel only)")
        self.assertEqual(ds.raw, "none:something")

    def test_none_with_target_raw_preserved(self):
        # raw is always preserved regardless of validity
        ds = parse_design_source("none:foo")
        self.assertEqual(ds.raw, "none:foo")

    def test_bare_none_still_valid_case_insensitive(self):
        # Guard: bare "none" (no colon) stays valid across case variants
        for value in ("none", "None", "NONE", "NoNe"):
            ds = parse_design_source(value)
            self.assertTrue(ds.valid,
                            "Bare {0!r} must still be valid; got valid={1}".format(value, ds.valid))
            self.assertEqual(ds.scheme, "none")


# ---------------------------------------------------------------------------
# Tests: _source.py — cmd_check_design_source
# ---------------------------------------------------------------------------


class TestCmdCheckDesignSource(unittest.TestCase):
    """Integration tests for cmd_check_design_source using real temp files."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_spec(self, design_source_line=None, content=None):
        # type: (str, str) -> str
        """Write a spec.md to self._tmp and return its path.

        If content is provided it is used verbatim.
        Otherwise a minimal spec with (or without) a **Design source**: line
        is written.
        """
        if content is not None:
            text = content
        else:
            if design_source_line is not None:
                text = (
                    "# Test Feature\n\n"
                    "**Status**: Draft\n"
                    "**Design source**: {0}\n\n"
                    "## Section\n\nSome content.\n"
                ).format(design_source_line)
            else:
                text = (
                    "# Test Feature\n\n"
                    "**Status**: Draft\n\n"
                    "## Section\n\nSome content.\n"
                )
        spec_path = os.path.join(self._tmp, "spec.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return spec_path

    def _write_reference_html(self):
        # type: () -> str
        """Write a minimal design/reference.html and return its path."""
        design_dir = os.path.join(self._tmp, "design")
        os.makedirs(design_dir, exist_ok=True)
        ref_path = os.path.join(design_dir, "reference.html")
        with open(ref_path, "w", encoding="utf-8") as fh:
            fh.write("<html><body><!-- reference --></body></html>")
        return ref_path

    def _make_args(self, spec, workspace_root=None):
        class _NS:
            pass
        ns = _NS()
        ns.spec = spec
        ns.workspace_root = workspace_root if workspace_root is not None else self._tmp
        return ns

    # --- figma + no reference.html → WARN ---

    def test_figma_no_reference_warns_stderr_exit_0(self):
        spec = self._write_spec("figma:https://figma.com/file/abc/Frame?node-id=1:2")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0, "Expected exit 0; got {0}".format(code))
        self.assertIn("check-design-source", err)
        self.assertIn("figma", err)
        self.assertIn("design/reference.html", err)
        self.assertIn("absent", err)

    # --- screenshot + no reference.html → WARN ---

    def test_screenshot_no_reference_warns_stderr_exit_0(self):
        spec = self._write_spec("screenshot:design/mock.png")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("screenshot", err)
        self.assertIn("absent", err)

    # --- figma + reference.html present → silent ---

    def test_figma_with_reference_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("figma:https://figma.com/file/abc")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "", "Expected no stderr; got: {0!r}".format(err))

    # --- screenshot + reference.html present → silent ---

    def test_screenshot_with_reference_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("screenshot:design/mock.png")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- html: file present → silent ---

    def test_html_with_file_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("html:design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- html: file absent → WARN ---

    def test_html_file_absent_warns(self):
        spec = self._write_spec("html:design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("absent", err)

    # --- none → silent ---

    def test_none_is_silent(self):
        spec = self._write_spec("none")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- no **Design source**: line → silent (back-compat) ---

    def test_no_design_source_line_is_silent(self):
        spec = self._write_spec(design_source_line=None)
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- malformed value → WARN with malformed body ---

    def test_malformed_unknown_scheme_warns(self):
        spec = self._write_spec("foo:bar")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("malformed", err)
        self.assertIn("foo:bar", err)
        # remedy should mention valid shapes
        self.assertIn("html:", err)
        self.assertIn("figma:", err)

    # --- absent spec → silent (back-compat) ---

    def test_absent_spec_file_is_silent(self):
        args = self._make_args(spec=os.path.join(self._tmp, "nonexistent.md"))
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- no spec arg → silent ---

    def test_no_spec_arg_is_silent(self):
        class _NS:
            pass
        ns = _NS()
        ns.spec = None
        ns.workspace_root = self._tmp
        code, out, err = _capture_stdout(cmd_check_design_source, ns)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    # --- verify WARN body content for figma case ---

    def test_figma_warn_contains_declared_value(self):
        figma_url = "figma:https://figma.com/file/abc/Frame?node-id=1:2"
        spec = self._write_spec(figma_url)
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertIn("declared:", err)
        self.assertIn("figma:https://figma.com/file/abc/Frame?node-id=1:2", err)

    def test_figma_warn_contains_remedy(self):
        spec = self._write_spec("figma:https://figma.com/file/abc")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertIn("remedy:", err)
        self.assertIn("design/reference.html", err)

    # --- cli dispatch via main ---

    def test_check_design_source_via_main_none_silent(self):
        spec = self._write_spec("none")
        code, out, err = _capture_stdout(
            main, ["check-design-source", "--spec", spec, "--workspace-root", self._tmp]
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_check_design_source_via_main_figma_warns(self):
        spec = self._write_spec("figma:https://figma.com/file/abc")
        code, out, err = _capture_stdout(
            main, ["check-design-source", "--spec", spec, "--workspace-root", self._tmp]
        )
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)

    # --- Finding 1: html with space after colon, file present → silent ---

    def test_html_space_after_colon_file_present_silent(self):
        """Finding 1: 'html: design/reference.html' (space after colon) with the
        real file present must produce silent exit 0 — NOT a false WARN caused by
        looking for a path with a leading space."""
        # Create the actual file at workspace_root/design/reference.html
        design_dir = os.path.join(self._tmp, "design")
        os.makedirs(design_dir, exist_ok=True)
        ref_path = os.path.join(design_dir, "reference.html")
        with open(ref_path, "w", encoding="utf-8") as fh:
            fh.write("<html><body><!-- ref --></body></html>")
        # Spec declares "html: design/reference.html" — note the space after colon
        spec = self._write_spec("html: design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "",
                         "Expected silent exit; got stderr: {0!r}".format(err))

    # --- Finding 2: html with custom target → WARN names the actual target ---

    def test_html_custom_target_absent_warn_names_actual_target(self):
        """Finding 2: 'html:design/mockup.html' with the file absent must emit a
        WARN whose absent-file line and remedy 'create' instruction name
        'design/mockup.html', NOT the hardcoded 'design/reference.html'.

        The remedy may still mention design/reference.html in an informational
        clause explaining what plan-40 requires — that is correct and expected.
        What must be absent is the hardcoded absent-file line
        '  - design/reference.html: absent' and a create-instruction that names
        reference.html when the user declared mockup.html.
        """
        spec = self._write_spec("html:design/mockup.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("absent", err)
        # The absent-file bullet must name the actual declared target
        self.assertIn("design/mockup.html: absent", err,
                      "WARN absent-file line must name the declared target; got: {0!r}".format(err))
        # The old bug: the absent-file bullet hardcoded design/reference.html.
        # That specific pattern must NOT appear.
        self.assertNotIn("design/reference.html: absent", err,
                         "WARN absent-file line must NOT hardcode design/reference.html; "
                         "got: {0!r}".format(err))
        # The remedy 'create' instruction must name the actual declared target
        self.assertIn("create design/mockup.html", err,
                      "Remedy must say 'create design/mockup.html'; got: {0!r}".format(err))

    # --- spec with Design source line using \s* bleed edge case ---

    # --- "none:" is malformed (SYNC contract) — must take the WARN path ---

    def test_none_colon_bare_malformed_warns_stderr_exit_0(self):
        """'none:' is malformed (colon present, but none is only valid as bare
        sentinel).  cmd_check_design_source must emit a malformed WARN on stderr
        and exit 0 (non-blocking), NOT silently pass like the valid bare 'none'."""
        spec = self._write_spec("none:")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0, "Expected non-blocking exit 0; got {0}".format(code))
        self.assertIn("malformed", err,
                      "Expected malformed WARN in stderr; got: {0!r}".format(err))
        self.assertIn("none:", err,
                      "Expected raw value 'none:' in WARN message; got: {0!r}".format(err))

    def test_none_colon_something_malformed_warns_stderr_exit_0(self):
        """'none:something' is malformed — same WARN path as 'none:'."""
        spec = self._write_spec("none:something")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("malformed", err,
                      "Expected malformed WARN; got: {0!r}".format(err))

    def test_bare_none_remains_silent(self):
        """Bare 'none' (no colon) must remain silent (regression guard)."""
        spec = self._write_spec("none")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "",
                         "Bare none must be silent; got stderr: {0!r}".format(err))

    def test_design_source_regex_does_not_bleed_across_blank_line(self):
        # A malformed spec where **Design source**: is followed by a blank line
        # then a value on the next non-empty line.  The regex must NOT capture
        # the value from the next line ([ \t]* horizontal-only, not \s*).
        content = (
            "**Status**: Draft\n"
            "**Design source**:\n"   # blank value on same line (after colon)
            "\n"
            "figma:https://figma.com/file/abc\n"
        )
        spec = self._write_spec(content=content)
        args = self._make_args(spec)
        # The **Design source**: line has an empty value → treated as "none" → silent
        # (the regex captures the group after **: [ \t]* — if nothing follows on
        #  the same line, the MULTILINE $ matches end-of-line and group(1) won't
        #  contain the next line's figma URL)
        # NOTE: if the regex has no content after [ \t]*, it WON'T match because
        # (.+) requires at least one char — so the whole pattern won't match and
        # we fall through to the "no Design source line" → silent path.
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        # Must NOT emit a figma warn (the figma URL is on the next line, not captured)
        if err:
            self.assertNotIn("figma", err,
                             "Regex bled across blank line into next-line figma URL; err={0!r}".format(err))


if __name__ == "__main__":
    unittest.main(verbosity=2)
