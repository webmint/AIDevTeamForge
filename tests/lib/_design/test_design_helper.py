"""Tests for src/devforge/lib/_design/ — the design_helper subpackage.

Plan 53 Phase 3 reframes this subpackage's schema from the retired data-ref /
disposition-manifest shape (plan 40 Phase 2: ElementRecord, DISPOSITION_*,
ManifestContainer's element/gap-list shape, resolve-reference, init-manifest)
to the anchor + binding split (plan 53 D4/D7): the BINDING is
`{route, pairs: [{anchor_selector, built_testid}]}`, authored at /breakdown,
validated by `validate-binding` against `specs/[feature]/design-manifest.json`
(same on-disk filename as the retired manifest — plan 53 D4).

Real-fixture discipline note: there is no longer a mechanical PRODUCER of a
binding (resolve-reference / init-manifest are retired — a binding's route
and pairs are always human/LLM authored, since there is no walkable element
list to derive a skeleton from once data-ref HTML extraction is gone). So the
binding-schema tests below construct `Binding`/`BindingPair` directly via the
real dataclass constructors + round-trip through the real (de)serializers —
that IS the producer at this layer (there is no separate parser to round-trip
against, unlike resolve_reference's real-HTML-fixture discipline that applied
to the now-retired manifest flow).

extract_spacing_scale and check-design-source are UNCHANGED by plan 53 Phase 3
(kept per the plan) — their tests are carried over unmodified except for the
import path of the (relocated, still real) CSS-parsing utilities.

Coverage plan
-------------
_schema.py
  BindingPair validation (validate_pair):
    - valid pair → no errors
    - empty anchor_selector → error naming anchor_selector
    - whitespace-only anchor_selector → error
    - empty built_testid → error naming built_testid
    - control char in anchor_selector → error
    - control char in built_testid → error

  Binding validation (validate_binding):
    - route + 1 pair (container floor only) → no errors
    - route + 2 pairs (floor + opt-in precision pair) → no errors
    - missing route → error naming route
    - whitespace-only route → error
    - zero pairs → error
    - one pair missing anchor_selector → error naming pairs[0]
    - one pair missing built_testid → error naming pairs[1] (2nd pair)
    - empty binding (no route, no pairs) → BOTH route and pairs errors present
      (honesty invariant #3 — never a silent clean pass on omission)

  Serialization round-trip:
    - pair_to_dict / pair_from_dict → identical data
    - binding_to_dict / binding_from_dict → identical data (incl. version)
    - binding_to_json / binding_from_json → identical data
    - version field defaults to SCHEMA_VERSION on a fresh Binding

_css_parse.py (relocated from the retired _reference.py)
  _parse_css_rules / _extract_rule_blocks:
    - simple rule captured
    - custom property definition captured
    - custom property not treated as a regular rule property
    - multiple rules
    - empty CSS yields empty dicts
    - F2: class defined only inside @media is collected
    - F2: class defined only inside @supports is collected
    - F2: _extract_rule_blocks recurses into @media directly

_manifest.py
  cmd_validate_binding (CLI handler):
    - valid binding (route + 1 pair) → exit 0, valid=true
    - valid binding (route + 2 pairs) → exit 0
    - missing route → exit 1, valid=false, error names 'route'
    - zero pairs → exit 1, error mentions 'pairs'
    - pair missing anchor_selector → exit 1, error names 'pairs[0]' + 'anchor_selector'
    - pair missing built_testid → exit 1, error names 'built_testid'
    - empty binding → exit 1, BOTH route and pairs errors present
    - missing --binding-path: exit 2
    - non-existent file: exit 2
    - malformed JSON: exit 2

  extract_spacing_scale / cmd_extract_spacing_scale (V5, V6 — unchanged):
    - styles.css present with spacing rules → available=true, scale non-empty
    - scale contains px and rem values from the fixture
    - scale does NOT contain non-spacing properties (e.g. color)
    - styles.css absent → available=false, scale=[], source=None, exit 0
    - scale values are sorted (smallest first)

_cli.py / main entry:
  - no subcommand → exit 2
  - unknown subcommand → SystemExit (argparse rejects it)
  - resolve-reference / init-manifest are NOT recognized subcommands (retired)
  - validate-binding reachable via main([...])
  - extract-spacing-scale reachable via main([...])
  - check-design-source reachable via main([...])

_source.py — UNCHANGED (plan 53 Phase 3 does not touch this module):
  parse_design_source + cmd_check_design_source — full suite carried over.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — make _design importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._schema import (  # noqa: E402
    SCHEMA_VERSION,
    BindingPair,
    Binding,
    validate_pair,
    validate_binding,
    pair_to_dict,
    pair_from_dict,
    binding_to_dict,
    binding_from_dict,
    binding_to_json,
    binding_from_json,
    RetiredManifestSchemaError,
    BindingParseError,
)
from _design._css_parse import (  # noqa: E402
    _parse_css_rules,
    _extract_rule_blocks,
)
from _design._manifest import (  # noqa: E402
    cmd_validate_binding,
    extract_spacing_scale,
    cmd_extract_spacing_scale,
)
from _design._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

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


def _retired_disposition_manifest_dict():
    # type: () -> dict
    """A real plan-40 disposition-manifest dict, shaped exactly as the
    retired `ManifestContainer.manifest_to_dict` (git history commit
    6cc933c, `src/devforge/lib/_design/_schema.py` pre-plan-53) actually
    emitted -- {"version": "1", "reference_html": ..., "elements": [...],
    "gap_list": [...]}. This is NOT a hand-guessed shape: it is transcribed
    from the real retired producer's serializer output so the FIX 1
    regression test round-trips against the actual stale on-disk artifact
    a consumer install would have, not an invented approximation.
    """
    return {
        "version": "1",
        "reference_html": "design/reference.html",
        "elements": [
            {"data_ref": "hero", "disposition": "MATCH"},
            {"data_ref": "cta-button", "disposition": "DEVIATE",
             "deviate_reason": "new copy per stakeholder review"},
        ],
        "gap_list": [],
    }


def _make_args(**kwargs):
    """Build a simple namespace object."""
    class _NS:
        pass
    ns = _NS()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# Tests: _schema.py — BindingPair validation
# ---------------------------------------------------------------------------


class TestBindingPairValidation(unittest.TestCase):

    def test_valid_pair_no_errors(self):
        pair = BindingPair("[data-ref=hero]", "hero-container")
        self.assertEqual(validate_pair(pair, 0), [])

    def test_empty_anchor_selector_is_error(self):
        pair = BindingPair("", "hero-container")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("anchor_selector" in e for e in errors),
                        "Expected anchor_selector error; got: {0}".format(errors))
        self.assertTrue(any("pairs[0]" in e for e in errors),
                        "Expected pair index in error; got: {0}".format(errors))

    def test_whitespace_only_anchor_selector_is_error(self):
        pair = BindingPair("   ", "hero-container")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("anchor_selector" in e for e in errors))

    def test_empty_built_testid_is_error(self):
        pair = BindingPair("[data-ref=hero]", "")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("built_testid" in e for e in errors),
                        "Expected built_testid error; got: {0}".format(errors))

    def test_whitespace_only_built_testid_is_error(self):
        pair = BindingPair("[data-ref=hero]", "   ")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("built_testid" in e for e in errors))

    def test_control_char_in_anchor_selector(self):
        pair = BindingPair("hero\nselector", "hero-container")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("control" in e for e in errors),
                        "Expected control char error; got: {0}".format(errors))

    def test_control_char_in_built_testid(self):
        pair = BindingPair("[data-ref=hero]", "hero\x01container")
        errors = validate_pair(pair, 0)
        self.assertTrue(any("control" in e for e in errors),
                        "Expected control char error; got: {0}".format(errors))

    def test_pair_index_named_in_label(self):
        pair = BindingPair("", "")
        errors = validate_pair(pair, 3)
        self.assertTrue(any("pairs[3]" in e for e in errors),
                        "Expected pairs[3] in label; got: {0}".format(errors))


# ---------------------------------------------------------------------------
# Tests: _schema.py — Binding validation
# ---------------------------------------------------------------------------


class TestBindingValidation(unittest.TestCase):

    def test_route_plus_container_floor_pair_is_valid(self):
        b = Binding(
            route="/dashboard",
            pairs=[BindingPair("[data-ref=container]", "dashboard-root")],
        )
        self.assertEqual(validate_binding(b), [])

    def test_route_plus_floor_and_opt_in_pair_is_valid(self):
        b = Binding(
            route="/dashboard",
            pairs=[
                BindingPair("[data-ref=container]", "dashboard-root"),
                BindingPair(".title", "dashboard-title"),
            ],
        )
        self.assertEqual(validate_binding(b), [])

    def test_missing_route_is_error(self):
        b = Binding(route="", pairs=[BindingPair(".a", "a-testid")])
        errors = validate_binding(b)
        self.assertTrue(any("route" in e for e in errors),
                        "Expected route error; got: {0}".format(errors))

    def test_whitespace_only_route_is_error(self):
        b = Binding(route="   ", pairs=[BindingPair(".a", "a-testid")])
        errors = validate_binding(b)
        self.assertTrue(any("route" in e for e in errors))

    def test_zero_pairs_is_error(self):
        b = Binding(route="/dashboard", pairs=[])
        errors = validate_binding(b)
        self.assertTrue(any("pairs" in e for e in errors),
                        "Expected pairs error; got: {0}".format(errors))

    def test_pair_missing_anchor_selector_named(self):
        b = Binding(
            route="/dashboard",
            pairs=[BindingPair("", "dashboard-root")],
        )
        errors = validate_binding(b)
        self.assertTrue(any("pairs[0]" in e and "anchor_selector" in e for e in errors),
                        "Expected pairs[0] anchor_selector error; got: {0}".format(errors))

    def test_second_pair_missing_built_testid_named(self):
        b = Binding(
            route="/dashboard",
            pairs=[
                BindingPair("[data-ref=container]", "dashboard-root"),
                BindingPair(".title", ""),
            ],
        )
        errors = validate_binding(b)
        self.assertTrue(any("pairs[1]" in e and "built_testid" in e for e in errors),
                        "Expected pairs[1] built_testid error; got: {0}".format(errors))

    def test_empty_binding_fails_both_route_and_pairs(self):
        # Honesty invariant #3: an empty binding must never validate clean.
        b = Binding(route="", pairs=[])
        errors = validate_binding(b)
        self.assertTrue(any("route" in e for e in errors),
                        "Expected route error on empty binding; got: {0}".format(errors))
        self.assertTrue(any("pairs" in e for e in errors),
                        "Expected pairs error on empty binding; got: {0}".format(errors))
        self.assertGreaterEqual(len(errors), 2)


# ---------------------------------------------------------------------------
# Tests: _schema.py — serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization(unittest.TestCase):

    def test_pair_roundtrip_dict(self):
        orig = BindingPair("[data-ref=hero]", "hero-container")
        restored = pair_from_dict(pair_to_dict(orig))
        self.assertEqual(restored.anchor_selector, "[data-ref=hero]")
        self.assertEqual(restored.built_testid, "hero-container")

    def test_binding_roundtrip_dict(self):
        b = Binding(
            route="/dashboard",
            pairs=[
                BindingPair("[data-ref=container]", "dashboard-root"),
                BindingPair(".title", "dashboard-title"),
            ],
        )
        restored = binding_from_dict(binding_to_dict(b))
        self.assertEqual(restored.route, "/dashboard")
        self.assertEqual(len(restored.pairs), 2)
        self.assertEqual(restored.pairs[0].anchor_selector, "[data-ref=container]")
        self.assertEqual(restored.pairs[1].built_testid, "dashboard-title")

    def test_binding_roundtrip_json(self):
        b = Binding(
            route="/catalog",
            pairs=[BindingPair(".catalog-root", "catalog-container")],
        )
        restored = binding_from_json(binding_to_json(b))
        self.assertEqual(restored.route, "/catalog")
        self.assertEqual(restored.pairs[0].built_testid, "catalog-container")

    def test_version_defaults_to_schema_version(self):
        b = Binding(route="/x", pairs=[BindingPair(".a", "a")])
        self.assertEqual(b.version, SCHEMA_VERSION)
        d = binding_to_dict(b)
        self.assertEqual(d["version"], SCHEMA_VERSION)

    def test_binding_to_dict_shape(self):
        b = Binding(route="/x", pairs=[BindingPair(".a", "a-id")])
        d = binding_to_dict(b)
        self.assertEqual(set(d.keys()), {"version", "route", "pairs"})
        self.assertEqual(d["pairs"], [{"anchor_selector": ".a", "built_testid": "a-id"}])

    def test_binding_from_dict_missing_pairs_key_defaults_empty(self):
        restored = binding_from_dict({"route": "/x"})
        self.assertEqual(restored.pairs, [])

    def test_binding_from_dict_missing_route_key_defaults_empty_string(self):
        restored = binding_from_dict({"pairs": []})
        self.assertEqual(restored.route, "")


# ---------------------------------------------------------------------------
# Tests: _schema.py — binding_from_dict retired-schema detection (FIX 1)
# ---------------------------------------------------------------------------


class TestBindingFromDictRetiredSchema(unittest.TestCase):
    """A stale on-disk plan-40 disposition manifest must raise a
    DISTINGUISHABLE error from binding_from_dict, not silently coerce to an
    empty Binding that then fails validate_binding with the generic
    route/pairs message."""

    def test_real_old_format_dict_raises_retired_schema_error(self):
        d = _retired_disposition_manifest_dict()
        with self.assertRaises(RetiredManifestSchemaError) as ctx:
            binding_from_dict(d)
        msg = str(ctx.exception)
        self.assertIn("retired", msg)
        self.assertIn("elements/gap_list", msg)
        self.assertIn("route+pairs", msg)

    def test_elements_key_alone_triggers_retired_detection(self):
        # version absent, but "elements" key alone is sufficient.
        d = {"reference_html": "design/reference.html", "elements": []}
        with self.assertRaises(RetiredManifestSchemaError):
            binding_from_dict(d)

    def test_gap_list_key_alone_triggers_retired_detection(self):
        d = {"gap_list": ["some-unresolved-token"]}
        with self.assertRaises(RetiredManifestSchemaError):
            binding_from_dict(d)

    def test_version_1_alone_triggers_retired_detection(self):
        d = {"version": "1"}
        with self.assertRaises(RetiredManifestSchemaError):
            binding_from_dict(d)

    def test_new_but_incomplete_binding_stays_on_generic_path(self):
        """{"route": "", "pairs": []} is NOT retired-shaped -- it must
        deserialize normally and fail validate_binding's EXISTING generic
        route/pairs message, unchanged by FIX 1."""
        d = {"route": "", "pairs": []}
        restored = binding_from_dict(d)  # must NOT raise
        errors = validate_binding(restored)
        self.assertTrue(any("route" in e for e in errors))
        self.assertTrue(any("pairs" in e for e in errors))
        # And must NOT contain the retired-schema wording.
        joined = " ".join(errors)
        self.assertNotIn("retired", joined)

    def test_valid_binding_dict_still_deserializes(self):
        """A genuinely valid (current-schema) dict is unaffected by the
        retired-shape check."""
        d = {
            "version": SCHEMA_VERSION,
            "route": "/dashboard",
            "pairs": [{"anchor_selector": ".root", "built_testid": "dashboard-root"}],
        }
        restored = binding_from_dict(d)
        self.assertEqual(validate_binding(restored), [])


# ---------------------------------------------------------------------------
# Tests: _schema.py — binding_from_dict / pair_from_dict non-object-shape
# guard (FIX F2)
# ---------------------------------------------------------------------------


class TestBindingFromDictNonObjectShape(unittest.TestCase):
    """A binding (or a pairs entry within it) that is not a JSON object
    where one is required must raise a distinguishable BindingParseError,
    never an uncaught TypeError/AttributeError from a bare `.get()` call."""

    def test_null_top_level_raises_binding_parse_error(self):
        with self.assertRaises(BindingParseError) as ctx:
            binding_from_json("null")
        self.assertIn("JSON object", str(ctx.exception))

    def test_list_top_level_raises_binding_parse_error(self):
        with self.assertRaises(BindingParseError):
            binding_from_json("[1, 2, 3]")

    def test_string_top_level_raises_binding_parse_error(self):
        with self.assertRaises(BindingParseError):
            binding_from_json('"x"')

    def test_number_top_level_raises_binding_parse_error(self):
        with self.assertRaises(BindingParseError):
            binding_from_dict(42)

    def test_binding_parse_error_is_a_value_error(self):
        # Existing (OSError, ValueError) / (RetiredManifestSchemaError,
        # ValueError) catch sites depend on this.
        self.assertTrue(issubclass(BindingParseError, ValueError))

    def test_non_dict_pairs_entry_raises_binding_parse_error(self):
        d = {"route": "/x", "pairs": ["x"]}
        with self.assertRaises(BindingParseError) as ctx:
            binding_from_dict(d)
        self.assertIn("pairs entry", str(ctx.exception))

    def test_non_list_pairs_value_raises_binding_parse_error(self):
        d = {"route": "/x", "pairs": "not-a-list"}
        with self.assertRaises(BindingParseError):
            binding_from_dict(d)

    def test_pair_from_dict_non_dict_raises_binding_parse_error(self):
        with self.assertRaises(BindingParseError):
            pair_from_dict("not-a-dict")

    def test_null_top_level_checked_before_retired_shape_detection(self):
        # A None payload would crash `_is_retired_manifest_shape`'s
        # `"elements" in d` with a TypeError if the isinstance guard did not
        # run FIRST -- assert the raised error is the non-object one, not a
        # retired-schema false-positive or an uncaught TypeError.
        with self.assertRaises(BindingParseError):
            binding_from_dict(None)

    def test_valid_binding_dict_unaffected(self):
        """A genuinely valid dict still deserializes normally -- the new
        guard must not reject well-formed input."""
        d = {
            "version": SCHEMA_VERSION,
            "route": "/dashboard",
            "pairs": [{"anchor_selector": ".root", "built_testid": "dashboard-root"}],
        }
        restored = binding_from_dict(d)
        self.assertEqual(restored.route, "/dashboard")
        self.assertEqual(len(restored.pairs), 1)


# ---------------------------------------------------------------------------
# Tests: _css_parse.py — retained CSS parsing utilities
# ---------------------------------------------------------------------------


class TestCSSParse(unittest.TestCase):
    """Tests for _parse_css_rules / _extract_rule_blocks (relocated, plan 53 Phase 3)."""

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

    def test_F2_class_inside_at_media_is_collected(self):
        css = """
@media (max-width: 768px) {
  .media-only-class {
    margin: 8px;
    padding: 4px;
  }
}
"""
        rules, custom_props = _parse_css_rules(css)
        keys = list(rules.keys())
        self.assertTrue(
            any("media-only-class" in k for k in keys),
            "F2: .media-only-class should be collected from @media block; "
            "got keys: {0}".format(keys),
        )

    def test_F2_at_supports_class_collected(self):
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
        css = "@media screen { .inner { color: red; } } .outer { margin: 4px; }"
        blocks = _extract_rule_blocks(css)
        selectors = [b[0] for b in blocks]
        self.assertTrue(any("inner" in s for s in selectors),
                        "Expected .inner from @media body; got: {0}".format(selectors))
        self.assertTrue(any("outer" in s for s in selectors),
                        "Expected .outer at top level; got: {0}".format(selectors))


# ---------------------------------------------------------------------------
# Tests: _manifest.py — cmd_validate_binding CLI handler
# ---------------------------------------------------------------------------


class TestCmdValidateBinding(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_binding_file(self, binding):
        # type: (Binding) -> str
        """Write a real binding (via the real serializer) to a temp file."""
        path = os.path.join(self._tmp, "design-manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(binding))
        return path

    def test_valid_binding_one_pair_exit_0(self):
        b = Binding(route="/dashboard", pairs=[BindingPair(".root", "dashboard-root")])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 0, "Expected exit 0; stderr: {0}".format(err))
        data = json.loads(out)
        self.assertTrue(data["valid"])
        self.assertEqual(data["errors"], [])

    def test_valid_binding_two_pairs_exit_0(self):
        b = Binding(
            route="/dashboard",
            pairs=[
                BindingPair(".root", "dashboard-root"),
                BindingPair(".title", "dashboard-title"),
            ],
        )
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 0, "Expected exit 0; stderr: {0}".format(err))

    def test_missing_route_exit_1_names_route(self):
        b = Binding(route="", pairs=[BindingPair(".root", "dashboard-root")])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 1, "Expected exit 1; stderr: {0}".format(err))
        data = json.loads(out)
        self.assertFalse(data["valid"])
        self.assertTrue(any("route" in e for e in data["errors"]))

    def test_zero_pairs_exit_1(self):
        b = Binding(route="/dashboard", pairs=[])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["valid"])
        self.assertTrue(any("pairs" in e for e in data["errors"]))

    def test_pair_missing_anchor_selector_exit_1(self):
        b = Binding(route="/dashboard", pairs=[BindingPair("", "dashboard-root")])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertTrue(any("pairs[0]" in e and "anchor_selector" in e for e in data["errors"]))

    def test_pair_missing_built_testid_exit_1(self):
        b = Binding(route="/dashboard", pairs=[BindingPair(".root", "")])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertTrue(any("built_testid" in e for e in data["errors"]))

    def test_empty_binding_exit_1_both_errors(self):
        b = Binding(route="", pairs=[])
        path = self._write_binding_file(b)
        args = _make_args(binding_path=path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertTrue(any("route" in e for e in data["errors"]))
        self.assertTrue(any("pairs" in e for e in data["errors"]))

    def test_missing_binding_path_arg_exit_2(self):
        args = _make_args(binding_path=None)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 2)

    def test_nonexistent_file_exit_2(self):
        args = _make_args(binding_path="/tmp/no-such-binding-99999.json")
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 2)

    def test_malformed_json_exit_2(self):
        bad_path = os.path.join(self._tmp, "bad.json")
        with open(bad_path, "w") as fh:
            fh.write("{invalid json")
        args = _make_args(binding_path=bad_path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 2)

    def test_retired_disposition_manifest_exit_2_distinguishable_message(self):
        """FIX 1: a stale plan-40 disposition-manifest file must exit
        non-zero with the DISTINGUISHABLE retired-schema message, not the
        generic 'route must be non-empty' / 'pairs must contain at least
        one pair' message."""
        old_path = os.path.join(self._tmp, "design-manifest.json")
        with open(old_path, "w", encoding="utf-8") as fh:
            json.dump(_retired_disposition_manifest_dict(), fh)
        args = _make_args(binding_path=old_path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertNotEqual(code, 0, "Expected non-zero exit; stdout: {0}".format(out))
        self.assertIn("retired", err)
        self.assertIn("elements/gap_list", err)
        self.assertNotIn("route: must be non-empty", err)
        self.assertNotIn("pairs: must contain at least one pair", err)

    def test_null_top_level_binding_exit_2_not_traceback(self):
        """FIX F2: a binding file whose JSON top level is `null` must exit 2
        via cmd_validate_binding's (OSError, ValueError) catch, not crash
        with an uncaught TypeError."""
        null_path = os.path.join(self._tmp, "design-manifest.json")
        with open(null_path, "w", encoding="utf-8") as fh:
            fh.write("null")
        args = _make_args(binding_path=null_path)
        code, out, err = _capture_stdout(cmd_validate_binding, args)
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)


# ---------------------------------------------------------------------------
# Tests: _manifest.py — extract_spacing_scale (V5, V6 — unchanged by plan 53)
# ---------------------------------------------------------------------------


class TestExtractSpacingScale(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_V5_present_css_returns_available_true_and_scale(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        self.assertTrue(result["available"])
        self.assertIsInstance(result["scale"], list)
        self.assertGreater(len(result["scale"]), 0)

    def test_V5_scale_contains_px_values(self):
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
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
        css_path = _write_styles_css(self._tmp)
        result = extract_spacing_scale(css_path)
        self.assertIsInstance(result["scale"], list)
        for v in result["scale"]:
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
        absent_path = os.path.join(self._tmp, "nonexistent-styles.css")
        result = extract_spacing_scale(absent_path)
        self.assertFalse(result["available"])
        self.assertEqual(result["scale"], [])
        self.assertIsNone(result["source"])

    def test_V6_absent_css_exit_0(self):
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

    def test_F2_spacing_scale_from_at_media_block(self):
        """F2: spacing values defined inside @media blocks are collected."""
        css = """
@media (max-width: 768px) {
  .responsive-container {
    margin: 12px;
    padding: 6px;
  }
}
"""
        css_path = os.path.join(self._tmp, "styles.css")
        with open(css_path, "w", encoding="utf-8") as fh:
            fh.write(css)
        result = extract_spacing_scale(css_path)
        self.assertTrue(result["available"])
        self.assertIn("12px", result["scale"],
                      "F2: 12px from @media block should appear in scale; "
                      "got: {0}".format(result["scale"]))
        self.assertIn("6px", result["scale"],
                      "F2: 6px from @media block should appear in scale; "
                      "got: {0}".format(result["scale"]))


# ---------------------------------------------------------------------------
# Tests: _cli.py — main dispatch
# ---------------------------------------------------------------------------


class TestCLIDispatch(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_subcommand_exit_2(self):
        code, out, err = _capture_stdout(main, [])
        self.assertEqual(code, 2)

    def test_validate_binding_via_main(self):
        b = Binding(route="/x", pairs=[BindingPair(".a", "a-id")])
        path = os.path.join(self._tmp, "design-manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(b))
        code, out, err = _capture_stdout(
            main, ["validate-binding", "--binding-path", path]
        )
        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertTrue(data["valid"])

    def test_extract_spacing_scale_via_main_absent(self):
        code, out, err = _capture_stdout(
            main,
            ["extract-spacing-scale", "--css-path", "/tmp/no-such-styles-99999.css"],
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["available"])

    def test_resolve_reference_is_retired_not_a_subcommand(self):
        """Plan 53 Phase 3: resolve-reference is retired; argparse must reject it."""
        with self.assertRaises(SystemExit):
            main(["resolve-reference", "--html-path", "whatever.html"])

    def test_init_manifest_is_retired_not_a_subcommand(self):
        """Plan 53 Phase 3: init-manifest is retired; argparse must reject it."""
        with self.assertRaises(SystemExit):
            main(["init-manifest", "--reference-json", "whatever.json"])

    def test_validate_manifest_verb_name_is_retired(self):
        """The OLD verb name 'validate-manifest' no longer exists — renamed
        to 'validate-binding' (plan 53 Phase 3)."""
        with self.assertRaises(SystemExit):
            main(["validate-manifest", "--manifest-path", "whatever.json"])


# ---------------------------------------------------------------------------
# Tests: _source.py — parse_design_source (UNCHANGED by plan 53 Phase 3)
# ---------------------------------------------------------------------------

from _design._source import parse_design_source, cmd_check_design_source  # noqa: E402


class TestParseDesignSource(unittest.TestCase):
    """Unit tests for parse_design_source."""

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
        url = "https://figma.com/file/abc/Frame?node-id=1:2"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.target, url)

    def test_screenshot_scheme_valid(self):
        ds = parse_design_source("screenshot:design/mock.png")
        self.assertEqual(ds.scheme, "screenshot")
        self.assertEqual(ds.target, "design/mock.png")
        self.assertTrue(ds.valid)

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
        ds = parse_design_source("something-else")
        self.assertFalse(ds.valid)

    def test_raw_always_preserved_on_invalid(self):
        ds = parse_design_source("foo:bar")
        self.assertEqual(ds.raw, "foo:bar")

    def test_raw_preserved_on_valid(self):
        ds = parse_design_source("html:design/reference.html")
        self.assertEqual(ds.raw, "html:design/reference.html")

    def test_html_with_space_after_colon_target_stripped(self):
        ds = parse_design_source("html: design/reference.html")
        self.assertEqual(ds.scheme, "html")
        self.assertEqual(ds.target, "design/reference.html",
                         "target should be stripped; got: {0!r}".format(ds.target))
        self.assertTrue(ds.valid)

    def test_figma_target_preserves_full_url_after_strip(self):
        url = "https://figma.com/file/abc/Frame?node-id=1:2"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.target, url,
                         "figma URL must be preserved verbatim after strip; got: {0!r}".format(ds.target))

    def test_figma_url_with_multiple_colons(self):
        url = "https://figma.com/design/XYZ?node-id=0:1&t=abc"
        ds = parse_design_source("figma:" + url)
        self.assertEqual(ds.scheme, "figma")
        self.assertEqual(ds.target, url)
        self.assertTrue(ds.valid)

    def test_none_with_empty_target_colon_is_invalid(self):
        ds = parse_design_source("none:")
        self.assertFalse(ds.valid,
                         "none: must be invalid (bare sentinel only, no colon allowed)")
        self.assertEqual(ds.raw, "none:")

    def test_none_with_nonempty_target_is_invalid(self):
        ds = parse_design_source("none:something")
        self.assertFalse(ds.valid,
                         "none:something must be invalid (bare sentinel only)")
        self.assertEqual(ds.raw, "none:something")

    def test_none_with_target_raw_preserved(self):
        ds = parse_design_source("none:foo")
        self.assertEqual(ds.raw, "none:foo")

    def test_bare_none_still_valid_case_insensitive(self):
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

    def test_figma_no_reference_warns_stderr_exit_0(self):
        spec = self._write_spec("figma:https://figma.com/file/abc/Frame?node-id=1:2")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0, "Expected exit 0; got {0}".format(code))
        self.assertIn("check-design-source", err)
        self.assertIn("figma", err)
        self.assertIn("design/reference.html", err)
        self.assertIn("absent", err)

    def test_screenshot_no_reference_warns_stderr_exit_0(self):
        spec = self._write_spec("screenshot:design/mock.png")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("screenshot", err)
        self.assertIn("absent", err)

    def test_figma_with_reference_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("figma:https://figma.com/file/abc")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "", "Expected no stderr; got: {0!r}".format(err))

    def test_screenshot_with_reference_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("screenshot:design/mock.png")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_html_with_file_present_silent(self):
        self._write_reference_html()
        spec = self._write_spec("html:design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_html_file_absent_warns(self):
        spec = self._write_spec("html:design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("absent", err)

    def test_none_is_silent(self):
        spec = self._write_spec("none")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_no_design_source_line_is_silent(self):
        spec = self._write_spec(design_source_line=None)
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_malformed_unknown_scheme_warns(self):
        spec = self._write_spec("foo:bar")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("malformed", err)
        self.assertIn("foo:bar", err)
        self.assertIn("html:", err)
        self.assertIn("figma:", err)

    def test_absent_spec_file_is_silent(self):
        args = self._make_args(spec=os.path.join(self._tmp, "nonexistent.md"))
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_no_spec_arg_is_silent(self):
        class _NS:
            pass
        ns = _NS()
        ns.spec = None
        ns.workspace_root = self._tmp
        code, out, err = _capture_stdout(cmd_check_design_source, ns)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

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

    def test_html_space_after_colon_file_present_silent(self):
        design_dir = os.path.join(self._tmp, "design")
        os.makedirs(design_dir, exist_ok=True)
        ref_path = os.path.join(design_dir, "reference.html")
        with open(ref_path, "w", encoding="utf-8") as fh:
            fh.write("<html><body><!-- ref --></body></html>")
        spec = self._write_spec("html: design/reference.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "",
                         "Expected silent exit; got stderr: {0!r}".format(err))

    def test_html_custom_target_absent_warn_names_actual_target(self):
        spec = self._write_spec("html:design/mockup.html")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("check-design-source", err)
        self.assertIn("absent", err)
        self.assertIn("design/mockup.html: absent", err,
                      "WARN absent-file line must name the declared target; got: {0!r}".format(err))
        self.assertNotIn("design/reference.html: absent", err,
                         "WARN absent-file line must NOT hardcode design/reference.html; "
                         "got: {0!r}".format(err))
        self.assertIn("create design/mockup.html", err,
                      "Remedy must say 'create design/mockup.html'; got: {0!r}".format(err))

    def test_none_colon_bare_malformed_warns_stderr_exit_0(self):
        spec = self._write_spec("none:")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0, "Expected non-blocking exit 0; got {0}".format(code))
        self.assertIn("malformed", err,
                      "Expected malformed WARN in stderr; got: {0!r}".format(err))
        self.assertIn("none:", err,
                      "Expected raw value 'none:' in WARN message; got: {0!r}".format(err))

    def test_none_colon_something_malformed_warns_stderr_exit_0(self):
        spec = self._write_spec("none:something")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertIn("malformed", err,
                      "Expected malformed WARN; got: {0!r}".format(err))

    def test_bare_none_remains_silent(self):
        spec = self._write_spec("none")
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        self.assertEqual(err, "",
                         "Bare none must be silent; got stderr: {0!r}".format(err))

    def test_design_source_regex_does_not_bleed_across_blank_line(self):
        content = (
            "**Status**: Draft\n"
            "**Design source**:\n"
            "\n"
            "figma:https://figma.com/file/abc\n"
        )
        spec = self._write_spec(content=content)
        args = self._make_args(spec)
        code, out, err = _capture_stdout(cmd_check_design_source, args)
        self.assertEqual(code, 0)
        if err:
            self.assertNotIn("figma", err,
                             "Regex bled across blank line into next-line figma URL; err={0!r}".format(err))


if __name__ == "__main__":
    unittest.main(verbosity=2)
