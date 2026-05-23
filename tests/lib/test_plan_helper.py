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

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper.py"
HELPER_SHIM = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper"
SPECIFY_HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "specify_helper.py"

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
        self.assertIn("## Manual next step — run /breakdown", output)
        self.assertIn("/breakdown", output)
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


if __name__ == "__main__":
    unittest.main()
