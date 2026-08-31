"""Real-producer round-trip for the AI_ATTRIBUTION provenance gate
(91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 4, D9/OQ-8(i)).

set-ai-attribution's own schema/validation coverage already lives in
tests/lib/test_configure_helper.py (the enum, the reject-invalid path,
the default). This file covers only the boundary this plan's Phase 4
adds: configure_helper set-ai-attribution + render-config write the
real project-config.json; _shared.provenance.read_ai_attribution_enabled
(the OQ-8(i) consumer -- the Run-by stamp's gate, riding the EXISTING
ai_attribution answer rather than a new key) reads it back correctly.
Mirrors tests/lib/_configure/test_require_ticket.py's
RealProducerRoundTripTests exactly.

Follows the _EnvIsolationMixin + module-level subprocess-helper pattern
from tests/lib/test_configure_helper.py (mirrored, not imported, per the
existing tests/lib/_configure/ precedent in test_require_ticket.py).

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "configure_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402
from _shared.provenance import read_ai_attribution_enabled  # noqa: E402


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_init(devforge_dir, *args):
    """Invoke init_helper.py <args> as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self._tmp.name/          <- install_root
        .devforge/             <- devforge_dir
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _write_full_init_yaml(self):
        """Minimal init.yaml sufficient for render-config to succeed."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_init(self.devforge_dir, "set-project-root", ".")
        _run_init(self.devforge_dir, "set-project-state", "brownfield")
        _run_init(self.devforge_dir, "set-default-branch", "main")


class RealProducerRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_yes_round_trips_through_render_config_and_reader(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-ai-attribution", "Yes")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("AI_ATTRIBUTION", data)
        self.assertEqual(data["AI_ATTRIBUTION"], "Yes")

        # The actual consumer this plan wires the gate for.
        self.assertTrue(read_ai_attribution_enabled(self.devforge_dir))

    def test_no_round_trips_through_render_config_and_reader(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["AI_ATTRIBUTION"], "No")
        self.assertFalse(read_ai_attribution_enabled(self.devforge_dir))

    def test_never_set_round_trips_through_reader(self):
        """Key present with its default (never called set-ai-attribution):
        the same COMMIT_ATTRIBUTION gate _configure/_render.py already
        derives from this field reads the identical default, so the two
        gates never disagree about an install that never answered the
        question either way."""
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        # Whatever the unanswered default renders as, the two readers
        # (COMMIT_ATTRIBUTION's own `== "Yes"` gate and
        # read_ai_attribution_enabled) must agree.
        self.assertEqual(
            data["AI_ATTRIBUTION"] == "Yes",
            read_ai_attribution_enabled(self.devforge_dir),
        )


if __name__ == "__main__":
    unittest.main()
