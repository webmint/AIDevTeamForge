"""Suite-wide defaults.

`DEVFORGE_DIR` defaults to a throwaway directory for every test.

Why this exists: helper state and diagnostic files resolve their location
from `DEVFORGE_DIR`, falling back to the helper module's own parent —
which, when the helpers are imported from this repo rather than from a
consumer install, is `src/devforge/`.  Any test that exercises a helper
WITHOUT setting `DEVFORGE_DIR` therefore writes real runtime state into the
framework's own source tree.  `test_generate_docs_helper.py` did exactly
that, leaving `src/devforge/.generate-docs-trace.log` behind.

That is not merely untidy.  `install.sh` guards against stray user-state
files in the framework source tree — correctly, because the bulk `cp -R`
would copy them into the target and overwrite the target's real state — and
aborts with `error: stray user-state file in framework source`.  So running
the test suite made `install.sh` refuse to start, for everyone, until the
leaked file was deleted by hand.  Fixing the leak at its source is what
keeps that guard's meaning intact: an artifact in the source tree should be
an unusual event worth aborting over, not the normal aftermath of a test
run.

This sets a DEFAULT, never an override.  A test that assigns
`DEVFORGE_DIR` itself still wins, and a test that deliberately POPS it to
exercise the fallback resolution (as
`test_generate_docs_helper.TestStateFilePath` does) still sees it unset —
both keep working unchanged.
"""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _default_devforge_dir():
    """Point DEVFORGE_DIR at a throwaway dir unless the test sets its own."""
    saved = os.environ.get("DEVFORGE_DIR")
    with tempfile.TemporaryDirectory(prefix="devforge-test-") as tmp:
        os.environ["DEVFORGE_DIR"] = tmp
        try:
            yield tmp
        finally:
            if saved is None:
                os.environ.pop("DEVFORGE_DIR", None)
            else:
                os.environ["DEVFORGE_DIR"] = saved
