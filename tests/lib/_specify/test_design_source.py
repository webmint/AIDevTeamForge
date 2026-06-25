"""Tests for the design_source field: render + set-design-source setter.

Coverage:
Render:
  - default state (no design_source key) renders '**Design source**: none'
  - state with design_source='none' renders '**Design source**: none'
  - state with design_source='html:design/reference.html' renders the full value
  - state with design_source='figma:https://figma.com/file/x?node-id=1:2' renders
    the full URL including internal colons
  - state with design_source='screenshot:design/mockup.png' renders correctly
  - Design source line appears AFTER **Status**: and BEFORE **Author**:
  - cmd_verify_rendered round-trips with design_source='none' (state default)
  - cmd_verify_rendered round-trips with design_source='figma:https://...'

set-design-source setter:
  - '--value none' → state["design_source"]=="none", exit 0
  - '--value html:design/reference.html' → stored, exit 0
  - '--value figma:https://figma.com/file/x?node-id=1:2' → stored with full
    URL (second colon in URL preserved), exit 0
  - '--value screenshot:path/to/mock.png' → stored, exit 0
  - '--value foo:bar' (unknown scheme) → exit 2, stderr names valid shapes
  - '--value figma:' (recognised scheme, empty target) → exit 2
  - '--value figma' (recognised scheme, no colon at all, not "none") → exit 2
  - '--value html' (recognised scheme, no colon, not "none") → exit 2
  - '--value none:something' → exit 2 (none is only valid bare, not as scheme)
  - '--value ""' (empty) → exit 2
  - round-trip: set-design-source then render produces the correct line

All tests use real cmd_* producers via the subprocess interface so they
round-trip through the actual parser/handler path, not hand-built state JSON.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]  # repo root
LIB = ROOT / "src" / "devforge" / "lib"

HELPER = LIB / "specify_helper.py"


def _run(argv, cwd=None, env=None):
    cmd = [sys.executable, str(HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
    )


def _seed_minimal(dev: Path) -> None:
    """Initialise a minimal valid state via real setters."""
    _run(["--devforge-dir", str(dev), "reset-state"])
    _run(["--devforge-dir", str(dev), "set-date", "--date", "2026-06-25"])
    _run(["--devforge-dir", str(dev), "assign-feature-name",
          "--feature-name", "design-source-test"])


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------


class TestDesignSourceRender(unittest.TestCase):

    def _render(self, dev: Path) -> str:
        r = _run(["--devforge-dir", str(dev), "render"])
        self.assertEqual(r.returncode, 0, "render failed: " + r.stderr)
        return r.stdout

    def test_default_state_renders_none(self):
        """Fresh state (no design_source set) renders '**Design source**: none'."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            output = self._render(dev)
            self.assertIn("**Design source**: none", output)

    def test_explicit_none_renders_none(self):
        """After set-design-source --value none, renders '**Design source**: none'."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "none"])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(dev)
            self.assertIn("**Design source**: none", output)

    def test_html_source_renders_full_value(self):
        """html:<path> value renders verbatim in the frontmatter line."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "html:design/reference.html"])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(dev)
            self.assertIn(
                "**Design source**: html:design/reference.html", output,
            )

    def test_figma_url_with_internal_colons_renders_verbatim(self):
        """figma:https://figma.com/file/x?node-id=1:2 preserves the full URL."""
        value = "figma:https://figma.com/file/x?node-id=1:2"
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", value])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(dev)
            self.assertIn(
                "**Design source**: {0}".format(value), output,
            )

    def test_screenshot_source_renders_full_value(self):
        """screenshot:<path> value renders verbatim."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "screenshot:design/mockup.png"])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(dev)
            self.assertIn(
                "**Design source**: screenshot:design/mockup.png", output,
            )

    def test_design_source_line_position_after_status_before_author(self):
        """**Design source**: must appear after **Status**: and before **Author**:."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            output = self._render(dev)
            pos_status = output.index("**Status**:")
            pos_design = output.index("**Design source**:")
            pos_author = output.index("**Author**:")
            self.assertLess(
                pos_status, pos_design,
                "**Design source**: must come AFTER **Status**:",
            )
            self.assertLess(
                pos_design, pos_author,
                "**Design source**: must come BEFORE **Author**:",
            )


# ---------------------------------------------------------------------------
# verify-rendered round-trip tests
# ---------------------------------------------------------------------------


class TestDesignSourceVerifyRendered(unittest.TestCase):

    def _write_render(self, dev: Path, spec_dir: Path) -> Path:
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        r = _run(["--devforge-dir", str(dev), "render"])
        self.assertEqual(r.returncode, 0, "render failed: " + r.stderr)
        spec_path.write_text(r.stdout, encoding="utf-8")
        return spec_path

    def test_verify_rendered_passes_with_default_none(self):
        """verify-rendered succeeds when design_source defaults to 'none'."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            spec_dir = Path(td) / "specs" / "001-design-source-test"
            spec_path = self._write_render(dev, spec_dir)
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered", "--path", str(spec_path),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "")

    def test_verify_rendered_passes_with_figma_url(self):
        """verify-rendered succeeds when design_source is a figma URL."""
        value = "figma:https://figma.com/file/x?node-id=1:2"
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", value])
            self.assertEqual(r.returncode, 0, r.stderr)
            spec_dir = Path(td) / "specs" / "001-design-source-test"
            spec_path = self._write_render(dev, spec_dir)
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered", "--path", str(spec_path),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "")

    def test_verify_rendered_detects_tampered_design_source_line(self):
        """verify-rendered exits 2 when the **Design source**: line is changed."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            spec_dir = Path(td) / "specs" / "001-design-source-test"
            spec_path = self._write_render(dev, spec_dir)
            disk = spec_path.read_text(encoding="utf-8")
            tampered = disk.replace(
                "**Design source**: none",
                "**Design source**: html:design/tampered.html",
                1,
            )
            spec_path.write_text(tampered, encoding="utf-8")
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered", "--path", str(spec_path),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("drift at line", r.stderr)


# ---------------------------------------------------------------------------
# Setter tests
# ---------------------------------------------------------------------------


class TestSetDesignSource(unittest.TestCase):

    def _get_state(self, dev: Path) -> dict:
        import json
        state_path = dev / "specify-state.json"
        return json.loads(state_path.read_text(encoding="utf-8"))

    def test_value_none_is_accepted(self):
        """'none' is a valid value; stored as 'none', exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "none"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = self._get_state(dev)
            self.assertEqual(state["design_source"], "none")

    def test_html_path_is_stored(self):
        """'html:design/reference.html' is stored verbatim, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source",
                      "--value", "html:design/reference.html"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = self._get_state(dev)
            self.assertEqual(state["design_source"], "html:design/reference.html")

    def test_figma_url_with_multiple_colons_is_stored(self):
        """figma URL with internal colons is stored with the full target."""
        value = "figma:https://figma.com/file/x?node-id=1:2"
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", value])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = self._get_state(dev)
            self.assertEqual(state["design_source"], value)

    def test_screenshot_path_is_stored(self):
        """'screenshot:design/mockup.png' is stored verbatim, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source",
                      "--value", "screenshot:design/mockup.png"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = self._get_state(dev)
            self.assertEqual(
                state["design_source"], "screenshot:design/mockup.png",
            )

    def test_unknown_scheme_is_rejected(self):
        """Unknown scheme exits 2 and stderr names valid shapes."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "foo:bar"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("html:<path>", r.stderr)
            self.assertIn("figma:<url>", r.stderr)
            self.assertIn("screenshot:<path>", r.stderr)
            self.assertIn("none", r.stderr)

    def test_recognised_scheme_empty_target_is_rejected(self):
        """'figma:' (recognised scheme, empty target) exits 2."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "figma:"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("figma", r.stderr)

    def test_recognised_scheme_no_colon_not_none_is_rejected(self):
        """'figma' alone (no colon, not 'none') exits 2."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "figma"])
            self.assertEqual(r.returncode, 2)

    def test_html_alone_no_colon_is_rejected(self):
        """'html' alone (no colon) exits 2."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "html"])
            self.assertEqual(r.returncode, 2)

    def test_none_with_colon_is_rejected(self):
        """'none:something' exits 2 — 'none' is only valid as the bare sentinel."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "none:something"])
            self.assertEqual(r.returncode, 2)

    def test_none_with_empty_target_colon_is_rejected(self):
        """'none:' (colon but empty target) exits 2.
        SYNC contract: none is only valid as the bare sentinel (no colon at all).
        Mirrors the parser fix: parse_design_source('none:') must also be invalid."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "none:"])
            self.assertEqual(r.returncode, 2,
                             "Expected exit 2 for 'none:'; got {0}; stderr: {1!r}".format(
                                 r.returncode, r.stderr))

    def test_none_colon_error_message_names_sentinel_constraint(self):
        """Error message for 'none:' must clarify that none is a bare sentinel,
        NOT a generic 'scheme not recognised' message."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "none:"])
            self.assertEqual(r.returncode, 2)
            # The message must make clear none cannot take a colon/target
            self.assertTrue(
                "sentinel" in r.stderr or "colon" in r.stderr or "bare" in r.stderr,
                "Error message should explain none is a bare sentinel; got: {0!r}".format(r.stderr),
            )

    def test_can_overwrite_previous_value(self):
        """A second set-design-source overwrites the first."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            _run(["--devforge-dir", str(dev),
                  "set-design-source", "--value", "html:design/v1.html"])
            r = _run(["--devforge-dir", str(dev),
                      "set-design-source", "--value", "html:design/v2.html"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = self._get_state(dev)
            self.assertEqual(state["design_source"], "html:design/v2.html")

    def test_round_trip_set_then_render(self):
        """set-design-source then render produces the expected frontmatter line."""
        value = "figma:https://figma.com/file/abc123?node-id=0:1"
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            r_set = _run(["--devforge-dir", str(dev),
                          "set-design-source", "--value", value])
            self.assertEqual(r_set.returncode, 0, r_set.stderr)
            r_render = _run(["--devforge-dir", str(dev), "render"])
            self.assertEqual(r_render.returncode, 0, r_render.stderr)
            self.assertIn(
                "**Design source**: {0}".format(value), r_render.stdout,
            )

    def test_reset_state_initialises_design_source_to_none(self):
        """After reset-state, design_source is DESIGN_SOURCE_DEFAULT ('none')."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_minimal(dev)
            # Set to a non-default value first.
            _run(["--devforge-dir", str(dev),
                  "set-design-source", "--value", "html:design/reference.html"])
            # Reset.
            _run(["--devforge-dir", str(dev), "reset-state"])
            state = self._get_state(dev)
            self.assertEqual(state.get("design_source"), "none")


if __name__ == "__main__":
    unittest.main()
