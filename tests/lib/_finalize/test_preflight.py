"""Tests for src/devforge/lib/_finalize/_preflight.py.

Coverage:
  preflight_context — all-files-absent defaults, each setup-chain artefact
                      missing individually, real populated spec in both
                      Complete/not-Complete states, source_root / wrapper_mode
                      extraction, memory.md excerpt, WIP/checkpoint commit
                      detection (both arms), and the CLI gate (exit 2 on
                      missing setup chain, exit 3 on not-Complete spec)
                      via cmd_preflight.

Real-producer round-trip:
  - A real CLAUDE.md built the same way _summarize's test_preflight.py
    builds its fixture (standalone + wrapper-mode cases).
  - A real spec in the not-Complete state: uses the actual
    tests/lib/fixtures/specify-sample-migration.md (Status: Draft) — asserts
    the gate REJECTS it with a "run /verify first" stop.
  - A real spec in the Complete state: produced by the REAL
    _verify._specstatus.flip_spec_status (the verify-helper producer) on a
    copy of that fixture with no tasks/ dir (so the task cross-check passes).
    NOT hand-authored.
  - WIP/checkpoint detection: uses a REAL temporary git repository with
    actual [WIP] and [checkpoint] commits — NOT hand-faked output.

CRITICAL: the preflight reads .devforge/memory.md (the live path per
src/CLAUDE.md References block), NOT .claude/memory/MEMORY.md.
Tests explicitly verify this invariant.

NOTE: /finalize deliberately OMITS the constitution-populated sentinel guard
(_UNPOPULATED_SENTINELS) that /verify and /review carry — same rationale as
/summarize (the spec-Complete gate is a strictly stronger precondition at this
pipeline stage).  Tests confirm an unpopulated constitution does NOT block.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _finalize._preflight import (  # noqa: E402
    _SETUP_CHAIN_ARTEFACTS,
    _REQUIRED_SPEC_STATUS,
    _count_wip_commits,
    preflight_context,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(td, rel_path, content):
    # type: (str, str, str) -> str
    """Write content to td/rel_path, creating parent dirs."""
    full = os.path.join(td, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _make_full_install(td):
    # type: (str) -> None
    """Write a minimal but complete 4-command setup-chain install into td.

    Files created:
      constitution.md               — populated (no sentinels)
      CLAUDE.md                     — minimal CLAUDE.md with Source Root
      .devforge/project-config.json — /configure output stub
      .devforge/index.json          — /generate-docs output stub
      .devforge/memory.md           — memory file (live path, NOT .claude/memory/)
    """
    _write(td, "constitution.md",
           "# Architecture Rules\n\n1. Use dependency injection.\n2. No globals.\n")
    _write(td, "CLAUDE.md",
           "# CLAUDE.md\n\n"
           "- **Name**: TestProject\n"
           "- **Type**: web-app\n"
           "- **Frameworks**: Django\n"
           "- **Languages**: Python\n"
           "- **Project Root**: src/backend\n")
    _write(td, ".devforge/project-config.json",
           json.dumps({"configure_version": 1}))
    _write(td, ".devforge/index.json",
           json.dumps({"version": 1, "packages": []}))
    _write(td, ".devforge/memory.md",
           "- [Lesson 1](lesson_1.md)\n- [Lesson 2](lesson_2.md)\n")


def _make_complete_spec(td):
    # type: (str) -> str
    """Produce a real Complete spec.md via the REAL verify flip_spec_status.

    Copies the real not-Complete fixture into td, then calls
    _verify._specstatus.flip_spec_status (the producer) with no tasks dir
    (so the task cross-check passes) to flip it to Complete.

    Returns the absolute path to the Complete spec.md.
    """
    from _verify._specstatus import flip_spec_status

    spec_src = str(_FIXTURES_DIR / "specify-sample-migration.md")
    spec_dst = os.path.join(td, "spec.md")
    shutil.copy(spec_src, spec_dst)

    # flip_spec_status requires a feature_dir; with no tasks/ subdir it skips
    # the task cross-check and flips the **Status**: line directly.
    result = flip_spec_status(
        feature_dir=td,
        ac_results=[],
        spec_path=spec_dst,
    )
    if not result["flipped"]:
        raise RuntimeError(
            "flip_spec_status failed in test setup: {0}".format(result.get("blocker"))
        )
    return spec_dst


def _git(args, cwd):
    # type: (list, str) -> tuple
    """Run a git command. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _make_git_repo(td):
    # type: (str) -> str
    """Create a real git repo at td with an initial commit. Returns td."""
    _git(["init", "--initial-branch=main"], cwd=td)
    # Fallback for older git that doesn't support --initial-branch
    _git(["checkout", "-b", "main"], cwd=td)
    _git(["config", "user.email", "test@example.com"], cwd=td)
    _git(["config", "user.name", "Test"], cwd=td)
    _write(td, "README.md", "# Project\n")
    _git(["add", "README.md"], cwd=td)
    _git(["commit", "-m", "feat: initial commit"], cwd=td)
    return td


def _add_commit(td, filename, message):
    # type: (str, str, str) -> None
    """Add a file and commit it with the given message."""
    _write(td, filename, "content of {0}\n".format(filename))
    _git(["add", filename], cwd=td)
    _git(["commit", "-m", message], cwd=td)


# ---------------------------------------------------------------------------
# TestConstantsAndExports
# ---------------------------------------------------------------------------

class TestConstantsAndExports(unittest.TestCase):
    """Verify the exported constants have the correct shape."""

    def test_required_spec_status_is_complete(self):
        self.assertEqual(_REQUIRED_SPEC_STATUS, "Complete")

    def test_four_artefacts_defined(self):
        self.assertEqual(len(_SETUP_CHAIN_ARTEFACTS), 4)

    def test_constitution_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn("constitution.md", paths)

    def test_claude_md_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn("CLAUDE.md", paths)

    def test_project_config_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn(".devforge/project-config.json", paths)

    def test_index_json_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn(".devforge/index.json", paths)

    def test_no_unpopulated_sentinels_exported(self):
        """_finalize/_preflight.py must NOT export _UNPOPULATED_SENTINELS.

        /finalize omits the constitution-populated sentinel guard — only the
        setup-chain existence check applies.  A future session must NOT add
        the sentinel guard back.
        """
        import _finalize._preflight as mod
        self.assertFalse(
            hasattr(mod, "_UNPOPULATED_SENTINELS"),
            "_finalize/_preflight.py must NOT define _UNPOPULATED_SENTINELS "
            "(the constitution-populated guard is intentionally omitted; "
            "the spec-Complete gate is a strictly stronger precondition)",
        )


# ---------------------------------------------------------------------------
# TestPreflightContext — pure function
# ---------------------------------------------------------------------------

class TestPreflightContext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.td)

    # --- No files ---

    def test_no_files_returns_sane_defaults(self):
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertEqual(r["source_root"], ".")
        self.assertFalse(r["wrapper_mode"])
        self.assertEqual(r["project_type"], "")
        self.assertEqual(r["framework"], "")
        self.assertEqual(r["language"], "")
        self.assertFalse(r["claude_md_present"])
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_no_files_spec_gate_defaults(self):
        r = preflight_context(self.td)
        self.assertEqual(r["spec_path"], "")
        self.assertEqual(r["spec_status"], "")
        self.assertFalse(r["spec_complete"])

    def test_no_files_missing_artefacts_contains_all_four(self):
        r = preflight_context(self.td)
        self.assertEqual(len(r["missing_artefacts"]), 4)

    def test_nonexistent_workspace_no_raise(self):
        r = preflight_context(os.path.join(self.td, "does_not_exist"))
        self.assertFalse(r["setup_chain_ok"])
        self.assertFalse(r["spec_complete"])

    def test_result_has_all_expected_keys(self):
        r = preflight_context(self.td)
        expected_keys = {
            "setup_chain_ok", "missing_artefacts",
            "spec_path", "spec_status", "spec_complete",
            "source_root", "wrapper_mode",
            "project_type", "framework", "language",
            "claude_md_present", "memory_present", "memory_excerpt",
            "wip_commit_count", "has_wip_commits",
        }
        self.assertEqual(set(r.keys()), expected_keys)

    def test_wip_defaults_to_zero(self):
        """No git repo in temp dir — wip_commit_count defaults to 0."""
        r = preflight_context(self.td)
        self.assertEqual(r["wip_commit_count"], 0)
        self.assertFalse(r["has_wip_commits"])

    # --- Full install (all artefacts present) ---

    def test_full_install_setup_chain_ok(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["missing_artefacts"], [])

    def test_full_install_source_root_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "src/backend")

    def test_full_install_project_type_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["project_type"], "web-app")

    def test_full_install_framework_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["framework"], "Django")

    def test_full_install_language_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["language"], "Python")

    def test_full_install_claude_md_present(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["claude_md_present"])

    # --- Spec gate — not-Complete (real fixture, Status: Draft) ---

    def test_draft_spec_fails_spec_complete_gate(self):
        """The real specify-sample-migration.md fixture is Status: Draft.

        preflight_context must parse it correctly and report spec_complete=False.
        """
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["spec_status"], "Draft")
        self.assertFalse(r["spec_complete"])

    def test_in_progress_spec_fails_complete_gate(self):
        spec_path = _write(
            self.td, "spec_ip.md",
            "# Spec\n\n**Status**: In Progress\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_status"], "In Progress")
        self.assertFalse(r["spec_complete"])

    def test_approved_spec_fails_complete_gate(self):
        spec_path = _write(
            self.td, "spec_ap.md",
            "# Spec\n\n**Status**: Approved\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_status"], "Approved")
        self.assertFalse(r["spec_complete"])

    # --- Spec gate — Complete (produced by REAL verify flip_spec_status) ---

    def test_complete_spec_passes_gate_real_producer(self):
        """The Complete spec is produced by the REAL flip_spec_status (not hand-authored).

        This validates the gate against a real producer output — the same file
        /verify writes when it approves a feature.
        """
        _make_full_install(self.td)
        spec_path = _make_complete_spec(self.td)

        r = preflight_context(self.td, spec_path=spec_path)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["spec_status"], "Complete")
        self.assertTrue(r["spec_complete"])

    def test_complete_spec_path_preserved_in_result(self):
        spec_path = _make_complete_spec(self.td)
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_path"], spec_path)

    def test_spec_path_none_skips_spec_gate(self):
        """When spec_path is None the spec gate is skipped — setup chain is still checked."""
        _make_full_install(self.td)
        r = preflight_context(self.td, spec_path=None)
        self.assertTrue(r["setup_chain_ok"])
        # Spec gate skipped
        self.assertEqual(r["spec_status"], "")
        self.assertFalse(r["spec_complete"])
        self.assertEqual(r["spec_path"], "")

    def test_missing_spec_file_spec_complete_false(self):
        """When spec_path is given but file does not exist, spec_complete=False."""
        _make_full_install(self.td)
        r = preflight_context(
            self.td,
            spec_path=os.path.join(self.td, "nonexistent_spec.md"),
        )
        self.assertTrue(r["setup_chain_ok"])
        self.assertFalse(r["spec_complete"])
        self.assertEqual(r["spec_status"], "")

    def test_multiline_status_is_rejected(self):
        """_STATUS_RE must NOT match across blank lines (horizontal whitespace only)."""
        spec_path = _write(
            self.td, "spec_malformed.md",
            "# Spec\n\n**Status**:\n\nComplete\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertFalse(r["spec_complete"],
                         "Malformed multi-line status must NOT pass the spec_complete gate")
        self.assertEqual(r["spec_status"], "",
                         "spec_status must be empty when value is not on the same line")

    # --- Constitution: existence is checked but sentinel content is NOT ---

    def test_unpopulated_constitution_does_not_block(self):
        """/finalize does NOT check sentinels — same rationale as /summarize."""
        _make_full_install(self.td)
        # Overwrite with an unpopulated sentinel body
        _write(self.td, "constitution.md",
               "{{CONSTITUTION_BODY}}\nRun `/constitute` to populate this.\n")
        r = preflight_context(self.td)
        # setup chain ok (constitution.md EXISTS)
        self.assertTrue(r["setup_chain_ok"])
        # No sentinel-populated key in the result
        self.assertNotIn("constitution_populated", r)

    def test_missing_constitution_fails_setup_chain(self):
        """constitution.md is artefact #1 — its absence fails the setup chain."""
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "constitution.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:constitute", r["missing_artefacts"])

    # --- Each setup-chain artefact missing individually ---

    def test_missing_claude_md_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "CLAUDE.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:init-forge", r["missing_artefacts"])

    def test_missing_project_config_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "project-config.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:configure", r["missing_artefacts"])

    def test_missing_index_json_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "index.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:generate-docs", r["missing_artefacts"])

    # --- Memory: .devforge/memory.md (live path) ---

    def test_full_install_memory_present(self):
        """Reads .devforge/memory.md — the live path."""
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Lesson 1", r["memory_excerpt"])

    def test_devforge_memory_md_is_read(self):
        """Explicit test: .devforge/memory.md present → memory_present=True."""
        _write(self.td, ".devforge/memory.md", "- Session note.\n")
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Session note", r["memory_excerpt"])

    def test_stale_claude_memory_path_is_NOT_consulted(self):
        """Only .devforge/memory.md is the live path.

        The stale path (.claude/memory/MEMORY.md) must NOT be read even if present.
        """
        _write(self.td, ".claude/memory/MEMORY.md",
               "- Stale memory entry.\n")
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_memory_excerpt_capped_at_40_lines(self):
        mem_content = "\n".join(
            ["Line {0}".format(i) for i in range(60)]
        ) + "\n"
        _write(self.td, ".devforge/memory.md", mem_content)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        lines = r["memory_excerpt"].splitlines()
        self.assertLessEqual(len(lines), 40)

    def test_memory_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    # --- CLAUDE.md: source_root + wrapper-mode ---

    def test_source_root_extraction_project_root(self):
        _write(self.td, "CLAUDE.md",
               "- **Project Root**: src/backend\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "src/backend")

    def test_source_root_extraction_source_root_label(self):
        _write(self.td, "CLAUDE.md",
               "- **Source Root**: frontend/src\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "frontend/src")

    def test_source_root_default_when_absent(self):
        _write(self.td, "CLAUDE.md", "# Minimal CLAUDE.md\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], ".")

    def test_wrapper_mode_false_by_default(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertFalse(r["wrapper_mode"])

    def test_wrapper_mode_detected_from_claude_md(self):
        _write(self.td, "CLAUDE.md",
               "# CLAUDE.md\n\n"
               "**Wrapper mode**: the source root is a subdirectory.\n"
               "- **Source Root**: myapp/\n")
        r = preflight_context(self.td)
        self.assertTrue(r["wrapper_mode"])

    def test_wrapper_root_label_triggers_wrapper_mode(self):
        _write(self.td, "CLAUDE.md",
               "- Wrapper root: /Users/me/myapp\n")
        r = preflight_context(self.td)
        self.assertTrue(r["wrapper_mode"])


# ---------------------------------------------------------------------------
# TestWipCommitDetection — real git fixtures
# ---------------------------------------------------------------------------

class TestWipCommitDetection(unittest.TestCase):
    """Test WIP/checkpoint detection using REAL git repos — not hand-faked output."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_no_wip_commits_returns_zero(self):
        """A repo with only a regular commit reports 0 WIP commits."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)
        # Add a regular (non-WIP) commit
        _add_commit(repo, "feature.py", "feat: add feature")
        count = _count_wip_commits(repo, base_ref="main")
        self.assertEqual(count, 0)

    def test_no_wip_commits_has_wip_commits_false(self):
        """has_wip_commits is False when wip_commit_count == 0."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)
        _add_commit(repo, "feature.py", "feat: add feature")
        r = preflight_context(repo, base_ref="main")
        self.assertFalse(r["has_wip_commits"])

    def test_wip_commit_detected(self):
        """A commit starting with [WIP] is detected as a WIP commit."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        # Create a feature branch from main
        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "step1.py", "[WIP] Feat: add step 1 — phase detail")

        count = _count_wip_commits(repo, base_ref="main")
        self.assertGreater(count, 0)

    def test_checkpoint_commit_detected(self):
        """A commit starting with [checkpoint] is detected."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "step1.py", "[checkpoint] Pre-feat: before refactor")

        count = _count_wip_commits(repo, base_ref="main")
        self.assertGreater(count, 0)

    def test_both_wip_and_checkpoint_counted(self):
        """Both [WIP] and [checkpoint] commits are counted."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "step1.py", "[WIP] Feat: first step — phase 1")
        _add_commit(repo, "step2.py", "[checkpoint] Pre-feat: checkpoint")
        _add_commit(repo, "step3.py", "[WIP] Feat: second step — phase 2")

        count = _count_wip_commits(repo, base_ref="main")
        self.assertEqual(count, 3)

    def test_regular_commits_not_counted(self):
        """Regular (non-WIP/checkpoint) commits are not counted."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "step1.py", "[WIP] Feat: wip step — phase 1")
        _add_commit(repo, "step2.py", "feat: finalized implementation")

        count = _count_wip_commits(repo, base_ref="main")
        # Only 1 WIP; the regular commit is not counted
        self.assertEqual(count, 1)

    def test_preflight_has_wip_commits_true_on_wip_repo(self):
        """preflight_context.has_wip_commits is True when WIP commits exist."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "impl.py", "[WIP] Feat: implementation — phase 1")

        # The repo IS the workspace_root (source_root = "." → resolves to repo)
        _write(repo, "CLAUDE.md",
               "# CLAUDE.md\n\n- **Project Root**: .\n")

        r = preflight_context(repo, base_ref="main")
        self.assertTrue(r["has_wip_commits"])
        self.assertGreater(r["wip_commit_count"], 0)

    def test_preflight_nothing_to_finalize_on_clean_repo(self):
        """A clean repo (no [WIP]/[checkpoint] commits) reports nothing to finalize."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/my-feature"], cwd=repo)
        _add_commit(repo, "impl.py", "feat: clean feature commit")

        _write(repo, "CLAUDE.md",
               "# CLAUDE.md\n\n- **Project Root**: .\n")

        r = preflight_context(repo, base_ref="main")
        self.assertFalse(r["has_wip_commits"])
        self.assertEqual(r["wip_commit_count"], 0)

    def test_autodetect_base_uses_origin_head_direct_ref_when_symbolic_ref_fails(self):
        """_autodetect_base falls back to 'origin/HEAD' as a direct ref.

        Fixture: two repos — a bare 'remote' and a local clone.
        The clone has origin/HEAD set as a direct ref but the symbolic-ref
        command is made to fail by deleting the symbolic ref file from
        .git/refs/remotes/origin/HEAD (leaving the packed-refs entry so that
        'git rev-parse --verify origin/HEAD' still resolves).

        Strategy: clone the bare remote (which sets origin/HEAD automatically),
        then delete .git/refs/remotes/origin/HEAD so symbolic-ref fails, but
        keep the packed-refs entry so the direct ref resolves.
        """
        from _finalize._preflight import _autodetect_base

        # Create a bare remote with one commit on 'main'.
        remote_dir = tempfile.mkdtemp(dir=self.td)
        _git(["init", "--bare", "--initial-branch=main", remote_dir], cwd=self.td)
        # Older git may not support --initial-branch for bare; tolerate that.
        _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote_dir)

        # Create a non-bare local repo, add a commit, push to remote.
        src_dir = tempfile.mkdtemp(dir=self.td)
        _git(["init", "--initial-branch=main"], cwd=src_dir)
        _git(["checkout", "-b", "main"], cwd=src_dir)
        _git(["config", "user.email", "test@example.com"], cwd=src_dir)
        _git(["config", "user.name", "Test"], cwd=src_dir)
        _write(src_dir, "README.md", "# Project\n")
        _git(["add", "README.md"], cwd=src_dir)
        _git(["commit", "-m", "initial"], cwd=src_dir)
        _git(["remote", "add", "origin", remote_dir], cwd=src_dir)
        _git(["push", "-u", "origin", "main"], cwd=src_dir)

        # Clone the remote so origin/HEAD is wired automatically.
        clone_dir = tempfile.mkdtemp(dir=self.td)
        _git(["clone", remote_dir, clone_dir], cwd=self.td)
        _git(["config", "user.email", "test@example.com"], cwd=clone_dir)
        _git(["config", "user.name", "Test"], cwd=clone_dir)

        # Verify origin/HEAD resolves as a direct ref at this point.
        rc, out, _ = _git(["rev-parse", "--verify", "origin/HEAD"], cwd=clone_dir)
        if rc != 0:
            self.skipTest("git clone did not wire origin/HEAD in this environment")

        # Now make symbolic-ref fail: remove .git/refs/remotes/origin/HEAD
        # if it exists as a plain file (it may be in packed-refs instead).
        symbolic_file = os.path.join(clone_dir, ".git", "refs", "remotes", "origin", "HEAD")
        if os.path.isfile(symbolic_file):
            os.unlink(symbolic_file)

        # Confirm symbolic-ref now fails.
        rc_sym, _, _ = _git(
            ["symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=clone_dir,
        )
        # If symbolic-ref still succeeds (git read packed-refs), skip the test —
        # this environment doesn't let us isolate the fallback arm cleanly.
        if rc_sym == 0:
            self.skipTest(
                "Cannot isolate origin/HEAD direct-ref fallback: "
                "symbolic-ref still succeeds after removing the loose file "
                "(git may have read packed-refs). "
                "The fallback code path is present and covered by review."
            )

        # Confirm the direct ref still resolves.
        rc_direct, _, _ = _git(
            ["rev-parse", "--verify", "origin/HEAD"],
            cwd=clone_dir,
        )
        if rc_direct != 0:
            self.skipTest(
                "origin/HEAD does not resolve as a direct ref in this environment"
            )

        # Now _autodetect_base must return "origin/HEAD" (direct-ref path),
        # NOT fall through to a local branch candidate.
        result = _autodetect_base(clone_dir)
        self.assertEqual(
            result,
            "origin/HEAD",
            "_autodetect_base must return 'origin/HEAD' when symbolic-ref fails "
            "but origin/HEAD resolves as a direct ref",
        )

    def test_not_a_git_repo_returns_zero_wip(self):
        """A non-git directory safely returns 0 WIP commits (no crash)."""
        not_git = tempfile.mkdtemp(dir=self.td)
        count = _count_wip_commits(not_git, base_ref="main")
        self.assertEqual(count, 0)

    def test_wip_count_explicit_base_ref(self):
        """An explicit base_ref is honored."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)

        _git(["checkout", "-b", "feature/work"], cwd=repo)
        _add_commit(repo, "f1.py", "[WIP] Feat: step 1 — phase 1")

        count = _count_wip_commits(repo, base_ref="main")
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# TestMemoryPathInvariant — source-level verification
# ---------------------------------------------------------------------------

class TestMemoryPathInvariant(unittest.TestCase):
    """Verify the preflight module reads .devforge/memory.md, not .claude/memory."""

    def test_preflight_module_contains_devforge_memory_path(self):
        """The source of _preflight.py must reference .devforge/memory.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn(".devforge/memory.md", source,
                      "preflight must read .devforge/memory.md")

    def test_preflight_module_does_not_contain_stale_claude_memory_path(self):
        """The source of _preflight.py must NOT reference .claude/memory/MEMORY.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn(
            ".claude/memory",
            source,
            "preflight must NOT reference the stale .claude/memory path",
        )

    def test_preflight_module_does_not_assign_unpopulated_sentinels(self):
        """_finalize/_preflight.py must NOT assign _UNPOPULATED_SENTINELS as a variable."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn(
            "_UNPOPULATED_SENTINELS = ",
            source,
            "_finalize/_preflight.py must NOT assign _UNPOPULATED_SENTINELS "
            "(the constitution-populated guard is intentionally omitted)",
        )

    def test_preflight_module_contains_complete_gate(self):
        """The source must reference the Complete gate and 'run /verify' message."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("Complete", source,
                      "preflight must reference the Complete gate")

    def test_preflight_module_does_not_read_dot_claude(self):
        """_preflight.py must have no .claude/ path string constants in executable code.

        Uses ast to walk the module tree and collect every string Constant that
        appears in a non-docstring context.  Module/class/function docstrings
        (which are ast.Expr nodes whose value is a Constant and appear as the
        first statement of their body) are excluded — they explain the invariant
        and are allowed to mention the stale path.

        Intent: enforce that path-construction strings never contain '.claude/'
        even if a future docstring edit introduces the text; the behavioral guard
        is test_stale_claude_memory_path_is_NOT_consulted.
        """
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()

        tree = ast.parse(source)

        def _collect_docstring_nodes(node):
            # type: (ast.AST,) -> set
            """Return the set of ast.Constant nodes that are docstrings."""
            docstrings = set()
            for n in ast.walk(node):
                body = getattr(n, "body", None)
                if not body:
                    continue
                first = body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(getattr(first, "value", None), ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    docstrings.add(id(first.value))
            return docstrings

        docstring_ids = _collect_docstring_nodes(tree)

        offending = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstring_ids
                and ".claude/" in node.value
            ):
                offending.append(node.value)

        self.assertEqual(
            offending,
            [],
            "_preflight.py must not contain '.claude/' in any executable string "
            "constant (only .devforge/ paths are valid). Offending values: {0}".format(
                offending
            ),
        )

    def test_preflight_module_uses_bsd_safe_grep_form(self):
        """_preflight.py must use separate --grep flags with --fixed-strings.

        Checks:
          1. Both [WIP] and [checkpoint] appear as separate --grep= values
             (BSD-safe form — not BRE alternation).
          2. --fixed-strings is present so brackets are not treated as char classes.
          3. The git log call list does NOT contain a combined grep pattern with
             the BRE alternation pipe character inside a string argument.
        """
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_finalize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        # The BSD-safe form passes each pattern as its own --grep argument.
        self.assertIn('"--grep=[WIP]"', source,
                      "Must use separate --grep=[WIP] flag (BSD-safe form)")
        self.assertIn('"--grep=[checkpoint]"', source,
                      "Must use separate --grep=[checkpoint] flag (BSD-safe form)")
        # Must use --fixed-strings to prevent [WIP] being treated as char class.
        self.assertIn('"--fixed-strings"', source,
                      "Must use --fixed-strings flag to prevent bracket-as-charclass bug")
        # Must NOT combine the two patterns in a single grep value
        # (e.g. "--grep=[WIP]\\|[checkpoint]" or similar combined form).
        self.assertNotIn('"--grep=[WIP]\\\\|[checkpoint]"', source,
                         "Must NOT combine patterns with BRE alternation in one --grep")


# ---------------------------------------------------------------------------
# TestCmdPreflight — CLI handler exit codes via _cli.main
# ---------------------------------------------------------------------------

class TestCmdPreflight(unittest.TestCase):
    """Verify the CLI gate behaviour (exit 2 on missing artefacts, exit 3 on not-Complete)."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.td)

    def _run_preflight(self, workspace_root, spec=None, base=None):
        # type: (str, str, str) -> tuple
        """Run finalize_helper preflight and return (exit_code, stdout_text, stderr_text)."""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from _finalize._cli import main

        argv = ["preflight", "--workspace-root", workspace_root]
        if spec:
            argv += ["--spec", spec]
        if base:
            argv += ["--base", base]

        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(argv)
        except SystemExit as exc:
            code = exc.code
        return code, buf.getvalue(), err.getvalue()

    # --- Happy path ---

    def test_full_install_no_spec_exits_0(self):
        """Without --spec, only the setup chain is checked."""
        _make_full_install(self.td)
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 for full install without spec, got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])

    def test_full_install_complete_spec_exits_0(self):
        """Full install + Complete spec (real producer) → exit 0."""
        _make_full_install(self.td)
        spec_path = _make_complete_spec(self.td)
        code, out, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 for Complete spec, got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        self.assertTrue(data["spec_complete"])
        self.assertEqual(data["spec_status"], "Complete")

    # --- Setup chain incomplete → exit 2 ---

    def test_missing_setup_chain_exits_2(self):
        code, _, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_missing_one_artefact_exits_2(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "index.json"))
        code, _, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_missing_artefact_stderr_names_finalize_helper(self):
        code, _, err = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        self.assertIn("finalize_helper", err)

    def test_missing_artefact_stderr_names_setup_sequence(self):
        code, _, err = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        self.assertIn("/devforge:init-forge", err)

    # --- Spec not Complete → exit 3 ---

    def test_draft_spec_exits_3(self):
        """The real specify-sample-migration.md (Status: Draft) → exit 3."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        code, out, err = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3,
                         msg="Expected exit 3 for Draft spec, got {0}".format(code))
        self.assertIn("/devforge:verify", err)

    def test_not_complete_stderr_mentions_current_status(self):
        """stderr must name the actual (non-Complete) status value."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        _, _, err = self._run_preflight(self.td, spec=spec_path)
        self.assertIn("Draft", err)

    def test_in_progress_spec_exits_3(self):
        _make_full_install(self.td)
        spec_path = _write(
            self.td, "spec_ip.md",
            "# Spec\n\n**Status**: In Progress\n\n## Overview\n\nContent.\n"
        )
        code, _, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3)

    def test_nonexistent_spec_path_exits_3(self):
        """When --spec points to a nonexistent file, spec_complete=False → exit 3."""
        _make_full_install(self.td)
        code, out, err = self._run_preflight(
            self.td, spec=os.path.join(self.td, "nonexistent_spec.md")
        )
        self.assertEqual(code, 3,
                         msg="Nonexistent spec path must exit 3 (not setup-chain exit 2), got {0}".format(code))
        self.assertIn("/devforge:verify", err,
                      msg="stderr must mention /devforge:verify when spec gate fails")

    # --- JSON always emitted to stdout ---

    def test_stdout_is_always_json_on_missing_setup_chain(self):
        """Even when exit 2, stdout must contain JSON."""
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertIn("setup_chain_ok", data)
        self.assertIn("missing_artefacts", data)

    def test_stdout_is_always_json_on_not_complete_spec(self):
        """Even when exit 3, stdout must contain JSON."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        code, out, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3)
        data = json.loads(out)
        self.assertIn("spec_complete", data)
        self.assertFalse(data["spec_complete"])

    def test_json_contains_wip_fields(self):
        """JSON output must contain wip_commit_count and has_wip_commits."""
        _make_full_install(self.td)
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("wip_commit_count", data)
        self.assertIn("has_wip_commits", data)

    # --- Wrapper mode via CLI ---

    def test_wrapper_mode_install_setup_chain_ok(self):
        """A wrapper-mode CLAUDE.md is correctly reported as wrapper_mode=True."""
        _make_full_install(self.td)
        # Overwrite CLAUDE.md with a wrapper-mode one.
        _write(self.td, "CLAUDE.md",
               "# CLAUDE.md\n\n"
               "**Wrapper mode**: active.\n"
               "- **Source Root**: myapp/\n")
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["wrapper_mode"])
        self.assertEqual(data["source_root"], "myapp/")

    # --- Unpopulated constitution does NOT block /finalize ---

    def test_unpopulated_constitution_does_not_trigger_exit_2(self):
        """/finalize has no constitution-populated guard — unpopulated = ok."""
        _make_full_install(self.td)
        _write(self.td, "constitution.md",
               "{{CONSTITUTION_BODY}}\nRun `/constitute` to populate this.\n")
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 (no sentinel guard), got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        # No constitution_populated key (the guard is intentionally absent)
        self.assertNotIn("constitution_populated", data)

    # --- WIP commit detection via CLI ---

    def test_cli_reports_wip_commits_in_json(self):
        """A repo with [WIP] commits surfaces them in JSON output."""
        repo = tempfile.mkdtemp(dir=self.td)
        _make_git_repo(repo)
        _git(["checkout", "-b", "feature/work"], cwd=repo)
        _add_commit(repo, "impl.py", "[WIP] Feat: step 1 — phase 1")

        # Lay the setup chain IN the repo (workspace_root = repo)
        _make_full_install(repo)
        # Override CLAUDE.md so source_root points to the repo itself
        _write(repo, "CLAUDE.md",
               "# CLAUDE.md\n\n"
               "- **Project Root**: .\n"
               "- **Name**: TestProject\n")

        code, out, _ = self._run_preflight(repo, base="main")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["has_wip_commits"])
        self.assertGreater(data["wip_commit_count"], 0)


# ---------------------------------------------------------------------------
# TestLauncherSmoke — import + help + registry shape
# ---------------------------------------------------------------------------

class TestLauncherSmoke(unittest.TestCase):
    """Verify the CLI entry point parses --help and the registry is extensible."""

    def test_help_exits_cleanly(self):
        from _finalize._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_no_subcommand_exits_2(self):
        from _finalize._cli import main
        code = main([])
        self.assertEqual(code, 2)

    def test_preflight_help_exits_0(self):
        from _finalize._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["preflight", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_registry_has_preflight(self):
        from _finalize._cli import _SUBCOMMAND_REGISTRY
        verbs = [v for v, _, _ in _SUBCOMMAND_REGISTRY]
        self.assertIn("preflight", verbs)

    def test_registry_has_all_verbs_through_phase3(self):
        """Phase 1 + 2 + 3 verbs are all present in the registry."""
        from _finalize._cli import _SUBCOMMAND_REGISTRY
        verbs = [v for v, _, _ in _SUBCOMMAND_REGISTRY]
        # Phase 1: preflight
        self.assertIn("preflight", verbs)
        # Phase 2: read/compute verbs (no mutation)
        self.assertIn("gather-change-data", verbs)
        self.assertIn("resolve-squash-base", verbs)
        self.assertIn("check-pushed", verbs)
        # Phase 3: git-mutating squash verb
        self.assertIn("squash", verbs)
        # Total through Phase 3: 5 verbs
        self.assertEqual(len(_SUBCOMMAND_REGISTRY), 5)

    def test_registry_entries_are_triples(self):
        from _finalize._cli import _SUBCOMMAND_REGISTRY
        for entry in _SUBCOMMAND_REGISTRY:
            self.assertEqual(len(entry), 3,
                             msg="Registry entry must be a (verb, help, handler) triple")

    def test_main_is_importable_from_init(self):
        from _finalize import main
        self.assertTrue(callable(main))

    def test_parser_prog_is_finalize_helper(self):
        """prog must be 'finalize_helper', not 'summarize_helper' or other."""
        from _finalize._cli import build_parser
        parser = build_parser()
        self.assertEqual(parser.prog, "finalize_helper")


# ---------------------------------------------------------------------------
# TestFinalizeHelperShim — Python shim imports and dispatches
# ---------------------------------------------------------------------------

class TestFinalizeHelperShim(unittest.TestCase):
    """Verify finalize_helper.py shim wires _finalize._cli.main correctly."""

    def test_shim_imports_main_from_finalize_cli(self):
        """finalize_helper.py must import from _finalize._cli, not _summarize or other."""
        shim_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "finalize_helper.py"
        )
        with open(str(shim_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("from _finalize._cli import main", source)
        self.assertNotIn("from _summarize._cli import main", source)
        self.assertNotIn("from _verify._cli import main", source)

    def test_launcher_is_executable(self):
        launcher = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "finalize_helper"
        )
        self.assertTrue(
            os.access(str(launcher), os.X_OK),
            "finalize_helper must be executable (chmod +x)",
        )

    def test_launcher_references_finalize_helper_py(self):
        launcher = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "finalize_helper"
        )
        with open(str(launcher), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("finalize_helper.py", source)

    def test_launcher_is_posix_shell(self):
        """The POSIX launcher must start with #!/bin/sh."""
        launcher = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "finalize_helper"
        )
        with open(str(launcher), "r", encoding="utf-8") as fh:
            first_line = fh.readline()
        self.assertEqual(first_line.strip(), "#!/bin/sh")


if __name__ == "__main__":
    unittest.main()
