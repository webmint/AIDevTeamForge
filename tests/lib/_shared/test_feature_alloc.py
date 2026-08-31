"""Tests for src/devforge/lib/_shared/feature_alloc.py.

Coverage:
  next_spec_number      — fresh repo -> 1; existing specs/003-* -> 4;
                           non-NNN dirs ignored; wrapper-root resolution.
                           UNCHANGED by 91-FEATURE-DIR-IDENTITY-AND-
                           PROVENANCE-PLAN.md Phase 3 — allocate_feature_dir
                           no longer calls this function (D6), but the
                           function itself, and this whole coverage block,
                           are untouched.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3 coverage (the
layout switch — allocate_feature_dir now composes
specs/<YYYY>/<MM>/<leaf>/, never specs/<NNN>-<slug>/, for every fresh
allocation; decide_branch_action now emits spec/<ticket-or-slug>, never
spec/<NNN>-<slug>):
  allocate_feature_dir  — new-shape composition (year/month from an
                           injected `now`, deterministic); ticket-given ->
                           leaf is the ticket; ticketless (require_ticket
                           False) -> leaf is the SLUG (Phase 3's own
                           unresolved item 1 — see feature_alloc.py's
                           docstring for the full argument; pinned here);
                           `number`/`formatted_number`/`dirname` ABSENT
                           from the result; wrapper-root resolution;
                           relative_path correctness (forward slashes,
                           genuinely relative, recombines to `path`);
                           invalid slug still rejected first, unchanged;
                           never-overwrite fails loudly on a same-ticket
                           collision AND on a same-slug (ticketless)
                           collision, both in the same YYYY/MM bucket, with
                           NO mocking needed (the collision is constructed
                           directly via a fixed `now` + a repeated
                           ticket/slug — the old NNN-scan race simulation
                           this replaces needed mock.patch precisely
                           because NNN was derived from a scan; a
                           ticket/slug leaf is caller-supplied, so the
                           collision is just two calls with the same
                           inputs).
  decide_branch_action  — all three arms (create / keep-spec / keep-other);
                           ticket-given -> spec/<ticket>; ticketless ->
                           spec/<slug> (same Phase-3 item-1 fallback,
                           pinned on this function too); missing BOTH
                           ticket and slug on the default branch refuses;
                           keep-spec and keep-other render IDENTICAL text
                           (the original /specify wording, preserved).
  (mixed-shape coexistence — D6 mandates both the legacy specs/NNN-slug/
  shape and the new specs/YYYY/MM/leaf/ shape resolve, forever, in the
  SAME install; TestIterFeatureDirs / TestFindFeatureDirsWith below
  already pin this with hand-built trees from Phase 1, and
  TestMixedShapeRealProducerRoundTrip adds a real-producer round-trip: an
  actual allocate_feature_dir call writing the new shape, discovered
  alongside a hand-built legacy dir, via iter_feature_dirs /
  find_feature_dirs_with unmodified.)
  specs_root_for        — repo-root and wrapper-root resolution; pure path
                           arithmetic (no stat, safe on nonexistent paths);
                           composes with iter_feature_dirs.
  iter_feature_dirs      — legacy-only / new-shape-only / mixed trees;
                           specs/ absent or empty; a 9999-too-many-digits
                           dir claimed by neither arm; stray non-directory
                           entries at every level ignored; documented sort
                           order (legacy family first, then new-shape);
                           an unreadable specs/ (or an unreadable ancestor)
                           returns [] rather than raising; symlinked
                           feature dirs are followed, dangling ones
                           excluded; near-miss name shapes (0001-x, 12345,
                           202-6, 2026-08) classified by exactly one arm
                           or none, never both.
  find_feature_dirs_with — sentinel-file filter on top of
                           iter_feature_dirs; a dir lacking the sentinel is
                           excluded, and so is a dir holding a DIRECTORY of
                           that name rather than a file; a symlinked
                           sentinel file matches, a dangling one does not.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2 coverage (ticket
identity):
  normalize_ticket      — valid "PROJ-123"; whitespace stripped around an
                           otherwise-valid ticket; every close-but-wrong
                           input (lowercase, mixed case, a bare number, a
                           space where the dash belongs, empty string,
                           None) rejected with a message, never silently
                           coerced.
  read_require_ticket   — hand-written project-config.json fixtures for
                           the reader's own edge/error paths (absent
                           file, malformed JSON, non-object top level,
                           key absent, key present with a non-"true"
                           value) — mirroring tests/lib/_verify/
                           test_e2e.py's precedent for testing a
                           project-config.json reader in isolation. The
                           REAL-PRODUCER round-trip (configure_helper
                           set-require-ticket + render-config feeding
                           this same function) lives in
                           tests/lib/_configure/test_require_ticket.py,
                           where the configure_helper subprocess
                           machinery already lives.
  allocate_feature_dir  — ticket/require_ticket wiring: ticketless
                           allocation still succeeds when require_ticket
                           is False; a valid ticket is accepted and
                           echoed back (canonical case) in the result;
                           require_ticket True + no ticket refuses,
                           naming both routes out; require_ticket True +
                           a malformed ticket refuses the same way;
                           require_ticket False + a malformed ticket
                           supplied anyway still refuses (format is
                           always checked), but WITHOUT the "REQUIRE_
                           TICKET" framing, since the gate itself is not
                           what is refusing.

All tests use real tempfile-backed filesystem trees — no hand-fabricated
JSON, no mocked Path objects (except the read_require_ticket edge-case
fixtures noted above, which mirror the _verify/test_e2e.py precedent for
a project-config.json reader's own malformed-input paths). Phase 3's own
collision tests need no mocking at all (see the coverage note above) —
the pre-Phase-3 race-simulation test that patched next_spec_number is
retired along with the NNN-scan it simulated a race against.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Permission-guarded test gate.
#
# chmod(..., 0o000) only enforces anything under POSIX, and only for a
# non-root user (root bypasses all permission checks, so the assertion
# would pass for the wrong reason -- it would prove nothing about the
# OSError-handling code path under test). No prior test in this file
# exercises permission errors; this constant is the first such gate.
# ---------------------------------------------------------------------------

_SKIP_PERMISSION_TESTS = os.name != "posix" or (
    hasattr(os, "geteuid") and os.geteuid() == 0
)
_PERMISSION_SKIP_REASON = (
    "permission enforcement requires a non-root POSIX user"
)

# ---------------------------------------------------------------------------
# Path setup (mirrors tests/lib/_shared/test_feature_scope.py).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.feature_alloc import (  # noqa: E402
    FEATURE_NAME_RE,
    MONTH_DIR_RE,
    SPEC_NUMBER_DIR_RE,
    SPEC_NUMBER_WIDTH,
    SPECS_ROOT_DEFAULT,
    TICKET_RE,
    YEAR_DIR_RE,
    allocate_feature_dir,
    decide_branch_action,
    find_feature_dirs_with,
    iter_feature_dirs,
    next_spec_number,
    normalize_ticket,
    read_require_ticket,
    specs_root_for,
)


# ---------------------------------------------------------------------------
# next_spec_number
# ---------------------------------------------------------------------------


class TestNextSpecNumber(unittest.TestCase):
    def test_fresh_repo_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_no_specs_dir_at_all_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            # Not even the repo root's specs/ exists.
            devforge_dir = Path(td) / "sub" / ".devforge"
            devforge_dir.mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_existing_specs_003_returns_4(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "001-foo").mkdir(parents=True)
            (specs_root / "003-bar").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 4)

    def test_non_nnn_dirs_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "002-real").mkdir(parents=True)
            (specs_root / "not-a-spec-dir").mkdir(parents=True)
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 3)

    def test_files_in_specs_root_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            (specs_root / "005-a-file-not-a-dir").write_text("x")
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_wrapper_root_resolution(self):
        """devforge_dir's PARENT is the repo/install root, matching wrapper mode."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            specs_root = wrapper_root / SPECS_ROOT_DEFAULT
            (specs_root / "007-x").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 8)
            # Confirm it did NOT look one level further up (outside wrapper root).
            outer_specs = Path(td) / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())


# ---------------------------------------------------------------------------
# allocate_feature_dir
# ---------------------------------------------------------------------------


class TestAllocateFeatureDir(unittest.TestCase):
    # Fixed clock for every test below that needs a deterministic
    # year/month bucket -- mirrors this codebase's "inject the timestamp"
    # convention (see allocate_feature_dir's "Date source" docstring
    # paragraph) rather than mocking datetime.now itself.
    _NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    def test_fresh_allocation_ticketless_uses_slug_as_leaf(self):
        """91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3's own
        unresolved item 1, pinned: REQUIRE_TICKET defaults False (OQ-1)
        and a ticketless allocation must still succeed (Phase 2's shipped
        contract) even though the ticket is now the leaf (D2/D3). The
        chosen resolution: the SLUG becomes the leaf when no ticket is
        given."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["slug"], "add-dark-mode")
            self.assertIsNone(result["ticket"])
            self.assertEqual(result["year"], "2026")
            self.assertEqual(result["month"], "08")
            self.assertEqual(result["leaf"], "add-dark-mode")
            self.assertTrue(result["created"])
            expected_path = (
                Path(td).resolve() / SPECS_ROOT_DEFAULT / "2026" / "08" / "add-dark-mode"
            )
            self.assertEqual(Path(result["path"]), expected_path)
            self.assertTrue(expected_path.is_dir())

    def test_fresh_allocation_with_ticket_uses_ticket_as_leaf(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="PROJ-123", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["ticket"], "PROJ-123")
            self.assertEqual(result["leaf"], "PROJ-123")
            expected_path = (
                Path(td).resolve() / SPECS_ROOT_DEFAULT / "2026" / "08" / "PROJ-123"
            )
            self.assertEqual(Path(result["path"]), expected_path)
            self.assertTrue(expected_path.is_dir())
            # D3: no slug composite in the leaf.
            self.assertNotIn("add-dark-mode", result["leaf"])

    def test_ticket_and_slug_both_given_ticket_wins(self):
        """D3: the leaf is the ticket ONLY -- a supplied slug never rides
        along even when both are available."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="ENG-9", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["leaf"], "ENG-9")
            self.assertEqual(result["relative_path"], "specs/2026/08/ENG-9")

    def test_legacy_shape_keys_absent_from_new_result(self):
        """number / formatted_number / dirname existed on the pre-Phase-3
        legacy-shape result; a fresh allocation no longer computes an NNN
        at all, so these keys must not appear -- a caller must not assume
        they exist."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertNotIn("number", result)
            self.assertNotIn("formatted_number", result)
            self.assertNotIn("dirname", result)

    def test_slug_reused_across_different_tickets_same_month_allowed(self):
        """The plan-68 OQ-4 precedent, carried forward: the identity
        (now the ticket) is what must be unique, not the slug -- two
        features may legitimately share a slug."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result1, error1 = allocate_feature_dir(
                devforge_dir, "same-slug-twice", ticket="PROJ-1", now=self._NOW,
            )
            self.assertIsNone(error1)
            result2, error2 = allocate_feature_dir(
                devforge_dir, "same-slug-twice", ticket="PROJ-2", now=self._NOW,
            )
            self.assertIsNone(error2)
            self.assertEqual(result1["slug"], result2["slug"])
            self.assertNotEqual(result1["leaf"], result2["leaf"])
            specs_root = Path(td) / SPECS_ROOT_DEFAULT / "2026" / "08"
            self.assertTrue((specs_root / "PROJ-1").is_dir())
            self.assertTrue((specs_root / "PROJ-2").is_dir())

    def test_invalid_slug_single_word_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "onlyoneword")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("invalid slug", error)
            # No directory was created.
            self.assertFalse((Path(td) / SPECS_ROOT_DEFAULT).exists())

    def test_invalid_slug_uppercase_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "Add-DarkMode")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_invalid_slug_too_many_words_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "way-too-many-words-here-now",
            )
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_invalid_slug_empty_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_existing_target_dir_failure_is_loud_same_ticket_same_month(self):
        """Never-overwrite, ticket path: two allocations naming the SAME
        ticket in the SAME YYYY/MM bucket -- the second fails loudly, no
        mocking needed (the collision is just two calls with the same
        ticket + the same injected `now`)."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result1, error1 = allocate_feature_dir(
                devforge_dir, "first-slug", ticket="PROJ-123", now=self._NOW,
            )
            self.assertIsNone(error1)
            result2, error2 = allocate_feature_dir(
                devforge_dir, "second-slug", ticket="PROJ-123", now=self._NOW,
            )
            self.assertEqual(result2, {})
            self.assertIsNotNone(error2)
            self.assertIn("already exists", error2)
            self.assertIn("refusing to reuse", error2)
            # The first allocation's directory is untouched.
            self.assertTrue(Path(result1["path"]).is_dir())

    def test_existing_target_dir_failure_is_loud_same_slug_same_month_ticketless(self):
        """Never-overwrite, item-1's slug-fallback path: two TICKETLESS
        allocations naming the SAME slug in the SAME YYYY/MM bucket -- the
        second fails loudly too. This is the disclosed narrowing of plan
        68 OQ-4's original guarantee (see allocate_feature_dir's own
        docstring): OQ-4 promised no collision on a shared slug because
        NNN (now the ticket) was the identity: with no ticket, the slug
        itself becomes that identity, so a repeat is a genuine collision,
        not a label reuse."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result1, error1 = allocate_feature_dir(
                devforge_dir, "same-slug-twice", now=self._NOW,
            )
            self.assertIsNone(error1)
            result2, error2 = allocate_feature_dir(
                devforge_dir, "same-slug-twice", now=self._NOW,
            )
            self.assertEqual(result2, {})
            self.assertIsNotNone(error2)
            self.assertIn("already exists", error2)
            self.assertIn("refusing to reuse", error2)
            self.assertTrue(Path(result1["path"]).is_dir())

    def test_valid_slug_boundaries_2_and_4_words(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "two-words", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["leaf"], "two-words")

        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "one-two-three-four", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["leaf"], "one-two-three-four")

    def test_wrapper_root_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            result, error = allocate_feature_dir(
                devforge_dir, "wrapper-mode-feature", now=self._NOW,
            )
            self.assertIsNone(error)
            expected_path = (
                wrapper_root.resolve()
                / SPECS_ROOT_DEFAULT / "2026" / "08" / "wrapper-mode-feature"
            )
            self.assertEqual(Path(result["path"]), expected_path)
            self.assertTrue(expected_path.is_dir())
            # Confirm no dir was created one level further up.
            outer_specs = Path(td) / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())

    def test_relative_path_present_and_correct(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["relative_path"], "specs/2026/08/add-dark-mode")

    def test_relative_path_is_genuinely_relative(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "genuinely-relative")
            self.assertIsNone(error)
            relative_path = result["relative_path"]
            self.assertFalse(relative_path.startswith("/"))
            self.assertNotIn(str(Path(td).resolve()), relative_path)
            self.assertNotIn(td, relative_path)

    def test_relative_path_uses_forward_slashes(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "forward-slash-check")
            self.assertIsNone(error)
            self.assertNotIn("\\", result["relative_path"])
            self.assertIn("/", result["relative_path"])

    def test_relative_path_recombines_to_absolute_path(self):
        """os.path.join(repo_root, relative_path) must reconstruct exactly
        the absolute `path` the SAME call returned -- the two keys must
        never disagree."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "recombine-check")
            self.assertIsNone(error)
            repo_root = Path(td).resolve()
            reconstructed = repo_root.joinpath(*result["relative_path"].split("/"))
            self.assertEqual(reconstructed, Path(result["path"]))
            # And the os.path.join form the spec text describes, resolved
            # through Path for cross-platform separator equivalence.
            joined = os.path.join(str(repo_root), result["relative_path"])
            self.assertEqual(Path(joined).resolve(), Path(result["path"]).resolve())

    def test_relative_path_wrapper_root_resolution(self):
        """Wrapper mode: relative_path is relative to the install root
        (devforge_dir's parent), not to any outer directory."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            result, error = allocate_feature_dir(
                devforge_dir, "wrapper-relative", now=self._NOW,
            )
            self.assertIsNone(error)
            self.assertEqual(result["relative_path"], "specs/2026/08/wrapper-relative")
            reconstructed = wrapper_root.resolve() / result["relative_path"]
            self.assertEqual(reconstructed, Path(result["path"]))

    def test_now_defaults_to_utc_now_when_not_injected(self):
        """No `now` argument -> the function falls back to
        datetime.now(timezone.utc), not local time (see the "Date source"
        docstring paragraph for why UTC, not OQ-3's own -- incorrect --
        "local date" claim). Bounded assertion: the returned year/month
        match a UTC-now snapshot taken immediately either side of the
        call, tolerating the (vanishingly rare) case of a UTC month
        rollover occurring mid-test."""
        before = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "no-now-injected")
        after = datetime.now(timezone.utc)
        self.assertIsNone(error)
        possible_years = {before.strftime("%Y"), after.strftime("%Y")}
        possible_months = {before.strftime("%m"), after.strftime("%m")}
        self.assertIn(result["year"], possible_years)
        self.assertIn(result["month"], possible_months)


# ---------------------------------------------------------------------------
# decide_branch_action
# ---------------------------------------------------------------------------


class TestDecideBranchAction(unittest.TestCase):
    """91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md D5: branch is
    spec/<ticket> when a ticket is given, else spec/<slug> (the same
    item-1 fallback allocate_feature_dir applies to the directory leaf).
    Signature changed from (current, default, spec_number, slug) to
    (current, default, ticket, slug) -- every test in this class is
    rewritten, not merely re-pointed, because D5 retires the spec/NNN-slug
    branch shape for a NEW branch outright."""

    def test_arm_create_on_default_branch_with_ticket(self):
        decision, line, error = decide_branch_action(
            "main", "main", "PROJ-123", "add-dark-mode",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/PROJ-123")

    def test_arm_create_on_default_branch_ticketless_uses_slug(self):
        """Item 1's fallback, pinned on the branch-naming side too."""
        decision, line, error = decide_branch_action(
            "main", "main", None, "add-dark-mode",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/add-dark-mode")

    def test_arm_create_ticket_wins_over_slug_when_both_given(self):
        decision, line, error = decide_branch_action(
            "main", "main", "PROJ-123", "add-dark-mode",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertNotIn("add-dark-mode", line)

    def test_arm_create_missing_both_ticket_and_slug(self):
        decision, line, error = decide_branch_action("main", "main", None, None)
        self.assertEqual(decision, "create")
        self.assertEqual(line, "")
        self.assertIsNotNone(error)
        self.assertIn("ticket", error)
        self.assertIn("slug", error)

    def test_arm_create_missing_both_empty_strings(self):
        decision, line, error = decide_branch_action("main", "main", "", "")
        self.assertEqual(decision, "create")
        self.assertIsNotNone(error)

    def test_arm_keep_spec_on_existing_feature_branch(self):
        decision, line, error = decide_branch_action(
            "spec/000-other-feature", "main", "PROJ-123", "add-dark-mode",
        )
        self.assertEqual(decision, "keep-spec")
        self.assertIsNone(error)
        self.assertEqual(
            line,
            "# already on non-default branch 'spec/000-other-feature'; "
            "no checkout emitted",
        )

    def test_arm_keep_other_on_unrelated_branch(self):
        decision, line, error = decide_branch_action(
            "feature/scratch", "main", "PROJ-123", "add-dark-mode",
        )
        self.assertEqual(decision, "keep-other")
        self.assertIsNone(error)
        self.assertEqual(
            line,
            "# already on non-default branch 'feature/scratch'; "
            "no checkout emitted",
        )

    def test_keep_spec_and_keep_other_render_identical_text_shape(self):
        """The two 'keep' arms must differ only in the branch name embedded,
        never in the surrounding template — /specify's stdout depends on
        this being the single original message shape."""
        _, line_spec, _ = decide_branch_action(
            "spec/999-x", "main", "PROJ-123", "add-dark-mode",
        )
        _, line_other, _ = decide_branch_action(
            "some-other-branch", "main", "PROJ-123", "add-dark-mode",
        )
        template = "# already on non-default branch {0!r}; no checkout emitted"
        self.assertEqual(line_spec, template.format("spec/999-x"))
        self.assertEqual(line_other, template.format("some-other-branch"))

    def test_current_equals_default_takes_priority_over_spec_prefix(self):
        """If the default branch itself were named spec/..., current==default
        still wins (matches the original code's branch order)."""
        decision, line, error = decide_branch_action(
            "spec/main", "spec/main", "PROJ-2", "weird-default-branch",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/PROJ-2")

    def test_strips_whitespace_on_branch_names(self):
        decision, line, error = decide_branch_action(
            "  main  ", "  main  ", "PROJ-3", "trim-test-feature",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/PROJ-3")

    def test_strips_whitespace_on_ticket_and_slug(self):
        decision, line, error = decide_branch_action(
            "main", "main", "  PROJ-4  ", "  trim-test-feature  ",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/PROJ-4")


# ---------------------------------------------------------------------------
# Constants sanity (used elsewhere via re-export — pin their values here).
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_feature_name_re_shape(self):
        self.assertTrue(FEATURE_NAME_RE.match("two-words"))
        self.assertTrue(FEATURE_NAME_RE.match("one-two-three-four"))
        self.assertFalse(FEATURE_NAME_RE.match("oneword"))
        self.assertFalse(FEATURE_NAME_RE.match("Two-Words"))
        self.assertFalse(FEATURE_NAME_RE.match("one-two-three-four-five"))

    def test_spec_number_dir_re_shape(self):
        self.assertTrue(SPEC_NUMBER_DIR_RE.match("001-foo"))
        self.assertFalse(SPEC_NUMBER_DIR_RE.match("1-foo"))
        self.assertFalse(SPEC_NUMBER_DIR_RE.match("abc-foo"))

    def test_spec_number_width_and_root(self):
        self.assertEqual(SPEC_NUMBER_WIDTH, 3)
        self.assertEqual(SPECS_ROOT_DEFAULT, "specs")

    def test_year_dir_re_shape(self):
        self.assertTrue(YEAR_DIR_RE.match("2026"))
        self.assertFalse(YEAR_DIR_RE.match("26"))
        self.assertFalse(YEAR_DIR_RE.match("20266"))
        self.assertFalse(YEAR_DIR_RE.match("2026-08"))

    def test_month_dir_re_shape(self):
        self.assertTrue(MONTH_DIR_RE.match("08"))
        self.assertFalse(MONTH_DIR_RE.match("8"))
        self.assertFalse(MONTH_DIR_RE.match("123"))


# ---------------------------------------------------------------------------
# specs_root_for
# ---------------------------------------------------------------------------


class TestSpecsRootFor(unittest.TestCase):
    def test_returns_repo_root_specs(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            expected = Path(td).resolve() / SPECS_ROOT_DEFAULT
            self.assertEqual(specs_root_for(devforge_dir), expected)

    def test_wrapper_root_resolution(self):
        """devforge_dir's PARENT is the wrapper/install root -- the same
        convention next_spec_number / allocate_feature_dir already rely
        on."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            expected = wrapper_root.resolve() / SPECS_ROOT_DEFAULT
            self.assertEqual(specs_root_for(devforge_dir), expected)

    def test_pure_path_arithmetic_does_not_require_existing_paths(self):
        """Docstring claim: does not stat devforge_dir, the returned
        specs_root, or any ancestor -- safe to call even when none of
        them exist on disk."""
        with tempfile.TemporaryDirectory() as td:
            nonexistent_devforge_dir = Path(td) / "never-created" / ".devforge"
            # Must not raise even though nothing on this path exists.
            result = specs_root_for(nonexistent_devforge_dir)
            self.assertEqual(
                result,
                Path(td).resolve() / "never-created" / SPECS_ROOT_DEFAULT,
            )
            self.assertFalse(result.exists())

    def test_composes_with_iter_feature_dirs(self):
        """specs_root_for's whole reason to exist: a devforge_dir-holding
        caller reaches the specs_root iter_feature_dirs actually takes, in
        one explicit call."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "001-x").mkdir(parents=True)
            result = iter_feature_dirs(specs_root_for(devforge_dir))
            self.assertEqual(result, [specs_root / "001-x"])


# ---------------------------------------------------------------------------
# iter_feature_dirs / find_feature_dirs_with
# ---------------------------------------------------------------------------


class TestIterFeatureDirs(unittest.TestCase):
    def test_specs_dir_absent_returns_empty_list(self):
        """specs_root itself was never created -- distinct from
        test_specs_dir_present_but_empty_returns_empty_list (exists but
        empty) and the two test_unreadable_specs_root_* cases (exists but
        (ancestor-)unreadable)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_specs_dir_present_but_empty_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_legacy_only_tree(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "003-legacy-three").mkdir(parents=True)
            (specs_root / "001-legacy-one").mkdir(parents=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [specs_root / "001-legacy-one", specs_root / "003-legacy-three"],
            )

    def test_new_shape_only_tree(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-100").mkdir(parents=True)
            (specs_root / "2025" / "01" / "PROJ-050").mkdir(parents=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [
                    specs_root / "2025" / "01" / "PROJ-050",
                    specs_root / "2026" / "08" / "PROJ-100",
                    specs_root / "2026" / "08" / "PROJ-200",
                ],
            )

    def test_mixed_tree_legacy_family_sorts_before_new_shape(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT

            # Legacy family.
            (specs_root / "003-legacy-three").mkdir(parents=True)
            (specs_root / "001-legacy-one").mkdir(parents=True)

            # New-shape family.
            (specs_root / "2026" / "09" / "PROJ-300").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-100").mkdir(parents=True)
            (specs_root / "2025" / "01" / "PROJ-050").mkdir(parents=True)

            # Directories claimed by neither arm.
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            (specs_root / "not-a-spec-dir").mkdir(parents=True)

            # Stray non-directory entries at every level.
            (specs_root / "README.txt").write_text("x")
            (specs_root / "2026" / "README.txt").write_text("x")
            (specs_root / "2026" / "08" / "README.txt").write_text("x")

            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [
                    specs_root / "001-legacy-one",
                    specs_root / "003-legacy-three",
                    specs_root / "2025" / "01" / "PROJ-050",
                    specs_root / "2026" / "08" / "PROJ-100",
                    specs_root / "2026" / "08" / "PROJ-200",
                    specs_root / "2026" / "09" / "PROJ-300",
                ],
            )

    def test_9999_dir_claimed_by_neither_arm(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            self.assertEqual(iter_feature_dirs(specs_root), [])
            # And next_spec_number (the existing pin) still ignores it too.
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_stray_file_directly_under_specs_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            (specs_root / "2026-stray-file").write_text("x")
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_year_entry_that_is_a_file_not_a_dir_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            # A file literally named like a year -- must not be walked
            # into as though it were a year directory.
            (specs_root / "2026").write_text("x")
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_wrapper_root_resolution(self):
        """specs_root_for resolves wrapper_root/specs from wrapper_root/.devforge,
        and composing it with iter_feature_dirs reproduces the old
        single-call (devforge_dir-in) behaviour this test used to pin
        before iter_feature_dirs took a specs_root directly."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = (Path(td).resolve()) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            specs_root = wrapper_root / SPECS_ROOT_DEFAULT
            (specs_root / "007-x").mkdir(parents=True)

            resolved_specs_root = specs_root_for(devforge_dir)
            self.assertEqual(resolved_specs_root, specs_root)

            result = iter_feature_dirs(resolved_specs_root)
            self.assertEqual(result, [specs_root / "007-x"])

            outer_specs = Path(td).resolve() / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_specs_root_returns_empty_list_not_raise(self):
        """specs/ itself locked down (0o000): iterdir() on it raises --
        confirm the function swallows that OSError and returns [] rather
        than propagating (the "never raises" contract)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "001-locked-out").mkdir(parents=True)
            os.chmod(specs_root, 0o000)
            try:
                self.assertEqual(iter_feature_dirs(specs_root), [])
            finally:
                # Always restore, even on assertion failure, so the
                # TemporaryDirectory cleanup below can remove the tree.
                os.chmod(specs_root, 0o755)

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_specs_root_ancestor_returns_empty_list_not_raise(self):
        """The PARENT of specs/ locked down (0o000): stat()/exists() on
        specs_root itself raises before the emptiness guard is even
        evaluated -- confirm that path is guarded too, not just the
        iterdir() path covered above."""
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td).resolve()
            specs_root = repo_root / SPECS_ROOT_DEFAULT
            (specs_root / "001-x").mkdir(parents=True)
            os.chmod(repo_root, 0o000)
            try:
                self.assertEqual(iter_feature_dirs(specs_root), [])
            finally:
                os.chmod(repo_root, 0o755)

    def test_valid_symlink_to_dir_included(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            real_target = Path(td).resolve() / "elsewhere" / "real-feature-dir"
            real_target.mkdir(parents=True)
            specs_root.mkdir(parents=True, exist_ok=True)
            symlinked = specs_root / "005-symlinked-feature"
            symlinked.symlink_to(real_target, target_is_directory=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(result, [symlinked])

    def test_dangling_symlink_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            specs_root.mkdir(parents=True)
            dangling = specs_root / "006-dangling-feature"
            dangling.symlink_to(
                specs_root / "does-not-exist", target_is_directory=True,
            )
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_near_miss_name_shapes_classified_correctly(self):
        """Pins the disjointness claim the single-pass if/elif dispatch
        rests on: each of these near-miss name shapes is claimed by
        exactly one arm or by neither -- never both, and never
        misclassified into the wrong arm."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "0001-x").mkdir(parents=True)    # neither arm
            (specs_root / "12345").mkdir(parents=True)     # neither arm
            (specs_root / "202-6").mkdir(parents=True)     # legacy arm (NNN=202)
            (specs_root / "2026-08").mkdir(parents=True)   # neither arm
            result = iter_feature_dirs(specs_root)
            self.assertEqual(result, [specs_root / "202-6"])


class TestFindFeatureDirsWith(unittest.TestCase):
    def test_specs_dir_absent_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            self.assertEqual(find_feature_dirs_with(specs_root, "spec.md"), [])

    def test_legacy_only_tree_filters_on_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            has_spec = specs_root / "001-has-spec"
            has_spec.mkdir(parents=True)
            (has_spec / "spec.md").write_text("x")
            no_spec = specs_root / "002-no-spec"
            no_spec.mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [has_spec])

    def test_new_shape_tree_filters_on_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            has_it = specs_root / "2026" / "08" / "PROJ-100"
            has_it.mkdir(parents=True)
            (has_it / "breakdown-handoff.json").write_text("{}")
            lacks_it = specs_root / "2026" / "08" / "PROJ-200"
            lacks_it.mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "breakdown-handoff.json")
            self.assertEqual(result, [has_it])

    def test_mixed_tree_filters_across_both_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            legacy_hit = specs_root / "001-legacy-hit"
            legacy_hit.mkdir(parents=True)
            (legacy_hit / "plan.md").write_text("x")
            (specs_root / "002-legacy-miss").mkdir(parents=True)
            new_hit = specs_root / "2026" / "08" / "PROJ-100"
            new_hit.mkdir(parents=True)
            (new_hit / "plan.md").write_text("x")
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "plan.md")
            self.assertEqual(result, [legacy_hit, new_hit])

    def test_dir_lacking_sentinel_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "001-no-sentinel").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "research-handoff.json")
            self.assertEqual(result, [])

    def test_directory_named_like_sentinel_is_not_a_match(self):
        """A DIRECTORY named filename must not satisfy the filter -- only a
        FILE does (Path.is_file(), not mere existence)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-sentinel-is-a-dir"
            (feature_dir / "spec.md").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [])

    def test_symlink_to_file_matches(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-symlinked-sentinel"
            feature_dir.mkdir(parents=True)
            real_file = Path(td).resolve() / "elsewhere-spec.md"
            real_file.write_text("x")
            (feature_dir / "spec.md").symlink_to(real_file)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [feature_dir])

    def test_dangling_symlink_to_file_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-dangling-sentinel"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").symlink_to(
                specs_root / "nonexistent-target.md",
            )
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [])

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_feature_dir_excludes_rather_than_raises(self):
        """A feature dir that iter_feature_dirs already listed, but whose
        contents become unreadable (0o000) before this function's own
        is_file() probe, must be treated as "no match", not raise."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-locked-contents"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("x")
            os.chmod(feature_dir, 0o000)
            try:
                result = find_feature_dirs_with(specs_root, "spec.md")
                self.assertEqual(result, [])
            finally:
                os.chmod(feature_dir, 0o755)


# ---------------------------------------------------------------------------
# normalize_ticket (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2,
# OQ-2).
# ---------------------------------------------------------------------------


class TestNormalizeTicket(unittest.TestCase):
    def test_valid_ticket_accepted(self):
        ticket, error = normalize_ticket("PROJ-123")
        self.assertIsNone(error)
        self.assertEqual(ticket, "PROJ-123")

    def test_multi_letter_prefix_accepted(self):
        ticket, error = normalize_ticket("ENG-4")
        self.assertIsNone(error)
        self.assertEqual(ticket, "ENG-4")

    def test_surrounding_whitespace_stripped(self):
        """The only transformation applied: strip, not case-fold."""
        ticket, error = normalize_ticket("  PROJ-123  ")
        self.assertIsNone(error)
        self.assertEqual(ticket, "PROJ-123")

    def test_none_rejected(self):
        ticket, error = normalize_ticket(None)
        self.assertIsNone(ticket)
        self.assertIsNotNone(error)
        self.assertIn("no ticket supplied", error)

    def test_empty_string_rejected(self):
        ticket, error = normalize_ticket("")
        self.assertIsNone(ticket)
        self.assertIn("no ticket supplied", error)

    def test_blank_after_strip_rejected(self):
        ticket, error = normalize_ticket("   ")
        self.assertIsNone(ticket)
        self.assertIn("no ticket supplied", error)

    def test_lowercase_rejected_not_silently_upper_cased(self):
        """OQ-2's closed hazard: lowercase FAILS, it is never coerced to
        the case-insensitive-filesystem-safe uppercase spelling."""
        ticket, error = normalize_ticket("proj-123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)
        self.assertIn("proj-123", error)

    def test_mixed_case_rejected(self):
        ticket, error = normalize_ticket("Proj-123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_bare_number_rejected(self):
        ticket, error = normalize_ticket("123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_space_instead_of_dash_rejected(self):
        ticket, error = normalize_ticket("PROJ 123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_spaces_around_dash_rejected(self):
        ticket, error = normalize_ticket("PROJ - 123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_trailing_garbage_rejected(self):
        ticket, error = normalize_ticket("PROJ-123-extra")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_no_digits_rejected(self):
        ticket, error = normalize_ticket("PROJ-")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_no_letters_before_dash_rejected(self):
        ticket, error = normalize_ticket("-123")
        self.assertIsNone(ticket)
        self.assertIn("invalid ticket", error)

    def test_ticket_re_matches_normalize_ticket_success_shape(self):
        """TICKET_RE is the exported constant normalize_ticket enforces."""
        self.assertTrue(TICKET_RE.match("PROJ-123"))
        self.assertFalse(TICKET_RE.match("proj-123"))


# ---------------------------------------------------------------------------
# read_require_ticket (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
# Phase 2, OQ-1).  Edge/error paths use hand-written project-config.json
# fixtures (mirroring tests/lib/_verify/test_e2e.py's precedent for
# testing a project-config.json reader's own malformed-input handling in
# isolation); the real-producer round-trip lives in
# tests/lib/_configure/test_require_ticket.py.
# ---------------------------------------------------------------------------


class TestReadRequireTicket(unittest.TestCase):
    def test_missing_file_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_missing_devforge_dir_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / "nonexistent" / ".devforge"
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_true_value_returns_true(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"REQUIRE_TICKET": "true"}', encoding="utf-8"
            )
            self.assertTrue(read_require_ticket(devforge_dir))

    def test_false_value_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"REQUIRE_TICKET": "false"}', encoding="utf-8"
            )
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_key_absent_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"WORKSPACE_MODE": "standalone"}', encoding="utf-8"
            )
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_unexpected_value_returns_false(self):
        """Neither "True" (wrong case) nor a JSON boolean is accepted --
        only the exact string "true"."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"REQUIRE_TICKET": true}', encoding="utf-8"
            )
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_malformed_json_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_non_object_top_level_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                "[1, 2, 3]", encoding="utf-8"
            )
            self.assertFalse(read_require_ticket(devforge_dir))

    def test_never_raises_on_unreadable_directory_as_file(self):
        """devforge_dir pointing at a plain FILE (not a dir) must not raise."""
        with tempfile.TemporaryDirectory() as td:
            not_a_dir = Path(td) / "actually-a-file"
            not_a_dir.write_text("x")
            self.assertFalse(read_require_ticket(not_a_dir))


# ---------------------------------------------------------------------------
# allocate_feature_dir -- ticket / require_ticket wiring (Phase 2, D4).
# ---------------------------------------------------------------------------


class TestAllocateFeatureDirTicket(unittest.TestCase):
    def test_require_ticket_false_ticketless_still_succeeds(self):
        """Zero behaviour change for every existing caller: no ticket
        argument at all, require_ticket defaults False."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "add-dark-mode")
            self.assertIsNone(error)
            self.assertIsNone(result["ticket"])

    def test_require_ticket_true_with_valid_ticket_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="PROJ-123", require_ticket=True,
            )
            self.assertIsNone(error)
            self.assertEqual(result["ticket"], "PROJ-123")
            # Phase 3 (built here): the ticket IS the directory leaf.
            self.assertEqual(result["leaf"], "PROJ-123")

    def test_require_ticket_true_no_ticket_refuses_naming_both_routes(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket=None, require_ticket=True,
            )
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("REQUIRE_TICKET", error)
            # Route 1: supply a ticket.
            self.assertIn("supply a ticket", error)
            # Route 2: turn the key off.
            self.assertIn("turn REQUIRE_TICKET off", error)
            # No directory was created on refusal.
            self.assertFalse((Path(td) / "specs").exists())

    def test_require_ticket_true_malformed_ticket_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="proj-123", require_ticket=True,
            )
            self.assertEqual(result, {})
            self.assertIn("REQUIRE_TICKET", error)
            self.assertIn("supply a ticket", error)
            self.assertIn("turn REQUIRE_TICKET off", error)

    def test_require_ticket_false_malformed_ticket_still_refuses(self):
        """Format is ALWAYS checked when a ticket is supplied, regardless
        of require_ticket -- but the message does not invoke REQUIRE_
        TICKET, since the gate itself is not what refused."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="not a ticket", require_ticket=False,
            )
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertNotIn("REQUIRE_TICKET", error)
            self.assertIn("invalid ticket", error)

    def test_require_ticket_false_empty_string_ticket_treated_as_absent(self):
        """An explicit empty-string ticket behaves exactly like None when
        require_ticket is False -- no validation is even attempted."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="", require_ticket=False,
            )
            self.assertIsNone(error)
            self.assertIsNone(result["ticket"])

    def test_slug_error_takes_precedence_over_ticket_error(self):
        """Both invalid: the pre-existing slug check still fires first --
        unmodified behaviour for the check that existed before this
        parameter pair was added."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "onlyoneword", ticket=None, require_ticket=True,
            )
            self.assertEqual(result, {})
            self.assertIn("invalid slug", error)
            self.assertNotIn("REQUIRE_TICKET", error)

    def test_ticket_normalized_to_canonical_case_in_result(self):
        """The ticket in the result dict is normalize_ticket's canonical
        (already-uppercase) form -- this test only exercises the already-
        uppercase case, since a lowercase input is rejected outright
        (see TestNormalizeTicket / the *_true_malformed_ticket_refuses
        tests above for the rejection path)."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "add-dark-mode", ticket="  ENG-7  ", require_ticket=True,
            )
            self.assertIsNone(error)
            self.assertEqual(result["ticket"], "ENG-7")


# ---------------------------------------------------------------------------
# Mixed-shape coexistence: a REAL allocate_feature_dir call (writing the
# new specs/YYYY/MM/leaf/ shape) discovered alongside a hand-built legacy
# specs/NNN-slug/ dir, via the unmodified Phase-1 read side.
#
# This is a real-producer round-trip (per the "Real-fixture testing"
# discipline), not just a hand-authored iter_feature_dirs fixture:
# TestIterFeatureDirs / TestFindFeatureDirsWith above already pin the
# read-side contract with hand-built trees; this class additionally
# proves that allocate_feature_dir's OWN new-shape output -- not a
# stand-in -- is exactly what that read side finds.
# ---------------------------------------------------------------------------


class TestMixedShapeRealProducerRoundTrip(unittest.TestCase):
    _NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    def test_iter_feature_dirs_finds_both_a_legacy_dir_and_a_real_new_allocation(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            repo_root = Path(td).resolve()
            specs_root = repo_root / SPECS_ROOT_DEFAULT

            # A hand-built legacy dir (nothing migrates plan 68 D3's
            # inert history; D6 mandates it stays resolvable forever).
            (specs_root / "003-legacy-feature").mkdir(parents=True)

            # A REAL new-shape allocation via the function under test.
            result, error = allocate_feature_dir(
                devforge_dir, "brand-new-feature", ticket="PROJ-500", now=self._NOW,
            )
            self.assertIsNone(error)

            found = iter_feature_dirs(specs_root)
            self.assertEqual(
                found,
                [
                    specs_root / "003-legacy-feature",
                    specs_root / "2026" / "08" / "PROJ-500",
                ],
            )
            self.assertEqual(Path(result["path"]), specs_root / "2026" / "08" / "PROJ-500")

    def test_find_feature_dirs_with_finds_a_sentinel_in_a_real_new_allocation(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            repo_root = Path(td).resolve()
            specs_root = repo_root / SPECS_ROOT_DEFAULT

            legacy_dir = specs_root / "001-legacy-with-spec"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "spec.md").write_text("legacy spec")

            result, error = allocate_feature_dir(
                devforge_dir, "brand-new-feature", ticket="PROJ-501", now=self._NOW,
            )
            self.assertIsNone(error)
            new_dir = Path(result["path"])
            (new_dir / "spec.md").write_text("new spec")

            found = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(found, [legacy_dir, new_dir])


if __name__ == "__main__":
    unittest.main()
