"""Tests for project-input project-label resolver — Fix 1.

Cases:
  1.  --project CLI arg wins over everything
  2.  PROJECT_NAME in project-config.json wins when CLI absent
  3.  init.yaml project_root wins when project-config.json null
  4.  Common path prefix from concerns wins when init.yaml absent
  5.  project_root.name fallback when none of the above resolve
  6.  init.yaml project_root="." (standalone mode) is skipped
  7.  init.yaml project_root with nested path takes basename
  8.  Common prefix returns None for single package
  9.  Common prefix returns None when packages disagree on first segment
 10.  Common prefix === project_root.name → falls through (no false promotion)

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._project_input import (  # noqa: E402
    _common_path_prefix,
    _read_project_name_from_config,
    _read_project_root_from_init_yaml,
    _resolve_project_label,
)


class CommonPathPrefixTests(unittest.TestCase):
    def test_all_share_first_segment(self):
        out = _common_path_prefix(
            ["db-cse-ui-strata/apps/app-web", "db-cse-ui-strata/packages/pkg-a"]
        )
        self.assertEqual(out, "db-cse-ui-strata")

    def test_disagree_returns_none(self):
        out = _common_path_prefix(["a/b/c", "x/b/c"])
        self.assertIsNone(out)

    def test_single_package_returns_none(self):
        out = _common_path_prefix(["only-one"])
        self.assertIsNone(out)

    def test_empty_list_returns_none(self):
        self.assertIsNone(_common_path_prefix([]))

    def test_empty_string_in_list_returns_none(self):
        self.assertIsNone(_common_path_prefix(["", "real"]))


class ReadProjectNameFromConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.devforge = Path(self.tmp.name) / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def test_returns_value_when_set(self):
        (self.devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_NAME": "my-app"}), encoding="utf-8"
        )
        self.assertEqual(_read_project_name_from_config(self.devforge), "my-app")

    def test_returns_none_when_null(self):
        (self.devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_NAME": None}), encoding="utf-8"
        )
        self.assertIsNone(_read_project_name_from_config(self.devforge))

    def test_returns_none_when_blank(self):
        (self.devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_NAME": "  "}), encoding="utf-8"
        )
        self.assertIsNone(_read_project_name_from_config(self.devforge))

    def test_returns_none_when_missing_file(self):
        self.assertIsNone(_read_project_name_from_config(self.devforge))


class ReadProjectRootFromInitYamlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.devforge = Path(self.tmp.name) / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def test_wrapper_mode_returns_inner_dir(self):
        (self.devforge / "init.yaml").write_text(
            "workspace_mode: wrapper\nproject_root: db-cse-ui-strata\n",
            encoding="utf-8",
        )
        self.assertEqual(
            _read_project_root_from_init_yaml(self.devforge), "db-cse-ui-strata"
        )

    def test_standalone_dot_returns_none(self):
        (self.devforge / "init.yaml").write_text(
            "workspace_mode: standalone\nproject_root: .\n", encoding="utf-8"
        )
        self.assertIsNone(_read_project_root_from_init_yaml(self.devforge))

    def test_nested_path_returns_basename(self):
        (self.devforge / "init.yaml").write_text(
            "project_root: parent/child\n", encoding="utf-8"
        )
        self.assertEqual(_read_project_root_from_init_yaml(self.devforge), "child")

    def test_quoted_value_unquoted(self):
        (self.devforge / "init.yaml").write_text(
            'project_root: "quoted-name"\n', encoding="utf-8"
        )
        self.assertEqual(_read_project_root_from_init_yaml(self.devforge), "quoted-name")

    def test_missing_file_returns_none(self):
        self.assertIsNone(_read_project_root_from_init_yaml(self.devforge))


class ResolveProjectLabelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def test_cli_arg_wins(self):
        (self.devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_NAME": "from-config"}), encoding="utf-8"
        )
        out = _resolve_project_label("from-cli", self.devforge, self.root, [])
        self.assertEqual(out, "from-cli")

    def test_config_wins_over_init_yaml(self):
        (self.devforge / "project-config.json").write_text(
            json.dumps({"PROJECT_NAME": "from-config"}), encoding="utf-8"
        )
        (self.devforge / "init.yaml").write_text(
            "project_root: from-yaml\n", encoding="utf-8"
        )
        out = _resolve_project_label("", self.devforge, self.root, [])
        self.assertEqual(out, "from-config")

    def test_init_yaml_wins_over_common_prefix(self):
        (self.devforge / "init.yaml").write_text(
            "project_root: from-yaml\n", encoding="utf-8"
        )
        out = _resolve_project_label(
            "",
            self.devforge,
            self.root,
            ["common-prefix/pkg-a", "common-prefix/pkg-b"],
        )
        self.assertEqual(out, "from-yaml")

    def test_common_prefix_used_when_no_yaml_or_config(self):
        out = _resolve_project_label(
            "",
            self.devforge,
            self.root,
            ["db-cse-ui-strata/apps/app-web", "db-cse-ui-strata/packages/pkg-a"],
        )
        self.assertEqual(out, "db-cse-ui-strata")

    def test_root_name_fallback_when_nothing_resolves(self):
        out = _resolve_project_label("", self.devforge, self.root, [])
        self.assertEqual(out, self.root.name)

    def test_common_prefix_equal_to_root_name_falls_through(self):
        # Common prefix is the wrapper basename → not a useful promotion.
        out = _resolve_project_label(
            "",
            self.devforge,
            self.root,
            [f"{self.root.name}/pkg-a", f"{self.root.name}/pkg-b"],
        )
        self.assertEqual(out, self.root.name)


if __name__ == "__main__":
    unittest.main()
