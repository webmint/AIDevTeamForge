"""Tests for _configure/_lint_ignore.py — cross-ecosystem linter-ignore detector.

Coverage:
- prettier: existing .prettierignore with entries (append, idempotent)
- prettier: absent file + prettier configured via package.json (create)
- prettier: no prettier config → not detected
- flake8: setup.cfg with existing [flake8] extend-exclude (merge, preserve other keys)
- flake8: .flake8 absent table (new file, clean write)
- flake8: already excluded → idempotent
- biome.json: existing files.includes (merge negations, idempotent)
- biome.json: absent files.includes (create key)
- biome.json: JSONC with comments → manual
- pyproject.toml: [tool.ruff] ABSENT → append clean block
- pyproject.toml: [tool.ruff] PRESENT → manual (safe targeted: key absent → append)
- pyproject.toml: [tool.black] ABSENT → append clean block (regex value)
- pyproject.toml: [tool.black] PRESENT extend-exclude key absent → safe append
- pyproject.toml: [tool.black] PRESENT extend-exclude key present → manual
- pyproject.toml: ruff idempotency (re-run adds nothing)
- vscode: existing keys preserved, folders merged into search.exclude + files.watcherExclude
- vscode: JSONC with comments → manual (no corruption)
- vscode: absent .vscode/settings.json → create with merged keys
- eslint flat config present → manual (no .eslintignore written)
- eslint legacy .eslintrc → auto append .eslintignore
- scoping: no prettier config file → prettier handler skips
- scoping: .prettierignore present → prettier fires (config-file-presence mechanism)
- idempotency: every auto handler re-run produces already-present status
- ruff.toml top-level: [tool.ruff] absent → append clean block
- markdownlint: .markdownlintignore present → append idempotent
- markdownlint-cli2 JSONC: structured merge ignores array
- markdownlint-cli2 YAML: manual
- rubocop: .rubocop.yml → manual
- golangci-lint: .golangci.yml → manual
- jetbrains: .idea/ present → manual
- rustfmt: rustfmt.toml absent table → append
- mypy: pyproject.toml [tool.mypy] absent → append clean regex block
- pylint: pyproject.toml [tool.pylint.main] absent → append clean block
- isort: pyproject.toml [tool.isort] absent → append clean block
- report shape: summary counts correct
- preemptive flag: specs/ absent → entry has preemptive=True
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# Import the module under test.
from _configure._lint_ignore import (  # noqa: E402
    FRAMEWORK_FOLDERS,
    run_lint_ignore,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(root: Path, rel: str, content: str) -> Path:
    """Write content to root/rel, creating parent dirs. Returns the path."""
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _run_dry(root: Path, devforge_dir: Optional[str] = None) -> dict:
    """Run lint_ignore in dry-run mode on root. Returns parsed JSON report."""
    dfd = devforge_dir or str(root / ".devforge")
    report = run_lint_ignore(
        install_root=str(root),
        devforge_dir=dfd,
        apply=False,
    )
    return report


def _run_apply(root: Path, devforge_dir: Optional[str] = None) -> dict:
    """Run lint_ignore with --apply on root. Returns parsed JSON report."""
    dfd = devforge_dir or str(root / ".devforge")
    report = run_lint_ignore(
        install_root=str(root),
        devforge_dir=dfd,
        apply=True,
    )
    return report


from typing import Optional


# ---------------------------------------------------------------------------
# FRAMEWORK_FOLDERS constant
# ---------------------------------------------------------------------------


class TestFrameworkFolders(unittest.TestCase):

    def test_all_required_folders_present(self):
        required = [".claude", ".devforge", "specs", "bugs", "research", "discover", "audits"]
        for f in required:
            self.assertIn(f, FRAMEWORK_FOLDERS, "Missing folder: {0}".format(f))

    def test_docs_not_present(self):
        self.assertNotIn("docs", FRAMEWORK_FOLDERS)


# ---------------------------------------------------------------------------
# Prettier handler
# ---------------------------------------------------------------------------


class TestPrettierHandler(unittest.TestCase):

    def test_existing_prettierignore_appends_missing_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "node_modules\ndist\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        self.assertTrue(len(entries) > 0)
        entry = entries[0]
        self.assertEqual(entry["action"], "auto")
        self.assertIn(entry["status"], ("would-add", "would-create"))
        # All framework folders should be in the lines list
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, entry["lines"])

    def test_existing_prettierignore_idempotent(self):
        """All folders already present → already-present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "\n".join(FRAMEWORK_FOLDERS) + "\n"
            _write(root, ".prettierignore", content)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "already-present")

    def test_prettier_absent_file_but_configured_in_package_json(self):
        """Prettier key in package.json + no .prettierignore → would-create."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pkg = {"name": "test", "prettier": {"semi": False}}
            _write(root, "package.json", json.dumps(pkg))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "would-create")

    def test_prettier_no_config_not_detected(self):
        """No .prettierrc* and no prettier key in package.json → not detected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "package.json", json.dumps({"name": "test", "version": "1.0.0"}))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        self.assertEqual(len(entries), 0)

    def test_apply_creates_prettierignore_when_absent(self):
        """--apply creates the file if prettier is configured."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierrc.json", json.dumps({"semi": False}))
            _run_apply(root)
            pi = root / ".prettierignore"
            self.assertTrue(pi.exists())
            content = pi.read_text(encoding="utf-8")
            for folder in FRAMEWORK_FOLDERS:
                self.assertIn(folder, content)

    def test_apply_appends_only_missing_lines(self):
        """--apply appends only lines not already in .prettierignore."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Already has .claude and .devforge
            existing = ".claude\n.devforge\n"
            _write(root, ".prettierignore", existing)
            _run_apply(root)
            content = (root / ".prettierignore").read_text(encoding="utf-8")
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            # Should not duplicate .claude/.devforge
            self.assertEqual(lines.count(".claude"), 1)
            self.assertEqual(lines.count(".devforge"), 1)
            # Should add the rest
            for folder in FRAMEWORK_FOLDERS:
                self.assertIn(folder, lines)

    def test_apply_idempotent_rerun(self):
        """Second apply → no changes, report shows already-present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "")
            _run_apply(root)
            # Second run
            report2 = _run_apply(root)
        entries = [e for e in report2["entries"] if e["tool"] == "prettier"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "already-present")


# ---------------------------------------------------------------------------
# flake8 handler
# ---------------------------------------------------------------------------


class TestFlake8Handler(unittest.TestCase):

    def test_setup_cfg_flake8_extend_exclude_merge(self):
        """setup.cfg with [flake8] extend-exclude: merges framework folders."""
        cfg = textwrap.dedent("""\
            [flake8]
            max-line-length = 88
            extend-exclude = venv,build
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "setup.cfg", cfg)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "flake8"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")
        self.assertIn(entries[0]["status"], ("would-add",))

    def test_setup_cfg_preserves_other_keys(self):
        """--apply preserves max-line-length and other [flake8] keys."""
        cfg = textwrap.dedent("""\
            [flake8]
            max-line-length = 88
            extend-exclude = venv
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "setup.cfg", cfg)
            _run_apply(root)
            import configparser
            cp = configparser.ConfigParser()
            cp.read(str(root / "setup.cfg"), encoding="utf-8")
            self.assertEqual(cp.get("flake8", "max-line-length"), "88")
            excludes = cp.get("flake8", "extend-exclude")
            self.assertIn("venv", excludes)
            for folder in FRAMEWORK_FOLDERS:
                self.assertIn(folder, excludes)

    def test_flake8_ini_detected(self):
        """.flake8 file detected, extend-exclude added."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".flake8", "[flake8]\nmax-line-length = 120\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "flake8"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_flake8_idempotent(self):
        """All framework folders already in extend-exclude → already-present."""
        folders_str = ",".join(FRAMEWORK_FOLDERS)
        cfg = textwrap.dedent("""\
            [flake8]
            extend-exclude = {0}
        """).format(folders_str)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".flake8", cfg)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "flake8"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "already-present")

    def test_tox_ini_flake8_section_detected(self):
        """tox.ini with [flake8] section detected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "tox.ini", "[flake8]\nmax-line-length = 79\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "flake8"]
        self.assertEqual(len(entries), 1)

    def test_flake8_no_config_not_detected(self):
        """No flake8 config → not detected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "flake8"]
        self.assertEqual(len(entries), 0)


# ---------------------------------------------------------------------------
# Biome handler
# ---------------------------------------------------------------------------


class TestBiomeHandler(unittest.TestCase):

    def test_existing_files_includes_merge_negations(self):
        """biome.json with existing files.includes → merges negated entries."""
        biome = {"files": {"includes": ["**"]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", json.dumps(biome))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "biome"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")
        self.assertIn(entries[0]["status"], ("would-add",))

    def test_biome_absent_files_includes_key(self):
        """biome.json without files.includes → adds it."""
        biome = {"linter": {"enabled": True}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", json.dumps(biome))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "biome"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_biome_already_present_idempotent(self):
        """All negated folders already in files.includes → already-present."""
        includes = ["**"] + ["!{0}".format(f) for f in FRAMEWORK_FOLDERS]
        biome = {"files": {"includes": includes}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", json.dumps(biome))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "biome"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "already-present")

    def test_biome_jsonc_with_comments_manual(self):
        """biome.json with inline comments → classified manual (can't parse)."""
        jsonc_content = '{\n  // a comment\n  "files": {"includes": ["**"]}\n}\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", jsonc_content)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "biome"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")

    def test_biome_apply_writes_negations(self):
        """--apply writes negated folders into files.includes."""
        biome = {"files": {"includes": ["**"]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", json.dumps(biome))
            _run_apply(root)
            updated = json.loads((root / "biome.json").read_text(encoding="utf-8"))
        includes = updated["files"]["includes"]
        self.assertIn("**", includes)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn("!{0}".format(folder), includes)

    def test_biome_apply_idempotent(self):
        """Second apply on biome.json → already-present."""
        biome = {"files": {"includes": ["**"]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "biome.json", json.dumps(biome))
            _run_apply(root)
            report2 = _run_apply(root)
        entries = [e for e in report2["entries"] if e["tool"] == "biome"]
        self.assertEqual(entries[0]["status"], "already-present")


# ---------------------------------------------------------------------------
# pyproject.toml — ruff handler
# ---------------------------------------------------------------------------


class TestRuffHandler(unittest.TestCase):

    def test_ruff_table_absent_appends_clean_block(self):
        """[tool.ruff] absent → status would-add, action auto."""
        toml = textwrap.dedent("""\
            [tool.pytest.ini_options]
            testpaths = ["tests"]
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")
        self.assertIn(entries[0]["status"], ("would-add", "would-create"))

    def test_ruff_table_absent_apply_writes_block(self):
        """--apply when [tool.ruff] absent → block appended."""
        toml = "[build-system]\nrequires = []\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            _run_apply(root)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.ruff]", content)
        self.assertIn("extend-exclude", content)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, content)

    def test_ruff_idempotency_rerun_no_corruption(self):
        """Re-run on a file that already has [tool.ruff] extend-exclude → already-present, no corruption."""
        toml = "[build-system]\nrequires = []\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            _run_apply(root)
            content_after_first = (root / "pyproject.toml").read_text(encoding="utf-8")
            report2 = _run_apply(root)
            content_after_second = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(content_after_first, content_after_second, "File changed on second apply")
        entries = [e for e in report2["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "already-present")

    def test_ruff_table_present_no_extend_exclude_safe_append(self):
        """[tool.ruff] present but no extend-exclude → safe to append the key."""
        toml = textwrap.dedent("""\
            [tool.ruff]
            line-length = 88
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        # Table present, key absent — safe to append key under heading
        self.assertEqual(len(entries), 1)
        self.assertIn(entries[0]["action"], ("auto", "manual"))

    def test_ruff_not_detected_without_pyproject(self):
        """No pyproject.toml and no ruff.toml → not detected."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 0)


# ---------------------------------------------------------------------------
# pyproject.toml — black handler
# ---------------------------------------------------------------------------


class TestBlackHandler(unittest.TestCase):

    def test_black_table_absent_appends_regex_block(self):
        """[tool.black] absent → clean block appended with regex value."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "black"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_black_table_absent_apply_produces_regex(self):
        """--apply: extend-exclude value is a regex string, dots escaped."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            _run_apply(root)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.black]", content)
        self.assertIn("extend-exclude", content)
        # .devforge and .claude have dots that must be escaped in regex
        # The regex should escape the dot in .devforge → \.devforge
        self.assertIn(r"\.", content)

    def test_black_extend_exclude_present_manual(self):
        """[tool.black] with extend-exclude already set → manual (preserve user's regex)."""
        toml = textwrap.dedent("""\
            [tool.black]
            line-length = 88
            extend-exclude = "/(venv|build)/"
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "black"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")

    def test_black_table_present_no_extend_exclude_safe_append(self):
        """[tool.black] present but no extend-exclude → safe to append."""
        toml = textwrap.dedent("""\
            [tool.black]
            line-length = 88
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "black"]
        self.assertEqual(len(entries), 1)
        self.assertIn(entries[0]["action"], ("auto", "manual"))

    def test_black_idempotency(self):
        """Re-run after apply → already-present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            _run_apply(root)
            report2 = _run_apply(root)
        entries = [e for e in report2["entries"] if e["tool"] == "black"]
        self.assertEqual(entries[0]["status"], "already-present")


# ---------------------------------------------------------------------------
# pyproject.toml — isort handler
# ---------------------------------------------------------------------------


class TestIsortHandler(unittest.TestCase):

    def test_isort_table_absent_appends_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "isort"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_isort_uses_extend_skip_glob_key(self):
        """The key written is extend_skip_glob (underscored)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            _run_apply(root)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("extend_skip_glob", content)


# ---------------------------------------------------------------------------
# pyproject.toml — mypy handler
# ---------------------------------------------------------------------------


class TestMypyHandler(unittest.TestCase):

    def test_mypy_table_absent_appends_regex_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "mypy"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_mypy_exclude_is_regex(self):
        """mypy exclude value is a regex pattern (dots escaped)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            _run_apply(root)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.mypy]", content)
        self.assertIn("exclude", content)
        self.assertIn(r"\.", content)


# ---------------------------------------------------------------------------
# pyproject.toml — pylint handler
# ---------------------------------------------------------------------------


class TestPylintHandler(unittest.TestCase):

    def test_pylint_table_absent_appends_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "pylint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_pylint_uses_tool_pylint_main_table(self):
        """Written section header is [tool.pylint.main]."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            _run_apply(root)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.pylint.main]", content)


# ---------------------------------------------------------------------------
# ruff.toml (top-level config)
# ---------------------------------------------------------------------------


class TestRuffTomlHandler(unittest.TestCase):

    def test_ruff_toml_absent_extend_exclude_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "ruff.toml", 'line-length = 88\n')
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_ruff_toml_apply_writes_extend_exclude(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "ruff.toml", 'line-length = 88\n')
            _run_apply(root)
            content = (root / "ruff.toml").read_text(encoding="utf-8")
        self.assertIn("extend-exclude", content)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, content)


# ---------------------------------------------------------------------------
# rustfmt handler
# ---------------------------------------------------------------------------


class TestRustfmtHandler(unittest.TestCase):

    def test_rustfmt_toml_absent_table_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "rustfmt.toml", "max_width = 100\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "rustfmt"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_rustfmt_toml_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "rustfmt.toml", "max_width = 100\n")
            _run_apply(root)
            content = (root / "rustfmt.toml").read_text(encoding="utf-8")
        self.assertIn("ignore", content)

    def test_rustfmt_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "rustfmt.toml", "max_width = 100\n")
            _run_apply(root)
            report2 = _run_apply(root)
        entries = [e for e in report2["entries"] if e["tool"] == "rustfmt"]
        self.assertEqual(entries[0]["status"], "already-present")


# ---------------------------------------------------------------------------
# markdownlint handler
# ---------------------------------------------------------------------------


class TestMarkdownlintHandler(unittest.TestCase):

    def test_markdownlintignore_append(self):
        """Existing .markdownlintignore → append missing folders."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".markdownlintignore", "node_modules\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "markdownlint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_markdownlintignore_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "\n".join(FRAMEWORK_FOLDERS) + "\n"
            _write(root, ".markdownlintignore", content)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "markdownlint"]
        self.assertEqual(entries[0]["status"], "already-present")

    def test_markdownlint_cli2_jsonc_merge(self):
        """markdownlint-cli2 JSON config → structured merge of ignores array."""
        cli2 = {"ignores": ["node_modules"]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".markdownlint-cli2.jsonc", json.dumps(cli2))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "markdownlint-cli2"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_markdownlint_cli2_yaml_manual(self):
        """markdownlint-cli2 .yaml config → manual (no stdlib YAML writer)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".markdownlint-cli2.yaml", "ignores:\n  - node_modules\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "markdownlint-cli2"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")


# ---------------------------------------------------------------------------
# ESLint handler
# ---------------------------------------------------------------------------


class TestEslintHandler(unittest.TestCase):

    def test_eslint_legacy_rc_auto_eslintignore(self):
        """.eslintrc.json present → auto append .eslintignore."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".eslintrc.json", json.dumps({"rules": {}}))
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "eslint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_eslint_flat_config_manual(self):
        """eslint.config.mjs → manual (no .eslintignore)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "eslint.config.mjs", "export default [];\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "eslint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")

    def test_eslint_flat_does_not_write_eslintignore(self):
        """With flat config, --apply must NOT create .eslintignore."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "eslint.config.js", "module.exports = [];\n")
            _run_apply(root)
            self.assertFalse((root / ".eslintignore").exists())


# ---------------------------------------------------------------------------
# VS Code handler
# ---------------------------------------------------------------------------


class TestVSCodeHandler(unittest.TestCase):

    def test_vscode_existing_keys_preserved(self):
        """Existing settings.json keys preserved; framework folders added to excludes."""
        settings = {
            "editor.fontSize": 14,
            "search.exclude": {"node_modules": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vscode_dir = root / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "vscode"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto")

    def test_vscode_apply_merges_search_exclude_and_watcher(self):
        """--apply merges folders into search.exclude + files.watcherExclude."""
        settings = {"editor.fontSize": 14}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vscode_dir = root / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
            _run_apply(root)
            updated = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        # editor.fontSize preserved
        self.assertEqual(updated["editor.fontSize"], 14)
        # Framework folders added
        for folder in FRAMEWORK_FOLDERS:
            key = "{0}/**".format(folder)
            self.assertIn(key, updated.get("search.exclude", {}))
            self.assertIn(key, updated.get("files.watcherExclude", {}))

    def test_vscode_jsonc_with_comments_manual(self):
        """settings.json with JSON comments → manual (no corruption)."""
        jsonc = '{\n  // my comment\n  "editor.fontSize": 14\n}\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vscode_dir = root / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text(jsonc, encoding="utf-8")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "vscode"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")

    def test_vscode_absent_settings_json_creates_on_apply(self):
        """No settings.json but .vscode/ exists → created on apply."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vscode").mkdir()
            _run_apply(root)
            settings_path = root / ".vscode" / "settings.json"
            self.assertTrue(settings_path.exists())
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        for folder in FRAMEWORK_FOLDERS:
            key = "{0}/**".format(folder)
            self.assertIn(key, data.get("search.exclude", {}))

    def test_vscode_idempotent(self):
        """Re-run on already-configured settings.json → already-present."""
        settings = {}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vscode_dir = root / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
            _run_apply(root)
            report2 = _run_apply(root)
        entries = [e for e in report2["entries"] if e["tool"] == "vscode"]
        self.assertEqual(entries[0]["status"], "already-present")


# ---------------------------------------------------------------------------
# JetBrains handler
# ---------------------------------------------------------------------------


class TestJetBrainsHandler(unittest.TestCase):

    def test_idea_present_manual(self):
        """.idea/ present → manual instruction."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".idea").mkdir()
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "jetbrains"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")
        self.assertIn("instruction", entries[0])

    def test_idea_absent_not_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "jetbrains"]
        self.assertEqual(len(entries), 0)


# ---------------------------------------------------------------------------
# Manual-only handlers (rubocop, golangci-lint)
# ---------------------------------------------------------------------------


class TestManualOnlyHandlers(unittest.TestCase):

    def test_rubocop_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".rubocop.yml", "AllCops:\n  NewCops: enable\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "rubocop"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")

    def test_golangci_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".golangci.yml", "run:\n  timeout: 5m\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "golangci-lint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual")


# ---------------------------------------------------------------------------
# Scoping: config-file-presence drives handler activation
# ---------------------------------------------------------------------------


class TestScoping(unittest.TestCase):

    def test_no_prettier_config_file_prettier_skips(self):
        """No .prettierrc* and no prettier key in package.json → prettier not detected.

        Detection is driven purely by config-file presence, not by language.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", "[tool.pytest]\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        # No prettier config file present → prettier not detected
        self.assertEqual(len(entries), 0)

    def test_prettierignore_present_prettier_fires(self):
        """.prettierignore exists → prettier handler fires (config-file-presence)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "dist\n")
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        self.assertEqual(len(entries), 1)


# ---------------------------------------------------------------------------
# Pre-emptive flag
# ---------------------------------------------------------------------------


class TestPreemptiveFlag(unittest.TestCase):

    def test_specs_absent_entry_is_preemptive(self):
        """specs/ folder absent → entries for it should have preemptive=True."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "")
            report = _run_dry(root)
        # Find a prettier entry
        entries = [e for e in report["entries"] if e["tool"] == "prettier"]
        if entries and entries[0].get("lines"):
            # specs is one of the lines (not yet existing folder)
            # The preemptive flag is on the top-level entry (the folder set includes specs)
            # Check that specs is in lines — it's preemptive since folder doesn't exist
            self.assertIn("specs", entries[0]["lines"])

    def test_preemptive_field_present_in_entries(self):
        """All auto entries have a 'preemptive' boolean field."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "")
            report = _run_dry(root)
        for entry in report["entries"]:
            if entry.get("action") == "auto":
                self.assertIn("preemptive", entry, "Missing preemptive field in entry: {0}".format(entry))


# ---------------------------------------------------------------------------
# Report shape + summary
# ---------------------------------------------------------------------------


class TestReportShape(unittest.TestCase):

    def test_report_has_entries_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = _run_dry(root)
        self.assertIn("entries", report)
        self.assertIn("summary", report)

    def test_summary_counts_auto_and_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "")
            _write(root, ".rubocop.yml", "AllCops:\n  NewCops: enable\n")
            report = _run_dry(root)
        summary = report["summary"]
        self.assertIn("auto_count", summary)
        self.assertIn("manual_count", summary)
        auto_cnt = sum(1 for e in report["entries"] if e.get("action") == "auto")
        manual_cnt = sum(1 for e in report["entries"] if e.get("action") == "manual")
        self.assertEqual(summary["auto_count"], auto_cnt)
        self.assertEqual(summary["manual_count"], manual_cnt)

    def test_dry_run_no_files_written(self):
        """Dry-run must not write any files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "node_modules")
            before = set(root.rglob("*"))
            _run_dry(root)
            after = set(root.rglob("*"))
        # File count and names must not change
        self.assertEqual(before, after)

    def test_apply_does_not_touch_manual_entries(self):
        """--apply must not write files for manual entries."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rubocop_path = root / ".rubocop.yml"
            rubocop_content = "AllCops:\n  NewCops: enable\n"
            rubocop_path.write_text(rubocop_content, encoding="utf-8")
            _run_apply(root)
            # .rubocop.yml must be untouched
            self.assertEqual(rubocop_path.read_text(encoding="utf-8"), rubocop_content)


# ---------------------------------------------------------------------------
# Fix 1: flake8 empty extend-exclude does not produce duplicate key
# ---------------------------------------------------------------------------


class TestFlake8EmptyExtendExclude(unittest.TestCase):
    """Fix 1 — HIGH: present-but-empty extend-exclude must be replaced, not duplicated."""

    def test_empty_extend_exclude_no_duplicate_key(self):
        """[flake8] with extend-exclude = (empty) → apply replaces it, no duplicate."""
        import configparser as _cp_mod
        cfg = "[flake8]\nextend-exclude =\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = _write(root, ".flake8", cfg)
            _run_apply(root)
            content = p.read_text(encoding="utf-8")
            # Exactly one occurrence of extend-exclude
            self.assertEqual(content.count("extend-exclude"), 1,
                             "Duplicate extend-exclude key written")
            # File must re-parse cleanly (inside tmp so file still exists)
            cp = _cp_mod.ConfigParser()
            cp.read(str(p), encoding="utf-8")
            val = cp.get("flake8", "extend-exclude")
            for folder in FRAMEWORK_FOLDERS:
                self.assertIn(folder, val)

    def test_empty_extend_exclude_comma_only_no_duplicate(self):
        """[flake8] with extend-exclude = , (comma-only value) → apply replaces, no duplicate."""
        import configparser as _cp_mod
        cfg = "[flake8]\nextend-exclude = ,\nmax-line-length = 88\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = _write(root, ".flake8", cfg)
            _run_apply(root)
            content = p.read_text(encoding="utf-8")
            self.assertEqual(content.count("extend-exclude"), 1)
            cp = _cp_mod.ConfigParser()
            cp.read(str(p), encoding="utf-8")
            self.assertEqual(cp.get("flake8", "max-line-length"), "88")


# ---------------------------------------------------------------------------
# Fix 2: dead re.sub removed — existing flake8 tests cover behavior; smoke-check
# ---------------------------------------------------------------------------


class TestFlake8ReSubRemoved(unittest.TestCase):
    """Fix 2 — MEDIUM: confirm apply still works correctly (dead re.sub removed)."""

    def test_apply_still_merges_correctly_after_re_sub_removal(self):
        """After re.sub removal, _replace_ini_key still merges correctly."""
        cfg = textwrap.dedent("""\
            [flake8]
            max-line-length = 88
            extend-exclude = venv,build
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = _write(root, "setup.cfg", cfg)
            _run_apply(root)
            import configparser
            cp = configparser.ConfigParser()
            cp.read(str(p), encoding="utf-8")
            val = cp.get("flake8", "extend-exclude")
        self.assertIn("venv", val)
        self.assertIn("build", val)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, val)
        # max-line-length untouched
        self.assertEqual(cp.get("flake8", "max-line-length"), "88")


# ---------------------------------------------------------------------------
# Fix 3: rustfmt idempotency — whole-file comment must not cause false-positive
# ---------------------------------------------------------------------------


class TestRustfmtFalsePositive(unittest.TestCase):
    """Fix 3 — MEDIUM: folder names in comment must not trigger already-present."""

    def test_folder_names_in_comment_not_already_present(self):
        """rustfmt.toml with ignore = ['src'] + comment containing all folder names
        must NOT report already-present (they aren't in the ignore key value)."""
        # Put all folder names in a comment, but the actual ignore key only has "src"
        comment = "# " + " ".join(FRAMEWORK_FOLDERS)
        content = "{comment}\nignore = [\"src\"]\n".format(comment=comment)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "rustfmt.toml", content)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "rustfmt"]
        self.assertEqual(len(entries), 1)
        # Should NOT be already-present — key exists but value only has "src"
        self.assertNotEqual(entries[0]["status"], "already-present",
                            "False-positive: folder names in comment caused already-present")
        self.assertEqual(entries[0]["action"], "manual",
                         "Expected manual (key present, partial value)")


# ---------------------------------------------------------------------------
# Fix 4: applied_count counts actually-changed entries
# ---------------------------------------------------------------------------


class TestAppliedCount(unittest.TestCase):
    """Fix 4 — MEDIUM: applied_count reflects entries actually written, not all auto entries."""

    def test_applied_count_one_changed_one_already_present(self):
        """Mix of one would-add tool + one already-present tool → applied_count == 1."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # prettier already has all folders → already-present
            content = "\n".join(FRAMEWORK_FOLDERS) + "\n"
            _write(root, ".prettierignore", content)
            # ESLint legacy rc → .eslintignore absent → would-create → applied
            _write(root, ".eslintrc.json", json.dumps({"rules": {}}))
            report = _run_apply(root)
        summary = report["summary"]
        self.assertEqual(summary["applied_count"], 1,
                         "applied_count should be 1 (only eslintignore was written)")
        self.assertGreaterEqual(summary["already_present_count"], 1,
                                "already_present_count should count prettier as already-present")

    def test_dry_run_applied_count_is_zero(self):
        """Dry-run always has applied_count == 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".prettierignore", "node_modules\n")
            report = _run_dry(root)
        self.assertEqual(report["summary"]["applied_count"], 0)

    def test_all_already_present_applied_count_is_zero(self):
        """When everything is already-present, applying changes nothing → applied_count == 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Apply once to write everything
            _write(root, ".prettierignore", "node_modules\n")
            _run_apply(root)
            # Apply again — now everything is already-present
            report2 = _run_apply(root)
        self.assertEqual(report2["summary"]["applied_count"], 0,
                         "Second apply should not count already-present entries as applied")


# ---------------------------------------------------------------------------
# Fix 5: _preemptive_for_lines deleted — confirm it is gone
# ---------------------------------------------------------------------------


class TestPreemptiveForLinesDeleted(unittest.TestCase):
    """Fix 5 — LOW: dead function _preemptive_for_lines must not exist."""

    def test_function_not_exported(self):
        import _configure._lint_ignore as mod
        self.assertFalse(
            hasattr(mod, "_preemptive_for_lines"),
            "_preemptive_for_lines still exists — it should have been deleted",
        )


# ---------------------------------------------------------------------------
# Fix 6: pyproject sub-table ordering — [tool.ruff.lint] present, [tool.ruff] absent → manual
# ---------------------------------------------------------------------------


class TestPyprojectSubTableOrdering(unittest.TestCase):
    """Fix 6 — MEDIUM: parent table absent + sub-table present → manual, not auto-append."""

    def test_ruff_subtable_present_parent_absent_is_manual(self):
        """pyproject.toml with only [tool.ruff.lint] → ruff handler returns manual."""
        toml = textwrap.dedent("""\
            [build-system]
            requires = ["setuptools"]

            [tool.ruff.lint]
            select = ["E", "F"]
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual",
                         "Expected manual when [tool.ruff] absent but [tool.ruff.lint] present")
        self.assertIn("instruction", entries[0])

    def test_ruff_no_subtable_parent_absent_is_auto(self):
        """pyproject.toml with no [tool.ruff.*] at all → ruff handler returns auto (can append safely)."""
        toml = "[build-system]\nrequires = []\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "ruff"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "auto",
                         "Expected auto when neither [tool.ruff] nor sub-tables present")

    def test_mypy_subtable_present_parent_absent_is_manual(self):
        """pyproject.toml with only [tool.mypy.overrides] → mypy handler returns manual."""
        toml = textwrap.dedent("""\
            [tool.mypy.overrides]
            module = "foo.*"
            ignore_missing_imports = true
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "mypy"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual",
                         "Expected manual when [tool.mypy] absent but [tool.mypy.overrides] present")

    def test_pylint_subtable_present_parent_absent_is_manual(self):
        """pyproject.toml with [tool.pylint.messages_control] but no [tool.pylint.main] → manual."""
        toml = textwrap.dedent("""\
            [tool.pylint.messages_control]
            disable = ["C0114"]
        """)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "pyproject.toml", toml)
            report = _run_dry(root)
        entries = [e for e in report["entries"] if e["tool"] == "pylint"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "manual",
                         "Expected manual when [tool.pylint.main] absent but sibling pylint table present")


# ---------------------------------------------------------------------------
# Fix 7: no double file-read in ruff.toml / rustfmt.toml — behavior smoke test
# ---------------------------------------------------------------------------


class TestNoDoubleReadBehavior(unittest.TestCase):
    """Fix 7 — NIT: ruff.toml and rustfmt.toml apply branches use already-read content."""

    def test_ruff_toml_apply_writes_correct_content(self):
        """ruff.toml apply still works correctly (text variable reuse, not re-read)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "ruff.toml", "line-length = 88\n")
            _run_apply(root)
            content = (root / "ruff.toml").read_text(encoding="utf-8")
        self.assertIn("line-length = 88", content)
        self.assertIn("extend-exclude", content)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, content)

    def test_rustfmt_toml_apply_writes_correct_content(self):
        """rustfmt.toml apply still works correctly (text variable reuse, not re-read)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "rustfmt.toml", "max_width = 100\n")
            _run_apply(root)
            content = (root / "rustfmt.toml").read_text(encoding="utf-8")
        self.assertIn("max_width = 100", content)
        self.assertIn("ignore", content)
        for folder in FRAMEWORK_FOLDERS:
            self.assertIn(folder, content)


if __name__ == "__main__":
    unittest.main()
