"""Tests for src/devforge/lib/_grill/_cli.py.

Coverage:

Build / registry:
  build_parser              — returns ArgumentParser with expected prog name
  _SUBCOMMAND_REGISTRY      — contains all 12 expected verbs
  main(no subcommand)       — prints help + returns 2
  main(unknown subcommand)  — returns non-zero

check-status-and-flip (Phase 1):
  read-only mode (no --to)  — returns 0, emits valid JSON GrillState
  flip mode (--to scope)    — returns 0, emits updated state JSON
  flip mode with --status   — status reflected in output
  empty --to string         — returns 2 + stderr message

preflight (Phase 1):
  missing workspace-root artefacts → returns 2, JSON still emitted
  all artefacts present, no feature-dir → returns 0
  all artefacts present, feature-dir missing spec.md → returns 2
  all artefacts present, feature-dir has spec+plan → returns 0

resolve-scope (Phase 2):
  auto-detect from specs/ with plan.md  — returns 0, JSON with path fields
  explicit --feature arg                — returns 0
  no feature found                      — returns 2 + stderr message
  missing plan.md in explicit feature   — returns 2

render-brief (Phase 3):
  happy path with manifest JSON + references files — returns 0, text to stdout
  missing --manifest arg                            — returns 2
  non-JSON --manifest file                          — returns 2
  missing anti-relitigation-preamble.md             — returns 2

consume-tmp (Phase 3):
  missing --tmp arg                   — returns 2
  non-existent file                   — returns 2, JSON status=missing
  real tmp file with 0 findings       — returns 0, status=complete

validate-findings (Phase 3):
  missing --findings arg              — returns 2
  non-JSON file                       — returns 2
  non-array JSON                      — returns 2
  empty array                         — returns 0

route-refutation (Phase 4, shared engine):
  basic round-trip: findings JSON emitted  — returns 0
  architect-excluded: findings authored by code-reviewer must not route
    to architect even though architect is in the _shared default list —
    route-refutation uses _GRILL_REFUTER_PRIORITY which excludes architect
  missing --findings arg               — returns 2
  non-JSON --findings                  — returns 2
  non-array JSON                       — returns 2

render-verify-brief (Phase 4, shared engine):
  happy path with refutation-preamble.md  — returns 0, text includes preamble
  missing --findings arg                  — returns 2
  missing --refuter arg                   — returns 2
  missing --scope-block arg               — returns 2

consume-verdicts (Phase 4, shared engine):
  missing --verdicts arg                  — returns 2
  non-existent file                       — returns 2, JSON status=missing
  valid verdict file                      — returns 0, status=complete
  refuter hint applied when header absent — returns 0

apply-verdicts (Phase 4, shared engine):
  missing --findings arg              — returns 2
  missing --verdicts arg              — returns 2
  bare-array verdicts                 — returns 0
  consume-verdicts wrapper object     — returns 0

render-report (Phase 5):
  missing --partition arg             — returns 2
  missing --date arg                  — returns 2
  missing --disposition arg           — returns 2
  missing --rationale arg             — returns 2
  invalid disposition value           — returns 2
  happy path PROCEED                  — returns 0, JSON ack + file written
  happy path RE-ENTER-UPSTREAM        — returns 0 with --re-entry-target spec

write-seed (Phase 5):
  missing --target-stage arg          — returns 2
  missing --prior-conclusion arg      — returns 2
  missing --invalidating-evidence arg — returns 2
  missing --must-satisfy arg          — returns 2
  missing --provenance arg            — returns 2
  bad --cycle-count (non-int)         — returns 2
  invalid target-stage                — returns 2
  happy path                          — returns 0, JSON ack + file written
  with --carried-findings             — returns 0, findings in seed JSON

CLI wiring for three previously-library-only helpers (merge-passes new
verb; render-report's ack "clean" key; check-status-and-flip's
--adversary-status / --plan-sha256 flags) is covered in the sibling file
test_cli_phase1_wiring.py, NOT here — this file only carries the registry
verb-name/count update those additions required.
"""

import dataclasses
import io
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

from _grill._cli import (  # noqa: E402
    _GRILL_REFUTER_PRIORITY,
    _SUBCOMMAND_REGISTRY,
    build_parser,
    main,
)


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _finding(agent="code-reviewer", file="specs/001-auth/plan.md", line=10,
             pattern="Scope creep", category="mislogic", tags=None):
    # type: (...) -> dict
    """Return a minimal ParsedFinding dict."""
    return {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": "High",
        "confidence": "Likely",
        "evidence": "some quoted plan text",
        "why": "explains why this is wrong",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }


def _verdict_text(refuter="code-reviewer", status="complete", verdicts=None):
    # type: (...) -> str
    """Build a verdict file matching the refutation-preamble contract."""
    if verdicts is None:
        verdicts = [{"finding_id": "F-001", "decision": "confirmed",
                     "reason": "defect demonstrated"}]
    lines = [
        "# Refuter: {0}".format(refuter),
        "# Status: {0}".format(status),
        "",
    ]
    for i, v in enumerate(verdicts, 1):
        lines += [
            "## Verdict {0}".format(i),
            "Finding: {0}".format(v.get("finding_id", "F-001")),
            "Decision: {0}".format(v.get("decision", "confirmed")),
            "Reason: {0}".format(v.get("reason", "")),
            "",
        ]
    return "\n".join(lines)


def _write_json(obj, path):
    # type: (object, str) -> None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def _write_text(content, path):
    # type: (str, str) -> None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _capture(argv, capsys=None):
    # type: (...) -> tuple
    """Run main(argv), capture stdout/stderr, return (exit_code, out, err)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = buf_out
    sys.stderr = buf_err
    try:
        code = main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return code, buf_out.getvalue(), buf_err.getvalue()


def _make_workspace(tmp):
    # type: (str) -> str
    """Write minimal setup-chain artefacts (no unpopulated sentinels)."""
    for rel in ("CLAUDE.md", ".devforge/project-config.json",
                ".devforge/index.json"):
        full = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        _write_text("stub\n", full)
    const = os.path.join(tmp, "constitution.md")
    _write_text("# Constitution\nSome rules.\n", const)
    return tmp


def _make_feature(tmp, feature_id="001-auth", with_plan=True, with_spec=True):
    # type: (str, str, bool, bool) -> str
    """Create a feature directory under tmp/specs/ with optional plan/spec."""
    feature_dir = os.path.join(tmp, "specs", feature_id)
    os.makedirs(feature_dir, exist_ok=True)
    if with_plan:
        _write_text("# Plan\nplan content\n", os.path.join(feature_dir, "plan.md"))
    if with_spec:
        _write_text("# Spec\nspec content\n", os.path.join(feature_dir, "spec.md"))
    return feature_dir


def _make_refs(refs_dir, preamble_content="PREAMBLE TEXT\n",
               checklist_content="ATTACK CHECKLIST\n",
               refutation_content=None):
    # type: (str, str, str, object) -> None
    """Write standard reference files into refs_dir."""
    os.makedirs(refs_dir, exist_ok=True)
    _write_text(preamble_content,
                os.path.join(refs_dir, "anti-relitigation-preamble.md"))
    _write_text(checklist_content,
                os.path.join(refs_dir, "design-attack-checklist.md"))
    if refutation_content is not None:
        _write_text(refutation_content,
                    os.path.join(refs_dir, "refutation-preamble.md"))


# ---------------------------------------------------------------------------
# Test: build_parser / registry / main dispatch
# ---------------------------------------------------------------------------


class TestBuildParser(unittest.TestCase):
    def test_prog_name(self):
        parser = build_parser()
        self.assertEqual(parser.prog, "grill_helper")

    def test_registry_verb_names(self):
        verbs = [v[0] for v in _SUBCOMMAND_REGISTRY]
        expected = [
            "check-status-and-flip",
            "preflight",
            "resolve-scope",
            "render-brief",
            "consume-tmp",
            "validate-findings",
            "merge-passes",
            "route-refutation",
            "render-verify-brief",
            "consume-verdicts",
            "apply-verdicts",
            "render-report",
            "write-seed",
        ]
        self.assertEqual(verbs, expected)

    def test_registry_length(self):
        self.assertEqual(len(_SUBCOMMAND_REGISTRY), 13)

    def test_grill_refuter_priority_excludes_architect(self):
        self.assertNotIn("architect", _GRILL_REFUTER_PRIORITY)

    def test_grill_refuter_priority_has_three_entries(self):
        self.assertEqual(
            _GRILL_REFUTER_PRIORITY,
            ["code-reviewer", "qa-reviewer", "security-reviewer"],
        )

    def test_main_no_subcommand_returns_2(self):
        code, out, err = _capture([])
        self.assertEqual(code, 2)

    def test_main_unknown_subcommand_returns_nonzero(self):
        code, out, err = _capture(["no-such-verb"])
        self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# Test: check-status-and-flip
# ---------------------------------------------------------------------------


class TestCheckStatusAndFlip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_only_returns_0_and_json(self):
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("phase", data)
        self.assertIn("status", data)

    def test_read_only_default_phase_empty(self):
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "")

    def test_flip_mode_updates_phase(self):
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp, "--to", "scope"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "scope")

    def test_flip_mode_with_status(self):
        code, out, err = _capture(
            [
                "check-status-and-flip",
                "--feature-dir", self.tmp,
                "--to", "attack",
                "--status", "complete",
            ]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "attack")
        self.assertEqual(data["status"], "complete")

    def test_flip_mode_empty_to_returns_2(self):
        # argparse will parse "" as the value; the handler must reject it.
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp, "--to", ""]
        )
        self.assertEqual(code, 2)
        self.assertIn("check-status-and-flip", err)

    def test_flip_persists_to_disk(self):
        _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp, "--to", "refute"]
        )
        # Second read should see the flipped state.
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "refute")


# ---------------------------------------------------------------------------
# Test: preflight
# ---------------------------------------------------------------------------


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_artefacts_returns_2(self):
        # Empty workspace — nothing present.
        code, out, err = _capture(
            ["preflight", "--workspace-root", self.tmp]
        )
        self.assertEqual(code, 2)
        # JSON still emitted before the error.
        data = json.loads(out)
        self.assertFalse(data["setup_chain_ok"])
        self.assertIn("preflight", err)

    def test_all_artefacts_no_feature_dir_returns_0(self):
        _make_workspace(self.tmp)
        code, out, err = _capture(
            ["preflight", "--workspace-root", self.tmp]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        self.assertTrue(data["constitution_populated"])

    def test_feature_dir_missing_spec_returns_2(self):
        _make_workspace(self.tmp)
        feat = _make_feature(self.tmp, with_plan=True, with_spec=False)
        code, out, err = _capture(
            ["preflight", "--workspace-root", self.tmp, "--feature-dir", feat]
        )
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertFalse(data["feature_gate_ok"])
        self.assertIn("preflight", err)

    def test_feature_dir_with_spec_and_plan_returns_0(self):
        _make_workspace(self.tmp)
        feat = _make_feature(self.tmp, with_plan=True, with_spec=True)
        code, out, err = _capture(
            ["preflight", "--workspace-root", self.tmp, "--feature-dir", feat]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["feature_gate_ok"])

    def test_unpopulated_constitution_returns_2(self):
        _make_workspace(self.tmp)
        # Overwrite constitution with unpopulated sentinel.
        _write_text("{{CONSTITUTION_BODY}}\n",
                    os.path.join(self.tmp, "constitution.md"))
        code, out, err = _capture(
            ["preflight", "--workspace-root", self.tmp]
        )
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertFalse(data["constitution_populated"])


# ---------------------------------------------------------------------------
# Test: resolve-scope
# ---------------------------------------------------------------------------


class TestResolveScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_auto_detect_with_plan_md(self):
        feat = _make_feature(self.tmp, "001-auth", with_plan=True, with_spec=True)
        code, out, err = _capture(
            ["resolve-scope",
             "--workspace-root", self.tmp,
             "--specs-dir", os.path.join(self.tmp, "specs")]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("feature_dir", data)
        self.assertIn("plan_path", data)
        self.assertTrue(data["plan_path"].endswith("plan.md"))

    def test_explicit_feature_arg(self):
        feat = _make_feature(self.tmp, "002-pay", with_plan=True, with_spec=True)
        code, out, err = _capture(
            ["resolve-scope",
             "--workspace-root", self.tmp,
             "--feature", feat]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("002-pay", data["feature_dir"])

    def test_no_features_returns_2(self):
        os.makedirs(os.path.join(self.tmp, "specs"), exist_ok=True)
        code, out, err = _capture(
            ["resolve-scope",
             "--workspace-root", self.tmp,
             "--specs-dir", os.path.join(self.tmp, "specs")]
        )
        self.assertEqual(code, 2)
        self.assertIn("resolve-scope", err)

    def test_missing_plan_md_in_explicit_feature_returns_2(self):
        feat = _make_feature(self.tmp, "003-x", with_plan=False, with_spec=True)
        code, out, err = _capture(
            ["resolve-scope",
             "--workspace-root", self.tmp,
             "--feature", feat]
        )
        self.assertEqual(code, 2)
        self.assertIn("resolve-scope", err)

    def test_output_contains_spec_path(self):
        feat = _make_feature(self.tmp, "001-auth", with_plan=True, with_spec=True)
        code, out, err = _capture(
            ["resolve-scope",
             "--workspace-root", self.tmp,
             "--specs-dir", os.path.join(self.tmp, "specs")]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("spec_path", data)
        self.assertTrue(data["spec_path"].endswith("spec.md"))


# ---------------------------------------------------------------------------
# Test: render-brief
# ---------------------------------------------------------------------------


class TestRenderBrief(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.refs = os.path.join(self.tmp, "references")
        os.makedirs(self.refs, exist_ok=True)
        self.feat = _make_feature(self.tmp, "001-auth",
                                  with_plan=True, with_spec=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _manifest_path(self):
        from _grill._scope import GrillScopeManifest, build_scope_manifest
        manifest, err = build_scope_manifest(self.feat, self.tmp)
        self.assertIsNone(err, err)
        path = os.path.join(self.tmp, "manifest.json")
        _write_json(dataclasses.asdict(manifest), path)
        return path

    def test_missing_manifest_arg_returns_2(self):
        code, out, err = _capture(
            ["render-brief", "--references-dir", self.refs]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-brief", err)

    def test_non_json_manifest_returns_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        _write_text("not json", bad)
        code, out, err = _capture(
            ["render-brief", "--manifest", bad,
             "--references-dir", self.refs]
        )
        self.assertEqual(code, 2)

    def test_missing_preamble_returns_2(self):
        # refs dir exists but has no anti-relitigation-preamble.md.
        manifest_path = self._manifest_path()
        code, out, err = _capture(
            ["render-brief", "--manifest", manifest_path,
             "--references-dir", self.refs]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-brief", err)

    def test_happy_path_returns_0_with_text(self):
        _make_refs(self.refs,
                   preamble_content="PREAMBLE MARKER\n",
                   checklist_content="CHECKLIST MARKER\n")
        manifest_path = self._manifest_path()
        code, out, err = _capture(
            ["render-brief", "--manifest", manifest_path,
             "--references-dir", self.refs]
        )
        self.assertEqual(code, 0)
        self.assertIn("PREAMBLE MARKER", out)
        self.assertIn("CHECKLIST MARKER", out)

    def test_output_contains_plan_path(self):
        _make_refs(self.refs)
        manifest_path = self._manifest_path()
        code, out, err = _capture(
            ["render-brief", "--manifest", manifest_path,
             "--references-dir", self.refs]
        )
        self.assertEqual(code, 0)
        self.assertIn("plan.md", out)


# ---------------------------------------------------------------------------
# Test: consume-tmp
# ---------------------------------------------------------------------------


class TestConsumeTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_tmp_arg_returns_2(self):
        code, out, err = _capture(["consume-tmp"])
        self.assertEqual(code, 2)
        self.assertIn("consume-tmp", err)

    def test_nonexistent_file_returns_2_with_json(self):
        code, out, err = _capture(
            ["consume-tmp", "--tmp", "/no/such/file.md"]
        )
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertIn("missing", data["status"].lower())

    def test_zero_findings_file_returns_0(self):
        tmp_file = os.path.join(self.tmp, "agent.md")
        _write_text(
            "# Agent: devils-advocate\n# Status: complete\n# Finding count: 0\n",
            tmp_file,
        )
        code, out, err = _capture(
            ["consume-tmp", "--tmp", tmp_file]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["finding_count"], 0)

    def test_agent_hint_applied(self):
        tmp_file = os.path.join(self.tmp, "agent.md")
        _write_text(
            "# Status: complete\n# Finding count: 0\n",
            tmp_file,
        )
        code, out, err = _capture(
            ["consume-tmp", "--tmp", tmp_file, "--agent", "devils-advocate"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["agent"], "devils-advocate")


# ---------------------------------------------------------------------------
# Test: validate-findings
# ---------------------------------------------------------------------------


class TestValidateFindings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_findings_arg_returns_2(self):
        code, out, err = _capture(["validate-findings"])
        self.assertEqual(code, 2)
        self.assertIn("validate-findings", err)

    def test_non_json_file_returns_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        _write_text("not json", bad)
        code, out, err = _capture(
            ["validate-findings", "--findings", bad]
        )
        self.assertEqual(code, 2)

    def test_non_array_json_returns_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        _write_json({"key": "val"}, bad)
        code, out, err = _capture(
            ["validate-findings", "--findings", bad]
        )
        self.assertEqual(code, 2)
        self.assertIn("validate-findings", err)

    def test_empty_array_returns_0(self):
        path = os.path.join(self.tmp, "findings.json")
        _write_json([], path)
        code, out, err = _capture(
            ["validate-findings", "--findings", path,
             "--repo-root", self.tmp]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, (dict, list))


# ---------------------------------------------------------------------------
# Test: route-refutation (shared engine — critical architect-exclusion check)
# ---------------------------------------------------------------------------


class TestRouteRefutation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _findings_path(self, findings):
        # type: (list) -> str
        path = os.path.join(self.tmp, "findings.json")
        _write_json(findings, path)
        return path

    def test_basic_round_trip_returns_0_with_json(self):
        findings = [_finding(agent="code-reviewer")]
        path = self._findings_path(findings)
        code, out, err = _capture(
            ["route-refutation", "--findings", path,
             "--finders", "code-reviewer,qa-reviewer,security-reviewer"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)

    def test_architect_never_assigned_as_refuter(self):
        """Core check: architect is in present_finders but must NEVER be a refuter.

        The _shared default priority is [code-reviewer, architect, qa-reviewer,
        security-reviewer] — with architect present, the _shared engine WOULD
        pick architect as refuter for a code-reviewer-authored finding.  Grill
        overrides that with _GRILL_REFUTER_PRIORITY (architect excluded), so
        architect must still not appear.  This test passes architect in
        --finders so that _GRILL_REFUTER_PRIORITY is the ONLY thing preventing
        it from being assigned — passing it proves the override is in effect.
        """
        # Finding authored by code-reviewer.  Architect is present as a finder.
        # With the _shared default priority architect would be its refuter.
        # With _GRILL_REFUTER_PRIORITY the next eligible non-author is qa-reviewer.
        findings = [
            _finding(agent="code-reviewer"),
        ]
        path = self._findings_path(findings)
        code, out, err = _capture(
            ["route-refutation", "--findings", path,
             "--finders", "code-reviewer,architect,qa-reviewer,security-reviewer"]
        )
        self.assertEqual(code, 0)
        groups = json.loads(out)
        for group in groups:
            self.assertNotEqual(
                group.get("refuter"), "architect",
                "architect must never be a refuter in /grill even when it is "
                "listed as a present finder; got group: {0}".format(group),
            )

    def test_architect_not_in_grill_refuter_priority(self):
        """Structural check: the priority constant itself excludes architect."""
        self.assertNotIn("architect", _GRILL_REFUTER_PRIORITY)

    def test_missing_findings_returns_2(self):
        code, out, err = _capture(["route-refutation"])
        self.assertEqual(code, 2)
        self.assertIn("route-refutation", err)

    def test_non_json_findings_returns_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        _write_text("not json", bad)
        code, out, err = _capture(
            ["route-refutation", "--findings", bad]
        )
        self.assertEqual(code, 2)

    def test_non_array_findings_returns_2(self):
        bad = os.path.join(self.tmp, "bad.json")
        _write_json({"key": "val"}, bad)
        code, out, err = _capture(
            ["route-refutation", "--findings", bad]
        )
        self.assertEqual(code, 2)
        self.assertIn("route-refutation", err)

    def test_empty_findings_returns_0(self):
        path = self._findings_path([])
        code, out, err = _capture(
            ["route-refutation", "--findings", path,
             "--finders", "code-reviewer"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIsInstance(data, list)


# ---------------------------------------------------------------------------
# Test: render-verify-brief
# ---------------------------------------------------------------------------


class TestRenderVerifyBrief(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.refs = os.path.join(self.tmp, "refs")
        os.makedirs(self.refs, exist_ok=True)
        # Write refutation-preamble.md.
        _write_text("REFUTATION PREAMBLE CONTENT\n",
                    os.path.join(self.refs, "refutation-preamble.md"))
        # Write a scope-block file.
        self.scope_block_path = os.path.join(self.tmp, "scope.txt")
        _write_text("## Read Context\nplan.md: /some/path/plan.md\n",
                    self.scope_block_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _findings_path(self, findings):
        # type: (list) -> str
        path = os.path.join(self.tmp, "findings.json")
        _write_json(findings, path)
        return path

    def test_happy_path_returns_0_with_preamble(self):
        path = self._findings_path([_finding()])
        code, out, err = _capture(
            ["render-verify-brief",
             "--findings", path,
             "--refuter", "code-reviewer",
             "--references-dir", self.refs,
             "--scope-block", self.scope_block_path]
        )
        self.assertEqual(code, 0)
        self.assertIn("REFUTATION PREAMBLE CONTENT", out)

    def test_missing_findings_returns_2(self):
        code, out, err = _capture(
            ["render-verify-brief",
             "--refuter", "code-reviewer",
             "--references-dir", self.refs,
             "--scope-block", self.scope_block_path]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-verify-brief", err)

    def test_missing_refuter_returns_2(self):
        path = self._findings_path([])
        code, out, err = _capture(
            ["render-verify-brief",
             "--findings", path,
             "--references-dir", self.refs,
             "--scope-block", self.scope_block_path]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-verify-brief", err)

    def test_missing_scope_block_returns_2(self):
        path = self._findings_path([])
        code, out, err = _capture(
            ["render-verify-brief",
             "--findings", path,
             "--refuter", "code-reviewer",
             "--references-dir", self.refs]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-verify-brief", err)


# ---------------------------------------------------------------------------
# Test: consume-verdicts
# ---------------------------------------------------------------------------


class TestConsumeVerdicts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_verdicts_arg_returns_2(self):
        code, out, err = _capture(["consume-verdicts"])
        self.assertEqual(code, 2)
        self.assertIn("consume-verdicts", err)

    def test_nonexistent_file_returns_2_with_json(self):
        code, out, err = _capture(
            ["consume-verdicts", "--verdicts", "/no/such/verdicts.md"]
        )
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertIn("missing", data["status"].lower())

    def test_valid_verdict_file_returns_0(self):
        vpath = os.path.join(self.tmp, "verdicts.md")
        _write_text(_verdict_text(), vpath)
        code, out, err = _capture(
            ["consume-verdicts", "--verdicts", vpath]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "complete")

    def test_refuter_hint_applied_when_header_absent(self):
        vpath = os.path.join(self.tmp, "verdicts.md")
        # No "# Refuter:" header in the file.
        _write_text("# Status: complete\n\n", vpath)
        code, out, err = _capture(
            ["consume-verdicts", "--verdicts", vpath,
             "--refuter", "qa-reviewer"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["refuter"], "qa-reviewer")


# ---------------------------------------------------------------------------
# Test: apply-verdicts
# ---------------------------------------------------------------------------


class TestApplyVerdicts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_findings(self, findings):
        # type: (list) -> str
        path = os.path.join(self.tmp, "findings.json")
        _write_json(findings, path)
        return path

    def _write_verdicts(self, verdicts):
        # type: (object) -> str
        path = os.path.join(self.tmp, "verdicts.json")
        _write_json(verdicts, path)
        return path

    def test_missing_findings_returns_2(self):
        vpath = self._write_verdicts([])
        code, out, err = _capture(
            ["apply-verdicts", "--verdicts", vpath]
        )
        self.assertEqual(code, 2)
        self.assertIn("apply-verdicts", err)

    def test_missing_verdicts_returns_2(self):
        fpath = self._write_findings([])
        code, out, err = _capture(
            ["apply-verdicts", "--findings", fpath]
        )
        self.assertEqual(code, 2)
        self.assertIn("apply-verdicts", err)

    def test_bare_array_verdicts_returns_0(self):
        fpath = self._write_findings([_finding()])
        vpath = self._write_verdicts([])  # bare array
        code, out, err = _capture(
            ["apply-verdicts", "--findings", fpath, "--verdicts", vpath]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("confirmed", data)

    def test_consume_verdicts_wrapper_object_returns_0(self):
        fpath = self._write_findings([_finding()])
        # A consume-verdicts result object with "verdicts" key.
        vpath = self._write_verdicts({"status": "complete", "verdicts": []})
        code, out, err = _capture(
            ["apply-verdicts", "--findings", fpath, "--verdicts", vpath]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("dismissed", data)

    def test_high_stakes_security_uncertain_goes_to_contested(self):
        finding = _finding(agent="code-reviewer", category="security",
                           tags=["[CONSTITUTION-VIOLATION]"])
        fpath = self._write_findings([finding])
        # One verdict: uncertain on a security + constitution-violation finding.
        verdicts = [
            {
                "finding_id": None,
                "file": finding["file"],
                "line": finding["line"],
                "decision": "uncertain",
                "reason": "could not confirm from plan alone",
                "refuter": "qa-reviewer",
            }
        ]
        vpath = self._write_verdicts(verdicts)
        code, out, err = _capture(
            ["apply-verdicts", "--findings", fpath, "--verdicts", vpath]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        # Security + [CONSTITUTION-VIOLATION] uncertain → contested, not buried.
        self.assertGreater(
            len(data.get("contested", [])) + len(data.get("confirmed", [])),
            0,
            "high-stakes finding must not be silently dismissed",
        )


# ---------------------------------------------------------------------------
# Test: render-report
# ---------------------------------------------------------------------------


class TestRenderReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _partition_path(self, confirmed=None, dismissed=None,
                        uncertain=None, contested=None):
        # type: (...) -> str
        partition = {
            "confirmed": confirmed or [],
            "dismissed": dismissed or [],
            "uncertain": uncertain or [],
            "contested": contested or [],
        }
        path = os.path.join(self.tmp, "partition.json")
        _write_json(partition, path)
        return path

    def test_missing_partition_returns_2(self):
        code, out, err = _capture(
            ["render-report",
             "--date", "2026-06-17",
             "--disposition", "PROCEED",
             "--rationale", "plan is fine"]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_missing_date_returns_2(self):
        path = self._partition_path()
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--disposition", "PROCEED",
             "--rationale", "rationale"]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_missing_disposition_returns_2(self):
        path = self._partition_path()
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--date", "2026-06-17",
             "--rationale", "rationale"]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_missing_rationale_returns_2(self):
        path = self._partition_path()
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--date", "2026-06-17",
             "--disposition", "PROCEED"]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_invalid_disposition_returns_2(self):
        path = self._partition_path()
        feature_dir = os.path.join(self.tmp, "specs", "001-auth")
        os.makedirs(feature_dir, exist_ok=True)
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--feature", feature_dir,
             "--date", "2026-06-17",
             "--disposition", "INVALID",
             "--rationale", "rationale"]
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_happy_path_proceed_returns_0(self):
        path = self._partition_path()
        feature_dir = os.path.join(self.tmp, "specs", "001-auth")
        os.makedirs(feature_dir, exist_ok=True)
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--feature", feature_dir,
             "--date", "2026-06-17",
             "--disposition", "PROCEED",
             "--rationale", "The plan is sound.",
             "--finders", "devils-advocate"]
        )
        self.assertEqual(code, 0)
        ack = json.loads(out)
        self.assertIn("path", ack)
        self.assertTrue(ack["path"].endswith("grill.md"))
        self.assertTrue(os.path.isfile(ack["path"]))

    def test_re_enter_upstream_without_re_entry_target_returns_2(self):
        """RE-ENTER-UPSTREAM without --re-entry-target must return 2.

        render_report raises ValueError when disposition is RE-ENTER-UPSTREAM
        but re_entry_target is None; the handler catches it and returns 2.
        """
        path = self._partition_path(confirmed=[_finding()])
        feature_dir = os.path.join(self.tmp, "specs", "003-re-enter")
        os.makedirs(feature_dir, exist_ok=True)
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--feature", feature_dir,
             "--date", "2026-06-17",
             "--disposition", "RE-ENTER-UPSTREAM",
             "--rationale", "Defect is in the spec."]
            # --re-entry-target intentionally omitted
        )
        self.assertEqual(code, 2)
        self.assertIn("render-report", err)

    def test_happy_path_re_enter_upstream_returns_0(self):
        path = self._partition_path(confirmed=[_finding()])
        feature_dir = os.path.join(self.tmp, "specs", "002-pay")
        os.makedirs(feature_dir, exist_ok=True)
        code, out, err = _capture(
            ["render-report",
             "--partition", path,
             "--feature", feature_dir,
             "--date", "2026-06-17",
             "--disposition", "RE-ENTER-UPSTREAM",
             "--rationale", "Defect is in the spec.",
             "--re-entry-target", "spec"]
        )
        self.assertEqual(code, 0)
        ack = json.loads(out)
        self.assertTrue(os.path.isfile(ack["path"]))
        # Check the report content mentions the disposition.
        with open(ack["path"], encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("RE-ENTER-UPSTREAM", content)

    def test_grill_md_content_includes_disposition_section(self):
        path = self._partition_path()
        feature_dir = os.path.join(self.tmp, "specs", "001-check")
        os.makedirs(feature_dir, exist_ok=True)
        _capture(
            ["render-report",
             "--partition", path,
             "--feature", feature_dir,
             "--date", "2026-06-17",
             "--disposition", "REVISE-PLAN",
             "--rationale", "Fix these items."]
        )
        grill_path = os.path.join(feature_dir, "grill.md")
        self.assertTrue(os.path.isfile(grill_path))
        with open(grill_path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("## Disposition", text)
        self.assertIn("REVISE-PLAN", text)


# ---------------------------------------------------------------------------
# Test: write-seed
# ---------------------------------------------------------------------------


class TestWriteSeed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.feat = os.path.join(self.tmp, "specs", "001-auth")
        os.makedirs(self.feat, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _base_args(self):
        # type: () -> list
        return [
            "write-seed",
            "--feature", self.feat,
            "--target-stage", "spec",
            "--prior-conclusion", "The spec said X.",
            "--invalidating-evidence", "plan.md line 42: contradicts X",
            "--must-satisfy", "The re-run must address Y.",
            "--provenance", os.path.join(self.feat, "grill.md"),
        ]

    def test_missing_target_stage_returns_2(self):
        code, out, err = _capture(
            ["write-seed",
             "--feature", self.feat,
             "--prior-conclusion", "x",
             "--invalidating-evidence", "e",
             "--must-satisfy", "y",
             "--provenance", "grill.md"]
        )
        self.assertEqual(code, 2)
        self.assertIn("write-seed", err)

    def test_missing_prior_conclusion_returns_2(self):
        code, out, err = _capture(
            ["write-seed",
             "--feature", self.feat,
             "--target-stage", "spec",
             "--invalidating-evidence", "e",
             "--must-satisfy", "y",
             "--provenance", "grill.md"]
        )
        self.assertEqual(code, 2)

    def test_missing_invalidating_evidence_returns_2(self):
        code, out, err = _capture(
            ["write-seed",
             "--feature", self.feat,
             "--target-stage", "spec",
             "--prior-conclusion", "x",
             "--must-satisfy", "y",
             "--provenance", "grill.md"]
        )
        self.assertEqual(code, 2)

    def test_missing_must_satisfy_returns_2(self):
        code, out, err = _capture(
            ["write-seed",
             "--feature", self.feat,
             "--target-stage", "spec",
             "--prior-conclusion", "x",
             "--invalidating-evidence", "e",
             "--provenance", "grill.md"]
        )
        self.assertEqual(code, 2)

    def test_missing_provenance_returns_2(self):
        code, out, err = _capture(
            ["write-seed",
             "--feature", self.feat,
             "--target-stage", "spec",
             "--prior-conclusion", "x",
             "--invalidating-evidence", "e",
             "--must-satisfy", "y"]
        )
        self.assertEqual(code, 2)

    def test_bad_cycle_count_returns_2(self):
        args = self._base_args() + ["--cycle-count", "not-an-int"]
        code, out, err = _capture(args)
        self.assertEqual(code, 2)
        self.assertIn("write-seed", err)

    def test_invalid_target_stage_returns_2(self):
        args = self._base_args()
        # Replace --target-stage spec with an invalid value.
        idx = args.index("spec")
        args[idx] = "invalid-stage"
        code, out, err = _capture(args)
        self.assertEqual(code, 2)
        self.assertIn("write-seed", err)

    def test_happy_path_returns_0_and_writes_file(self):
        code, out, err = _capture(self._base_args())
        self.assertEqual(code, 0)
        ack = json.loads(out)
        self.assertIn("path", ack)
        self.assertTrue(ack["path"].endswith("grill-seed.json"))
        self.assertTrue(os.path.isfile(ack["path"]))

    def test_seed_json_has_correct_fields(self):
        _capture(self._base_args())
        seed_path = os.path.join(self.feat, "grill-seed.json")
        with open(seed_path, encoding="utf-8") as fh:
            seed = json.load(fh)
        self.assertEqual(seed["source"], "grill")
        self.assertEqual(seed["target_stage"], "spec")
        self.assertEqual(seed["cycle_count"], 1)
        self.assertIsInstance(seed["carried_findings"], list)

    def test_with_carried_findings(self):
        args = self._base_args() + [
            "--carried-findings", "finding A,finding B",
        ]
        code, out, err = _capture(args)
        self.assertEqual(code, 0)
        seed_path = os.path.join(self.feat, "grill-seed.json")
        with open(seed_path, encoding="utf-8") as fh:
            seed = json.load(fh)
        self.assertEqual(seed["carried_findings"], ["finding A", "finding B"])

    def test_cycle_count_greater_than_1(self):
        args = self._base_args() + ["--cycle-count", "3"]
        code, out, err = _capture(args)
        self.assertEqual(code, 0)
        seed_path = os.path.join(self.feat, "grill-seed.json")
        with open(seed_path, encoding="utf-8") as fh:
            seed = json.load(fh)
        self.assertEqual(seed["cycle_count"], 3)

    def test_all_target_stages_accepted(self):
        # Phase 1: "plan" is now the 4th valid target stage.
        for stage in ("spec", "discovery", "research", "plan"):
            feat_dir = os.path.join(self.tmp, "s-{0}".format(stage))
            os.makedirs(feat_dir, exist_ok=True)
            args = [
                "write-seed",
                "--feature", feat_dir,
                "--target-stage", stage,
                "--prior-conclusion", "prior",
                "--invalidating-evidence", "evidence",
                "--must-satisfy", "must",
                "--provenance", "grill.md",
            ]
            code, out, err = _capture(args)
            self.assertEqual(code, 0,
                             "stage {0!r} should be accepted; err: {1}".format(stage, err))

    def test_write_seed_target_stage_plan_round_trip(self):
        """Phase 1+2: write-seed with --target-stage plan writes valid JSON."""
        feat_dir = os.path.join(self.tmp, "s-plan")
        os.makedirs(feat_dir, exist_ok=True)
        args = [
            "write-seed",
            "--feature", feat_dir,
            "--target-stage", "plan",
            "--prior-conclusion", "Plan assumed synchronous payment processing.",
            "--invalidating-evidence", "grill F-002: SLA requires < 200ms.",
            "--must-satisfy", "Plan must address async processing.",
            "--provenance", os.path.join(feat_dir, "grill.md"),
            "--cycle-count", "2",
            "--carried-findings", "prior finding A,prior finding B",
        ]
        code, out, err = _capture(args)
        self.assertEqual(code, 0, "write-seed with --target-stage plan failed; err: {0}".format(err))
        ack = json.loads(out)
        self.assertIn("path", ack)
        # Round-trip: read back the JSON and verify target_stage == "plan".
        with open(ack["path"], encoding="utf-8") as fh:
            seed = json.load(fh)
        self.assertEqual(seed["target_stage"], "plan")
        self.assertEqual(seed["source"], "grill")
        self.assertEqual(seed["cycle_count"], 2)
        self.assertEqual(seed["carried_findings"], ["prior finding A", "prior finding B"])


if __name__ == "__main__":
    unittest.main()
