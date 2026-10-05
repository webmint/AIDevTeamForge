"""_wip -- WIP marker removal for /implement.

The .devforge/wip.md file is the crash-recovery marker /devforge:implement's
orchestrator writes before each task and reads back at the next run's
PHASE 0.  The orchestrator writes and reads it directly -- no Python writer or
reader exists.  The format's one home is /devforge:implement's crash-recovery
reference.

This module's one function removes the marker after an approved per-task WIP
commit:

  clear_wip_marker(devforge_dir)
      Remove wip.md.  Silent no-op when the file is absent.

Stdlib only. No third-party dependencies. Python 3.8+.
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clear_wip_marker(devforge_dir):
    # type: (object) -> None
    """Remove .devforge/wip.md.  Silent no-op when absent.

    Parameters
    ----------
    devforge_dir : str or Path
        Path to the .devforge/ directory.
    """
    wip_path = Path(devforge_dir) / "wip.md"
    try:
        wip_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # Re-raise unexpected OS errors (permission denied, etc.).
        raise
