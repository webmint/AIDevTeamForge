"""Tests for src/devforge/lib/_specify/_topic.py's source_origin_for_path.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md: the classifier must return
the same source_origin for a file whether the caller spells it repo-
relative or absolute -- `find-handoffs` emits absolute `handoff_path`
values, and main.md's `<feature_dir>`-token reads pass those straight to
`record-input-read`, so a spelling-dependent classifier silently mis-tags
research/discover reads as "context".

Three layers:
  - Direct unit tests against `_topic.source_origin_for_path` (pure,
    no filesystem access) for every classification shape, relative and
    absolute, in-root and out-of-root.
  - A real-producer round trip through `record-input-read` +
    `read-state` (specify_helper._cli.main, in-process) proving the
    actual CLI call site -- not just the bare function -- resolves an
    absolute path to the same source_origin as the relative spelling of
    the same file.
  - A real-producer round trip through `record-input-read` +
    `render-findings` proving the SECOND consumer of the same
    normalization, `_cmds_phase01._group_for_path`, buckets an absolute
    path under the same render heading its relative spelling gets --
    the two functions share `normalize_source_path` but deliberately
    keep DIFFERENT classification rules (a render-group key is not a
    4-way provenance tag), so this layer proves the shared step landed
    in both consumers without merging what shouldn't be merged.

Stdlib only. Python 3.8+. No third-party deps.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _specify._cli import main  # noqa: E402
from _specify._state import _load_state  # noqa: E402
from _specify._topic import source_origin_for_path  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests: source_origin_for_path, relative vs absolute identity.
# ---------------------------------------------------------------------------


class TestSourceOriginForPathIdentity(unittest.TestCase):
    """Same file, spelled two ways, must classify identically."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)

    def test_research_report_relative_and_absolute_agree(self):
        rel = "specs/007-thing/research-report.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "research")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "research",
        )

    def test_discovery_report_relative_and_absolute_agree(self):
        rel = "specs/007-thing/discovery-report.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "discover")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "discover",
        )

    def test_prior_spec_relative_and_absolute_agree(self):
        rel = "specs/007-thing/spec.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "prior_spec")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "prior_spec",
        )

    def test_new_layout_shape_relative_and_absolute_agree_as_research(self):
        """Plan 91 Phase 3's deeper layout (specs/YYYY/MM/PROJ-123/...);
        pinned so a future change to the prefix rule cannot silently stop
        matching it -- the classifier keys on the top-level "specs/"
        prefix plus the basename, not on the number of segments between
        them."""
        rel = "specs/2026/08/PROJ-123/research-report.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "research")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "research",
        )

    def test_legacy_discover_prefix_relative_and_absolute_agree(self):
        rel = "discover/2026-05-14-feature.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "discover")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "discover",
        )

    def test_legacy_research_prefix_relative_and_absolute_agree(self):
        rel = "research/2026-05-14-bug.md"
        abs_path = str(self.root / rel)
        self.assertEqual(source_origin_for_path(rel), "research")
        self.assertEqual(
            source_origin_for_path(abs_path, root=str(self.root)),
            "research",
        )


class TestSourceOriginForPathOutsideRoot(unittest.TestCase):
    """An absolute path outside this install's root must not borrow it."""

    def test_absolute_path_in_sibling_checkout_returns_context(self):
        with tempfile.TemporaryDirectory() as root_a, \
                tempfile.TemporaryDirectory() as root_b:
            other_install_path = str(
                Path(root_b) / "specs" / "001-x" / "research-report.md"
            )
            # Same basename, same "specs/" shape -- would classify
            # "research" if it were under root_a. It is not.
            self.assertEqual(
                source_origin_for_path(other_install_path, root=root_a),
                "context",
            )
            # Contrast: the SAME relative spelling under root_a's own
            # tree is "research" -- proves the miss above is the
            # outside-root guard firing, not a broken prefix match.
            self.assertEqual(
                source_origin_for_path(
                    "specs/001-x/research-report.md",
                ),
                "research",
            )

    def test_absolute_path_with_no_common_ancestor_returns_context(self):
        # On POSIX this is a different top-level path entirely; relative_to
        # can never succeed, exercising the ValueError branch directly.
        self.assertEqual(
            source_origin_for_path(
                "/completely/unrelated/specs/research-report.md",
                root="/tmp/some-other-root-xyz",
            ),
            "context",
        )


class TestSourceOriginForPathUnaffectedShapes(unittest.TestCase):
    """Every classification that already worked keeps working, unmodified
    -- with and without a `root` argument passed (root must be inert for
    inputs it does not apply to: relative paths, or root=None)."""

    def test_context_constitution_no_root(self):
        self.assertEqual(
            source_origin_for_path("constitution.md"), "context",
        )

    def test_context_constitution_with_root(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(
                source_origin_for_path("constitution.md", root=root),
                "context",
            )

    def test_context_memory_path(self):
        self.assertEqual(
            source_origin_for_path(".devforge/memory.md"), "context",
        )

    def test_context_claude_md(self):
        self.assertEqual(
            source_origin_for_path("CLAUDE.md"), "context",
        )

    def test_context_docs(self):
        self.assertEqual(
            source_origin_for_path("docs/architecture.md"), "context",
        )

    def test_leading_dot_slash_stripped(self):
        self.assertEqual(
            source_origin_for_path("./discover/foo.md"), "discover",
        )

    def test_leading_whitespace_stripped(self):
        self.assertEqual(
            source_origin_for_path("  research/foo.md"), "research",
        )

    def test_absolute_path_no_root_falls_through_to_context_unchanged(self):
        """The exact prior behaviour: root=None (the default) never
        re-expresses an absolute path, so it still falls through every
        prefix check -- this is not a regression, it is the documented
        opt-in shape of the fix (a caller that never passes `root` sees
        no behaviour change at all)."""
        with tempfile.TemporaryDirectory() as root:
            abs_path = str(
                Path(root) / "specs" / "001-x" / "research-report.md"
            )
            self.assertEqual(source_origin_for_path(abs_path), "context")


class TestSourceOriginForPathPurityBounds(unittest.TestCase):
    """Documented bound: no filesystem access, so a `..` segment is NOT
    lexically collapsed before the prefix/basename rules run. Most `..`
    placements don't matter -- _classify_relative only ever looks at the
    first segment and the last one -- but a ".." placed directly after
    "specs/" is not caught: the string still literally starts with
    "specs/", so a file that actually resolves OUTSIDE specs/ (here,
    root/CLAUDE.md, a real top-level context file) is misclassified as
    "prior_spec" instead of "context". This pins that accepted bound
    rather than leaving it silently untested; the fix is "pass an
    already-canonical path", not something this function does for you."""

    def test_uncanonicalized_dotdot_after_specs_escapes_undetected(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "CLAUDE.md").write_text("x", encoding="utf-8")
            noisy = str(Path(root) / "specs" / ".." / "CLAUDE.md")
            # What the canonical form would (correctly) classify as:
            self.assertEqual(
                source_origin_for_path("CLAUDE.md"), "context",
            )
            # What the uncanonicalized absolute form actually returns --
            # the accepted, documented miss:
            self.assertEqual(
                source_origin_for_path(noisy, root=root), "prior_spec",
            )


# ---------------------------------------------------------------------------
# Real-producer round trip: record-input-read + read-state.
# ---------------------------------------------------------------------------


def _run(*argv: str, devforge_dir: str) -> int:
    return main(["--devforge-dir", devforge_dir] + list(argv))


def _load(devforge_dir: str) -> Dict[str, Any]:
    return _load_state(devforge_dir)


class TestRecordInputReadAbsolutePathRoundTrip(unittest.TestCase):
    """Drives the real `record-input-read` CLI verb -- not the bare
    function -- with both spellings of the same on-disk file, mirroring
    what /devforge:specify actually does: main.md composes
    `<feature_dir>/research-report.md` where `<feature_dir>` is the
    absolute parent of find-handoffs's `.resolve()`d handoff_path."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        # Resolved: the production caller derives `root` from a resolved
        # --devforge-dir (Path(args.devforge_dir).resolve().parent), so an
        # absolute path built from an UNresolved tempdir (e.g. macOS's
        # /var -> /private/var) would mismatch it component-for-component
        # and wrongly look "outside root". Real callers -- find-handoffs
        # included -- always hand this classifier already-canonical paths.
        self.root = Path(self._td.name).resolve()
        self.devforge_dir = str(self.root / ".devforge")
        feature_dir = self.root / "specs" / "007-thing"
        feature_dir.mkdir(parents=True)
        (feature_dir / "research-report.md").write_text(
            "# report\n", encoding="utf-8",
        )
        (feature_dir / "discovery-report.md").write_text(
            "# report\n", encoding="utf-8",
        )
        (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
        _run("reset-state", devforge_dir=self.devforge_dir)

    def _record(self, path: str) -> int:
        return _run(
            "record-input-read", "--path", path,
            devforge_dir=self.devforge_dir,
        )

    def _origin_for(self, path: str) -> str:
        state = _load(self.devforge_dir)
        for r in state["input_reads"]:
            if r.get("path") == path:
                return r.get("source_origin")
        self.fail("path not recorded: {0}".format(path))

    def test_relative_and_absolute_research_report_agree(self):
        rel = "specs/007-thing/research-report.md"
        abs_path = str(self.root / rel)
        self.assertEqual(self._record(rel), 0)
        self.assertEqual(self._record(abs_path), 0)
        self.assertEqual(self._origin_for(rel), "research")
        self.assertEqual(self._origin_for(abs_path), "research")

    def test_relative_and_absolute_discovery_report_agree(self):
        rel = "specs/007-thing/discovery-report.md"
        abs_path = str(self.root / rel)
        self.assertEqual(self._record(rel), 0)
        self.assertEqual(self._record(abs_path), 0)
        self.assertEqual(self._origin_for(rel), "discover")
        self.assertEqual(self._origin_for(abs_path), "discover")

    def test_relative_and_absolute_spec_md_agree_as_prior_spec(self):
        rel = "specs/007-thing/spec.md"
        abs_path = str(self.root / rel)
        self.assertEqual(self._record(rel), 0)
        self.assertEqual(self._record(abs_path), 0)
        self.assertEqual(self._origin_for(rel), "prior_spec")
        self.assertEqual(self._origin_for(abs_path), "prior_spec")

    def test_memory_probe_still_fires(self):
        """Guards the memory branch's shared `workspace_root` computation
        (now unconditional, reused for both the origin classification and
        the probe) -- the probe must still run and record a valid
        MEMORY_STATE_KEY, exactly as before this change."""
        from _shared.memory import MEMORY_RELATIVE_PATH, MEMORY_STATE_KEY

        self.assertEqual(self._record(MEMORY_RELATIVE_PATH), 0)
        state = _load(self.devforge_dir)
        rec = next(
            r for r in state["input_reads"]
            if r.get("path") == MEMORY_RELATIVE_PATH
        )
        self.assertIn(MEMORY_STATE_KEY, rec)
        self.assertEqual(rec["source_origin"], "context")


# ---------------------------------------------------------------------------
# Real-producer round trip: record-input-read + render-findings.
#
# _cmds_phase01._group_for_path is the SECOND consumer of
# normalize_source_path (used by cmd_render_findings to bucket the
# "Findings from Inputs" section). Before the fix it duplicated the
# strip/"./"-only normalization independently and had no root-aware
# absolute-path handling at all, so an absolute path fell to its OWN
# group key (the full path string) -- not one of _RENDER_SECTION_ORDER's
# fixed keys -- and its "### From <path>" heading, plus every finding
# filed against it, silently vanished from the rendered output. These
# tests drive the real CLI (record-input-read + render-findings), not
# the bare function, so the observable render output is what's asserted.
# ---------------------------------------------------------------------------


def _run_capture_stdout(*argv: str, devforge_dir: str):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = main(["--devforge-dir", devforge_dir] + list(argv))
    finally:
        sys.stdout = old
    return rc, buf.getvalue()


class TestGroupForPathAbsoluteRoundTrip(unittest.TestCase):
    """_group_for_path answers a DIFFERENT question than
    source_origin_for_path (a render-group key, not a 4-way provenance
    tag -- see the module comment above RESEARCH_REPORT_BASENAME in
    _topic.py) so the two are deliberately NOT merged into one function.
    What they share -- and what used to be duplicated independently in
    each -- is normalize_source_path; these tests exercise that sharing
    through _group_for_path's own real caller, render-findings."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        # Resolved for the same reason as TestRecordInputReadAbsolutePathRoundTrip.
        self.root = Path(self._td.name).resolve()
        self.devforge_dir = str(self.root / ".devforge")
        feature_dir = self.root / "specs" / "007-thing"
        feature_dir.mkdir(parents=True)
        for name in ("research-report.md", "discovery-report.md", "spec.md"):
            (feature_dir / name).write_text("# x\n", encoding="utf-8")
        (self.root / "constitution.md").write_text("# c\n", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "architecture.md").write_text(
            "# a\n", encoding="utf-8",
        )
        _run("reset-state", devforge_dir=self.devforge_dir)

    def _record(self, path: str) -> None:
        rc = _run(
            "record-input-read", "--path", path,
            devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0, "record-input-read failed for " + path)

    def _render(self) -> str:
        rc, out = _run_capture_stdout(
            "render-findings", devforge_dir=self.devforge_dir,
        )
        self.assertEqual(rc, 0, "render-findings failed")
        return out

    def test_absolute_research_report_renders_not_dropped(self):
        rel = "specs/007-thing/research-report.md"
        abs_path = str(self.root / rel)
        self._record(rel)
        self._record(abs_path)
        out = self._render()
        self.assertIn("### From {0}".format(rel), out)
        self.assertIn("### From {0}".format(abs_path), out)

    def test_absolute_discovery_report_renders_not_dropped(self):
        rel = "specs/007-thing/discovery-report.md"
        abs_path = str(self.root / rel)
        self._record(rel)
        self._record(abs_path)
        out = self._render()
        self.assertIn("### From {0}".format(rel), out)
        self.assertIn("### From {0}".format(abs_path), out)

    def test_absolute_prior_spec_renders_not_dropped(self):
        rel = "specs/007-thing/spec.md"
        abs_path = str(self.root / rel)
        self._record(rel)
        self._record(abs_path)
        out = self._render()
        self.assertIn("### From {0}".format(rel), out)
        self.assertIn("### From {0}".format(abs_path), out)

    def test_absolute_path_outside_root_does_not_borrow_a_group(self):
        with tempfile.TemporaryDirectory() as other:
            outside = str(
                Path(other).resolve()
                / "specs" / "999-x" / "research-report.md"
            )
            self._record(outside)
            out = self._render()
            # Not borrowed into "research/" (or any other bucket): its
            # own private group key isn't one of _RENDER_SECTION_ORDER's
            # fixed keys, so -- matching the pre-existing fallback shape
            # for any unmatched path -- it renders under no heading.
            self.assertNotIn("### From {0}".format(outside), out)

    def test_every_mandatory_context_path_keeps_its_own_heading(self):
        """Pins the deliberate non-merge: source_origin_for_path collapses
        all four of these into one "context" tag, but the render must
        keep each under its OWN heading (or, for docs/architecture.md,
        the shared "docs/" bucket) -- proving _group_for_path was
        correctly NOT replaced by source_origin_for_path's return value,
        and that the render's grouping is unaffected by this fix."""
        for p in (
            "constitution.md", ".devforge/memory.md", "CLAUDE.md",
            "docs/architecture.md",
        ):
            self._record(p)
        out = self._render()
        self.assertIn("### From constitution.md", out)
        self.assertIn("### From .devforge/memory.md", out)
        self.assertIn("### From CLAUDE.md", out)
        self.assertIn("### From docs/architecture.md", out)
        # Render order matches _RENDER_SECTION_ORDER, unchanged by this fix.
        self.assertLess(
            out.index("### From constitution.md"),
            out.index("### From .devforge/memory.md"),
        )
        self.assertLess(
            out.index("### From .devforge/memory.md"),
            out.index("### From CLAUDE.md"),
        )
        self.assertLess(
            out.index("### From CLAUDE.md"),
            out.index("### From docs/architecture.md"),
        )

    def test_every_relative_grouping_unchanged(self):
        """Every path shape _group_for_path already handled correctly
        renders identically after the fix -- legacy discover/research
        prefixes included."""
        paths = [
            "constitution.md",
            ".devforge/memory.md",
            "CLAUDE.md",
            "docs/architecture.md",
            "specs/007-thing/spec.md",
            "specs/007-thing/research-report.md",
            "specs/007-thing/discovery-report.md",
            "discover/2026-05-14-feature.md",
            "research/2026-05-14-bug.md",
        ]
        for p in paths:
            self._record(p)
        out = self._render()
        for p in paths:
            self.assertIn("### From {0}".format(p), out)


if __name__ == "__main__":
    unittest.main()
