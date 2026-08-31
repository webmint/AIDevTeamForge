"""Tests for src/devforge/lib/_specify/_schema.py::resolve_bucketed_feature_dir.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3's fourth Step 4.1
path (e1ffb2f) reuses a specs/<YYYY>/<MM>/<leaf>/ intake directory without
ever allocating a spec_number, so write-design-anchor and finalize-handoff
-- which both composed their output path from
{specs_root}/{spec_number}-{feature_slug}/ -- had no way to find it.
resolve_bucketed_feature_dir is the read-time fix: given /specify state,
it re-derives the same directory Step 4.1's own ancestry test (parent is a
2-digit month, grandparent a 4-digit year) already resolved, from
state["source"]["handoff_path"].

This is a pure function of a plain dict -- no filesystem, no subprocess --
so, matching tests/lib/_shared/test_feature_alloc.py's own convention for
the sibling classify_feature_dir_identity, these are direct unit tests
over hand-built state shapes, not a producer round-trip. The producer
round-trip for the two REAL consumers (write-design-anchor,
finalize-handoff) lives in tests/lib/test_specify_helper.py, driven
through allocate_feature_dir + the real import-handoff CLI.

Stdlib only. No third-party dependencies.
"""

import sys
import unittest
from pathlib import Path

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _specify._schema import resolve_bucketed_feature_dir  # noqa: E402


def _state(**kwargs):
    """Minimal state shape resolve_bucketed_feature_dir actually reads."""
    base = {
        "spec_number": None,
        "source": {"handoff_path": None},
    }
    base.update(kwargs)
    return base


class TestResolveBucketedFeatureDir(unittest.TestCase):
    def test_legacy_spec_number_set_returns_none(self):
        """spec_number already set -- legacy composition is correct;
        nothing to override, even when source.handoff_path looks bucketed."""
        state = _state(
            spec_number="003",
            source={"handoff_path": "specs/2026/08/003-auth-token-refresh/research-handoff.json"},
        )
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_no_handoff_path_returns_none(self):
        """A manual /specify run with no upstream handoff at all."""
        state = _state(spec_number=None, source={"handoff_path": None})
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_missing_source_key_returns_none(self):
        """A pre-plan-91 state dict with no 'source' key at all must not crash."""
        state = {"spec_number": None}
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_bucketed_ticketless_resolves_directory(self):
        state = _state(
            spec_number=None,
            source={"handoff_path": "specs/2026/08/second-feature/research-handoff.json"},
        )
        result = resolve_bucketed_feature_dir(state)
        self.assertEqual(result, Path("specs/2026/08/second-feature"))

    def test_bucketed_ticketed_resolves_directory(self):
        """Ancestry alone decides -- the leaf being a ticket (not a slug)
        is irrelevant to this function; only the two parent segments matter."""
        state = _state(
            spec_number=None,
            source={"handoff_path": "specs/2026/08/PROJ-123/research-handoff.json"},
        )
        result = resolve_bucketed_feature_dir(state)
        self.assertEqual(result, Path("specs/2026/08/PROJ-123"))

    def test_discover_handoff_kind_also_resolves(self):
        """The field name is source.handoff_path regardless of which
        intake command produced it -- discover-handoff.json included."""
        state = _state(
            spec_number=None,
            source={"handoff_path": "specs/2026/08/greenfield-thing/discover-handoff.json"},
        )
        result = resolve_bucketed_feature_dir(state)
        self.assertEqual(result, Path("specs/2026/08/greenfield-thing"))

    def test_genuine_fallback_stray_handoff_returns_none(self):
        """A pre-migration / arbitrary-path handoff (the genuine-fallback
        case) has no real YYYY/MM ancestry -- must NOT be misread as
        bucketed, or the artifact would misroute into a stale directory
        Step 4.1 deliberately does not reuse."""
        state = _state(
            spec_number=None,
            source={"handoff_path": "handoff.json"},
        )
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_month_matches_but_year_does_not_returns_none(self):
        state = _state(
            spec_number=None,
            source={"handoff_path": "specs/notayear/08/second-feature/research-handoff.json"},
        )
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_year_matches_but_month_does_not_returns_none(self):
        state = _state(
            spec_number=None,
            source={"handoff_path": "specs/2026/summer/second-feature/research-handoff.json"},
        )
        self.assertIsNone(resolve_bucketed_feature_dir(state))

    def test_absolute_handoff_path_also_resolves(self):
        """import-handoff stores an ABSOLUTE handoff_path when the handoff
        sits outside the repo root -- the ancestry test works identically
        on an absolute Path."""
        state = _state(
            spec_number=None,
            source={"handoff_path": "/tmp/repo/specs/2026/08/second-feature/research-handoff.json"},
        )
        result = resolve_bucketed_feature_dir(state)
        self.assertEqual(result, Path("/tmp/repo/specs/2026/08/second-feature"))

    def test_empty_string_spec_number_is_falsy_not_legacy(self):
        """spec_number "" (never seeded, default_state()'s sibling shape)
        behaves like None -- only a real truthy value short-circuits."""
        state = _state(
            spec_number="",
            source={"handoff_path": "specs/2026/08/second-feature/research-handoff.json"},
        )
        result = resolve_bucketed_feature_dir(state)
        self.assertEqual(result, Path("specs/2026/08/second-feature"))


if __name__ == "__main__":
    unittest.main()
