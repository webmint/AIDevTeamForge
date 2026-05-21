"""Tests for ``_cross_layer._graph``: ``load_layer_graph`` + ``classify_path``.

Every test constructs config dicts directly and exercises the public API.
No filesystem interaction required (pure dict/string processing).

Coverage
--------
test_load_layer_graph_basic                      -- happy path; self always included
test_load_layer_graph_self_always_allowed         -- isolated layer (empty deps) still allows self
test_load_layer_graph_accepts_string_glob         -- layer_dirs string value -> 1-element list
test_load_layer_graph_accepts_list_glob           -- layer_dirs list value -> kept as list
test_load_layer_graph_unknown_layer_in_graph_value -- unknown dep -> ValueError
test_load_layer_graph_layer_in_dirs_not_in_graph  -- only in dirs -> ValueError
test_load_layer_graph_layer_in_graph_not_in_dirs  -- only in graph -> ValueError
test_load_layer_graph_invalid_deps_type           -- deps is not a list -> ValueError
test_classify_path_match_single_glob              -- path matches first layer's glob
test_classify_path_match_infra                    -- path under 'pkg/infra/**' classifies to 'infra'
test_classify_path_no_match_returns_none          -- path under no layer -> None
test_classify_path_first_match_wins               -- overlapping globs; first dict entry wins
test_classify_path_list_glob_matches_second_glob  -- layer with multiple globs; second glob matches
test_classify_path_paired_pattern_convention      -- path/to/file matched by **/path/to/file pattern
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._forcing_functions._cross_layer._graph import (  # noqa: E402
    classify_path,
    load_layer_graph,
)


# ---------------------------------------------------------------------------
# load_layer_graph tests
# ---------------------------------------------------------------------------

class TestLoadLayerGraphBasic(unittest.TestCase):

    def test_load_layer_graph_basic(self):
        """Happy path: domain(isolated) + infra(can import domain) + ui(can import both)."""
        config = {
            "layer_graph": {
                "domain": [],
                "infra": ["domain"],
                "ui": ["domain", "infra"],
            },
            "layer_dirs": {
                "domain": "packages/domain/**",
                "infra": "packages/infra/**",
                "ui": "packages/ui/**",
            },
        }
        allowed, dirs = load_layer_graph(config)

        # domain is isolated except for itself
        self.assertEqual(allowed["domain"], {"domain"})
        # infra can import domain + itself
        self.assertEqual(allowed["infra"], {"domain", "infra"})
        # ui can import both + itself
        self.assertEqual(allowed["ui"], {"domain", "infra", "ui"})

        # layer_dirs normalized to lists
        self.assertEqual(dirs["domain"], ["packages/domain/**"])
        self.assertEqual(dirs["infra"], ["packages/infra/**"])
        self.assertEqual(dirs["ui"], ["packages/ui/**"])

    def test_load_layer_graph_self_always_allowed(self):
        """Layer with empty dep list still allows imports from itself."""
        config = {
            "layer_graph": {"a": []},
            "layer_dirs": {"a": "pkg/a/**"},
        }
        allowed, _ = load_layer_graph(config)
        self.assertIn("a", allowed["a"])

    def test_load_layer_graph_accepts_string_glob(self):
        """layer_dirs value as a plain string -> normalised to a one-element list."""
        config = {
            "layer_graph": {"a": [], "b": ["a"]},
            "layer_dirs": {"a": "pkg/a/**", "b": "pkg/b/**"},
        }
        _, dirs = load_layer_graph(config)
        self.assertIsInstance(dirs["a"], list)
        self.assertEqual(dirs["a"], ["pkg/a/**"])

    def test_load_layer_graph_accepts_list_glob(self):
        """layer_dirs value as a list -> kept as list (paired-pattern convention)."""
        config = {
            "layer_graph": {"a": []},
            "layer_dirs": {"a": ["pkg/a/**", "**/pkg/a/**"]},
        }
        _, dirs = load_layer_graph(config)
        self.assertIsInstance(dirs["a"], list)
        self.assertEqual(dirs["a"], ["pkg/a/**", "**/pkg/a/**"])


class TestLoadLayerGraphValidation(unittest.TestCase):

    def test_load_layer_graph_unknown_layer_in_graph_value(self):
        """Dependency list references a layer name not in layer_dirs -> ValueError."""
        config = {
            "layer_graph": {"a": ["x"]},
            "layer_dirs": {"a": "pkg/a/**"},
        }
        with self.assertRaises(ValueError) as ctx:
            load_layer_graph(config)
        self.assertIn("x", str(ctx.exception))

    def test_load_layer_graph_layer_in_dirs_not_in_graph(self):
        """Layer declared in layer_dirs but missing from layer_graph -> ValueError."""
        config = {
            "layer_graph": {"a": []},
            "layer_dirs": {"a": "pkg/a/**", "b": "pkg/b/**"},
        }
        with self.assertRaises(ValueError) as ctx:
            load_layer_graph(config)
        self.assertIn("b", str(ctx.exception))

    def test_load_layer_graph_layer_in_graph_not_in_dirs(self):
        """Layer declared in layer_graph but missing from layer_dirs -> ValueError."""
        config = {
            "layer_graph": {"a": [], "b": []},
            "layer_dirs": {"a": "pkg/a/**"},
        }
        with self.assertRaises(ValueError) as ctx:
            load_layer_graph(config)
        self.assertIn("b", str(ctx.exception))

    def test_load_layer_graph_invalid_deps_type(self):
        """Dependency value is not a list (e.g. string) -> ValueError."""
        config = {
            "layer_graph": {"a": "domain"},  # should be ["domain"] not a string
            "layer_dirs": {"a": "pkg/a/**"},
        }
        with self.assertRaises(ValueError) as ctx:
            load_layer_graph(config)
        self.assertIn("list", str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# classify_path tests
# ---------------------------------------------------------------------------

class TestClassifyPath(unittest.TestCase):

    def _make_dirs(self, spec):
        """Build layer_dirs_map from a dict of {layer: glob_or_list}."""
        _, dirs = load_layer_graph({
            "layer_graph": {k: [] for k in spec},
            "layer_dirs": spec,
        })
        return dirs

    def test_classify_path_match_single_glob(self):
        """Path under 'pkg/domain/**' classifies to 'domain'."""
        dirs = self._make_dirs({"domain": "pkg/domain/**", "infra": "pkg/infra/**"})
        result = classify_path(Path("pkg/domain/foo.ts"), dirs)
        self.assertEqual(result, "domain")

    def test_classify_path_match_infra(self):
        """Path under 'pkg/infra/**' classifies to 'infra'."""
        dirs = self._make_dirs({"domain": "pkg/domain/**", "infra": "pkg/infra/**"})
        result = classify_path(Path("pkg/infra/bar.ts"), dirs)
        self.assertEqual(result, "infra")

    def test_classify_path_no_match_returns_none(self):
        """Path not matching any layer glob -> None."""
        dirs = self._make_dirs({"domain": "pkg/domain/**", "infra": "pkg/infra/**"})
        result = classify_path(Path("scripts/build.ts"), dirs)
        self.assertIsNone(result)

    def test_classify_path_first_match_wins(self):
        """When two layers' globs overlap, the first dict entry wins.

        Python 3.7+ dicts maintain insertion order, so 'domain' is first.
        We construct a config where 'domain' has a glob that also matches the
        path we feed in, to confirm first-match semantics.
        """
        # Both 'domain' and 'shared' match 'shared/foo.ts' via their globs.
        # 'domain' is inserted first so it should win.
        config = {
            "layer_graph": {"domain": [], "shared": []},
            "layer_dirs": {"domain": "shared/**", "shared": "shared/**"},
        }
        _, dirs = load_layer_graph(config)
        result = classify_path(Path("shared/foo.ts"), dirs)
        self.assertEqual(result, "domain")

    def test_classify_path_list_glob_matches_second_glob(self):
        """Layer with multiple globs: path matching the second glob still classifies."""
        dirs = self._make_dirs({
            "domain": ["pkg/domain/**", "**/pkg/domain/**"],
        })
        # This path would match '**/pkg/domain/**' but not 'pkg/domain/**'.
        result = classify_path(Path("apps/web/pkg/domain/foo.ts"), dirs)
        self.assertEqual(result, "domain")

    def test_classify_path_paired_pattern_convention(self):
        """Top-level glob matches a top-level path; **-prefixed glob matches nested."""
        dirs = self._make_dirs({
            "domain": ["pkg/domain/**", "**/pkg/domain/**"],
        })
        # Top-level path: matched by 'pkg/domain/**'
        self.assertEqual(classify_path(Path("pkg/domain/foo.ts"), dirs), "domain")
        # Nested path: matched by '**/pkg/domain/**'
        self.assertEqual(
            classify_path(Path("apps/web/pkg/domain/bar.ts"), dirs), "domain"
        )


if __name__ == "__main__":
    unittest.main()
