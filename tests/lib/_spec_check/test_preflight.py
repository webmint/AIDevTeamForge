"""Tests for src/devforge/lib/_spec_check/_preflight.py.

Coverage:
  check_z3     — available path (real z3 import attempt) and forced-absent
                 path via an injected importer; message content check.
  preflight    — all-files-absent defaults, each setup-chain artefact missing
                 individually, sentinel constitution, real populated
                 constitution, feature-gate checks (spec.md ONLY -- NO
                 plan.md requirement, unlike /grill), feature_dir=None mode,
                 z3 present/absent wiring, and the all-green pass.

Real-producer round-trip: fixtures are written to temp dirs reproducing the
actual filesystem layout the real /init-forge, /configure, /generate-docs,
and /constitute commands produce. No hand-faked strings for the sentinel
check -- uses the exact sentinel strings exported from
_spec_check._preflight._UNPOPULATED_SENTINELS.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _spec_check._preflight import (  # noqa: E402
    _SETUP_CHAIN_ARTEFACTS,
    _UNPOPULATED_SENTINELS,
    Z3_INSTALL_MESSAGE,
    check_z3,
    preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(td, rel_path, content):
    # type: (str, str, str) -> str
    full = os.path.join(td, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _make_full_install(td):
    # type: (str) -> None
    """Write a minimal but complete 4-command setup-chain install into td."""
    _write(td, "constitution.md",
           "# Architecture Rules\n\n1. Use dependency injection.\n2. No globals.\n")
    _write(td, "CLAUDE.md",
           "# CLAUDE.md\n\n"
           "- **Name**: TestProject\n"
           "- **Type**: web-app\n")
    _write(td, ".devforge/project-config.json",
           json.dumps({"configure_version": 1}))
    _write(td, ".devforge/index.json",
           json.dumps({"version": 1, "packages": []}))


def _make_feature(td, slug="007-catalog-filters", with_spec=True, with_plan=False):
    # type: (str, str, bool, bool) -> str
    feature_dir = os.path.join(td, "specs", slug)
    os.makedirs(feature_dir, exist_ok=True)
    if with_spec:
        _write(feature_dir, "spec.md", "# Spec\n\n**Status**: Draft\n")
    if with_plan:
        _write(feature_dir, "plan.md", "# Plan\n\n**Status**: Approved\n")
    return feature_dir


def _raising_importer():
    raise ImportError("no module named z3")


def _ok_importer():
    return None


# ---------------------------------------------------------------------------
# check_z3
# ---------------------------------------------------------------------------

class TestCheckZ3(unittest.TestCase):

    def test_real_import_attempt_returns_bool_and_str(self):
        # Whatever the real environment has, the shape must be right.
        available, message = check_z3()
        self.assertIsInstance(available, bool)
        self.assertIsInstance(message, str)
        if available:
            self.assertEqual(message, "")
        else:
            self.assertEqual(message, Z3_INSTALL_MESSAGE)

    def test_forced_absent_via_injected_importer(self):
        available, message = check_z3(importer=_raising_importer)
        self.assertFalse(available)
        self.assertEqual(message, Z3_INSTALL_MESSAGE)

    def test_forced_present_via_injected_importer(self):
        available, message = check_z3(importer=_ok_importer)
        self.assertTrue(available)
        self.assertEqual(message, "")

    def test_install_message_mentions_pip_install(self):
        self.assertIn("pip install z3-solver", Z3_INSTALL_MESSAGE)

    def test_install_message_does_not_call_spec_check_opt_in(self):
        """/devforge:spec-check is run-mandatory before /devforge:plan (a
        gate a user being BLOCKED for skipping must not then be told is
        opt-in) -- only the z3-solver package itself is optional/
        not-bundled, which the message states without the word 'opt-in'."""
        self.assertNotIn("opt-in", Z3_INSTALL_MESSAGE)
        self.assertIn("not installed by default", Z3_INSTALL_MESSAGE)
        self.assertIn("/devforge:plan requires a fresh spec-check report",
                       Z3_INSTALL_MESSAGE)

    def test_install_message_mentions_spec_check(self):
        self.assertIn("/devforge:spec-check", Z3_INSTALL_MESSAGE)


# ---------------------------------------------------------------------------
# preflight — all-absent defaults
# ---------------------------------------------------------------------------

class TestPreflightAllAbsent(unittest.TestCase):

    def test_empty_workspace_all_false(self):
        with tempfile.TemporaryDirectory() as td:
            result = preflight(workspace_root=td, z3_importer=_raising_importer)
            self.assertFalse(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])
            self.assertFalse(result["setup_chain_ok"])
            self.assertEqual(
                set(result["missing_artefacts"]),
                {"/devforge:constitute", "/devforge:init-forge", "/devforge:configure", "/devforge:generate-docs"},
            )
            self.assertFalse(result["z3_available"])
            self.assertEqual(result["z3_message"], Z3_INSTALL_MESSAGE)

    def test_feature_dir_none_gate_not_applicable(self):
        with tempfile.TemporaryDirectory() as td:
            result = preflight(workspace_root=td, feature_dir=None)
            self.assertFalse(result["spec_present"])
            self.assertFalse(result["feature_gate_ok"])
            self.assertEqual(result["missing_feature_artefacts"], [])

    def test_workspace_root_default_is_cwd_relative(self):
        # No assertion on content -- just confirm it does not raise when
        # workspace_root is omitted (defaults to ".").
        result = preflight()
        self.assertIsInstance(result, dict)
        self.assertIn("setup_chain_ok", result)


# ---------------------------------------------------------------------------
# preflight — each setup-chain artefact missing individually
# ---------------------------------------------------------------------------

class TestPreflightSetupChainIndividual(unittest.TestCase):

    def test_missing_constitution_only(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            os.remove(os.path.join(td, "constitution.md"))
            result = preflight(workspace_root=td)
            self.assertFalse(result["setup_chain_ok"])
            self.assertEqual(result["missing_artefacts"], ["/devforge:constitute"])
            self.assertFalse(result["constitution_present"])

    def test_missing_claude_md_only(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            os.remove(os.path.join(td, "CLAUDE.md"))
            result = preflight(workspace_root=td)
            self.assertFalse(result["setup_chain_ok"])
            self.assertEqual(result["missing_artefacts"], ["/devforge:init-forge"])

    def test_missing_project_config_only(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            os.remove(os.path.join(td, ".devforge", "project-config.json"))
            result = preflight(workspace_root=td)
            self.assertFalse(result["setup_chain_ok"])
            self.assertEqual(result["missing_artefacts"], ["/devforge:configure"])

    def test_missing_index_json_only(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            os.remove(os.path.join(td, ".devforge", "index.json"))
            result = preflight(workspace_root=td)
            self.assertFalse(result["setup_chain_ok"])
            self.assertEqual(result["missing_artefacts"], ["/devforge:generate-docs"])

    def test_setup_chain_artefacts_are_the_expected_four(self):
        labels = [label for _rel, label in _SETUP_CHAIN_ARTEFACTS]
        self.assertEqual(
            labels, ["/devforge:constitute", "/devforge:init-forge", "/devforge:configure", "/devforge:generate-docs"]
        )


# ---------------------------------------------------------------------------
# preflight — constitution sentinel / populated
# ---------------------------------------------------------------------------

class TestPreflightConstitutionSentinel(unittest.TestCase):

    def test_unpopulated_sentinel_body_placeholder(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "constitution.md", "# Constitution\n\n{{CONSTITUTION_BODY}}\n")
            result = preflight(workspace_root=td)
            self.assertTrue(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])

    def test_unpopulated_sentinel_run_constitute(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "constitution.md", "Run `/constitute` to populate this file.\n")
            result = preflight(workspace_root=td)
            self.assertFalse(result["constitution_populated"])

    def test_unpopulated_sentinel_run_to_populate(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "constitution.md", "Run /constitute to populate the rules.\n")
            result = preflight(workspace_root=td)
            self.assertFalse(result["constitution_populated"])

    def test_unpopulated_sentinel_legacy_no_slash_form(self):
        # Pre-namespace stub literal (no slash) -- the form every existing
        # consumer install actually carries.
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "constitution.md", "Run constitute to populate the rules.\n")
            result = preflight(workspace_root=td)
            self.assertFalse(result["constitution_populated"])

    def test_unpopulated_sentinel_devforge_namespaced_form(self):
        # Post-namespace stub literal (current, plan 63 Phase 4c).
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "constitution.md", "Run /devforge:constitute to populate the rules.\n")
            result = preflight(workspace_root=td)
            self.assertFalse(result["constitution_populated"])

    def test_all_sentinels_exported(self):
        self.assertEqual(len(_UNPOPULATED_SENTINELS), 5)

    def test_populated_constitution_true(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight(workspace_root=td)
            self.assertTrue(result["constitution_present"])
            self.assertTrue(result["constitution_populated"])


# ---------------------------------------------------------------------------
# preflight — feature-level gate (spec.md ONLY, no plan.md)
# ---------------------------------------------------------------------------

class TestPreflightFeatureGate(unittest.TestCase):

    def test_spec_present_no_plan_gate_ok(self):
        """The defining behavior difference from /grill: no plan.md required."""
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            feature_dir = _make_feature(td, with_spec=True, with_plan=False)
            result = preflight(workspace_root=td, feature_dir=feature_dir)
            self.assertTrue(result["spec_present"])
            self.assertTrue(result["feature_gate_ok"])
            self.assertEqual(result["missing_feature_artefacts"], [])

    def test_spec_present_with_plan_also_present_gate_ok(self):
        """Presence of plan.md must not affect the gate either way."""
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            feature_dir = _make_feature(td, with_spec=True, with_plan=True)
            result = preflight(workspace_root=td, feature_dir=feature_dir)
            self.assertTrue(result["feature_gate_ok"])

    def test_spec_missing_gate_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            feature_dir = _make_feature(td, with_spec=False, with_plan=False)
            result = preflight(workspace_root=td, feature_dir=feature_dir)
            self.assertFalse(result["spec_present"])
            self.assertFalse(result["feature_gate_ok"])
            self.assertEqual(result["missing_feature_artefacts"], ["spec.md"])

    def test_no_plan_md_key_in_result(self):
        """The result dict must not carry a plan_present key -- /spec-check
        does not gate on plan.md at all."""
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            feature_dir = _make_feature(td, with_spec=True, with_plan=False)
            result = preflight(workspace_root=td, feature_dir=feature_dir)
            self.assertNotIn("plan_present", result)


# ---------------------------------------------------------------------------
# preflight — z3 wiring through the dict
# ---------------------------------------------------------------------------

class TestPreflightZ3Wiring(unittest.TestCase):

    def test_z3_absent_wired_into_result(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight(workspace_root=td, z3_importer=_raising_importer)
            self.assertFalse(result["z3_available"])
            self.assertEqual(result["z3_message"], Z3_INSTALL_MESSAGE)

    def test_z3_present_wired_into_result(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight(workspace_root=td, z3_importer=_ok_importer)
            self.assertTrue(result["z3_available"])
            self.assertEqual(result["z3_message"], "")


# ---------------------------------------------------------------------------
# preflight — all-green pass
# ---------------------------------------------------------------------------

class TestPreflightAllGreen(unittest.TestCase):

    def test_full_install_plus_spec_plus_z3_all_true(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            feature_dir = _make_feature(td, with_spec=True, with_plan=False)
            result = preflight(
                workspace_root=td, feature_dir=feature_dir, z3_importer=_ok_importer
            )
            self.assertTrue(result["constitution_present"])
            self.assertTrue(result["constitution_populated"])
            self.assertTrue(result["setup_chain_ok"])
            self.assertEqual(result["missing_artefacts"], [])
            self.assertTrue(result["spec_present"])
            self.assertTrue(result["feature_gate_ok"])
            self.assertEqual(result["missing_feature_artefacts"], [])
            self.assertTrue(result["z3_available"])
            self.assertEqual(result["z3_message"], "")


if __name__ == "__main__":
    unittest.main()
