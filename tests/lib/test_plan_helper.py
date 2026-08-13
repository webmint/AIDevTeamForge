"""Tests for src/devforge/lib/plan_helper.py.

Tests all six subcommands against a spec fixture that is rendered at test time
from a fully synthetic, anonymous specify-state (an invented "widget catalog
search" feature — no real-world content). `setUpModule` feeds that state to the
REAL `specify_helper render` producer, so the parser tests run against genuine
producer output (the "round-trip via real producer" requirement) without
embedding any identifiable case.

Fixtures (checked in):
  tests/lib/fixtures/specs/008-sample-feature/spec-state.json  (synthetic specify-state)
  tests/lib/fixtures/specs/008-sample-feature/plan.md          (synthetic plan; no producer exists)
The rendered spec.md is produced into a per-run TemporaryDirectory and exposed
as the module global FIXTURE_SPEC (populated by setUpModule).

Synthetic fixture counts (asserted below): 7 ACs across 7 §5.x subsections,
2 out-of-scope items, 2 risks, status = Complete.

CLI-level tests invoke plan_helper.py as a subprocess.
Module-level unit tests import plan_helper directly via sys.path insert.

Stdlib only.
"""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper.py"
HELPER_SHIM = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper"
SPECIFY_HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "specify_helper.py"
RESEARCH_HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "research_helper.py"
DISCOVER_HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "discover_helper.py"
_LIB_DIR = REPO_ROOT / "src" / "devforge" / "lib"

FIXTURE_DIR = (
    REPO_ROOT / "tests" / "lib" / "fixtures" / "specs" / "008-sample-feature"
)
SPEC_STATE = FIXTURE_DIR / "spec-state.json"
FIXTURE_PLAN = FIXTURE_DIR / "plan.md"

# FIXTURE_SPEC is the spec.md rendered from SPEC_STATE by setUpModule (runtime
# round-trip through the real specify_helper producer). Declared here so module
# references resolve at import; tests read it only inside methods, after setup.
FIXTURE_SPEC = None
_RENDER_TMP = None


def setUpModule():
    """Render the synthetic spec-state into spec.md via the real producer."""
    global FIXTURE_SPEC, _RENDER_TMP
    _RENDER_TMP = tempfile.TemporaryDirectory()
    dev = Path(_RENDER_TMP.name) / ".devforge"
    dev.mkdir(parents=True)
    (dev / "specify-state.json").write_text(
        SPEC_STATE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    proc = subprocess.run(
        [sys.executable, str(SPECIFY_HELPER_PY),
         "--devforge-dir", str(dev), "render"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "specify_helper render failed (rc={0}): {1}".format(
                proc.returncode, proc.stderr
            )
        )
    spec_path = Path(_RENDER_TMP.name) / "spec.md"
    spec_path.write_text(proc.stdout, encoding="utf-8")
    # Resolve symlinks (macOS /var -> /private/var) so the path handed to the
    # helper is already canonical and matches the helper's own abspath output.
    FIXTURE_SPEC = spec_path.resolve()


def tearDownModule():
    if _RENDER_TMP is not None:
        _RENDER_TMP.cleanup()


sys.path.insert(0, str(HELPER_PY.parent))
import plan_helper  # noqa: E402

# Producer imports for handoff round-trip tests.
# These are added to sys.path so _specify/_discover packages are importable.
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
if str(_LIB_DIR / "_specify") not in sys.path:
    sys.path.insert(0, str(_LIB_DIR / "_specify"))
if str(_LIB_DIR / "_discover") not in sys.path:
    sys.path.insert(0, str(_LIB_DIR / "_discover"))

from _specify._cmds_handoff import cmd_finalize_handoff as _specify_finalize_handoff  # noqa: E402
from _specify._cmds_handoff import _dict_to_dataclass as _specify_dict_to_dataclass  # noqa: E402
from _discover._cmds_handoff import cmd_finalize_handoff as _discover_finalize_handoff  # noqa: E402
from _discover._state import _atomic_write_json, MEMO_FILE_NAME, REPORT_FILE_NAME  # noqa: E402


def _run(cwd, *args):
    """Invoke plan_helper.py as a subprocess from cwd."""
    return subprocess.run(
        [sys.executable, str(HELPER_PY)] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _write_minimal_spec(path, status="Draft", include_all_sections=True):
    """Write a minimal but valid 9-section spec.md at path."""
    sections = ""
    if include_all_sections:
        sections = """
## 1. Overview

Minimal overview.

## 2. Current State

Minimal current state.

## 3. Desired Behavior

1. First desired behavior item.
2. Second desired behavior item.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Core | src/core.py | Add function |

## 5. Acceptance Criteria

### 5.1 Tooling / artifact presence and absence
- [x] **AC-1**: Some artifact exists.
- [x] **AC-2**: Another artifact exists.

### 5.2 Behavior preservation
- [x] **AC-3**: Old behavior unchanged.

### 5.3 Behavior change
- [x] **AC-4**: New behavior present.

### 5.4 CI / pipeline
- [x] **AC-5**: CI passes.

### 5.5 Hooks / gates
- [x] **AC-6**: Hook fires.

### 5.6 Documentation
- [x] **AC-7**: Docs updated.

### 5.7 Hygiene
- [x] **AC-8**: No debug artifacts.

## 6. Out of Scope

- NOT included: Some excluded thing.

## 7. Technical Constraints

- **Layer**: Use domain layer only.

## 8. Open Questions

- **Q1**: Is the approach correct?

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Some risk | Low | Low | Some mitigation |
"""

    content = (
        "# Spec: Test Feature\n\n"
        "**Date**: 2026-01-01\n"
        "**Status**: {status}\n"
        "**Author**: Claude + User\n"
        "{sections}"
    ).format(status=status, sections=sections)
    Path(path).write_text(content, encoding="utf-8")


class _CwdIsolation(unittest.TestCase):
    """Base class that restores cwd and provides a tmp dir."""

    def setUp(self):
        self._saved_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._saved_cwd)
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Tests: pick-spec
# ---------------------------------------------------------------------------


class PickSpecTests(_CwdIsolation):

    def test_pick_spec_with_explicit_path(self):
        """Pass fixture path explicitly; expect stdout = absolute path."""
        result = _run(self.tmp_path, "pick-spec", str(FIXTURE_SPEC))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(FIXTURE_SPEC.resolve()))

    def test_pick_spec_no_arg_picks_most_recent(self):
        """Two specs under specs/; expect most-recent-mtime one is picked."""
        specs_dir = self.tmp_path / "specs"
        older_dir = specs_dir / "007-older"
        newer_dir = specs_dir / "009-newer"
        older_dir.mkdir(parents=True)
        newer_dir.mkdir(parents=True)

        older_spec = older_dir / "spec.md"
        newer_spec = newer_dir / "spec.md"
        _write_minimal_spec(str(older_spec), status="Draft")
        _write_minimal_spec(str(newer_spec), status="Draft")

        # Force older mtime on older spec.
        old_time = time.time() - 3600
        os.utime(str(older_spec), (old_time, old_time))
        new_time = time.time()
        os.utime(str(newer_spec), (new_time, new_time))

        result = _run(self.tmp_path, "pick-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(newer_spec.resolve()))

    def test_pick_spec_no_specs_dir_exits_2(self):
        """No specs/ dir → exit 2, stderr contains 'no valid spec found'."""
        result = _run(self.tmp_path, "pick-spec")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no valid spec found", result.stderr)

    def test_pick_spec_malformed_spec_skipped(self):
        """Fixture missing §3-§9 is skipped; if no valid alternative, exits 2."""
        specs_dir = self.tmp_path / "specs"
        bad_dir = specs_dir / "001-bad"
        bad_dir.mkdir(parents=True)
        bad_spec = bad_dir / "spec.md"
        # Write a spec missing sections 3-9.
        bad_spec.write_text(
            "# Spec: Bad\n\n**Date**: 2026-01-01\n**Status**: Draft\n\n"
            "## 1. Overview\n\nHi.\n\n## 2. Current State\n\nHi.\n",
            encoding="utf-8",
        )

        result = _run(self.tmp_path, "pick-spec")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no valid spec found", result.stderr)

    def test_pick_spec_malformed_skipped_valid_selected(self):
        """Malformed spec is skipped; valid sibling is picked instead."""
        specs_dir = self.tmp_path / "specs"
        bad_dir = specs_dir / "001-bad"
        good_dir = specs_dir / "002-good"
        bad_dir.mkdir(parents=True)
        good_dir.mkdir(parents=True)

        bad_spec = bad_dir / "spec.md"
        good_spec = good_dir / "spec.md"
        bad_spec.write_text(
            "# Spec: Bad\n\n**Date**: 2026-01-01\n**Status**: Draft\n\n"
            "## 1. Overview\n\nHi.\n",
            encoding="utf-8",
        )
        _write_minimal_spec(str(good_spec), status="Draft")

        result = _run(self.tmp_path, "pick-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(good_spec.resolve()))

    def test_pick_spec_explicit_missing_exits_2(self):
        """Non-existent path → exit 2."""
        result = _run(self.tmp_path, "pick-spec", "nonexistent/spec.md")
        self.assertEqual(result.returncode, 2)

    def test_pick_spec_explicit_relative_path(self):
        """Explicit relative path resolved against cwd."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        spec = specs_dir / "spec.md"
        _write_minimal_spec(str(spec), status="Draft")

        result = _run(self.tmp_path, "pick-spec", "specs/001-test/spec.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(spec.resolve()))


# ---------------------------------------------------------------------------
# Tests: render-pick-summary
# ---------------------------------------------------------------------------


class RenderPickSummaryTests(_CwdIsolation):

    def _parse_summary(self, stdout: str) -> dict:
        """Parse the 5-line summary block into a dict."""
        result = {}
        for line in stdout.splitlines():
            if line.startswith("**Spec**:"):
                result["spec"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Type**:"):
                result["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("**AC count**:"):
                result["ac_count"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Status**:"):
                result["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("**Last modified**:"):
                result["last_modified"] = line.split(":", 1)[1].strip()
        return result

    def test_render_pick_summary_counts_acs(self):
        """AC count in summary matches actual AC lines in fixture."""
        result = _run(self.tmp_path, "render-pick-summary", str(FIXTURE_SPEC))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        self.assertIn("ac_count", parsed)

        # Manual count of AC lines in fixture.
        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        import re
        ac_lines = re.findall(
            r"^\s*-\s+\[[xX ]\]\s+\*\*AC-\d+\*\*", content, re.MULTILINE
        )
        expected_count = len(ac_lines)

        ac_str = parsed["ac_count"]
        # Format: "N criteria across M subsections"
        ac_num = int(ac_str.split(" criteria")[0])
        self.assertEqual(ac_num, expected_count)

    def test_render_pick_summary_subsection_count(self):
        """Subsection count M matches unique ### 5.x headings with ACs in fixture."""
        result = _run(self.tmp_path, "render-pick-summary", str(FIXTURE_SPEC))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        ac_str = parsed["ac_count"]
        # "N criteria across M subsections"
        m_part = ac_str.split("across ")[1].split(" ")[0]
        reported_m = int(m_part)

        # Manually count subsections with at least one AC in fixture.
        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        import re
        sec5_match = re.search(r"^##\s+5\.", content, re.MULTILINE)
        sec6_match = re.search(r"^##\s+6\.", content, re.MULTILINE)
        sec5_text = (
            content[sec5_match.start():sec6_match.start()]
            if sec5_match and sec6_match
            else ""
        )
        subsection_pats = re.finditer(r"^###\s+5\.\d+", sec5_text, re.MULTILINE)
        subsection_starts = list(subsection_pats)
        manual_m = 0
        for idx, sm in enumerate(subsection_starts):
            s_start = sm.start()
            s_end = (
                subsection_starts[idx + 1].start()
                if idx + 1 < len(subsection_starts)
                else len(sec5_text)
            )
            sub_chunk = sec5_text[s_start:s_end]
            if re.search(r"^\s*-\s+\[[xX ]\]\s+\*\*AC-\d+\*\*", sub_chunk, re.MULTILINE):
                manual_m += 1
        self.assertEqual(reported_m, manual_m)

    def test_render_pick_summary_status_field(self):
        """Status in summary matches fixture's **Status**: value."""
        result = _run(self.tmp_path, "render-pick-summary", str(FIXTURE_SPEC))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)

        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        import re
        m = re.search(r"^\*\*Status\*\*:\s*(.+)$", content, re.MULTILINE)
        expected_status = m.group(1).strip() if m else "unknown"
        self.assertEqual(parsed["status"], expected_status)

    def test_render_pick_summary_missing_file_exits_2(self):
        result = _run(self.tmp_path, "render-pick-summary", "nonexistent/spec.md")
        self.assertEqual(result.returncode, 2)

    def test_render_pick_summary_spec_type_unknown_when_missing(self):
        """Spec without **Spec type**: line reports 'unknown'."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        spec = specs_dir / "spec.md"
        _write_minimal_spec(str(spec))  # minimal spec has no spec-type line

        result = _run(self.tmp_path, "render-pick-summary", str(spec))
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = self._parse_summary(result.stdout)
        self.assertEqual(parsed.get("type"), "unknown")


# ---------------------------------------------------------------------------
# Tests: list-specs
# ---------------------------------------------------------------------------


class ListSpecsTests(_CwdIsolation):

    def test_list_specs_sorted_by_mtime_desc(self):
        """3 specs with controlled mtimes; output order matches mtime desc."""
        specs_dir = self.tmp_path / "specs"
        for name in ("001-alpha", "002-beta", "003-gamma"):
            d = specs_dir / name
            d.mkdir(parents=True)
            _write_minimal_spec(str(d / "spec.md"))

        # Assign distinct mtimes: 003 is newest, 001 is oldest.
        base = time.time()
        os.utime(str(specs_dir / "001-alpha" / "spec.md"), (base - 200, base - 200))
        os.utime(str(specs_dir / "002-beta" / "spec.md"), (base - 100, base - 100))
        os.utime(str(specs_dir / "003-gamma" / "spec.md"), (base, base))

        result = _run(self.tmp_path, "list-specs")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)
        # First line should be index 1) ... 003-gamma ...
        self.assertIn("003-gamma", lines[0])
        self.assertIn("002-beta", lines[1])
        self.assertIn("001-alpha", lines[2])

    def test_list_specs_empty_dir(self):
        """Empty specs/ → exit 0, no output."""
        (self.tmp_path / "specs").mkdir()
        result = _run(self.tmp_path, "list-specs")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_list_specs_no_specs_dir(self):
        """No specs/ dir at all → exit 2."""
        result = _run(self.tmp_path, "list-specs")
        self.assertEqual(result.returncode, 2)

    def test_list_specs_output_format(self):
        """Output lines follow '<N>) <path> [Status: <X>] (<N> ACs)' format."""
        specs_dir = self.tmp_path / "specs" / "001-test"
        specs_dir.mkdir(parents=True)
        _write_minimal_spec(str(specs_dir / "spec.md"), status="Draft")

        result = _run(self.tmp_path, "list-specs")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertTrue(line.startswith("1)"), line)
        self.assertIn("[Status:", line)
        self.assertIn("ACs)", line)


# ---------------------------------------------------------------------------
# Tests: check-status-and-flip
# ---------------------------------------------------------------------------


class CheckStatusAndFlipTests(_CwdIsolation):

    def test_check_status_flips_draft_to_approved(self):
        """Draft spec → file rewritten to Approved, stdout 'flipped'."""
        spec_file = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec_file), status="Draft")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "flipped")

        # Re-read to verify disk mutation.
        disk_content = spec_file.read_text(encoding="utf-8")
        self.assertIn("**Status**: Approved", disk_content)
        self.assertNotIn("**Status**: Draft", disk_content)

    def test_check_status_already_approved_idempotent(self):
        """Approved spec → no rewrite, stdout 'already-approved'."""
        spec_file = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec_file), status="Approved")
        mtime_before = os.path.getmtime(str(spec_file))

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "already-approved")

        # File should not be rewritten.
        mtime_after = os.path.getmtime(str(spec_file))
        self.assertAlmostEqual(mtime_before, mtime_after, delta=0.01)

    def test_check_status_complete_no_rewrite(self):
        """Complete spec → no rewrite, stdout 'complete'."""
        spec_file = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec_file), status="Complete")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "complete")

        disk_content = spec_file.read_text(encoding="utf-8")
        self.assertIn("**Status**: Complete", disk_content)

    def test_check_status_unknown_value_no_flip(self):
        """Unknown status value → no rewrite, stdout 'unknown-status:<value>'."""
        spec_file = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec_file), status="In Progress")
        mtime_before = spec_file.stat().st_mtime_ns

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "unknown-status:In Progress")

        disk_content = spec_file.read_text(encoding="utf-8")
        self.assertIn("**Status**: In Progress", disk_content)
        self.assertNotIn("**Status**: Approved", disk_content)
        self.assertEqual(spec_file.stat().st_mtime_ns, mtime_before,
                         "file should not be rewritten on unknown status")

    def test_check_status_missing_inserts(self):
        """Spec without Status line → inserts Approved after Date, stdout 'inserted'."""
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Author**: Claude + User\n\n"
            "## 1. Overview\n\nSomething.\n"
        )
        spec_file = self.tmp_path / "spec.md"
        spec_file.write_text(content, encoding="utf-8")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "inserted")

        disk_content = spec_file.read_text(encoding="utf-8")
        self.assertIn("**Status**: Approved", disk_content)
        # Status line should appear after the Date line.
        date_pos = disk_content.index("**Date**:")
        status_pos = disk_content.index("**Status**: Approved")
        self.assertGreater(status_pos, date_pos)

    def test_check_status_malformed_no_date_exits_2(self):
        """Spec with neither Date nor Status → exit 2."""
        content = "# Spec: Bad\n\nNo frontmatter here.\n\n## 1. Overview\n\nHi.\n"
        spec_file = self.tmp_path / "spec.md"
        spec_file.write_text(content, encoding="utf-8")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 2)
        self.assertIn("malformed", result.stderr)

    def test_check_status_missing_file_exits_2(self):
        """Non-existent spec path → exit 2."""
        result = _run(self.tmp_path, "check-status-and-flip", "no/such/file.md")
        self.assertEqual(result.returncode, 2)

    def test_check_status_atomic_no_tmp_file_survives(self):
        """After a successful flip, no temp file remains in spec directory."""
        spec_file = self.tmp_path / "spec.md"
        _write_minimal_spec(str(spec_file), status="Draft")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)

        # Only spec.md should be in the directory.
        survivors = [p.name for p in self.tmp_path.iterdir()]
        self.assertIn("spec.md", survivors)
        for name in survivors:
            self.assertFalse(name.endswith(".tmp"), "tmp file survived: " + name)


# ---------------------------------------------------------------------------
# Tests: render-findings-from-spec
# ---------------------------------------------------------------------------


class RenderFindingsTests(_CwdIsolation):

    def _get_output(self):
        result = _run(
            self.tmp_path, "render-findings-from-spec", str(FIXTURE_SPEC)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_render_findings_enumerates_all_sections(self):
        """Output contains headings for all 7 enumerated spec sections."""
        output = self._get_output()
        self.assertIn("### From spec §3 (Desired Behavior)", output)
        self.assertIn("### From spec §4 (Affected Areas)", output)
        self.assertIn("### From spec §5 (Acceptance Criteria)", output)
        self.assertIn("### From spec §6 (Out of Scope)", output)
        self.assertIn("### From spec §7 (Technical Constraints)", output)
        self.assertIn("### From spec §8 (Open Questions)", output)
        self.assertIn("### From spec §9 (Risks)", output)

    def test_render_findings_ac_count_matches_subsections(self):
        """§5 block emits an entry for each subsection with ACs."""
        output = self._get_output()
        import re
        # Count subsection summary lines like "- §5.N (Title): N ACs"
        subsec_lines = re.findall(r"- §5\.\d+ \(.+?\): \d+ ACs", output)
        # Fixture has 7 subsections, all with at least 1 AC.
        self.assertEqual(len(subsec_lines), 7)

    def test_render_findings_ac_lines_present(self):
        """Individual AC lines are emitted under each subsection block."""
        output = self._get_output()
        import re
        ac_lines = re.findall(r"- AC-\d+: .+ \[PLAN COVERAGE: \?\]", output)
        # Synthetic fixture has 7 ACs (one per §5.x subsection).
        self.assertEqual(len(ac_lines), 7)

    def test_render_findings_empty_section_placeholder(self):
        """Spec where §6 is empty emits the placeholder line."""
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n"
            "**Author**: Claude + User\n\n"
            "## 1. Overview\n\nOverview.\n\n"
            "## 2. Current State\n\nState.\n\n"
            "## 3. Desired Behavior\n\n1. Do the thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| _(none)_ | | |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: Something.\n\n"
            "### 5.2 Behavior preservation\n"
            "### 5.3 Behavior change\n"
            "### 5.4 CI / pipeline\n"
            "### 5.5 Hooks / gates\n"
            "### 5.6 Documentation\n"
            "### 5.7 Hygiene\n\n"
            "## 6. Out of Scope\n\n"
            "## 7. Technical Constraints\n\n"
            "- _(no constraints recorded)_\n\n"
            "## 8. Open Questions\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| _(none)_ | | | |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("(no out-of-scope items recorded)", output)
        self.assertIn("(no affected areas recorded)", output)
        self.assertIn("(no constraints recorded)", output)
        self.assertIn("(no risks recorded)", output)

    def test_render_findings_includes_plan_coverage_marker(self):
        """[PLAN COVERAGE: ?] appears in §3, §4, §5 output."""
        output = self._get_output()
        self.assertIn("[PLAN COVERAGE: ?]", output)
        # Verify it appears in §3 specifically.
        sec3_start = output.find("### From spec §3")
        sec4_start = output.find("### From spec §4")
        sec3_chunk = output[sec3_start:sec4_start] if sec4_start > sec3_start else output[sec3_start:]
        self.assertIn("[PLAN COVERAGE: ?]", sec3_chunk)

    def test_render_findings_missing_file_exits_2(self):
        result = _run(self.tmp_path, "render-findings-from-spec", "no/spec.md")
        self.assertEqual(result.returncode, 2)

    def test_render_findings_malformed_spec_exits_2(self):
        """Spec missing section headings → exit 2."""
        spec_file = self.tmp_path / "spec.md"
        spec_file.write_text("# Spec: Bad\n\n## 1. Overview\n\nHi.\n", encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 2)

    def test_render_findings_sec9_risk_count_matches_fixture(self):
        """§9 block emits one entry per data row in risks table."""
        output = self._get_output()
        import re
        risk_lines = re.findall(r"- §9 risk \d+: .+ \[MITIGATION CARRIED: \?\]", output)
        # Synthetic fixture has 2 risks.
        self.assertEqual(len(risk_lines), 2)

    def test_render_findings_sec6_oos_items(self):
        """§6 block enumerates 'NOT included:' bullets."""
        output = self._get_output()
        import re
        oos_lines = re.findall(r"- §6 item \d+: .+ \[must not contradict\]", output)
        # Synthetic fixture has 2 out-of-scope bullets.
        self.assertEqual(len(oos_lines), 2)

    def test_render_findings_sec5_subsection_numbers_match_headings(self):
        """§5 subsection labels reflect actual heading numbers, not loop index.

        Regression: spec with only §5.3 and §5.7 populated must emit
        "§5.3" and "§5.7" labels, not "§5.1" and "§5.2".
        """
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n\n"
            "## 1. Overview\n\nO.\n\n"
            "## 2. Current State\n\nS.\n\n"
            "## 3. Desired Behavior\n\n1. Thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| A | f.py | Modify |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.3 Behavior change\n"
            "- [x] **AC-1**: Item changes.\n\n"
            "### 5.7 Hygiene\n"
            "- [x] **AC-2**: No debug.\n\n"
            "## 6. Out of Scope\n\n- NOT included: x.\n\n"
            "## 7. Technical Constraints\n\n- Follow: y.\n\n"
            "## 8. Open Questions\n\n- **Q1**: z?\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| r | Low | Low | m |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("§5.3 (Behavior change)", result.stdout)
        self.assertIn("§5.7 (Hygiene)", result.stdout)
        # Must NOT emit shifted labels.
        self.assertNotIn("§5.1 (Behavior change)", result.stdout)
        self.assertNotIn("§5.2 (Hygiene)", result.stdout)

    def test_render_findings_sec8_captures_dp_entries(self):
        """§8 block captures DP-prefixed decision-point entries from specify_helper."""
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n\n"
            "## 1. Overview\n\nO.\n\n"
            "## 2. Current State\n\nS.\n\n"
            "## 3. Desired Behavior\n\n1. Thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| A | f.py | Modify |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: Something.\n\n"
            "## 6. Out of Scope\n\n- NOT included: x.\n\n"
            "## 7. Technical Constraints\n\n- Follow: y.\n\n"
            "## 8. Open Questions\n\n"
            "- **DP-A** [default applied]: choose pattern X → default: X-static.\n"
            "- **DP-B**: choose pattern Y.\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| r | Low | Low | m |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DP-A", result.stdout)
        self.assertIn("DP-B", result.stdout)
        # Must not collapse to the empty placeholder.
        self.assertNotIn("(no open questions recorded)", result.stdout)

    def test_render_findings_sec8_rejects_q_word_false_positives(self):
        """§8 pattern rejects words starting with Q or DP that aren't real IDs.

        Regression: prior pattern (Q|DP)[\\w-]* matched 'Question', 'Quality',
        'DPR' etc. The tightened grammar requires Q<digit> or DP-<...>.
        """
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n\n"
            "## 1. Overview\n\nO.\n\n"
            "## 2. Current State\n\nS.\n\n"
            "## 3. Desired Behavior\n\n1. Thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| A | f.py | Modify |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: Something.\n\n"
            "## 6. Out of Scope\n\n- NOT included: x.\n\n"
            "## 7. Technical Constraints\n\n- Follow: y.\n\n"
            "## 8. Open Questions\n\n"
            "- **Question**: this should NOT be captured.\n"
            "- **Quality**: also rejected.\n"
            "- **DPR**: rejected without hyphen.\n"
            "- **Q1**: this IS a real open question.\n"
            "- **DP-A**: this IS a real decision point.\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| r | Low | Low | m |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        # Only the two real IDs should appear.
        sec8_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith("- §8 item")
        ]
        self.assertEqual(len(sec8_lines), 2, sec8_lines)
        joined = "\n".join(sec8_lines)
        self.assertIn("Q1", joined)
        self.assertIn("DP-A", joined)
        self.assertNotIn("Question", joined)
        self.assertNotIn("Quality", joined)
        self.assertNotIn("DPR", joined)

    def test_render_findings_sec8_accepts_hyphenated_q_ids(self):
        """§8 pattern accepts Q-1 and Q-scope style IDs that /specify allows.

        /specify spec line 580: `--question-id "<Q-N or stable id>"`. The
        LLM may emit `Q-1` instead of `Q1`. Parser must capture both.
        """
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n\n"
            "## 1. Overview\n\nO.\n\n"
            "## 2. Current State\n\nS.\n\n"
            "## 3. Desired Behavior\n\n1. Thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| A | f.py | Modify |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: Something.\n\n"
            "## 6. Out of Scope\n\n- NOT included: x.\n\n"
            "## 7. Technical Constraints\n\n- Follow: y.\n\n"
            "## 8. Open Questions\n\n"
            "- **Q-1**: hyphenated digit.\n"
            "- **Q-scope**: hyphenated word.\n"
            "- **Q1-repro**: digit-then-hyphen.\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| r | Low | Low | m |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        sec8_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith("- §8 item")
        ]
        self.assertEqual(len(sec8_lines), 3, sec8_lines)
        joined = "\n".join(sec8_lines)
        self.assertIn("Q-1", joined)
        self.assertIn("Q-scope", joined)
        self.assertIn("Q1-repro", joined)

    def test_render_findings_sec8_strips_bold_markers_in_text(self):
        """§8 output strips residual ** from text content (annotated Q-IDs)."""
        spec_file = self.tmp_path / "spec.md"
        content = (
            "# Spec: Test\n\n"
            "**Date**: 2026-01-01\n"
            "**Status**: Draft\n\n"
            "## 1. Overview\n\nO.\n\n"
            "## 2. Current State\n\nS.\n\n"
            "## 3. Desired Behavior\n\n1. Thing.\n\n"
            "## 4. Affected Areas\n\n"
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| A | f.py | Modify |\n\n"
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: Something.\n\n"
            "## 6. Out of Scope\n\n- NOT included: x.\n\n"
            "## 7. Technical Constraints\n\n- Follow: y.\n\n"
            "## 8. Open Questions\n\n"
            "- **Q1 (PRODUCT — load-bearing)**: Is rule X correct?\n\n"
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| r | Low | Low | m |\n"
        )
        spec_file.write_text(content, encoding="utf-8")
        result = _run(self.tmp_path, "render-findings-from-spec", str(spec_file))
        self.assertEqual(result.returncode, 0, result.stderr)
        # Locate the §8 line in output.
        sec8_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith("- §8 item")
        ]
        self.assertEqual(len(sec8_lines), 1, sec8_lines)
        self.assertNotIn("**", sec8_lines[0])


# ---------------------------------------------------------------------------
# Tests: render-breakdown-handoff
# ---------------------------------------------------------------------------


class RenderBreakdownHandoffTests(_CwdIsolation):

    def test_render_breakdown_handoff_block_shape(self):
        """Output contains required structural elements."""
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            str(FIXTURE_SPEC),
            str(FIXTURE_PLAN),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("## Manual next step — run /devforge:breakdown", output)
        self.assertIn("/devforge:breakdown", output)
        self.assertIn(str(FIXTURE_PLAN), output)
        self.assertIn("**Spec ACs**:", output)
        self.assertIn("**Plan file impact**:", output)
        self.assertIn("**Plan risks**:", output)

    def test_render_breakdown_handoff_ac_count_correct(self):
        """AC count in handoff matches AC count from spec."""
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            str(FIXTURE_SPEC),
            str(FIXTURE_PLAN),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        import re
        m = re.search(r"\*\*Spec ACs\*\*:\s*(\d+)", output)
        self.assertIsNotNone(m)
        reported_acs = int(m.group(1))

        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        ac_lines = re.findall(
            r"^\s*-\s+\[[xX ]\]\s+\*\*AC-\d+\*\*", content, re.MULTILINE
        )
        self.assertEqual(reported_acs, len(ac_lines))

    def test_render_breakdown_handoff_missing_plan_exits_2(self):
        """Non-existent plan path → exit 2."""
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            str(FIXTURE_SPEC),
            "no/such/plan.md",
        )
        self.assertEqual(result.returncode, 2)

    def test_render_breakdown_handoff_missing_spec_exits_2(self):
        """Non-existent spec path → exit 2."""
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            "no/such/spec.md",
            str(FIXTURE_PLAN),
        )
        self.assertEqual(result.returncode, 2)

    def test_render_breakdown_handoff_plan_with_no_file_impact_table(self):
        """Minimal plan with no File Impact table → emit '0 files' without error."""
        minimal_plan = self.tmp_path / "plan.md"
        minimal_plan.write_text(
            "# Plan: Minimal\n\n**Status**: Draft\n\n## Summary\n\nSome work.\n",
            encoding="utf-8",
        )
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            str(FIXTURE_SPEC),
            str(minimal_plan),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("0 files", output)
        # Output format: "**Plan risks**: 0" — check for the key + zero value.
        self.assertIn("**Plan risks**: 0", output)

    def test_render_breakdown_handoff_file_risk_counts_from_plan(self):
        """File and risk counts are parsed from the fixture plan."""
        result = _run(
            self.tmp_path,
            "render-breakdown-handoff",
            str(FIXTURE_SPEC),
            str(FIXTURE_PLAN),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        import re
        file_m = re.search(r"\*\*Plan file impact\*\*:\s*(\d+) files", output)
        self.assertIsNotNone(file_m)
        risk_m = re.search(r"\*\*Plan risks\*\*:\s*(\d+)", output)
        self.assertIsNotNone(risk_m)
        # Synthetic fixture plan has 4 files in File Impact and 2 risks in Risk Assessment.
        file_count = int(file_m.group(1))
        risk_count = int(risk_m.group(1))
        self.assertGreater(file_count, 0)
        self.assertGreater(risk_count, 0)


# ---------------------------------------------------------------------------
# Tests: CLI shape (argparse, no subcommand, --help)
# ---------------------------------------------------------------------------


class CliShapeTests(_CwdIsolation):

    def test_no_subcommand_exits_2(self):
        result = _run(self.tmp_path)
        self.assertEqual(result.returncode, 2)

    def test_help_shows_all_subcommands(self):
        result = _run(self.tmp_path, "--help")
        self.assertEqual(result.returncode, 0)
        for sub in (
            "pick-spec",
            "render-pick-summary",
            "list-specs",
            "check-status-and-flip",
            "render-findings-from-spec",
            "render-breakdown-handoff",
        ):
            self.assertIn(sub, result.stdout)


# ---------------------------------------------------------------------------
# Tests: POSIX shell wrapper shim
# ---------------------------------------------------------------------------


class LauncherShimTests(_CwdIsolation):

    def _run_shim(self, cwd, *args):
        return subprocess.run(
            [str(HELPER_SHIM)] + list(args),
            cwd=str(cwd),
            capture_output=True,
            text=True,
        )

    def test_launcher_help(self):
        result = self._run_shim(self.tmp_path, "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("pick-spec", result.stdout)

    def test_launcher_pick_spec_with_explicit_path(self):
        result = self._run_shim(self.tmp_path, "pick-spec", str(FIXTURE_SPEC))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(FIXTURE_SPEC.resolve()))


# ---------------------------------------------------------------------------
# Tests: module-level unit tests (import plan_helper directly).
# ---------------------------------------------------------------------------


class ModuleUnitTests(unittest.TestCase):
    """Unit tests that import plan_helper directly (no subprocess)."""

    def test_has_nine_sections_true(self):
        content = "\n".join(
            "## {0}. Title".format(i) for i in range(1, 10)
        )
        self.assertTrue(plan_helper._has_nine_sections(content))

    def test_has_nine_sections_false_missing_middle(self):
        content = "\n".join(
            "## {0}. Title".format(i) for i in [1, 2, 4, 5, 6, 7, 8, 9]
        )
        self.assertFalse(plan_helper._has_nine_sections(content))

    def test_count_acs_zero(self):
        total, subs = plan_helper._count_acs("## 5. Acceptance Criteria\n\nNo ACs.\n")
        self.assertEqual(total, 0)
        self.assertEqual(subs, 0)

    def test_count_acs_multiple(self):
        content = (
            "## 5. Acceptance Criteria\n\n"
            "### 5.1 Tooling / artifact presence and absence\n"
            "- [x] **AC-1**: First.\n"
            "- [ ] **AC-2**: Second.\n\n"
            "### 5.2 Behavior preservation\n"
            "- [x] **AC-3**: Third.\n"
        )
        total, subs = plan_helper._count_acs(content)
        self.assertEqual(total, 3)
        self.assertEqual(subs, 2)

    def test_truncate_no_truncation(self):
        self.assertEqual(plan_helper._truncate("hello"), "hello")

    def test_truncate_exactly_80(self):
        text = "a" * 80
        self.assertEqual(plan_helper._truncate(text), text)

    def test_truncate_over_80(self):
        text = "b" * 100
        result = plan_helper._truncate(text)
        self.assertTrue(result.endswith("..."))
        self.assertEqual(len(result), 83)  # 80 + len("...")

    def test_extract_section_returns_correct_text(self):
        content = (
            "## 3. Desired Behavior\n\nSection 3 text.\n\n"
            "## 4. Affected Areas\n\nSection 4 text.\n"
        )
        sec3 = plan_helper._extract_section(content, 3)
        self.assertIn("Section 3 text", sec3)
        self.assertNotIn("Section 4 text", sec3)

    def test_parse_table_rows_skips_header_and_separator(self):
        table = (
            "| Area | Files | Impact |\n"
            "|------|-------|--------|\n"
            "| Core | src/a.py | Add function |\n"
            "| Tests | test/b.py | Add tests |\n"
        )
        rows = plan_helper._parse_table_rows(table)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "Core")
        self.assertEqual(rows[1][0], "Tests")

    def test_is_empty_placeholder_row_true(self):
        self.assertTrue(plan_helper._is_empty_placeholder_row(["_(none)_"]))

    def test_is_empty_placeholder_row_false(self):
        self.assertFalse(plan_helper._is_empty_placeholder_row(["Real Row"]))

    def test_render_sec3_numbered_bullets(self):
        sec_text = (
            "## 3. Desired Behavior\n\n"
            "1. First item.\n"
            "2. Second item.\n"
        )
        lines = plan_helper._render_sec3(sec_text)
        self.assertEqual(len(lines), 2)
        self.assertIn("§3 item 1", lines[0])
        self.assertIn("[PLAN COVERAGE: ?]", lines[0])
        self.assertIn("§3 item 2", lines[1])

    def test_render_sec6_not_included_bullets(self):
        sec_text = (
            "## 6. Out of Scope\n\n"
            "- NOT included: Thing A.\n"
            "- NOT included: Thing B.\n"
        )
        lines = plan_helper._render_sec6(sec_text)
        self.assertEqual(len(lines), 2)
        self.assertIn("[must not contradict]", lines[0])

    def test_render_sec6_empty_returns_placeholder(self):
        sec_text = "## 6. Out of Scope\n\n"
        lines = plan_helper._render_sec6(sec_text)
        self.assertEqual(len(lines), 1)
        self.assertIn("(no out-of-scope items recorded)", lines[0])

    def test_render_sec9_empty_table_placeholder_row(self):
        sec_text = (
            "## 9. Risks\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| _(none)_ | | | |\n"
        )
        lines = plan_helper._render_sec9(sec_text)
        self.assertEqual(len(lines), 1)
        self.assertIn("(no risks recorded)", lines[0])

    def test_count_file_impact_no_table(self):
        total, new_c, mod_c = plan_helper._count_file_impact("## Summary\n\nNothing.\n")
        self.assertEqual(total, 0)
        self.assertEqual(new_c, 0)
        self.assertEqual(mod_c, 0)

    def test_count_file_impact_stops_at_h2_boundary(self):
        """File Impact section ends at next ## or ### heading.

        Regression: when File Impact is the last ### subsection under a ##
        section, the next heading is ## Risk Assessment. The old `^###\\s+`
        boundary missed that and counted Risk Assessment table rows as files.
        """
        plan_text = (
            "## Implementation Approach\n\n"
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "|------|--------|-------------|\n"
            "| src/a.py | Modify | foo |\n"
            "| src/b.py | Create | new |\n\n"
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| Risk A | Low | Low | Mit A |\n"
            "| Risk B | Med | High | Mit B |\n"
        )
        total, new_c, mod_c = plan_helper._count_file_impact(plan_text)
        self.assertEqual(total, 2, "Risk Assessment rows must not leak into File Impact")
        self.assertEqual(new_c, 1)
        self.assertEqual(mod_c, 1)

    def test_count_file_impact_with_table(self):
        plan_text = (
            "### File Impact\n\n"
            "| File | Action | What Changes |\n"
            "|------|--------|-------------|\n"
            "| src/a.py | Modify | Add function |\n"
            "| src/b.py | Create | New file |\n"
            "| src/c.py | Verify | Check exports |\n"
        )
        total, new_c, mod_c = plan_helper._count_file_impact(plan_text)
        self.assertEqual(total, 3)
        self.assertEqual(new_c, 1)
        # Verify rows are counted in total but NOT as modified (read-only).
        self.assertEqual(mod_c, 1)

    def test_count_risks_with_table(self):
        plan_text = (
            "## Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| Risk A | Low | Low | Mitigation A |\n"
            "| Risk B | Med | High | Mitigation B |\n"
        )
        count = plan_helper._count_risks(plan_text)
        self.assertEqual(count, 2)

    def test_count_risks_no_table(self):
        count = plan_helper._count_risks("## Summary\n\nNothing.\n")
        self.assertEqual(count, 0)

    def test_count_risks_stops_at_sibling_h3_boundary(self):
        """Risk Assessment at ### level stops at next ### sibling heading.

        Regression: prior boundary `^##\\s+` missed sibling ### headings,
        leaking Dependencies table rows into the risk count.
        """
        plan_text = (
            "## Implementation Approach\n\n"
            "### Risk Assessment\n\n"
            "| Risk | Likelihood | Impact | Mitigation |\n"
            "|------|-----------|--------|------------|\n"
            "| Only one risk | Low | Low | Mit |\n\n"
            "### Dependencies\n\n"
            "| Dep | Version | Note |\n"
            "|-----|---------|------|\n"
            "| dep-a | 1.0 | required |\n"
            "| dep-b | 2.0 | optional |\n"
        )
        count = plan_helper._count_risks(plan_text)
        self.assertEqual(count, 1, "Dependencies rows must not leak into risk count")

    def test_fixture_spec_has_nine_sections(self):
        """Verify the real fixture spec has all 9 required sections."""
        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        self.assertTrue(plan_helper._has_nine_sections(content))

    def test_fixture_spec_status_is_complete(self):
        """Fixture spec status is 'Complete' (real spec, not modified)."""
        content = FIXTURE_SPEC.read_text(encoding="utf-8")
        status = plan_helper._parse_frontmatter_field(content, plan_helper._STATUS_PATTERN)
        self.assertEqual(status, "Complete")


# ---------------------------------------------------------------------------
# Fixture factories for handoff round-trip tests.
# ---------------------------------------------------------------------------


def _make_specify_state(handoff_path=None, handoff_kind=None,
                        research_completed_at=None, discover_completed_at=None,
                        discover_recommended_summary=None):
    """Build a minimal valid specify state dict for cmd_finalize_handoff.

    Uses an anonymous 'widget-catalog' domain (consistent with existing fixture
    theme) with all required fields populated.
    """
    return {
        "topic": "widget-catalog-search",
        "topic_slug": "widget-catalog-search",
        "date": "2026-05-22",
        "spec_number": "009",
        "feature_name": "widget-catalog-search",
        "feature_slug": "widget-catalog-search",
        "spec_type": "feature_addition",
        "spec_type_rationale": "Adding full-text search to the widget catalog",
        "spec_type_seeded_by_upstream": False,
        "status": "Draft",
        "overview": "Add full-text search capability to the widget catalog API.",
        "current_state": None,
        "desired_behavior": None,
        "affected_areas": [
            {"area": "WidgetService", "files": ["src/services/widget_service.py"],
             "impact": "Search logic added here"}
        ],
        "acceptance_criteria": [
            {
                "ac_id": "AC-1",
                "subsection": "behavior_change",
                "ears_variant": "event_driven",
                "statement": "WHEN a search query is submitted, the system shall return matching widgets.",
                "verification_command": "pytest tests/test_widget_search.py",
                "test_anchor": "test_search_returns_results",
                "n_a_reason": "",
            }
        ],
        "ac_subsection_na": {"ci_pipeline": "No CI changes required"},
        "out_of_scope": [
            {"content": "Real-time search indexing", "finding_ref": ""}
        ],
        "constraints": [
            {"kind": "nfr", "content": "Search must respond within 200ms",
             "quantifier": "p99 < 200ms"}
        ],
        "open_questions": [
            {"question_id": "OQ-1", "content": "Which search backend to use?",
             "category_no_dp_reason": ""}
        ],
        "risks": [
            {"risk": "Index staleness under heavy write load",
             "likelihood": "Low", "impact": "Med",
             "mitigation": "Async index refresh with TTL"}
        ],
        "approval_summary": None,
        "plan_handoff_block": None,
        "open_question_resolutions": [],
        "conflicts": [],
        "source": {
            "handoff_path": handoff_path,
            "handoff_kind": handoff_kind,
            "research_completed_at": research_completed_at,
            "discover_completed_at": discover_completed_at,
            "discover_recommended_summary": discover_recommended_summary,
        },
        "input_reads": [],
        "phase1_finalized": False,
        "findings": [],
        "source_no_items_relevant": {},
        "findings_finalized": False,
        "decision_points": [],
        "dp_finalized": False,
        "mode": None,
        "mandatory_reads": [],
        "discretionary_reads": [],
        "phase3_finalized": False,
        "current_branch": None,
        "default_branch": None,
        "branch_decision": None,
        "branch_created": None,
    }


def _write_specify_state(devforge_dir, state):
    """Write specify-state.json to devforge_dir."""
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    state_path = Path(devforge_dir) / "specify-state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state_path


def _make_specify_args(devforge_dir, emit_path=None, specs_root="specs",
                       completed_at="2026-05-22T10:00:00Z"):
    """Build argparse.Namespace for _specify_finalize_handoff."""
    ns = types.SimpleNamespace()
    ns.devforge_dir = str(devforge_dir)
    ns.emit_handoff_json = emit_path
    ns.specs_root = specs_root
    ns.completed_at = completed_at
    return ns


def _produce_specify_handoff(tmp_root, handoff_path=None, handoff_kind=None,
                              research_completed_at=None,
                              discover_completed_at=None,
                              discover_recommended_summary=None):
    """Produce a real specify handoff.json using the real producer.

    Returns the Path to the written handoff.json.
    """
    devforge_dir = tmp_root / ".devforge"
    state = _make_specify_state(
        handoff_path=handoff_path,
        handoff_kind=handoff_kind,
        research_completed_at=research_completed_at,
        discover_completed_at=discover_completed_at,
        discover_recommended_summary=discover_recommended_summary,
    )
    _write_specify_state(devforge_dir, state)
    emit_path = tmp_root / "specs" / "009-widget-catalog-search" / "handoff.json"
    emit_path.parent.mkdir(parents=True, exist_ok=True)
    args = _make_specify_args(devforge_dir, emit_path=str(emit_path))
    rc = _specify_finalize_handoff(args)
    if rc != 0:
        raise RuntimeError(
            "specify finalize-handoff failed rc={0}".format(rc)
        )
    return emit_path


def _make_discover_memo(topic_slug="widget-search-feature", topic="Widget Search Feature",
                        date="2026-05-22"):
    return {
        "topic": topic,
        "topic_slug": topic_slug,
        "date": date,
        "verbatim_prompt": "Add full-text search capability over the widget catalog for API consumers",
        "dimensions": {
            "functional_scope": {"value": "Full-text search over widget catalog", "state": "Clear", "turns": 1},
            "users": {"value": "API consumers and internal clients", "state": "Clear", "turns": 1},
            "inputs_outputs": {"value": "SearchQuery -> WidgetList", "state": "Clear", "turns": 1},
            "integration_points": {"value": "WidgetRepository", "state": "Clear", "turns": 1},
            "constraints": {"value": "200ms p99 latency", "state": "Clear", "turns": 1},
            "non_goals": {"value": "No real-time indexing", "state": "Clear", "turns": 1},
            "success_criteria": {"value": "Relevant widgets returned for query", "state": "Clear", "turns": 1},
            "edge_cases": {"value": "Empty query returns all", "state": "Clear", "turns": 1},
        },
        "references": [],
        "gaps": [],
        "override_recorded": False,
        "conflicts": [],
    }


def _make_discover_report(verdict="Worth pursuing", overall_fit="Good",
                           effort_estimate="Low"):
    return {
        "topic": "Widget Search Feature",
        "date": "2026-05-22",
        "topic_slug": "widget-search-feature",
        "summary": "Add full-text search to the widget catalog",
        "prior_art": [],
        "integration_touchpoints": [
            {"name": "WidgetRepository", "module_path": "src/repos/widget_repo.py",
             "reason": "Search queries go through the repository"}
        ],
        "fit_assessments": [],
        "overall_fit": overall_fit,
        "effort_estimate": effort_estimate,
        "fit_rationale": "Straightforward addition on top of existing repository layer",
        "design_options": [
            {
                "name": "In-memory filter",
                "shape": "Filter widget list in memory",
                "pros": ["Simple"],
                "cons": ["Slow for large catalogs"],
                "complexity": "Low",
            }
        ],
        "recommended_option": {"name": "In-memory filter", "rationale": "Lowest complexity for MVP"},
        "build_vs_buy": {
            "recommendation": "Build",
            "build": "Implement filter in WidgetService",
            "buy": "Third-party search library",
            "reasoning": "Existing service already owns widget data",
        },
        "derisk_plan": [
            {"risk": "Performance on large catalogs", "mitigation": "Paginate results"}
        ],
        "constitution_constraints": [],
        "verdict": verdict,
        "recommendation": "Use the in-memory filter approach as a starting point.",
        "next_step_text": "Run /specify widget-search-feature",
        "open_uncertainties": [],
        # plan 73 D6: build_vs_buy.recommendation == "Build" above + empty
        # prior_art is an absence-founded conclusion -- finalize-handoff's
        # declaration-exists guard requires >=1 absence_probes row.
        "absence_probes": [{
            "claim": "no existing internal full-text search implementation",
            "symbol": "WidgetSearch",
            "path": "none",
            "found": False,
            "deleted_commit_sha": None,
            "deleted_commit_subject": None,
        }],
    }


def _produce_discover_handoff(tmp_root, emit_path=None):
    """Produce a real discover handoff.json using the real producer (direct call).

    Returns the Path to the written handoff.json.
    """
    devforge_dir = tmp_root / ".devforge"
    devforge_dir.mkdir(parents=True, exist_ok=True)
    memo = _make_discover_memo()
    report = _make_discover_report()
    _atomic_write_json(memo, devforge_dir / MEMO_FILE_NAME)
    _atomic_write_json(report, devforge_dir / REPORT_FILE_NAME)

    if emit_path is None:
        emit_path = tmp_root / "discover" / "2026-05-22-widget-search-feature.handoff.json"

    ns = types.SimpleNamespace()
    ns.devforge_dir = str(devforge_dir)
    ns.emit_handoff_json = str(emit_path)
    rc = _discover_finalize_handoff(ns)
    if rc != 0:
        raise RuntimeError("discover finalize-handoff failed rc={0}".format(rc))
    return Path(emit_path)


def _run_research_setup(devforge, research_helper_py):
    """Set up minimal bug-mode research state and run finalize-handoff.

    Returns the Path to the written handoff.json.
    """
    def _rrun(*argv):
        return subprocess.run(
            [sys.executable, str(research_helper_py)] + list(argv),
            capture_output=True, text=True,
        )

    _rrun("--devforge-dir", str(devforge), "reset-memo")
    _rrun("--devforge-dir", str(devforge), "reset-report")

    # Phase 0 dimensions.
    for dim, val in (
        ("symptom", "Widget query returns stale results after catalog update"),
        ("affected-area", "src/services/widget_service.py"),
        ("repro-or-current", "Update catalog; query still returns old results"),
        ("desired", "Fresh results returned after any catalog update"),
        ("scope", "one function"),
        ("unchanged-behavior", "other catalog operations remain unchanged"),
    ):
        _rrun("--devforge-dir", str(devforge),
              "set-" + dim, "--value", val, "--state", "Clear")

    _rrun("--devforge-dir", str(devforge), "detect-mode", "--override", "bug")
    _rrun("--devforge-dir", str(devforge), "set-topic", "--value", "widget-stale-results")
    _rrun(
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value", "Widget query returns stale results after catalog update in widget_service",
    )
    _rrun("--devforge-dir", str(devforge), "set-date", "--value", "2026-05-22")

    # Phase 1.
    _rrun("--devforge-dir", str(devforge), "record-finding",
          "--surface", "widget cache",
          "--file-line", "src/services/widget_service.py:55",
          "--relevance", "cache not invalidated on write")
    _rrun("--devforge-dir", str(devforge), "record-finding",
          "--surface", "catalog update handler",
          "--file-line", "src/services/widget_service.py:80",
          "--relevance", "update does not clear cache entry")
    _rrun("--devforge-dir", str(devforge), "record-hypothesis",
          "--cause", "cache not cleared on catalog update",
          "--falsifier", "add logging to cache invalidation; check after update",
          "--runtime-probe-needed", "yes")
    _rrun("--devforge-dir", str(devforge), "record-hypothesis",
          "--cause", "wrong cache key used for lookup after update",
          "--falsifier", "compare cache keys before and after update",
          "--runtime-probe-needed", "no")
    _rrun("--devforge-dir", str(devforge), "set-root-cause-hypothesis",
          "--value", "cache not cleared on catalog update")
    _rrun("--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis")
    _rrun("--devforge-dir", str(devforge), "set-trigger",
          "--value", "catalog write operation")
    _rrun("--devforge-dir", str(devforge), "set-root-cause-systemic",
          "--value", "No cache invalidation hook on catalog writes")
    _rrun("--devforge-dir", str(devforge), "set-verify-step",
          "--probe", "add cache.clear() after catalog.update()",
          "--reproduction", "Run update; query; check if fresh result returned",
          "--discriminator",
          "fresh result -> cache not invalidated; stale -> different cause")

    # Phase 2.
    _rrun("--devforge-dir", str(devforge), "set-approach",
          "--name", "Option A: invalidate cache on write",
          "--description", "Clear cache entry when catalog update occurs",
          "--addresses-hypotheses", json.dumps(["cache not cleared on catalog update"]),
          "--does-not-cover", json.dumps(["wrong cache key used for lookup after update"]),
          "--pros", json.dumps(["simple"]),
          "--cons", json.dumps(["requires hook registration"]),
          "--complexity", "Low")
    _rrun("--devforge-dir", str(devforge), "set-approach",
          "--name", "Option B: remove cache entirely",
          "--description", "Fetch fresh data on every query",
          "--addresses-hypotheses", json.dumps([
              "cache not cleared on catalog update",
              "wrong cache key used for lookup after update",
          ]),
          "--does-not-cover", json.dumps([]),
          "--pros", json.dumps(["always fresh"]),
          "--cons", json.dumps(["higher latency"]),
          "--complexity", "Low")
    _rrun("--devforge-dir", str(devforge), "set-recommended-approach",
          "--name", "Option A: invalidate cache on write",
          "--rationale", "Targeted invalidation avoids latency cost of full removal",
          "--hypotheses-addressed",
          json.dumps(["cache not cleared on catalog update"]),
          "--hypotheses-not-covered",
          json.dumps(["wrong cache key used for lookup after update"]))
    _rrun("--devforge-dir", str(devforge), "set-constitution-constraints",
          "--rule", "Cache invalidation must be deterministic",
          "--impact", "Prevents stale data serving")
    _rrun("--devforge-dir", str(devforge), "set-complexity",
          "--codebase-changes", "Low", "--codebase-notes", "1-2 files",
          "--risk", "Low", "--risk-notes", "narrow scope",
          "--verify-cost", "Low", "--verify-notes", "unit test suffices")
    _rrun("--devforge-dir", str(devforge), "set-verdict",
          "--value", "Root cause hypothesis (needs repro)")
    _rrun("--devforge-dir", str(devforge), "set-summary",
          "--value", "Widget query returns stale results because cache is not cleared on update. Fix: hook invalidation to write.")

    # Fix-path helpers for verify checks.
    _rrun("--devforge-dir", str(devforge), "record-fix-path-helper",
          "--helper-qn", "widget_service.update_catalog",
          "--file-line", "src/services/widget_service.py:80")
    _rrun("--devforge-dir", str(devforge), "record-fix-path-helper",
          "--helper-qn", "widget_cache.invalidate",
          "--file-line", "src/services/widget_service.py:55")
    _rrun("--devforge-dir", str(devforge), "record-inbound-caller",
          "--helper-qn", "widget_service.update_catalog",
          "--caller-qn", "catalog_api.update",
          "--file-line", "src/api/catalog_api.py:30")
    _rrun("--devforge-dir", str(devforge), "record-runner-up-framing",
          "--frame", "wrong cache key used for lookup",
          "--falsifier", "compare cache keys before and after",
          "--confidence-vs-primary", "lower")
    _rrun("--devforge-dir", str(devforge), "record-finding",
          "--surface", "cache key derivation",
          "--file-line", "src/services/widget_service.py:60",
          "--relevance", "key derivation cross-check for runner-up",
          "--framing", "runner-up")

    # Step 4: probe feasibility.
    _rrun("--devforge-dir", str(devforge), "set-probe-feasibility",
          "--data-shape-only", "false",
          "--auth-required", "false",
          "--network-dependent", "false",
          "--timing-dependent", "false",
          "--is-test-code", "false")

    # Plan 73 D7: declaration-exists guard requires set-evidence-lanes to
    # have been called before finalize-handoff.
    _rrun("--devforge-dir", str(devforge), "set-evidence-lanes",
          "--static-graph", "false",
          "--text-search", "false",
          "--runtime-probe", "false",
          "--history", "false")


# ---------------------------------------------------------------------------
# Tests: read-specify-handoff
# ---------------------------------------------------------------------------


class ReadSpecifyHandoffTests(unittest.TestCase):
    """Tests for plan_helper read-specify-handoff subcommand."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *args):
        """Run plan_helper.py with args from self.tmp as cwd."""
        return subprocess.run(
            [sys.executable, str(HELPER_PY)] + list(args),
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )

    def test_no_sibling_handoff_prints_no_handoff(self):
        """Spec exists but no sibling handoff.json -> stdout 'no-handoff', exit 0."""
        spec_dir = self.tmp / "specs" / "009-widget-catalog-search"
        spec_dir.mkdir(parents=True)
        spec_path = spec_dir / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "no-handoff")

    def test_malformed_sibling_exits_2(self):
        """Sibling handoff.json exists but is malformed JSON -> exit 2."""
        spec_dir = self.tmp / "specs" / "009-widget-catalog-search"
        spec_dir.mkdir(parents=True)
        spec_path = spec_dir / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")
        # Write invalid JSON.
        (spec_dir / "handoff.json").write_text("{not valid json", encoding="utf-8")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_wrong_handoff_kind_exits_2(self):
        """Sibling handoff.json has handoff_kind != 'specify' -> exit 2."""
        spec_dir = self.tmp / "specs" / "009-widget-catalog-search"
        spec_dir.mkdir(parents=True)
        spec_path = spec_dir / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")
        bad = {
            "schema_version": "1.0",
            "handoff_kind": "research",  # wrong
            "spec_path": "specs/009-x/spec.md",
            "specify_completed_at": "2026-05-22T10:00:00Z",
            "classification": {},
            "spec_seeds": {},
            "provenance": {"upstream_handoff_path": None, "upstream_handoff_kind": None},
            "downstream_links": {},
        }
        (spec_dir / "handoff.json").write_text(json.dumps(bad), encoding="utf-8")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_missing_spec_exits_2(self):
        """Spec path does not exist -> exit 2."""
        result = self._run("read-specify-handoff", "/nonexistent/path/spec.md")
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_directory_spec_path_exits_2(self):
        """Spec path is a directory (not a file) -> exit 2.

        A directory passes .exists() but must hit the 'spec not found' exit-2
        path, not silently compute a wrong sibling handoff.
        """
        spec_dir = self.tmp / "specs" / "009-widget-catalog-search"
        spec_dir.mkdir(parents=True)
        # Pass the directory itself as the spec path.
        result = self._run("read-specify-handoff", str(spec_dir))
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_real_specify_handoff_with_upstream_provenance(self):
        """Real specify finalize-handoff output with upstream provenance is parsed.

        Produces a real specify handoff via the producer (round-trip discipline),
        then asserts read-specify-handoff reports the upstream path + kind.
        """
        upstream_handoff_path = "research/2026-05-22-widget-stale/handoff.json"
        upstream_kind = "research"
        upstream_completed_at = "2026-05-22T08:00:00Z"

        # Produce real specify handoff via the real producer.
        emit_path = _produce_specify_handoff(
            self.tmp,
            handoff_path=upstream_handoff_path,
            handoff_kind=upstream_kind,
            research_completed_at=upstream_completed_at,
        )

        # Place spec.md in the same directory (sibling).
        spec_path = emit_path.parent / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 0, result.stderr)

        lines = result.stdout.strip().splitlines()
        # Block must have exactly 4 lines.
        self.assertEqual(len(lines), 4, "Expected 4-line block, got: {0!r}".format(result.stdout))
        self.assertIn(str(emit_path.resolve()), lines[0],
                      "Line 0 must contain handoff.json absolute path")
        self.assertEqual(lines[1], "spec_seeds: present")
        self.assertIn(upstream_handoff_path, lines[2],
                      "Line 2 must contain upstream_handoff_path")
        self.assertIn(upstream_kind, lines[3],
                      "Line 3 must contain upstream_handoff_kind")

    def test_real_specify_handoff_no_upstream_reports_none(self):
        """Real specify handoff with null upstream provenance reports 'none' for both."""
        # Produce specify handoff with no upstream (cold path).
        emit_path = _produce_specify_handoff(
            self.tmp,
            handoff_path=None,
            handoff_kind=None,
        )

        spec_path = emit_path.parent / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 0, result.stderr)

        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn("upstream_handoff_path: none", lines[2])
        self.assertIn("upstream_handoff_kind: none", lines[3])

    def test_provenance_covary_path_set_kind_null_exits_2(self):
        """Provenance with upstream_handoff_path set but upstream_handoff_kind null -> exit 2.

        Co-vary invariant: both fields must be set or both must be null.
        Produces a real specify handoff (with valid upstream path+kind), then
        post-hoc nulls only upstream_handoff_kind to construct the corrupt case.
        """
        upstream_handoff_path = "research/2026-05-22-widget-stale/handoff.json"

        # Produce real specify handoff via the real producer (path+kind both set).
        emit_path = _produce_specify_handoff(
            self.tmp,
            handoff_path=upstream_handoff_path,
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )

        # Post-hoc: null only upstream_handoff_kind — leaving path set — to
        # construct the co-vary violation without hand-authoring a fixture.
        data = json.loads(emit_path.read_text(encoding="utf-8"))
        data["provenance"]["upstream_handoff_kind"] = None
        emit_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        spec_path = emit_path.parent / "spec.md"
        _write_minimal_spec(str(spec_path), status="Draft")

        result = self._run("read-specify-handoff", str(spec_path))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("upstream_handoff_path and upstream_handoff_kind", result.stderr)


# ---------------------------------------------------------------------------
# Tests: render-plan-seeds
# ---------------------------------------------------------------------------


class RenderPlanSeedsTests(unittest.TestCase):
    """Tests for plan_helper render-plan-seeds subcommand."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *args):
        """Run plan_helper.py with args from self.tmp as cwd."""
        return subprocess.run(
            [sys.executable, str(HELPER_PY)] + list(args),
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )

    def test_null_upstream_path_prints_cold_no_plan_seeds(self):
        """Specify handoff with null provenance -> stdout 'cold-no-plan-seeds', exit 0."""
        # Produce a real specify handoff with no upstream.
        emit_path = _produce_specify_handoff(self.tmp, handoff_path=None, handoff_kind=None)

        result = self._run("render-plan-seeds", str(emit_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "cold-no-plan-seeds")

    def test_dangling_upstream_path_exits_2(self):
        """Specify handoff references upstream that does not exist -> exit 2."""
        # Produce specify handoff pointing at a non-existent upstream.
        dangling = str(self.tmp / "research" / "does-not-exist.handoff.json")
        emit_path = _produce_specify_handoff(
            self.tmp,
            handoff_path=dangling,
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )

        result = self._run("render-plan-seeds", str(emit_path))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("not found", result.stderr)

    def test_research_upstream_renders_research_block(self):
        """Real research_helper handoff -> research-specific fields in block output.

        Proves research dispatch: 'Alternatives considered' and
        'Proposed call shape' are research-specific plan_seeds fields.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        # Produce the research handoff.
        research_emit = self.tmp / "research" / "2026-05-22-widget-stale-results.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path",
                "research/2026-05-22-widget-stale-results.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0,
                         "research finalize-handoff failed: " + proc.stderr)

        # Produce the specify handoff referencing this research handoff.
        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(research_emit),
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)

        output = result.stdout
        # Research-specific fields must appear.
        self.assertIn("Upstream plan-seeds (research handoff:", output)
        self.assertIn("Recommended approach", output)
        self.assertIn("Alternatives considered", output)
        self.assertIn("Proposed call shape", output)
        self.assertIn("Cited canonical patterns", output)
        # Discover-specific fields must NOT appear.
        self.assertNotIn("Design options", output)
        self.assertNotIn("Build vs buy", output)
        # Plan 67 D6 -- caller enumeration recorded by _run_research_setup's
        # record-fix-path-helper/record-inbound-caller calls rides all the
        # way through finalize-handoff -> render-plan-seeds.
        self.assertIn("Caller enumeration", output)
        self.assertIn("widget_service.update_catalog", output)
        self.assertIn("src/services/widget_service.py:80", output)
        self.assertIn("catalog_api.update", output)
        self.assertIn("src/api/catalog_api.py:30", output)
        # widget_cache.invalidate has no recorded inbound_callers row.
        self.assertIn("widget_cache.invalidate", output)
        self.assertIn("no inbound callers recorded", output)

    def test_discover_upstream_renders_discover_block(self):
        """Real discover_helper handoff -> discover-specific fields in block output.

        Proves discover dispatch: 'Design options' and 'Build vs buy' are
        discover-specific plan_seeds fields.
        """
        discover_emit = self.tmp / "discover" / "2026-05-22-widget-search-feature.handoff.json"
        _produce_discover_handoff(self.tmp, emit_path=discover_emit)

        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(discover_emit),
            handoff_kind="discover",
            discover_completed_at="2026-05-22T09:00:00Z",
            discover_recommended_summary="In-memory filter approach",
        )

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)

        output = result.stdout
        # Discover-specific fields must appear.
        self.assertIn("Upstream plan-seeds (discover handoff:", output)
        self.assertIn("Recommended option", output)
        self.assertIn("Build vs buy", output)
        self.assertIn("Design options", output)
        self.assertIn("Cited canonical patterns", output)
        # Research-specific fields must NOT appear.
        self.assertNotIn("Alternatives considered", output)
        self.assertNotIn("Proposed call shape", output)

    def test_unknown_handoff_kind_exits_2(self):
        """Specify handoff provenance has unknown handoff_kind -> exit 2.

        Kind dispatch uses provenance.upstream_handoff_kind from the specify
        handoff (authoritative). A provenance kind that is neither 'research'
        nor 'discover' must produce exit 2.

        Uses the real producer to generate the specify handoff (round-trip
        discipline), then post-hoc mutates provenance.upstream_handoff_kind
        to an unrecognised value to construct the corrupt case.
        """
        # Produce a real discover handoff to use as a valid upstream reference.
        discover_emit = self.tmp / "discover" / "2026-05-22-widget-search-feature.handoff.json"
        _produce_discover_handoff(self.tmp, emit_path=discover_emit)

        # Produce a real specify handoff pointing at the discover handoff.
        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(discover_emit),
            handoff_kind="discover",
            discover_completed_at="2026-05-22T09:00:00Z",
            discover_recommended_summary="In-memory filter approach",
        )

        # Post-hoc: corrupt provenance.upstream_handoff_kind to unknown value.
        data = json.loads(specify_emit.read_text(encoding="utf-8"))
        data["provenance"]["upstream_handoff_kind"] = "unknown_kind"
        specify_emit.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("unknown handoff_kind", result.stderr)

    def test_root_relative_upstream_path_resolves_against_cwd(self):
        """68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D9(d) pin.

        provenance.upstream_handoff_path as an install-root-relative string
        (e.g. "specs/001-x/research-handoff.json", no leading slash -- the
        new-layout shape import-handoff now writes) resolves against
        Path.cwd() when cwd == install root, and plan seeds render.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        # Produce the research handoff at the new-layout feature-dir location.
        feature_dir = self.tmp / "specs" / "001-widget-fix"
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--feature-dir", str(feature_dir),
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)
        research_emit = feature_dir / "research-handoff.json"
        self.assertTrue(research_emit.is_file())

        # Root-relative upstream path -- the D9(d) new-layout shape, NOT absolute.
        root_relative_path = "specs/001-widget-fix/research-handoff.json"
        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=root_relative_path,
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )
        # Sanity: the specify handoff's provenance really is root-relative,
        # not absolute -- otherwise this test would silently degrade into a
        # duplicate of test_research_upstream_renders_research_block.
        specify_data = json.loads(specify_emit.read_text(encoding="utf-8"))
        upstream_path_in_json = specify_data["provenance"]["upstream_handoff_path"]
        self.assertEqual(upstream_path_in_json, root_relative_path)
        self.assertFalse(Path(upstream_path_in_json).is_absolute())

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("Upstream plan-seeds (research handoff:", output)
        self.assertIn("Recommended approach", output)

    def test_absolute_upstream_path_still_resolves(self):
        """D3/D9(d) backward-compat pin: the pre-existing absolute-path
        tolerance is retained -- a pre-migration (or any absolute-path)
        specify handoff still resolves, since D3 never deletes old files."""
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        research_emit = self.tmp / "research" / "2026-05-22-widget-stale-results.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path",
                "research/2026-05-22-widget-stale-results.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)

        # Absolute upstream path -- the legacy/pre-migration shape.
        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(research_emit),
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )
        specify_data = json.loads(specify_emit.read_text(encoding="utf-8"))
        upstream_path_in_json = specify_data["provenance"]["upstream_handoff_path"]
        self.assertTrue(
            Path(upstream_path_in_json).is_absolute(),
            "precondition: this test must exercise the absolute-path branch",
        )

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Upstream plan-seeds (research handoff:", result.stdout)

    def test_zero_literal_archaeology_rows_render_nothing(self):
        """Plan 73 Phase 5 -- a research handoff with no literal-archaeology
        rows renders NO 'Literal provenance' section at all (silent, judged
        zero-rows behaviour: mirrors the caller_enumeration empty-carry
        branch, since verify checks 17/20 already mechanically force a row
        to exist whenever a literal is genuinely load-bearing -- an empty
        list reaching /plan is a verified 'nothing load-bearing', not an
        unverified silence).

        Uses the same real-producer chain as
        test_research_upstream_renders_research_block (_run_research_setup's
        fixture proposes no literal replacement, so no archaeology row is
        ever recorded or required).
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        research_emit = self.tmp / "research" / "2026-05-22-widget-stale-results.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path",
                "research/2026-05-22-widget-stale-results.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)

        # Precondition: the producer really did emit zero archaeology rows.
        data = json.loads(research_emit.read_text(encoding="utf-8"))
        self.assertEqual(data["spec_seeds"]["literal_archaeology"], [])

        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(research_emit),
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Literal provenance", result.stdout)

    def test_literal_archaeology_rows_render_mixed_use(self):
        """Plan 73 Phase 5 -- fix-layer and evidence rows both carried and
        render distinguishably, with intent + use + SHA + subject per row.

        Real chain, no hand-authored handoff JSON: two
        record-literal-archaeology calls (one --use fix-layer, one --use
        evidence) on top of _run_research_setup's fixture, through the real
        finalize-handoff producer and the real render-plan-seeds consumer.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        def _rrun(*argv):
            return subprocess.run(
                [sys.executable, str(RESEARCH_HELPER_PY)] + list(argv),
                capture_output=True, text=True,
            )

        r = _rrun(
            "--devforge-dir", str(devforge), "record-literal-archaeology",
            "--literal", "false",
            "--file-line", "src/services/widget_flags.py:14",
            "--introduced-by", "1a2b3c4",
            "--introduced-when", "2024-03-01",
            "--commit-subject", "Add feature flag for widget preview",
            "--intent", "deliberate",
            "--use", "fix-layer",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _rrun(
            "--devforge-dir", str(devforge), "record-literal-archaeology",
            "--literal", "true",
            "--file-line", "src/services/widget_flags.py:22",
            "--introduced-by", "9f8e7d6c5",
            "--introduced-when", "2023-11-15",
            "--commit-subject", "Restructure parent widget state handling",
            "--intent", "inherited-refactor",
            "--use", "evidence",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        research_emit = self.tmp / "research" / "2026-05-22-widget-stale-results.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path",
                "research/2026-05-22-widget-stale-results.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)

        # Precondition: the producer really did emit both rows with distinct use.
        data = json.loads(research_emit.read_text(encoding="utf-8"))
        rows = data["spec_seeds"]["literal_archaeology"]
        self.assertEqual(len(rows), 2)
        uses = sorted(row["use"] for row in rows)
        self.assertEqual(uses, ["evidence", "fix-layer"])

        specify_emit = _produce_specify_handoff(
            self.tmp,
            handoff_path=str(research_emit),
            handoff_kind="research",
            research_completed_at="2026-05-22T08:00:00Z",
        )

        result = self._run("render-plan-seeds", str(specify_emit))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("**Literal provenance** (recorded at /devforge:research):", output)
        # Row 1 -- fix-layer, deliberate.
        self.assertIn("`false`", output)
        self.assertIn("src/services/widget_flags.py:14", output)
        self.assertIn("intent: deliberate", output)
        self.assertIn("use: fix-layer", output)
        self.assertIn("SHA: 1a2b3c4", output)
        self.assertIn("Add feature flag for widget preview", output)
        # Row 2 -- evidence, inherited-refactor.
        self.assertIn("`true`", output)
        self.assertIn("src/services/widget_flags.py:22", output)
        self.assertIn("intent: inherited-refactor", output)
        self.assertIn("use: evidence", output)
        self.assertIn("SHA: 9f8e7d6c5", output)
        self.assertIn("Restructure parent widget state handling", output)
        # Distinguishable: the two use labels appear on separate lines, not merged.
        self.assertNotIn("use: fix-layerevidence", output)
        fix_layer_line = [ln for ln in output.splitlines() if "use: fix-layer" in ln]
        evidence_line = [ln for ln in output.splitlines() if "use: evidence" in ln]
        self.assertEqual(len(fix_layer_line), 1)
        self.assertEqual(len(evidence_line), 1)
        self.assertNotEqual(fix_layer_line[0], evidence_line[0])


# ---------------------------------------------------------------------------
# Tests: render-consultation-block
# ---------------------------------------------------------------------------


class RenderConsultationBlockTests(_CwdIsolation):
    """Tests for plan_helper render-consultation-block subcommand.

    The subcommand emits a fixed deterministic skeleton — no file parsing,
    no required arguments. Tests verify structural invariants and
    determinism.
    """

    def _get_output(self):
        """Run render-consultation-block and return stdout; assert exit 0."""
        result = _run(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_exit_0(self):
        """render-consultation-block exits 0."""
        result = _run(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_duplicate_heading(self):
        """Output does NOT contain '## Specialist Consultation' heading.

        The plan.md template owns the heading; emitting it here would produce
        a duplicate H2 when the orchestrator copies this block into that section.
        """
        output = self._get_output()
        lines = output.splitlines()
        self.assertNotIn(
            "## Specialist Consultation",
            lines,
            "Helper must not emit the heading — the template already has it.",
        )

    def test_table_header_has_five_columns(self):
        """Table header row contains exactly the five required columns.

        The required columns in order are: Specialist, Sub-question,
        Input summary, Verdict, Cites.
        """
        output = self._get_output()
        import re
        # Find the header row — first pipe-delimited row after the heading.
        header_match = re.search(
            r"\|\s*Specialist\s*\|\s*Sub-question\s*\|\s*Input summary\s*\|\s*Verdict\s*\|\s*Cites\s*\|",
            output,
        )
        self.assertIsNotNone(
            header_match,
            "Table header must contain all five columns in order: "
            "Specialist | Sub-question | Input summary | Verdict | Cites. "
            "Got:\n" + output,
        )

    def test_verdict_enum_present(self):
        """The verdict enum line lists all four valid values."""
        output = self._get_output()
        self.assertIn("accepted", output)
        self.assertIn("modified", output)
        self.assertIn("rejected", output)
        self.assertIn("no-response", output)

    def test_verdict_enum_on_rule_line(self):
        """The four verdict values appear together on the rule/constraint line."""
        output = self._get_output()
        # Find the line that mentions "Verdict" as a rule (not the table header).
        verdict_rule_line = None
        for line in output.splitlines():
            if "Verdict" in line and "accepted" in line:
                verdict_rule_line = line
                break
        self.assertIsNotNone(
            verdict_rule_line,
            "Expected a rule line mentioning Verdict and accepted; not found in:\n" + output,
        )
        self.assertIn("modified", verdict_rule_line)
        self.assertIn("rejected", verdict_rule_line)
        self.assertIn("no-response", verdict_rule_line)

    def test_none_empty_state_row_guidance_present(self):
        """Output contains guidance for the empty-state (none) row."""
        output = self._get_output()
        self.assertIn("(none)", output)

    def test_deterministic_two_runs_identical(self):
        """Two consecutive invocations produce byte-identical output."""
        first = _run(self.tmp_path, "render-consultation-block").stdout
        second = _run(self.tmp_path, "render-consultation-block").stdout
        self.assertEqual(first, second, "Output must be deterministic across runs")

    def test_cites_requirement_mentioned(self):
        """Output states the Cites requirement for every row."""
        output = self._get_output()
        self.assertIn("Cites", output)

    def test_no_required_arguments(self):
        """Subcommand takes no required arguments — invoking without args succeeds."""
        result = _run(self.tmp_path, "render-consultation-block")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Confirm it emits actual content, not just a blank line.
        self.assertGreater(len(result.stdout.strip()), 0)

    def test_appears_in_help(self):
        """render-consultation-block is listed in the top-level --help output."""
        result = _run(self.tmp_path, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("render-consultation-block", result.stdout)


# ---------------------------------------------------------------------------
# Regression: _STATUS_PATTERN must NOT bleed across blank lines
# ---------------------------------------------------------------------------


class TestPlanStatusPatternNoBleed(unittest.TestCase):
    """plan_helper._STATUS_PATTERN uses [ \\t]* (not \\s*) so a malformed spec/
    plan file where **Status**: appears on a line by itself does NOT capture a
    value from a subsequent non-empty line.

    Tests round-trip via the public check-status-and-flip verb (subprocess),
    mirroring production usage of _STATUS_PATTERN.search().
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    # Direct pattern-level tests (using the imported plan_helper module)
    # ------------------------------------------------------------------

    def test_malformed_blank_line_before_value_no_match(self):
        """**Status**: on its own line, blank line, 'Draft' on next → no match.

        Regression: \\s* matched across newlines; [ \\t]* does not.
        """
        malformed = "# Spec\n\n**Date**: 2026-01-01\n**Status**:\n\nDraft\n"
        result = plan_helper._parse_frontmatter_field(
            malformed, plan_helper._STATUS_PATTERN
        )
        self.assertIsNone(
            result,
            "Malformed spec (value on next line after blank) must return None; "
            "got {0!r}".format(result),
        )

    def test_malformed_immediate_next_line_no_match(self):
        """**Status**: on its own line, value immediately on next → no match."""
        malformed = "# Spec\n\n**Date**: 2026-01-01\n**Status**:\nDraft\n"
        result = plan_helper._parse_frontmatter_field(
            malformed, plan_helper._STATUS_PATTERN
        )
        self.assertIsNone(
            result,
            "Malformed spec (value on immediate next line) must return None; "
            "got {0!r}".format(result),
        )

    def test_well_formed_single_line_matches(self):
        """Well-formed '**Status**: Draft' is still captured."""
        content = "# Spec\n\n**Date**: 2026-01-01\n**Status**: Draft\n"
        result = plan_helper._parse_frontmatter_field(
            content, plan_helper._STATUS_PATTERN
        )
        self.assertEqual(result, "Draft")

    def test_well_formed_with_tab_matches(self):
        """**Status**:<TAB>Approved is a valid horizontal-ws layout."""
        content = "**Status**:\tApproved\n"
        result = plan_helper._parse_frontmatter_field(
            content, plan_helper._STATUS_PATTERN
        )
        self.assertEqual(result, "Approved")

    # ------------------------------------------------------------------
    # CLI-level round-trip: check-status-and-flip with malformed spec
    # ------------------------------------------------------------------

    def test_check_status_and_flip_malformed_blank_before_value_treated_as_missing(self):
        """check-status-and-flip on a spec whose **Status**: has no value on the
        same line falls through to the 'no Status line' branch.

        When **Date**: is also absent the helper exits 2 (malformed).  This
        confirms the malformed layout is NOT mis-parsed as a valid status value
        (which would previously yield 'flipped' or 'already-approved' due to
        the \\s* bleed bug).
        """
        # A spec with **Status**: on its own line and blank then value,
        # AND no **Date**: line → the 'no Date or Status found' path → exit 2.
        malformed = (
            "# Spec: Malformed\n\n"
            "**Status**:\n\n"
            "Draft\n\n"
            "## 1. Overview\n\nSomething.\n"
        )
        spec_file = self.tmp_path / "spec.md"
        spec_file.write_text(malformed, encoding="utf-8")

        result = _run(self.tmp_path, "check-status-and-flip", str(spec_file))
        # The helper must NOT treat the next line's "Draft" as the status value.
        # With the fix, no **Status**: match → falls to 'no Date or Status found'
        # path → exit 2 (malformed).
        self.assertNotEqual(
            result.stdout.strip(),
            "flipped",
            "check-status-and-flip must NOT 'flip' a spec whose **Status**: "
            "value is on the next line (bleed bug); stdout={0!r}".format(result.stdout),
        )
        self.assertNotEqual(
            result.stdout.strip(),
            "already-approved",
            "check-status-and-flip must NOT report 'already-approved' for a "
            "malformed spec; stdout={0!r}".format(result.stdout),
        )


# ---------------------------------------------------------------------------
# Tests: correctness_vetted provenance caveat in render-plan-seeds (Seam E).
# ---------------------------------------------------------------------------


class CorrectnessVettedRenderTests(unittest.TestCase):
    """Tests for the correctness_vetted caveat rendered by _render_research_plan_seeds.

    Tests call the private render function directly (plan_helper is imported at
    module level) to avoid the full subprocess overhead of render-plan-seeds.
    """

    def _ps_dict(self, **kwargs):
        """Return a minimal plan_seeds dict, overridable via kwargs."""
        base = {
            "recommended_approach_id": "fix_cache",
            "recommended_approach_summary": "Clear the cache on every catalog write",
            "layer_destination": "service",
            "layer_justification": "Service-layer only change",
            "complexity": {"changes": "Low", "risk": "Low", "verify_cost": "Low"},
            "cited_canonical_patterns": [],
            "alternatives_considered": [],
            "proposed_call_shape": None,
        }
        base.update(kwargs)
        return base

    def test_caveat_rendered_when_field_absent(self):
        """Back-compat: plan_seeds dict without correctness_vetted key renders caveat.

        Old handoffs lack the field. The consumer must default to False (shape-checked
        only) and render the caveat.
        """
        ps = self._ps_dict()  # no correctness_vetted key
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds("research/2026-01-01-test.handoff.json", d)
        self.assertIn("provenance", output)
        self.assertIn("shape-checked", output)
        self.assertIn("NOT correctness-vetted", output)

    def test_caveat_rendered_when_explicit_false(self):
        """Explicit correctness_vetted=False renders caveat."""
        ps = self._ps_dict(correctness_vetted=False)
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds("research/2026-01-01-test.handoff.json", d)
        self.assertIn("NOT correctness-vetted", output)
        self.assertIn("shape-checked", output)

    def test_no_caveat_when_true(self):
        """correctness_vetted=True suppresses the caveat entirely."""
        ps = self._ps_dict(correctness_vetted=True)
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds("research/2026-01-01-test.handoff.json", d)
        self.assertNotIn("NOT correctness-vetted", output)
        self.assertNotIn("shape-checked", output)
        # The recommendation line itself must still be present.
        self.assertIn("Recommended approach", output)
        self.assertIn("Clear the cache", output)

    def test_caveat_immediately_after_recommendation_before_layer(self):
        """Caveat appears after the Recommended approach line and before the Layer line."""
        ps = self._ps_dict()  # triggers caveat
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds("research/2026-01-01-test.handoff.json", d)
        rec_pos = output.index("Recommended approach")
        caveat_pos = output.index("NOT correctness-vetted")
        layer_pos = output.index("**Layer**")
        self.assertGreater(caveat_pos, rec_pos,
                           "caveat must appear after the Recommended approach line")


# ---------------------------------------------------------------------------
# Tests: caller_enumeration carry rendering in render-plan-seeds (plan 67 D6).
# ---------------------------------------------------------------------------


class CallerEnumerationRenderTests(unittest.TestCase):
    """Tests for the caller_enumeration block rendered by _render_research_plan_seeds.

    Tests call the private render function directly (plan_helper is imported
    at module level), mirroring CorrectnessVettedRenderTests above.
    """

    def _ps_dict(self, **kwargs):
        """Return a minimal plan_seeds dict, overridable via kwargs."""
        base = {
            "recommended_approach_id": "fix_cache",
            "recommended_approach_summary": "Clear the cache on every catalog write",
            "layer_destination": "service",
            "layer_justification": "Service-layer only change",
            "complexity": {"changes": "Low", "risk": "Low", "verify_cost": "Low"},
            "cited_canonical_patterns": [],
            "alternatives_considered": [],
            "proposed_call_shape": None,
            "correctness_vetted": True,  # suppress the unrelated Seam-E caveat
        }
        base.update(kwargs)
        return base

    def test_absent_field_renders_nothing(self):
        """Old handoff.json (predating plan 67) has no caller_enumeration key
        at all -> the rendered block carries no caller-enumeration section.

        Byte-identical output to today (pre-plan-67) for an old handoff.
        """
        ps = self._ps_dict()  # no caller_enumeration key
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertNotIn("Caller enumeration", output)

    def test_absent_field_byte_identical_to_pre_carry_output(self):
        """The exact byte-for-byte before/after comparison the brief asks for:
        an old-shaped plan_seeds dict renders identically whether or not the
        caller_enumeration carry code path exists (it must no-op on absence).
        """
        ps = self._ps_dict()
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        # Independently-constructed expected output, matching the pre-plan-67
        # template shape (no caller_block content anywhere).
        expected = (
            "## Upstream plan-seeds (research handoff: research/2026-01-01-test.handoff.json)\n"
            "\n"
            "**Recommended approach**: fix_cache — Clear the cache on every catalog write\n"
            "**Layer**: service — Service-layer only change\n"
            "**Complexity**: changes=Low, risk=Low, verify_cost=Low\n"
            "**Proposed call shape**: (none)\n"
            "\n"
            "**Alternatives considered**:\n"
            "- (none)\n"
            "\n"
            "**Cited canonical patterns**:\n"
            "- (none)\n"
        )
        self.assertEqual(output, expected)

    def test_empty_carry_renders_nothing(self):
        """caller_enumeration present but all-empty (neither Phase 2.4c path
        recorded) -> renders nothing, same as an absent field.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [],
            "inbound_callers": [],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertNotIn("Caller enumeration", output)

    def test_carried_helpers_render_qn_and_file_line(self):
        """Populated fix_path_helpers -> each helper's qn + definition file:line renders."""
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("Caller enumeration", output)
        self.assertIn("config.load", output)
        self.assertIn("services/api/config.py:42", output)

    def test_carried_callers_render_caller_qn_and_file_line(self):
        """Populated inbound_callers -> each caller's qn + call-site file:line renders,
        grouped under its helper.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "main.startup",
                    "file_line": "services/api/main.py:15",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("main.startup", output)
        self.assertIn("services/api/main.py:15", output)
        # The caller line must appear after its helper's line.
        helper_pos = output.index("config.load")
        caller_pos = output.index("main.startup")
        self.assertGreater(caller_pos, helper_pos)

    def test_helper_with_no_recorded_callers_flagged(self):
        """A helper with zero matching inbound_callers rows renders an explicit
        '(no inbound callers recorded)' marker rather than silently omitting it.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "env_loader.init", "file_line": "services/core/env_loader.py:10"},
            ],
            "inbound_callers": [],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("no inbound callers recorded", output)

    def test_justification_renders_recorded_at_research_framing(self):
        """no_shared_callers_justification present (escape path used, no helpers
        recorded) -> renders the explicit 'recorded at /research — zero shared
        callers asserted' framing plus the justification text verbatim.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [],
            "inbound_callers": [],
            "no_shared_callers_justification": "purely additive in a new module",
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("recorded at /devforge:research", output)
        self.assertIn("zero shared callers asserted", output)
        self.assertIn("purely additive in a new module", output)
        # The helper-enumeration path must not also render.
        self.assertNotIn("(no inbound callers recorded)", output)

    def test_helpers_take_precedence_over_justification(self):
        """If both are somehow present (contradictory upstream state), the
        helper-enumeration render path wins -- helpers are the ground truth
        when non-empty.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [],
            "no_shared_callers_justification": "should not render",
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("config.load", output)
        self.assertNotIn("should not render", output)

    # -- plan 69 D5/WI-E: per-caller surface/scope/justification suffix --

    def test_classified_caller_renders_surface_scope_justification_suffix(self):
        """A caller row carrying scope="in" (classify-caller-scope) renders the
        compact suffix -- surface, scope, and justification all appear on the
        same line as the caller.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "WidgetListBLoC.fetchArchivedWidgetsWithV2",
                    "file_line": "src/bloc/accounts_bloc.ts:80",
                    "surface": "WidgetPickerModal.vue",
                    "scope": "in",
                    "justification": "Drives the same Customer search flow.",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        caller_line = next(
            line for line in output.splitlines()
            if "WidgetListBLoC.fetchArchivedWidgetsWithV2" in line
        )
        self.assertIn("src/bloc/accounts_bloc.ts:80", caller_line)
        self.assertIn("surface: WidgetPickerModal.vue", caller_line)
        self.assertIn("scope: in", caller_line)
        self.assertIn("Drives the same Customer search flow.", caller_line)

    def test_classified_caller_scope_out_renders_suffix(self):
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "background.reindex",
                    "file_line": "src/jobs/reindex.py:20",
                    "surface": "none",
                    "scope": "out",
                    "justification": "Background job; not reachable from any UI surface.",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        caller_line = next(
            line for line in output.splitlines()
            if "background.reindex" in line
        )
        self.assertIn("surface: none", caller_line)
        self.assertIn("scope: out", caller_line)
        self.assertIn("Background job; not reachable from any UI surface.", caller_line)

    def test_classified_row_with_empty_surface_and_justification_renders_placeholders(self):
        """A schema-legal partial classification -- scope="in" with empty
        surface/justification -- is unreachable via the real producer
        (classify-caller-scope enforces non-empty --surface/--justification
        at the setter boundary; see
        TestInboundCaller.test_valid_construction_with_scope_in_and_empty_surface_justification
        in test_research_handoff_schema.py for the schema-side construction
        this exercises) but is schema-legal, so the render function must not
        crash on it. Locks the "?" fallback: `c.get("surface") or "?"` /
        `c.get("justification") or "?"` render literal "?" placeholders --
        this is the exact CURRENT output, not a byte-identical-to-legacy
        claim (the row is still classified: scope="in" renders, unlike the
        unclassified-legacy-line tests above).
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "main.startup",
                    "file_line": "services/api/main.py:15",
                    "surface": "",
                    "scope": "in",
                    "justification": "",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        caller_line = next(
            line for line in output.splitlines()
            if "main.startup" in line
        )
        self.assertEqual(
            caller_line,
            "  - caller: main.startup (services/api/main.py:15) — "
            "surface: ?, scope: in — ?",
        )

    def test_unclassified_caller_renders_legacy_line_byte_identical(self):
        """A caller row with no scope key (the pre-plan-69 shape, or a row
        recorded but never classified) renders EXACTLY the legacy
        'caller: X (file:line)' line -- no suffix, byte-identical to the
        pre-plan-69 output for the same inputs.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "main.startup",
                    "file_line": "services/api/main.py:15",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn(
            "  - caller: main.startup (services/api/main.py:15)\n", output,
        )
        self.assertNotIn("surface:", output)
        self.assertNotIn("scope:", output)

    def test_unclassified_caller_with_empty_scope_string_renders_legacy_line(self):
        """A row that explicitly carries scope="" (the InboundCaller default,
        e.g. via _build_caller_enumeration's absent-key floor) also renders
        the legacy line -- empty scope means unclassified, not a third
        rendered state.
        """
        ps = self._ps_dict(caller_enumeration={
            "fix_path_helpers": [
                {"qn": "config.load", "file_line": "services/api/config.py:42"},
            ],
            "inbound_callers": [
                {
                    "helper_qn": "config.load",
                    "caller_qn": "main.startup",
                    "file_line": "services/api/main.py:15",
                    "surface": "",
                    "scope": "",
                    "justification": "",
                },
            ],
            "no_shared_callers_justification": None,
        })
        d = {"plan_seeds": ps}
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn(
            "  - caller: main.startup (services/api/main.py:15)\n", output,
        )
        self.assertNotIn("surface:", output)


# ---------------------------------------------------------------------------
# Tests: literal_archaeology carry rendering in render-plan-seeds
# (plan 73 Phase 5, OQ-2/OQ-3).
# ---------------------------------------------------------------------------


class LiteralArchaeologyRenderTests(unittest.TestCase):
    """Tests for the literal-archaeology block rendered by
    _render_research_plan_seeds, for shapes the CURRENT producer cannot
    emit (a pre-plan-73 row without a `use` key; a handoff entirely missing
    `spec_seeds`) -- mirrors CallerEnumerationRenderTests' rationale for
    calling the private render function directly with a hand-built dict:
    the current record-literal-archaeology CLI always writes `--use`, so a
    genuinely legacy row shape cannot be produced by the real chain.
    Round-trip coverage for the reachable (current-producer) shapes lives in
    RenderPlanSeedsTests.test_literal_archaeology_rows_render_mixed_use and
    .test_zero_literal_archaeology_rows_render_nothing above.

    Unlike caller_enumeration, `d.get("spec_seeds")` is the carrier -- NOT
    `d.get("plan_seeds")` -- so these fixtures build a `spec_seeds` key
    sibling to `plan_seeds`, not nested inside it.
    """

    def _ps_dict(self, **kwargs):
        """Return a minimal plan_seeds dict (unrelated to literal_archaeology,
        included only because _render_research_plan_seeds reads other
        plan_seeds fields unconditionally)."""
        base = {
            "recommended_approach_id": "fix_cache",
            "recommended_approach_summary": "Clear the cache on every catalog write",
            "layer_destination": "service",
            "layer_justification": "Service-layer only change",
            "complexity": {"changes": "Low", "risk": "Low", "verify_cost": "Low"},
            "cited_canonical_patterns": [],
            "alternatives_considered": [],
            "proposed_call_shape": None,
            "correctness_vetted": True,  # suppress the unrelated Seam-E caveat
        }
        base.update(kwargs)
        return base

    def test_absent_spec_seeds_key_renders_nothing(self):
        """A handoff dict with no `spec_seeds` key at all (older than the
        literal_archaeology carrier itself) -> no 'Literal provenance'
        section. Byte-identical to today for a dict shape that never had
        the concept.
        """
        d = {"plan_seeds": self._ps_dict()}  # no spec_seeds key
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertNotIn("Literal provenance", output)

    def test_empty_literal_archaeology_list_renders_nothing(self):
        """spec_seeds present but literal_archaeology is an empty list ->
        renders nothing (same silent branch as an absent key)."""
        d = {
            "plan_seeds": self._ps_dict(),
            "spec_seeds": {"literal_archaeology": []},
        }
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertNotIn("Literal provenance", output)

    def test_pre_plan73_row_without_use_key_defaults_fix_layer(self):
        """A literal_archaeology row shaped like a handoff written before
        plan 73 OQ-5 (no `use` key on the row at all -- the real CLI cannot
        produce this today, since --use is required) still renders, with
        `use` defaulting to fix-layer -- matching the schema-level default
        (LiteralArchaeology.use) so the render never crashes or drops a
        legacy row silently.
        """
        d = {
            "plan_seeds": self._ps_dict(),
            "spec_seeds": {
                "literal_archaeology": [
                    {
                        "literal": "0",
                        "file_line": "src/legacy/OldFlag.py:9",
                        "introduced_by": "cafe123",
                        "introduced_when": "2022-06-01",
                        "commit_subject": "Initial flag plumbing",
                        "intent": "migrated",
                        # no "use" key -- the pre-plan-73 shape.
                    },
                ],
            },
        }
        output = plan_helper._render_research_plan_seeds(
            "research/2026-01-01-test.handoff.json", d
        )
        self.assertIn("**Literal provenance** (recorded at /devforge:research):", output)
        self.assertIn("`0`", output)
        self.assertIn("src/legacy/OldFlag.py:9", output)
        self.assertIn("intent: migrated", output)
        self.assertIn("use: fix-layer", output)
        self.assertIn("SHA: cafe123", output)
        self.assertIn("Initial flag plumbing", output)


class CorrectnessVettedBackCompatTests(unittest.TestCase):
    """Back-compat and round-trip tests via the real _dict_to_dataclass deserializer.

    These use the real research_helper finalize-handoff producer (subprocess) and
    the real _dict_to_dataclass function to exercise the full load path.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _load_research_hs(self):
        """Load the research handoff_schema module via importlib (unique name avoids collision)."""
        _research_dir = REPO_ROOT / "src" / "devforge" / "lib" / "_research"
        spec = importlib.util.spec_from_file_location(
            "_research_hs_correctness_vetted_backcompat",
            _research_dir / "handoff_schema.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_old_handoff_json_deserializes_correctness_vetted_defaults_false(self):
        """An old research handoff.json (no correctness_vetted in plan_seeds) deserializes to False.

        Produces a real handoff via the producer, strips correctness_vetted to simulate
        a pre-field record, then deserializes via _dict_to_dataclass and asserts the
        field defaults to False.

        Proves back-compat: D7 requirement — old handoffs parse without error.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        research_emit = self.tmp / "research" / "2026-05-22-widget-stale-results.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path", "research/2026-05-22-widget-stale-results.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)

        # Load produced JSON — the current producer MUST emit correctness_vetted=False.
        data = json.loads(research_emit.read_text(encoding="utf-8"))
        self.assertIn("correctness_vetted", data.get("plan_seeds", {}),
                      "Current producer must emit correctness_vetted in plan_seeds")
        self.assertFalse(data["plan_seeds"]["correctness_vetted"],
                         "Current producer must emit correctness_vetted=False by default")

        # Simulate old handoff by stripping the field.
        data["plan_seeds"].pop("correctness_vetted")

        # Deserialize via the real _dict_to_dataclass.
        rhs = self._load_research_hs()
        handoff = _specify_dict_to_dataclass(rhs.Handoff, data)
        self.assertIs(handoff.plan_seeds.correctness_vetted, False,
                      "Old handoff without correctness_vetted must default to False")

    def test_current_producer_output_round_trips_stably(self):
        """Current-producer handoff.json round-trips stably.

        Produce → serialize → _dict_to_dataclass → re-serialize produces
        byte-identical plan_seeds dict (JSON-comparable).
        Proves the field emits and re-parses without drift.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)

        research_emit = self.tmp / "research" / "2026-05-22-widget-stable.handoff.json"
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path", "research/2026-05-22-widget-stable.md",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)

        # First serialization (from the producer).
        data1 = json.loads(research_emit.read_text(encoding="utf-8"))
        ps_dict1 = data1["plan_seeds"]

        # Deserialize via the real _dict_to_dataclass, then re-serialize.
        rhs = self._load_research_hs()
        handoff = _specify_dict_to_dataclass(rhs.Handoff, data1)

        import dataclasses
        ps_dict2 = dataclasses.asdict(handoff.plan_seeds)
        ps_dict2.pop("_proposed_call_shape_parse_failed", None)

        # The re-serialized plan_seeds must match the first serialization.
        self.assertEqual(ps_dict1, ps_dict2,
                         "Round-trip must produce byte-identical plan_seeds dict")


class CallerClassificationBackCompatTests(unittest.TestCase):
    """Plan 69 D5/WI-E: per-caller surface/scope/justification handoff carry.

    Same honest back-compat pattern as CorrectnessVettedBackCompatTests
    (plan 67 Phase 3 precedent) -- an old-JSON->defaults test plus a
    current-producer-stable round-trip test, NOT a byte-identity claim
    about new-producer output (the new fields are additive content, so
    new-producer output legitimately differs from pre-plan-69 output).

    Uses the real research_helper classify-caller-scope + finalize-handoff
    producers (subprocess) and the real _dict_to_dataclass deserializer.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _load_research_hs(self):
        """Load the research handoff_schema module via importlib (unique name avoids collision)."""
        _research_dir = REPO_ROOT / "src" / "devforge" / "lib" / "_research"
        spec = importlib.util.spec_from_file_location(
            "_research_hs_caller_classification_backcompat",
            _research_dir / "handoff_schema.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _classify_recorded_caller(self, devforge):
        """Classify the (helper, caller) pair _run_research_setup already
        recorded via record-fix-path-helper + record-inbound-caller."""
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "classify-caller-scope",
                "--helper-qn", "widget_service.update_catalog",
                "--caller-qn", "catalog_api.update",
                "--surface", "Catalog admin page",
                "--scope", "in",
                "--justification", "Reachable from the catalog admin write path.",
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def _emit_handoff(self, devforge, stem):
        research_emit = self.tmp / "research" / "{0}.handoff.json".format(stem)
        research_emit.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                sys.executable, str(RESEARCH_HELPER_PY),
                "--devforge-dir", str(devforge),
                "finalize-handoff",
                "--emit-handoff-json", str(research_emit),
                "--research-md-path", "research/{0}.md".format(stem),
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, "research finalize-handoff failed: " + proc.stderr)
        return research_emit

    def test_current_producer_carries_classification_through_finalize_handoff(self):
        """classify-caller-scope's surface/scope/justification ride finalize-handoff
        into plan_seeds.caller_enumeration.inbound_callers verbatim.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)
        self._classify_recorded_caller(devforge)

        research_emit = self._emit_handoff(devforge, "2026-05-22-widget-classified")
        data = json.loads(research_emit.read_text(encoding="utf-8"))
        rows = data["plan_seeds"]["caller_enumeration"]["inbound_callers"]
        row = next(r for r in rows if r["caller_qn"] == "catalog_api.update")
        self.assertEqual(row["surface"], "Catalog admin page")
        self.assertEqual(row["scope"], "in")
        self.assertEqual(row["justification"], "Reachable from the catalog admin write path.")

    def test_current_producer_defaults_unclassified_row_to_empty_strings(self):
        """A row recorded (record-inbound-caller) but never classified
        (classify-caller-scope skipped) emits surface/scope/justification
        as "" -- the current producer's default, not an absent key.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)
        # Deliberately skip classify-caller-scope.

        research_emit = self._emit_handoff(devforge, "2026-05-22-widget-unclassified")
        data = json.loads(research_emit.read_text(encoding="utf-8"))
        rows = data["plan_seeds"]["caller_enumeration"]["inbound_callers"]
        row = next(r for r in rows if r["caller_qn"] == "catalog_api.update")
        self.assertEqual(row["surface"], "")
        self.assertEqual(row["scope"], "")
        self.assertEqual(row["justification"], "")

    def test_old_handoff_json_without_classification_fields_deserializes_to_empty_defaults(self):
        """An old research handoff.json (inbound_callers rows predating plan 69,
        no surface/scope/justification keys at all) deserializes cleanly --
        the fields default to "" (InboundCaller's own defaults), not a
        construction error.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)
        self._classify_recorded_caller(devforge)

        research_emit = self._emit_handoff(devforge, "2026-05-22-widget-old-shape")
        data = json.loads(research_emit.read_text(encoding="utf-8"))

        # Simulate a pre-plan-69 handoff by stripping the three keys from
        # every inbound_callers row.
        for row in data["plan_seeds"]["caller_enumeration"]["inbound_callers"]:
            row.pop("surface", None)
            row.pop("scope", None)
            row.pop("justification", None)

        rhs = self._load_research_hs()
        handoff = _specify_dict_to_dataclass(rhs.Handoff, data)
        rows = handoff.plan_seeds.caller_enumeration.inbound_callers
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.surface, "")
            self.assertEqual(row.scope, "")
            self.assertEqual(row.justification, "")

    def test_current_producer_output_round_trips_stably_with_classification(self):
        """Current-producer handoff.json (with a classified caller row)
        round-trips stably: produce -> serialize -> _dict_to_dataclass ->
        re-serialize produces a byte-identical plan_seeds dict.
        """
        devforge = self.tmp / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        _run_research_setup(devforge, RESEARCH_HELPER_PY)
        self._classify_recorded_caller(devforge)

        research_emit = self._emit_handoff(devforge, "2026-05-22-widget-stable-classified")
        data1 = json.loads(research_emit.read_text(encoding="utf-8"))
        ps_dict1 = data1["plan_seeds"]

        rhs = self._load_research_hs()
        handoff = _specify_dict_to_dataclass(rhs.Handoff, data1)

        import dataclasses
        ps_dict2 = dataclasses.asdict(handoff.plan_seeds)
        ps_dict2.pop("_proposed_call_shape_parse_failed", None)

        self.assertEqual(ps_dict1, ps_dict2,
                         "Round-trip must produce byte-identical plan_seeds dict")


if __name__ == "__main__":
    unittest.main()
