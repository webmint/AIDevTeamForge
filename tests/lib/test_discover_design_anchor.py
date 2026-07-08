"""Tests for discover_helper set-scope-design-anchor + its finalize-handoff
carry (plan 53 Phase 1 — design intent as a first-class pipeline input).

Covers:
  - set-scope-design-anchor persists {kind, file, selectors} into
    discover-scope.json (memo.design_anchor.value).
  - parse_design_source reuse: html:<path> -> kind="html"; figma:<url> ->
    kind="figma"; an invalid --value (unknown scheme, malformed) exits 2
    and does NOT persist.
  - Malformed --selectors (bad JSON, non-list, non-string element) exits 2
    and does NOT persist.
  - A captured anchor round-trips through the REAL finalize-handoff
    producer -> the emitted handoff.json carries spec_seeds.design_anchor
    with the captured values; re-reading it reconstructs the DesignAnchor
    dataclass.
  - No captured anchor -> finalize-handoff still succeeds, emitting the
    empty default anchor (an anchor is optional, plan 53 D3/D5).

Subprocess pattern (matches test_discover_helper.py): each test runs in its
own tempfile.TemporaryDirectory, invoking the real discover_helper.py CLI.
Stdlib only. Python 3.8+.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "discover_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _discover import handoff_schema as dhs  # noqa: E402
from _specify._cmds_handoff import (  # noqa: E402
    _dict_to_dataclass,
    _inject_plan_seeds_internal_fields,
)


def _run(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_memo(devforge):
    return json.loads((Path(devforge) / "discover-scope.json").read_text())


# ---------------------------------------------------------------------------
# set-scope-design-anchor setter.
# ---------------------------------------------------------------------------


class TestSetScopeDesignAnchor(unittest.TestCase):
    def test_html_value_persists_kind_file_selectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", '[".fooBar"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(
                memo["design_anchor"]["value"],
                {"kind": "html", "file": "design/reference.html", "selectors": [".fooBar"]},
            )

    def test_figma_value_persists_kind_figma(self):
        """parse_design_source reuse: figma:<url> -> kind='figma'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "figma:https://figma.com/file/abc123",
                "--selectors", '[".card", ".badge"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(
                memo["design_anchor"]["value"],
                {
                    "kind": "figma",
                    "file": "https://figma.com/file/abc123",
                    "selectors": [".card", ".badge"],
                },
            )

    def test_empty_selectors_array_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", "[]",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["design_anchor"]["value"]["selectors"], [])

    def test_invalid_value_exits_2_and_does_not_persist(self):
        """Unknown scheme -> exit 2, no state mutation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            before = _read_memo(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "bogus:whatever",
                "--selectors", "[]",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("malformed --value", r.stderr)
            after = _read_memo(devforge)
            self.assertEqual(before, after)

    def test_malformed_none_colon_value_exits_2(self):
        """'none:<target>' is malformed per parse_design_source (SYNC contract)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "none:design/reference.html",
                "--selectors", "[]",
            ])
            self.assertEqual(r.returncode, 2)

    def test_bare_none_clears_kind_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "none",
                "--selectors", "[]",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(
                memo["design_anchor"]["value"],
                {"kind": "", "file": "", "selectors": []},
            )

    def test_malformed_selectors_json_exits_2_and_does_not_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            before = _read_memo(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", "not-json",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--selectors is not valid JSON", r.stderr)
            after = _read_memo(devforge)
            self.assertEqual(before, after)

    def test_selectors_not_a_list_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", '{"not": "a list"}',
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("must decode to a JSON array", r.stderr)

    def test_selectors_non_string_element_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", "[1, 2]",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("items must be strings", r.stderr)

    def test_re_set_overwrites_previous_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", '[".a"]',
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "figma:https://figma.com/x",
                "--selectors", '[".b"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(
                memo["design_anchor"]["value"],
                {"kind": "figma", "file": "https://figma.com/x", "selectors": [".b"]},
            )


# ---------------------------------------------------------------------------
# finalize-handoff carry — real producer round trip.
# ---------------------------------------------------------------------------


def _build_minimal_worth_pursuing_state(devforge):
    """Populate the minimal valid 'Worth pursuing' state finalize-handoff requires."""
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "New badge widget"])
    _run([
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value", "Build a badge widget matching design/reference.html .badge",
    ])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-07-06"])

    for dim, val in (
        ("functional-scope", "Render a badge widget"),
        ("users", "end users"),
        ("inputs-outputs", "props in, DOM out"),
        ("integration-points", "component library"),
        ("constraints", "must match design"),
        ("non-goals", "no animation"),
        ("success-criteria", "matches design pixel for pixel"),
        ("edge-cases", "long text truncation"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-scope-" + dim, "--value", val, "--state", "Clear",
        ])

    _run([
        "--devforge-dir", str(devforge), "set-design-option",
        "--name", "Badge component", "--shape", "single component",
        "--pros", json.dumps(["simple"]), "--cons", json.dumps(["none"]),
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-option",
        "--name", "Badge component", "--rationale", "simplest option",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-build-vs-buy",
        "--build", "build in-house", "--buy", "no vendor fits",
        "--recommendation", "Build", "--reasoning", "small scope",
    ])
    _run(["--devforge-dir", str(devforge), "set-overall-fit", "--value", "Good"])
    _run(["--devforge-dir", str(devforge), "set-effort-estimate", "--value", "Low"])
    _run(["--devforge-dir", str(devforge), "set-fit-rationale", "--value", "straightforward component"])
    _run([
        "--devforge-dir", str(devforge), "set-derisk-plan",
        "--items", json.dumps(["confirm design tokens exist"]),
    ])
    _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Worth pursuing"])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "A small badge widget matching the design reference.",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommendation",
        "--action", "Build the badge component", "--next", "Run /specify badge-widget",
    ])
    _run(["--devforge-dir", str(devforge), "set-next-step-text"])


class TestFinalizeHandoffCarriesDesignAnchor(unittest.TestCase):
    def test_captured_anchor_round_trips_through_real_producer(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_worth_pursuing_state(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-scope-design-anchor",
                "--value", "html:design/reference.html",
                "--selectors", '[".badge"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

            emit = Path(tmp) / "handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

            data = json.loads(emit.read_text())
            self.assertEqual(
                data["spec_seeds"]["design_anchor"],
                {"kind": "html", "file": "design/reference.html", "selectors": [".badge"]},
            )
            # Re-reading it reconstructs the DesignAnchor dataclass.
            da = dhs.DesignAnchor(**data["spec_seeds"]["design_anchor"])
            self.assertEqual(da.kind, "html")
            self.assertEqual(da.file, "design/reference.html")
            self.assertEqual(da.selectors, [".badge"])

    def test_no_captured_anchor_finalizes_with_empty_default(self):
        """An anchor is OPTIONAL (plan 53 D3/D5) -- finalize-handoff succeeds
        with the empty default when set-scope-design-anchor was never called.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_worth_pursuing_state(devforge)

            emit = Path(tmp) / "handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

            data = json.loads(emit.read_text())
            self.assertEqual(
                data["spec_seeds"]["design_anchor"],
                {"kind": "", "file": "", "selectors": []},
            )


# ---------------------------------------------------------------------------
# Back-compat via the REAL loader (_specify/_cmds_handoff.py:_dict_to_dataclass)
# -- the function /specify import-handoff actually uses to reconstruct a
# Handoff from a real handoff.json.  A DesignAnchor() constructor call alone
# only proves the dataclass default_factory works; it does NOT prove the
# recursive dict->dataclass loader defaults a MISSING design_anchor key the
# way a pre-plan-53 handoff.json (produced before this field existed) would.
# ---------------------------------------------------------------------------


class TestDesignAnchorBackCompatViaRealLoader(unittest.TestCase):
    def test_missing_design_anchor_key_defaults_via_real_loader(self):
        """Produce a real handoff, strip spec_seeds.design_anchor entirely
        (simulating a pre-plan-53 handoff.json that predates the field), then
        reconstruct via the real _dict_to_dataclass and assert an empty
        DesignAnchor -- proving the loader Phase 2 depends on actually works.

        _inject_plan_seeds_internal_fields is required first because the
        discover producer strips PlanSeeds' constructor-required
        _effort_estimate/_overall_fit/_derisk_count fields from the emitted
        JSON (schema-internal, not serialized) -- unrelated to design_anchor,
        but required for _dict_to_dataclass to construct PlanSeeds at all
        (mirrors _import_handoff_discover's own real-loader call sequence).
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_worth_pursuing_state(devforge)

            emit = Path(tmp) / "handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

            data = json.loads(emit.read_text())
            self.assertIn(
                "design_anchor", data["spec_seeds"],
                "current producer must emit design_anchor",
            )
            # Simulate a pre-plan-53 handoff.json: the key never existed.
            data["spec_seeds"].pop("design_anchor")

            _inject_plan_seeds_internal_fields(data)
            handoff = _dict_to_dataclass(dhs.Handoff, data)
            self.assertEqual(handoff.spec_seeds.design_anchor, dhs.DesignAnchor())


if __name__ == "__main__":
    unittest.main()
