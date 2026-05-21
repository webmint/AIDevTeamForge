"""Tests for src/devforge/lib/constitute_helper.py — Step 0..4.

Step 4 coverage (added in this commit):
  validate — 4-dimension content quality framework.
  Slot-fill: fully-populated (1.0) / missing identity subfield (8/9) / empty
    domain rules (8/9) / greenfield+scaffolding (10/10) / greenfield+no-scaffolding
    (9/10) / existing-codebase ignores Section 7.
  Citation: real file resolves (1.0) / non-existent path (0.0) / no tokens (N/A)
    / mix resolved+unresolved (0.5) / package-name lookup via init.yaml
    / annotation INCLUDED in scan.
  Code-example syntax: valid Python / invalid Python / valid JSON / invalid JSON
    / TS balanced / TS unbalanced / exotic language non-empty / exotic empty;
    _count_code_syntax all-pass / one-fail / zero-examples.
  Rule-tag: all valid (1.0) / one bad tag (fractional) / zero rules (N/A).
  Composite + exit: all-pass exits 0 / one-dim-fail exits 2 / stdout JSON
    structure / stderr enumerates failures / corrupted state exits 1 /
    composite formula verification.

Step 3 coverage (added in this commit):
  render — fully-populated state produces 7 (greenfield) or 6 (existing-
    codebase) H2 sections; empty bucket → empty-state marker; tables +
    code examples + descriptions; missing required field → exit 2;
    atomic write leaves no .tmp files; idempotent byte-identical;
    rule text with internal commas (TS generic syntax) preserved;
    multi-line code example whitespace preserved.
  verify — fully-populated → exit 0; bad rule tag / missing title /
    table column-row mismatch / malformed scaffolding sample → exit 2;
    null scaffolding in existing-codebase ok; null in greenfield → exit 2;
    minimal round-trip identity (project_name + section count).
  summary — all-unset shows "(unset)" markers; populated values shown;
    section + per-section counts; all 6 pattern buckets; stable across
    reruns; scaffolding set vs unset; output to stdout not stderr;
    corrupted JSON → exit 1 (matches init/configure precedent).


Step 2 coverage (added in this commit):
  Validation helpers — _validate_scalar / _validate_enum (case-insensitive →
    canonical) / _validate_string_array (JSON-array form for internal-comma
    values + comma-sep legacy) / _validate_path_value / _validate_verbatim.
  State plumbing — _load returns default_state if missing, _state_transaction
    write-on-exit, abort-on-exception (state NOT written if body raises),
    lock file created on first use, _load propagates JSON parse error.
  _find_section — match in each of 4 buckets, return (None, None) for
    unknown number, first-match policy verified.
  Per-setter subprocess — happy path + validation failure + round-trip
    + idempotency/replace-vs-append semantics for all 10 setters
    (set-project-name, set-mode, set-dates, set-project-identity,
    add-section, add-rule, add-table, add-code-example, add-pattern-rule,
    set-scaffolding-guide).
  Cross-process safety — concurrent add-rule via subprocess.Popen (no lost
    array-append); mixed scalar+append concurrency (no corruption);
    add-section before add-rule race coverage.
  Round-trip integration — set every field type once + reload + compare;
    all 4 add-section buckets + all 6 patterns_and_antipatterns buckets
    exercised; ScaffoldingGuide set + reset clears it; add-section
    idempotency on (bucket, number) collision preserves rules.


Step 0 coverage (preserved):
  reset subcommand writes a JSON defaults file with the locked top-level
  shape. Idempotent: byte-identical re-runs.

Step 1 coverage:
  FIELD_SCHEMA — 12 keys (includes forcing_functions), locked order, correct kinds.
  ENUM_FIELDS  — 4 closed enums accessible by name; known values present.
  default_state() — top-level keys + types, patterns_and_antipatterns 6-bucket
    struct, project_identity + scaffolding_guide default to None.
  reset — JSON round-trip (matches default_state); idempotent byte-identical.
  read-init — round-trip via init_helper subprocess (write real init.yaml,
    parse via read-init, assert fields); file missing → exit 1 stderr;
    malformed yaml → exit 2 stderr.
  read-configure — round-trip via configure_helper subprocess; file missing
    → exit 1; malformed yaml → exit 2.
  read-docs — overview-only fixture (Tech Stack table + Project Structure
    fenced block + Key Commands table); architecture-only fixture (Patterns
    sub-headings + Conventions); both files together (testForge20 sample
    copied to tmpdir); overview missing → exit 1; architecture missing →
    exit 1; malformed markdown → graceful exit 0.
  read-glossary — 3-term hand-authored fixture; file missing → exit 1; empty
    file → exit 0 with empty list [].

Each subprocess test runs in its own tempfile.TemporaryDirectory.
Pure-function tests import the module directly.

Real-producer principle for read-init and read-configure: the real helper
subprocess writes the yaml; constitute_helper reads it back — no hand-authored
yaml fixtures bypass the real producer.

Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "constitute_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"
_CONFIGURE_HELPER_PY = _LIB_DIR / "configure_helper.py"
_TESTFORGE20 = Path("/Users/mykolakudlyk/Projects/testForge20")

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import constitute_helper  # noqa: E402
import init_helper  # noqa: E402
import configure_helper  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers.
# ---------------------------------------------------------------------------


def _run(argv, cwd=None, env=None):
    """Run constitute_helper.py with given argv; capture output."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_init(devforge_dir, *extra_args):
    """Run init_helper.py via DEVFORGE_DIR env var."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(extra_args),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_configure(devforge_dir, *extra_args):
    """Run configure_helper.py with --devforge-dir."""
    return subprocess.run(
        [sys.executable, str(_CONFIGURE_HELPER_PY),
         "--devforge-dir", str(devforge_dir)] + list(extra_args),
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Step 0 scaffolding (preserved verbatim).
# ---------------------------------------------------------------------------


class TestStep0Scaffolding(unittest.TestCase):
    def test_default_state_top_level_shape(self):
        """default_state() returns the locked top-level keys with correct types."""
        state = constitute_helper.default_state()

        self.assertIsNone(state["project_name"])
        self.assertIsNone(state["generated_date"])
        self.assertIsNone(state["last_updated"])
        self.assertIsNone(state["mode"])
        self.assertIsNone(state["project_identity"])
        self.assertEqual(state["architecture_rules"], [])
        self.assertEqual(state["code_quality_standards"], [])
        self.assertEqual(state["domain_rules"], [])
        self.assertEqual(state["workflow_rules"], [])
        self.assertIsNone(state["scaffolding_guide"])

        patterns = state["patterns_and_antipatterns"]
        self.assertEqual(
            sorted(patterns.keys()),
            sorted([
                "always_universal",
                "always_project_specific",
                "never_universal",
                "never_project_specific",
                "prefer_universal",
                "prefer_project_specific",
            ]),
        )
        for bucket in patterns.values():
            self.assertEqual(bucket, [])

    def test_reset_writes_default_state_json(self):
        """reset writes constitute.json containing the default state."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr)

            output_file = devforge / "constitute.json"
            self.assertTrue(output_file.exists())

            loaded = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded, constitute_helper.default_state())

    def test_reset_idempotent_byte_identical(self):
        """Re-running reset produces byte-identical output."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            r1 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first = (devforge / "constitute.json").read_bytes()

            r2 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second = (devforge / "constitute.json").read_bytes()

            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# Step 1 — FIELD_SCHEMA + ENUM_FIELDS.
# ---------------------------------------------------------------------------


class TestStep1Schema(unittest.TestCase):
    def test_field_schema_has_12_keys(self):
        """FIELD_SCHEMA defines exactly 12 top-level fields (includes forcing_functions)."""
        self.assertEqual(len(constitute_helper.FIELD_SCHEMA), 12)

    def test_field_schema_key_order(self):
        """FIELD_SCHEMA preserves the locked key order."""
        names = [name for name, _kind in constitute_helper.FIELD_SCHEMA]
        expected = [
            "project_name",
            "generated_date",
            "last_updated",
            "mode",
            "project_identity",
            "architecture_rules",
            "code_quality_standards",
            "patterns_and_antipatterns",
            "domain_rules",
            "workflow_rules",
            "scaffolding_guide",
            "forcing_functions",
        ]
        self.assertEqual(names, expected)

    def test_enum_fields_has_4_enums(self):
        """ENUM_FIELDS defines exactly 4 closed enums."""
        self.assertEqual(len(constitute_helper.ENUM_FIELDS), 4)

    def test_enum_fields_mode(self):
        """ENUM_FIELDS['mode'] contains the two expected values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["mode"],
            {"existing-codebase", "greenfield"},
        )

    def test_enum_fields_rule_tag(self):
        """ENUM_FIELDS['rule_tag'] contains 4 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["rule_tag"],
            {"extracted", "enforced", "universal", "project-specific"},
        )

    def test_enum_fields_section_tag(self):
        """ENUM_FIELDS['section_tag'] contains 3 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["section_tag"],
            {"universal", "project-specific", "greenfield-only"},
        )

    def test_enum_fields_code_label(self):
        """ENUM_FIELDS['code_label'] contains 3 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["code_label"],
            {"CORRECT", "WRONG", "EXAMPLE"},
        )

    def test_default_state_top_level_key_count(self):
        """default_state() returns a dict with exactly 12 top-level keys."""
        state = constitute_helper.default_state()
        self.assertEqual(len(state), 12)

    def test_default_state_section_arrays_empty(self):
        """Section array fields default to []."""
        state = constitute_helper.default_state()
        for field in (
            "architecture_rules",
            "code_quality_standards",
            "domain_rules",
            "workflow_rules",
        ):
            self.assertIsInstance(state[field], list)
            self.assertEqual(state[field], [])

    def test_default_state_patterns_and_antipatterns_structure(self):
        """patterns_and_antipatterns has 6 named buckets, each an empty list."""
        patterns = constitute_helper.default_state()["patterns_and_antipatterns"]
        expected_buckets = sorted([
            "always_universal",
            "always_project_specific",
            "never_universal",
            "never_project_specific",
            "prefer_universal",
            "prefer_project_specific",
        ])
        self.assertEqual(sorted(patterns.keys()), expected_buckets)
        for bucket_list in patterns.values():
            self.assertEqual(bucket_list, [])

    def test_default_state_nullable_fields(self):
        """project_identity and scaffolding_guide default to None."""
        state = constitute_helper.default_state()
        self.assertIsNone(state["project_identity"])
        self.assertIsNone(state["scaffolding_guide"])

    def test_default_state_scalar_fields_none(self):
        """Scalar fields default to None."""
        state = constitute_helper.default_state()
        for field in ("project_name", "generated_date", "last_updated", "mode"):
            self.assertIsNone(state[field])


# ---------------------------------------------------------------------------
# Step 1 — read-init.
# ---------------------------------------------------------------------------


class TestReadInit(unittest.TestCase):
    def test_read_init_round_trip(self):
        """read-init round-trips a real init.yaml written by init_helper."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()

            # Use init_helper subprocess to write a real init.yaml.
            r = _run_init(devforge, "set-workspace-mode", "standalone")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-project-root", ".")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-project-state", "brownfield")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-default-branch", "main")
            self.assertEqual(r.returncode, 0, r.stderr)

            # Now parse it back via read-init.
            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["workspace_mode"], "standalone")
            self.assertEqual(parsed["project_root"], ".")
            self.assertEqual(parsed["project_state"], "brownfield")
            self.assertEqual(parsed["default_branch"], "main")
            self.assertIn("packages_detected", parsed)

    def test_read_init_file_missing_exits_1(self):
        """read-init exits 1 with a stderr message when init.yaml is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()  # devforge dir exists but no init.yaml

            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("init.yaml", result.stderr)

    def test_read_init_malformed_yaml_exits_2(self):
        """read-init exits 2 when init.yaml is malformed."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()
            # Write a file that is syntactically invalid for init_helper's parser.
            init_yaml = devforge / "init.yaml"
            init_yaml.write_text("workspace_mode: {bad: yaml: here}\n", encoding="utf-8")

            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)


# ---------------------------------------------------------------------------
# Step 1 — read-configure.
# ---------------------------------------------------------------------------


class TestReadConfigure(unittest.TestCase):
    def test_read_configure_round_trip(self):
        """read-configure round-trips a real configure.yaml written by configure_helper."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            # Use configure_helper subprocess to reset + set a field.
            r = _run_configure(devforge, "reset")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_configure(devforge, "set-project-name", "my-test-project")
            self.assertEqual(r.returncode, 0, r.stderr)

            # Parse back via read-configure.
            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["project_name"], "my-test-project")
            # All 28 configure fields present.
            self.assertIn("project_description", parsed)
            self.assertIn("primary_language", parsed)
            self.assertIn("frameworks", parsed)
            self.assertIn("workflow_enforcement", parsed)

    def test_read_configure_all_28_fields_present(self):
        """read-configure emits all 28 configure fields."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            r = _run_configure(devforge, "reset")
            self.assertEqual(r.returncode, 0, r.stderr)

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            # configure_helper.FIELD_SCHEMA has exactly 28 fields.
            expected_fields = {name for name, _ in configure_helper.FIELD_SCHEMA}
            self.assertEqual(set(parsed.keys()), expected_fields)

    def test_read_configure_file_missing_exits_1(self):
        """read-configure exits 1 when configure.yaml is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("configure.yaml", result.stderr)

    def test_read_configure_malformed_yaml_exits_2(self):
        """read-configure exits 2 when configure.yaml is malformed."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()
            configure_yaml = devforge / "configure.yaml"
            configure_yaml.write_text(
                "project_name: {not: valid: for: closed: parser}\n",
                encoding="utf-8",
            )

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)


# ---------------------------------------------------------------------------
# Step 1 — read-docs.
# ---------------------------------------------------------------------------

# Hand-authored minimal fixture fragments for overview + architecture testing.
_OVERVIEW_FIXTURE = """\
# My Project

## Purpose

This is the project purpose text.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Vue |
| Language | TypeScript |
| Build Tool | Vite |

## Project Structure

```text
project/
├── src/
│   └── main.ts
└── package.json
```

## Key Commands

| Command | Description |
|---|---|
| `npm run dev` | Start dev server |
| `npm run build` | Build for production |
"""

_ARCHITECTURE_FIXTURE = """\
# My Project architecture

## Architecture Overview

This is the architecture overview text spanning multiple
lines of prose.

## Module / Package Structure

```text
src/
├── components/
└── utils/
```

## Patterns

### Repository Pattern

**Applies in**: Data layer implementations.

All data access goes through repositories.

```typescript
class UserRepository {
  getUser(id: string) { ... }
}
```

### Factory Pattern

**Applies in**: Service creation.

Use factories to construct services.

## Conventions

**Naming**
- Classes are PascalCase
- Functions are camelCase

**Import Style**
- Use barrel exports
"""


class TestReadDocs(unittest.TestCase):
    def _write_docs(self, tmp_path, overview_text, arch_text):
        """Write docs/overview.md + docs/architecture.md to tmp_path."""
        docs = tmp_path / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "overview.md").write_text(overview_text, encoding="utf-8")
        (docs / "architecture.md").write_text(arch_text, encoding="utf-8")
        return docs

    def test_read_docs_overview_tech_stack(self):
        """read-docs parses Tech Stack table from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            ts = parsed["overview"]["tech_stack"]
            self.assertIsInstance(ts, list)
            self.assertGreater(len(ts), 0)
            # Check that the table was parsed — layer + technology keys.
            layers = [row["layer"] for row in ts]
            self.assertIn("Framework", layers)
            self.assertIn("Language", layers)

    def test_read_docs_overview_purpose(self):
        """read-docs extracts Purpose section text from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            purpose = parsed["overview"]["purpose"]
            self.assertIn("purpose text", purpose)

    def test_read_docs_overview_key_commands(self):
        """read-docs parses Key Commands table from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            cmds = parsed["overview"]["key_commands"]
            self.assertIsInstance(cmds, list)
            self.assertGreater(len(cmds), 0)

    def test_read_docs_architecture_patterns(self):
        """read-docs parses ### Patterns sub-headings from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            patterns = parsed["architecture"]["patterns"]
            self.assertIsInstance(patterns, list)
            self.assertGreaterEqual(len(patterns), 2)
            names = [p["name"] for p in patterns]
            self.assertIn("Repository Pattern", names)
            self.assertIn("Factory Pattern", names)

    def test_read_docs_architecture_module_structure(self):
        """read-docs extracts Module / Package Structure section text from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            module_structure = parsed["architecture"]["module_structure"]
            self.assertTrue(module_structure, "module_structure should not be empty")
            self.assertIn("src/", module_structure)

    def test_read_docs_architecture_overview_text(self):
        """read-docs extracts Architecture Overview text from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            overview = parsed["architecture"]["architecture_overview"]
            self.assertIn("architecture overview", overview)

    @unittest.skipUnless(_TESTFORGE20.exists(), "testForge20 not present on this machine")
    def test_read_docs_testforge20_real_sample(self):
        """read-docs with testForge20 sample emits tech_stack + patterns."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs_src = _TESTFORGE20 / "docs"
            docs_dst = tmp_path / "docs"
            shutil.copytree(str(docs_src), str(docs_dst))
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertIn("tech_stack", parsed["overview"])
            self.assertGreater(len(parsed["overview"]["tech_stack"]), 0)
            self.assertIn("patterns", parsed["architecture"])
            self.assertGreater(len(parsed["architecture"]["patterns"]), 0)

    def test_read_docs_overview_missing_exits_1(self):
        """read-docs exits 1 when docs/overview.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            # Only architecture.md exists.
            (docs / "architecture.md").write_text(
                _ARCHITECTURE_FIXTURE, encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("overview.md", result.stderr)

    def test_read_docs_architecture_missing_exits_1(self):
        """read-docs exits 1 when docs/architecture.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "overview.md").write_text(
                _OVERVIEW_FIXTURE, encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("architecture.md", result.stderr)

    def test_read_docs_malformed_markdown_graceful_exit_0(self):
        """read-docs handles malformed markdown gracefully (exit 0, empty sections)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            # Files exist but contain no recognizable section headings.
            (docs / "overview.md").write_text(
                "This is just random prose with no headings.\n", encoding="utf-8"
            )
            (docs / "architecture.md").write_text(
                "Also random prose.\n", encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0)
            parsed = json.loads(result.stdout)
            self.assertIn("overview", parsed)
            self.assertIn("architecture", parsed)


# ---------------------------------------------------------------------------
# Step 1 — read-glossary (pure-function tests).
# ---------------------------------------------------------------------------


# Minimal 3-term glossary fixture.
_GLOSSARY_3_TERMS = """\
---
generated_by: /generate-docs
total_terms: 3
---

# Project Glossary

## Alpha

The first Greek letter. Used for primary identifiers.

- **Used in**: `docs/overview.md`, `docs/architecture.md` (and 1 others)
- **Related**: Beta, Gamma

## Beta

The second Greek letter. Used for secondary identifiers and testing.

- **Used in**: `docs/overview.md`
- **Related**: Alpha

## Gamma

The third Greek letter. Used only in math contexts.

- **Used in**: `docs/architecture.md`
- **Related**: Alpha, Beta
"""


class TestReadGlossaryPure(unittest.TestCase):
    """Pure-function tests for _parse_glossary_md."""

    def test_parse_glossary_three_terms(self):
        """_parse_glossary_md parses 3 terms from the hand-authored fixture."""
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertEqual(len(terms), 3)

    def test_parse_glossary_first_term_name(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertEqual(terms[0]["term"], "Alpha")

    def test_parse_glossary_first_term_definition(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertIn("first Greek letter", terms[0]["definition"])

    def test_parse_glossary_first_term_used_in(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        used_in = terms[0]["used_in"]
        self.assertIsInstance(used_in, list)
        self.assertGreater(len(used_in), 0)
        # Should include the two cited files (without trailing "(and 1 others)")
        self.assertTrue(
            any("overview.md" in u for u in used_in),
            "expected overview.md in used_in: {0}".format(used_in),
        )

    def test_parse_glossary_first_term_related(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        related = terms[0]["related"]
        self.assertIsInstance(related, list)
        self.assertIn("Beta", related)
        self.assertIn("Gamma", related)

    def test_parse_glossary_empty_text(self):
        """_parse_glossary_md returns [] for empty input."""
        terms = constitute_helper._parse_glossary_md("")
        self.assertEqual(terms, [])

    def test_parse_glossary_no_terms_only_frontmatter(self):
        """_parse_glossary_md returns [] when only YAML frontmatter is present."""
        text = "---\ntotal_terms: 0\n---\n\n# Project Glossary\n"
        terms = constitute_helper._parse_glossary_md(text)
        self.assertEqual(terms, [])

    def test_parse_glossary_term_with_no_metadata(self):
        """Term with no Used in / Related lines still parses definition."""
        text = "## Foo\n\nFoo is a placeholder term.\n"
        terms = constitute_helper._parse_glossary_md(text)
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["term"], "Foo")
        self.assertIn("placeholder", terms[0]["definition"])
        self.assertEqual(terms[0]["used_in"], [])
        self.assertEqual(terms[0]["related"], [])

    def test_parse_used_in_line_strips_and_others(self):
        """_parse_used_in_line strips '(and N others)' suffix."""
        line = "- **Used in**: `a.md`, `b.md` (and 3 others)"
        result = constitute_helper._parse_used_in_line(line)
        self.assertEqual(result, ["`a.md`", "`b.md`"])

    def test_parse_related_line_basic(self):
        """_parse_related_line parses comma-separated related terms."""
        line = "- **Related**: Alpha, Beta, Gamma"
        result = constitute_helper._parse_related_line(line)
        self.assertEqual(result, ["Alpha", "Beta", "Gamma"])


class TestReadGlossarySubprocess(unittest.TestCase):
    def test_read_glossary_round_trip(self):
        """read-glossary round-trips a 3-term hand-authored fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "glossary.md").write_text(_GLOSSARY_3_TERMS, encoding="utf-8")
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            terms = json.loads(result.stdout)
            self.assertEqual(len(terms), 3)
            names = [t["term"] for t in terms]
            self.assertEqual(names, ["Alpha", "Beta", "Gamma"])

    def test_read_glossary_file_missing_exits_1(self):
        """read-glossary exits 1 when glossary.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("glossary.md", result.stderr)

    def test_read_glossary_empty_file_exits_0_empty_list(self):
        """read-glossary exits 0 and emits [] for an empty glossary.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "glossary.md").write_text("", encoding="utf-8")
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            terms = json.loads(result.stdout)
            self.assertEqual(terms, [])

    @unittest.skipUnless(_TESTFORGE20.exists(), "testForge20 not present on this machine")
    def test_read_glossary_testforge20_real_sample(self):
        """read-glossary parses real testForge20 glossary without error."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs_src = _TESTFORGE20 / "docs"
            docs_dst = tmp_path / "docs"
            docs_dst.mkdir()
            # Copy only glossary.md to keep test lightweight.
            shutil.copy(
                str(docs_src / "glossary.md"),
                str(docs_dst / "glossary.md"),
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            terms = json.loads(result.stdout)
            self.assertIsInstance(terms, list)
            self.assertGreater(len(terms), 10, "Expected >10 terms in testForge20 glossary")
            # Each term has required keys.
            for t in terms:
                self.assertIn("term", t)
                self.assertIn("definition", t)
                self.assertIn("used_in", t)
                self.assertIn("related", t)


# ---------------------------------------------------------------------------
# Step 2 — Validation helpers (pure function tests).
# ---------------------------------------------------------------------------


class TestValidateScalar(unittest.TestCase):
    def test_strips_and_returns(self):
        """_validate_scalar strips whitespace and returns the value."""
        self.assertEqual(constitute_helper._validate_scalar("  hello  ", "f"), "hello")

    def test_empty_raises(self):
        """_validate_scalar raises ValueError on empty string."""
        with self.assertRaises(ValueError) as ctx:
            constitute_helper._validate_scalar("", "myfield")
        self.assertIn("myfield", str(ctx.exception))

    def test_whitespace_only_raises(self):
        """_validate_scalar raises ValueError on whitespace-only string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_scalar("   ", "f")

    def test_valid_value_returned(self):
        """_validate_scalar returns stripped value as-is."""
        self.assertEqual(constitute_helper._validate_scalar("my-project", "f"), "my-project")


class TestValidateEnum(unittest.TestCase):
    def test_canonical_case_accepted(self):
        """_validate_enum accepts canonical-case value directly."""
        result = constitute_helper._validate_enum("greenfield", "mode", constitute_helper.ENUM_FIELDS["mode"])
        self.assertEqual(result, "greenfield")

    def test_uppercase_normalized_to_canonical(self):
        """_validate_enum normalizes uppercase input to canonical case."""
        result = constitute_helper._validate_enum("GREENFIELD", "mode", constitute_helper.ENUM_FIELDS["mode"])
        self.assertEqual(result, "greenfield")

    def test_mixed_case_normalized(self):
        """_validate_enum normalizes mixed-case input."""
        result = constitute_helper._validate_enum("Extracted", "rule_tag", constitute_helper.ENUM_FIELDS["rule_tag"])
        self.assertEqual(result, "extracted")

    def test_unknown_value_raises(self):
        """_validate_enum raises ValueError for unknown value, enumerating allowed."""
        with self.assertRaises(ValueError) as ctx:
            constitute_helper._validate_enum("invalid", "mode", constitute_helper.ENUM_FIELDS["mode"])
        msg = str(ctx.exception)
        self.assertIn("invalid", msg)
        self.assertIn("mode", msg)
        # Stderr enumeration: the allowed values should appear in the message.
        self.assertIn("greenfield", msg)

    def test_empty_raises(self):
        """_validate_enum raises ValueError for empty string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_enum("", "mode", constitute_helper.ENUM_FIELDS["mode"])

    def test_code_label_correct(self):
        """_validate_enum accepts CORRECT for code_label."""
        result = constitute_helper._validate_enum("CORRECT", "code_label", constitute_helper.ENUM_FIELDS["code_label"])
        self.assertEqual(result, "CORRECT")

    def test_code_label_lowercase_normalized(self):
        """_validate_enum normalizes 'correct' → 'CORRECT' for code_label."""
        result = constitute_helper._validate_enum("correct", "code_label", constitute_helper.ENUM_FIELDS["code_label"])
        self.assertEqual(result, "CORRECT")


class TestValidateStringArray(unittest.TestCase):
    def test_comma_separated_basic(self):
        """_validate_string_array parses comma-separated input."""
        result = constitute_helper._validate_string_array("a, b, c", "f")
        self.assertEqual(result, ["a", "b", "c"])

    def test_json_array_basic(self):
        """_validate_string_array parses JSON-array input."""
        result = constitute_helper._validate_string_array('["x", "y"]', "f")
        self.assertEqual(result, ["x", "y"])

    def test_json_array_with_internal_commas(self):
        """_validate_string_array preserves internal commas inside JSON-array items."""
        result = constitute_helper._validate_string_array('["Either<DataError, T>", "Result<Ok, Err>"]', "f")
        self.assertEqual(result, ["Either<DataError, T>", "Result<Ok, Err>"])

    def test_empty_raises(self):
        """_validate_string_array raises ValueError on empty string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_string_array("", "f")

    def test_whitespace_only_item_raises(self):
        """_validate_string_array raises ValueError when an item is whitespace-only."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_string_array("a, , c", "f")

    def test_malformed_json_raises(self):
        """_validate_string_array raises ValueError on malformed JSON-array (bounded by [ and ])."""
        # Must start with [ AND end with ] to trigger JSON-array path.
        # '["unclosed"]' is valid JSON; '[bad]' starts with [ ends with ] but is invalid JSON.
        with self.assertRaises(ValueError) as ctx:
            constitute_helper._validate_string_array('[bad json content]', "f")
        self.assertIn("malformed", str(ctx.exception))

    def test_json_non_string_item_raises(self):
        """_validate_string_array raises ValueError when JSON-array item is not a string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_string_array('[1, 2]', "f")


class TestValidatePathValue(unittest.TestCase):
    def test_valid_path(self):
        """_validate_path_value accepts a valid path string."""
        result = constitute_helper._validate_path_value("src/main.py", "f")
        self.assertEqual(result, "src/main.py")

    def test_empty_raises(self):
        """_validate_path_value raises ValueError on empty string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_path_value("", "f")

    def test_newline_raises(self):
        """_validate_path_value raises ValueError when value contains a newline."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_path_value("src/\nmain.py", "f")


class TestValidateVerbatim(unittest.TestCase):
    def test_empty_raises(self):
        """_validate_verbatim raises ValueError on empty string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_verbatim("", "f")

    def test_whitespace_only_raises(self):
        """_validate_verbatim raises ValueError on whitespace-only string."""
        with self.assertRaises(ValueError):
            constitute_helper._validate_verbatim("   \n  ", "f")

    def test_multiline_preserved(self):
        """_validate_verbatim preserves internal whitespace including leading spaces."""
        text = "  def foo():\n    return 42\n"
        result = constitute_helper._validate_verbatim(text, "f")
        self.assertEqual(result, text)

    def test_single_line_returned(self):
        """_validate_verbatim returns a non-empty single-line value unchanged."""
        self.assertEqual(constitute_helper._validate_verbatim("hello", "f"), "hello")


# ---------------------------------------------------------------------------
# Step 2 — State plumbing tests.
# ---------------------------------------------------------------------------


class TestStatePlumbing(unittest.TestCase):
    def test_state_transaction_writes_on_exit(self):
        """_state_transaction writes state to disk on successful exit."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            with constitute_helper._state_transaction(str(devforge)) as state:
                state["project_name"] = "test-plumbing"
            loaded = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(loaded["project_name"], "test-plumbing")

    def test_state_transaction_abort_on_exception(self):
        """_state_transaction does NOT write state if the body raises."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # First set a known value.
            with constitute_helper._state_transaction(str(devforge)) as state:
                state["project_name"] = "before"
            # Now try a transaction that raises.
            try:
                with constitute_helper._state_transaction(str(devforge)) as state:
                    state["project_name"] = "after-raise"
                    raise RuntimeError("intentional abort")
            except RuntimeError:
                pass
            # State should remain "before" (aborted transaction not written).
            loaded = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(loaded["project_name"], "before")

    def test_lock_file_created(self):
        """_state_transaction creates the .lock sidecar file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            with constitute_helper._state_transaction(str(devforge)) as _state:
                pass
            lock_path = devforge / "constitute.json.lock"
            self.assertTrue(lock_path.exists(), "lock file should be created")

    def test_load_returns_default_state_if_missing(self):
        """_load returns default_state() when constitute.json does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            state = constitute_helper._load(str(devforge))
            self.assertEqual(state, constitute_helper.default_state())

    def test_load_propagates_json_error(self):
        """_load propagates json.JSONDecodeError on malformed JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text("{broken json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                constitute_helper._load(str(devforge))


# ---------------------------------------------------------------------------
# Step 2 — _find_section helper.
# ---------------------------------------------------------------------------


class TestFindSection(unittest.TestCase):
    def _state_with_sections(self):
        state = constitute_helper.default_state()
        for bucket_key, number in [
            ("architecture_rules", "1.1"),
            ("code_quality_standards", "2.1"),
            ("domain_rules", "3.0"),
            ("workflow_rules", "4.5"),
        ]:
            sec = constitute_helper._empty_section()
            sec["number"] = number
            sec["title"] = "Test section {0}".format(number)
            state[bucket_key].append(sec)
        return state

    def test_finds_in_architecture_rules(self):
        """_find_section finds a section in architecture_rules."""
        state = self._state_with_sections()
        bucket, section = constitute_helper._find_section(state, "1.1")
        self.assertIsNotNone(section)
        self.assertEqual(section["number"], "1.1")
        self.assertIs(bucket, state["architecture_rules"])

    def test_finds_in_code_quality_standards(self):
        """_find_section finds a section in code_quality_standards."""
        state = self._state_with_sections()
        _bucket, section = constitute_helper._find_section(state, "2.1")
        self.assertIsNotNone(section)
        self.assertEqual(section["number"], "2.1")

    def test_finds_in_domain_rules(self):
        """_find_section finds a section in domain_rules."""
        state = self._state_with_sections()
        _bucket, section = constitute_helper._find_section(state, "3.0")
        self.assertIsNotNone(section)

    def test_finds_in_workflow_rules(self):
        """_find_section finds a section in workflow_rules."""
        state = self._state_with_sections()
        _bucket, section = constitute_helper._find_section(state, "4.5")
        self.assertIsNotNone(section)

    def test_returns_none_none_when_not_found(self):
        """_find_section returns (None, None) for an unknown section number."""
        state = self._state_with_sections()
        bucket, section = constitute_helper._find_section(state, "99.99")
        self.assertIsNone(bucket)
        self.assertIsNone(section)

    def test_lexical_ordering_note(self):
        """_find_section uses exact string match — '10.1' != '1.0'."""
        state = constitute_helper.default_state()
        sec = constitute_helper._empty_section()
        sec["number"] = "10.1"
        state["architecture_rules"].append(sec)
        _bucket, found = constitute_helper._find_section(state, "10.1")
        self.assertIsNotNone(found)
        _bucket2, not_found = constitute_helper._find_section(state, "1.0")
        self.assertIsNone(not_found)


# ---------------------------------------------------------------------------
# Step 2 — Per-setter subprocess tests.
# ---------------------------------------------------------------------------


class TestSetProjectName(unittest.TestCase):
    def test_happy_path_exit_0(self):
        """set-project-name sets project_name and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-project-name", "--value", "my-project"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["project_name"], "my-project")

    def test_empty_value_exits_2(self):
        """set-project-name exits 2 for empty --value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-project-name", "--value", ""])
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)

    def test_round_trip(self):
        """set-project-name value survives a JSON round-trip."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-project-name", "--value", "  padded  "])
            state = json.loads((devforge / "constitute.json").read_text())
            # Value should be stripped.
            self.assertEqual(state["project_name"], "padded")

    def test_idempotent_overwrite(self):
        """set-project-name called twice overwrites the earlier value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-project-name", "--value", "first"])
            _run(["--devforge-dir", str(devforge), "set-project-name", "--value", "second"])
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["project_name"], "second")


class TestSetMode(unittest.TestCase):
    def test_happy_path_greenfield(self):
        """set-mode accepts 'greenfield'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-mode", "--value", "greenfield"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["mode"], "greenfield")

    def test_case_insensitive_input(self):
        """set-mode normalizes uppercase to canonical."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-mode", "--value", "EXISTING-CODEBASE"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["mode"], "existing-codebase")

    def test_invalid_value_exits_2(self):
        """set-mode exits 2 for an invalid enum value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-mode", "--value", "invalid-mode"])
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)

    def test_round_trip(self):
        """set-mode value survives JSON round-trip."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-mode", "--value", "greenfield"])
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["mode"], "greenfield")


class TestSetDates(unittest.TestCase):
    def test_happy_path(self):
        """set-dates sets both dates and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-dates",
                           "--generated", "2026-05-10", "--updated", "2026-05-11"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["generated_date"], "2026-05-10")
            self.assertEqual(state["last_updated"], "2026-05-11")

    def test_invalid_date_format_exits_2(self):
        """set-dates exits 2 for malformed date."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-dates",
                           "--generated", "not-a-date", "--updated", "2026-05-11"])
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)

    def test_date_with_time_component_exits_2(self):
        """set-dates exits 2 for datetime (time component present)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-dates",
                           "--generated", "2026-05-10T12:00:00", "--updated", "2026-05-11"])
            self.assertEqual(result.returncode, 2)

    def test_round_trip(self):
        """set-dates values survive JSON round-trip."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-dates",
                  "--generated", "2026-01-01", "--updated", "2026-06-30"])
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["generated_date"], "2026-01-01")
            self.assertEqual(state["last_updated"], "2026-06-30")


class TestSetProjectIdentity(unittest.TestCase):
    def test_happy_path(self):
        """set-project-identity sets all 4 subfields and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-project-identity",
                           "--name", "MyApp", "--type", "web-app",
                           "--domain", "e-commerce", "--stack", "TypeScript + Vue"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            pi = state["project_identity"]
            self.assertEqual(pi["name"], "MyApp")
            self.assertEqual(pi["type"], "web-app")
            self.assertEqual(pi["domain"], "e-commerce")
            self.assertEqual(pi["stack"], "TypeScript + Vue")

    def test_empty_field_exits_2(self):
        """set-project-identity exits 2 when a required field is empty."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-project-identity",
                           "--name", "", "--type", "web-app",
                           "--domain", "domain", "--stack", "stack"])
            self.assertEqual(result.returncode, 2)

    def test_replaces_prior_value(self):
        """set-project-identity replaces (not merges with) prior value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-project-identity",
                  "--name", "First", "--type", "t", "--domain", "d", "--stack", "s"])
            _run(["--devforge-dir", str(devforge), "set-project-identity",
                  "--name", "Second", "--type", "t2", "--domain", "d2", "--stack", "s2"])
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["project_identity"]["name"], "Second")
            self.assertEqual(state["project_identity"]["type"], "t2")

    def test_round_trip(self):
        """set-project-identity record survives JSON round-trip."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-project-identity",
                  "--name", "RoundTrip", "--type", "lib",
                  "--domain", "testing", "--stack", "Python"])
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertIsInstance(state["project_identity"], dict)
            self.assertEqual(set(state["project_identity"].keys()), {"name", "type", "domain", "stack"})


class TestAddSection(unittest.TestCase):
    def test_happy_path_architecture(self):
        """add-section adds a section to architecture_rules and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-section",
                           "--bucket", "architecture", "--number", "1.1",
                           "--title", "Layered Architecture"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            sections = state["architecture_rules"]
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0]["number"], "1.1")
            self.assertEqual(sections[0]["title"], "Layered Architecture")
            self.assertEqual(sections[0]["rules"], [])
            self.assertEqual(sections[0]["tables"], [])
            self.assertEqual(sections[0]["code_examples"], [])

    def test_all_4_buckets(self):
        """add-section can target each of the 4 buckets."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            for bucket, number in [
                ("architecture", "1.0"),
                ("code-quality", "2.0"),
                ("domain", "3.0"),
                ("workflow", "4.0"),
            ]:
                result = _run(["--devforge-dir", str(devforge), "add-section",
                               "--bucket", bucket, "--number", number,
                               "--title", "Title {0}".format(number)])
                self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(len(state["architecture_rules"]), 1)
            self.assertEqual(len(state["code_quality_standards"]), 1)
            self.assertEqual(len(state["domain_rules"]), 1)
            self.assertEqual(len(state["workflow_rules"]), 1)

    def test_invalid_section_number_exits_2(self):
        """add-section exits 2 for an invalid section number."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-section",
                           "--bucket", "architecture", "--number", "abc",
                           "--title", "Bad Number"])
            self.assertEqual(result.returncode, 2)

    def test_idempotent_preserves_rules(self):
        """Second add-section with same (bucket, number) replaces metadata but preserves rules."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Create section, then add a rule.
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "architecture", "--number", "1.1",
                  "--title", "Original Title"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "1.1", "--tag", "extracted",
                  "--text", "Always use dependency injection"])
            # Now update the section metadata.
            r = _run(["--devforge-dir", str(devforge), "add-section",
                      "--bucket", "architecture", "--number", "1.1",
                      "--title", "Updated Title"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            sections = state["architecture_rules"]
            # Only one section (idempotent, not appended).
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0]["title"], "Updated Title")
            # Rules preserved.
            self.assertEqual(len(sections[0]["rules"]), 1)
            self.assertEqual(sections[0]["rules"][0]["text"], "Always use dependency injection")

    def test_with_tag_and_description(self):
        """add-section stores optional tag and description."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "architecture", "--number", "2.0",
                  "--title", "Tagged Section",
                  "--tag", "universal",
                  "--description", "This is the description"])
            state = json.loads((devforge / "constitute.json").read_text())
            sec = state["architecture_rules"][0]
            self.assertEqual(sec["tag"], "universal")
            self.assertEqual(sec["description"], "This is the description")


class TestAddRule(unittest.TestCase):
    def _setup_section(self, devforge):
        """Helper: reset + add section 1.1 in architecture bucket."""
        _run(["--devforge-dir", str(devforge), "add-section",
              "--bucket", "architecture", "--number", "1.1",
              "--title", "Test Section"])

    def test_happy_path(self):
        """add-rule appends a rule to a section and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            result = _run(["--devforge-dir", str(devforge), "add-rule",
                           "--section", "1.1", "--tag", "extracted",
                           "--text", "All services must have interfaces"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            rules = state["architecture_rules"][0]["rules"]
            self.assertEqual(len(rules), 1)
            self.assertEqual(rules[0]["tag"], "extracted")
            self.assertEqual(rules[0]["text"], "All services must have interfaces")

    def test_section_not_found_exits_2(self):
        """add-rule exits 2 when section is not found."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-rule",
                           "--section", "99.99", "--tag", "extracted",
                           "--text", "Some rule"])
            self.assertEqual(result.returncode, 2)
            self.assertIn("99.99", result.stderr)

    def test_invalid_tag_exits_2(self):
        """add-rule exits 2 for an invalid rule tag."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            result = _run(["--devforge-dir", str(devforge), "add-rule",
                           "--section", "1.1", "--tag", "bad-tag",
                           "--text", "Some rule"])
            self.assertEqual(result.returncode, 2)

    def test_multiple_rules_appended(self):
        """add-rule appends (not replaces) successive rules."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "1.1", "--tag", "extracted", "--text", "Rule 1"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "1.1", "--tag", "enforced", "--text", "Rule 2"])
            state = json.loads((devforge / "constitute.json").read_text())
            rules = state["architecture_rules"][0]["rules"]
            self.assertEqual(len(rules), 2)
            self.assertEqual(rules[0]["text"], "Rule 1")
            self.assertEqual(rules[1]["text"], "Rule 2")


class TestAddTable(unittest.TestCase):
    def _setup_section(self, devforge):
        _run(["--devforge-dir", str(devforge), "add-section",
              "--bucket", "architecture", "--number", "1.1",
              "--title", "Test Section"])

    def test_happy_path(self):
        """add-table appends a table to a section and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            rows_json = json.dumps([["A", "1"], ["B", "2"]])
            result = _run(["--devforge-dir", str(devforge), "add-table",
                           "--section", "1.1", "--columns", "Name, Value",
                           "--rows-json", rows_json])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            tables = state["architecture_rules"][0]["tables"]
            self.assertEqual(len(tables), 1)
            self.assertEqual(tables[0]["columns"], ["Name", "Value"])
            self.assertEqual(tables[0]["rows"], [["A", "1"], ["B", "2"]])

    def test_columns_json_array_with_internal_comma(self):
        """add-table accepts JSON-array columns with internal commas."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            rows_json = json.dumps([["Either<A, B>"]])
            result = _run(["--devforge-dir", str(devforge), "add-table",
                           "--section", "1.1",
                           "--columns", '["Type<A, B>"]',
                           "--rows-json", rows_json])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            tables = state["architecture_rules"][0]["tables"]
            self.assertEqual(tables[0]["columns"], ["Type<A, B>"])

    def test_mismatched_column_count_exits_2(self):
        """add-table exits 2 when a row has wrong number of cells."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            rows_json = json.dumps([["A", "B", "C"]])  # 3 cells, but 2 columns
            result = _run(["--devforge-dir", str(devforge), "add-table",
                           "--section", "1.1", "--columns", "Name, Value",
                           "--rows-json", rows_json])
            self.assertEqual(result.returncode, 2)

    def test_section_not_found_exits_2(self):
        """add-table exits 2 when section is not found."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-table",
                           "--section", "99.0", "--columns", "A, B",
                           "--rows-json", "[]"])
            self.assertEqual(result.returncode, 2)


class TestAddCodeExample(unittest.TestCase):
    def _setup_section(self, devforge):
        _run(["--devforge-dir", str(devforge), "add-section",
              "--bucket", "domain", "--number", "3.1",
              "--title", "Domain Section"])

    def test_happy_path(self):
        """add-code-example appends a code example and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            result = _run(["--devforge-dir", str(devforge), "add-code-example",
                           "--section", "3.1", "--label", "CORRECT",
                           "--language", "python",
                           "--code", "def foo():\n    return 42"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            examples = state["domain_rules"][0]["code_examples"]
            self.assertEqual(len(examples), 1)
            self.assertEqual(examples[0]["label"], "CORRECT")
            self.assertEqual(examples[0]["language"], "python")
            self.assertIn("return 42", examples[0]["code"])
            self.assertIsNone(examples[0]["annotation"])

    def test_invalid_label_exits_2(self):
        """add-code-example exits 2 for invalid label."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            result = _run(["--devforge-dir", str(devforge), "add-code-example",
                           "--section", "3.1", "--label", "BAD-LABEL",
                           "--language", "python", "--code", "x = 1"])
            self.assertEqual(result.returncode, 2)

    def test_label_case_insensitive(self):
        """add-code-example normalizes lowercase label to canonical uppercase."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section(devforge)
            result = _run(["--devforge-dir", str(devforge), "add-code-example",
                           "--section", "3.1", "--label", "wrong",
                           "--language", "python", "--code", "x = bad()"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["domain_rules"][0]["code_examples"][0]["label"], "WRONG")

    def test_section_not_found_exits_2(self):
        """add-code-example exits 2 when section is not found."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-code-example",
                           "--section", "99.0", "--label", "EXAMPLE",
                           "--language", "python", "--code", "pass"])
            self.assertEqual(result.returncode, 2)


class TestAddPatternRule(unittest.TestCase):
    def test_happy_path_always_universal(self):
        """add-pattern-rule adds to always_universal bucket."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                           "--bucket", "always", "--scope", "universal",
                           "--tag", "enforced", "--text", "Use composition over inheritance"])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            rules = state["patterns_and_antipatterns"]["always_universal"]
            self.assertEqual(len(rules), 1)
            self.assertEqual(rules[0]["text"], "Use composition over inheritance")

    def test_all_6_pattern_buckets(self):
        """add-pattern-rule can target all 6 patterns_and_antipatterns buckets."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            combos = [
                ("always", "universal"),
                ("always", "project-specific"),
                ("never", "universal"),
                ("never", "project-specific"),
                ("prefer", "universal"),
                ("prefer", "project-specific"),
            ]
            for bucket, scope in combos:
                result = _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                               "--bucket", bucket, "--scope", scope,
                               "--tag", "extracted",
                               "--text", "Rule for {0} {1}".format(bucket, scope)])
                self.assertEqual(result.returncode, 0,
                                 "failed for {0}/{1}: {2}".format(bucket, scope, result.stderr))
            state = json.loads((devforge / "constitute.json").read_text())
            pap = state["patterns_and_antipatterns"]
            for key in ["always_universal", "always_project_specific",
                        "never_universal", "never_project_specific",
                        "prefer_universal", "prefer_project_specific"]:
                self.assertEqual(len(pap[key]), 1, "bucket {0} should have 1 rule".format(key))

    def test_invalid_bucket_exits_2(self):
        """add-pattern-rule exits 2 for unknown bucket."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                           "--bucket", "sometimes", "--scope", "universal",
                           "--tag", "extracted", "--text", "text"])
            # argparse will catch choices mismatch
            self.assertNotEqual(result.returncode, 0)

    def test_scope_project_specific_key(self):
        """add-pattern-rule maps 'project-specific' scope to underscore key."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                  "--bucket", "never", "--scope", "project-specific",
                  "--tag", "enforced", "--text", "Never use global state"])
            state = json.loads((devforge / "constitute.json").read_text())
            rules = state["patterns_and_antipatterns"]["never_project_specific"]
            self.assertEqual(len(rules), 1)
            self.assertEqual(rules[0]["text"], "Never use global state")


class TestSetScaffoldingGuide(unittest.TestCase):
    def _sample_files_json(self):
        return json.dumps([
            {"path": "src/main.py", "language": "python", "content": "# main entry"},
            {"path": "src/utils.py", "language": "python", "content": "# utilities"},
        ])

    def test_happy_path(self):
        """set-scaffolding-guide sets the record and exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                           "--starter-dirs", "src, tests, docs",
                           "--sample-files-json", self._sample_files_json()])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            sg = state["scaffolding_guide"]
            self.assertIsNotNone(sg)
            self.assertEqual(sg["starter_directories"], ["src", "tests", "docs"])
            self.assertEqual(len(sg["sample_files"]), 2)
            self.assertEqual(sg["sample_files"][0]["path"], "src/main.py")

    def test_starter_dirs_json_array_form(self):
        """set-scaffolding-guide accepts JSON-array form for starter-dirs with internal commas."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dirs_json = '["src/components", "src/utils"]'
            result = _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                           "--starter-dirs", dirs_json,
                           "--sample-files-json", self._sample_files_json()])
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((devforge / "constitute.json").read_text())
            self.assertEqual(state["scaffolding_guide"]["starter_directories"],
                             ["src/components", "src/utils"])

    def test_missing_sample_file_key_exits_2(self):
        """set-scaffolding-guide exits 2 when a sample file is missing a required key."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            bad_json = json.dumps([{"path": "x.py"}])  # missing language + content
            result = _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                           "--starter-dirs", "src",
                           "--sample-files-json", bad_json])
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)

    def test_replaces_prior_value(self):
        """set-scaffolding-guide replaces (not merges with) prior value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                  "--starter-dirs", "old",
                  "--sample-files-json", self._sample_files_json()])
            _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                  "--starter-dirs", "new",
                  "--sample-files-json", "[]"])
            state = json.loads((devforge / "constitute.json").read_text())
            sg = state["scaffolding_guide"]
            self.assertEqual(sg["starter_directories"], ["new"])
            self.assertEqual(sg["sample_files"], [])


# ---------------------------------------------------------------------------
# Step 2 — Cross-process safety tests.
# ---------------------------------------------------------------------------


class TestCrossProcessSafety(unittest.TestCase):
    def test_concurrent_add_rule_no_lost_appends(self):
        """5 concurrent add-rule calls to same section produce 5 rules (no lost writes)."""
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Set up the section first.
            r = _run(["--devforge-dir", str(devforge), "add-section",
                      "--bucket", "architecture", "--number", "1.1",
                      "--title", "Concurrent Section"])
            self.assertEqual(r.returncode, 0, r.stderr)

            procs = []
            for i in range(5):
                p = subprocess.Popen(
                    [sys.executable, str(_HELPER_PY),
                     "--devforge-dir", str(devforge),
                     "add-rule", "--section", "1.1",
                     "--tag", "extracted",
                     "--text", "Concurrent rule {0}".format(i)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                procs.append(p)

            for p in procs:
                p.wait(timeout=30)
                self.assertEqual(p.returncode, 0, p.stderr.read() if hasattr(p.stderr, 'read') else "")

            state = json.loads((devforge / "constitute.json").read_text())
            rules = state["architecture_rules"][0]["rules"]
            self.assertEqual(len(rules), 5, "Expected 5 rules, got: {0}".format(len(rules)))

    def test_concurrent_scalar_set_no_corruption(self):
        """Concurrent set-project-name calls produce a valid (non-corrupted) JSON file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            procs = []
            for i in range(5):
                p = subprocess.Popen(
                    [sys.executable, str(_HELPER_PY),
                     "--devforge-dir", str(devforge),
                     "set-project-name", "--value", "project-{0}".format(i)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                procs.append(p)

            for p in procs:
                p.wait(timeout=30)

            # File must be valid JSON (no corruption).
            text = (devforge / "constitute.json").read_text()
            state = json.loads(text)  # raises on corruption
            # project_name must be one of the values we set.
            self.assertIn(state["project_name"],
                          ["project-{0}".format(i) for i in range(5)])

    def test_add_rule_before_section_exits_2(self):
        """add-rule before add-section for that section exits 2 with stderr."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # No add-section called first.
            result = _run(["--devforge-dir", str(devforge), "add-rule",
                           "--section", "9.9", "--tag", "extracted",
                           "--text", "Rule without section"])
            self.assertEqual(result.returncode, 2)
            self.assertIn("9.9", result.stderr)

    def test_mixed_set_and_add_no_corruption(self):
        """Concurrent scalar set and array add produce valid JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Set up section first.
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "workflow", "--number", "4.0",
                  "--title", "Workflow"])

            procs = []
            for i in range(3):
                procs.append(subprocess.Popen(
                    [sys.executable, str(_HELPER_PY),
                     "--devforge-dir", str(devforge),
                     "set-project-name", "--value", "name-{0}".format(i)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ))
                procs.append(subprocess.Popen(
                    [sys.executable, str(_HELPER_PY),
                     "--devforge-dir", str(devforge),
                     "add-rule", "--section", "4.0",
                     "--tag", "extracted", "--text", "rule-{0}".format(i)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ))

            for p in procs:
                p.wait(timeout=30)

            # File must be valid JSON.
            text = (devforge / "constitute.json").read_text()
            state = json.loads(text)
            # Rules: at least some appended (race means count may vary from 0–3).
            rules = state["workflow_rules"][0]["rules"]
            self.assertIsInstance(rules, list)

    def test_concurrent_add_rule_exit_codes_all_zero(self):
        """All concurrent add-rule processes exit 0 (no process fails under lock)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "domain", "--number", "5.0", "--title", "D"])

            procs = []
            for i in range(5):
                p = subprocess.Popen(
                    [sys.executable, str(_HELPER_PY),
                     "--devforge-dir", str(devforge),
                     "add-rule", "--section", "5.0",
                     "--tag", "extracted", "--text", "rule-{0}".format(i)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                procs.append(p)

            return_codes = [p.wait(timeout=30) for p in procs]
            self.assertEqual(return_codes, [0] * 5)


# ---------------------------------------------------------------------------
# Step 2 — Round-trip integration tests.
# ---------------------------------------------------------------------------


class TestRoundTripIntegration(unittest.TestCase):
    def test_all_scalar_fields_set_and_reload(self):
        """Set project_name, mode, dates; reload via _load; compare."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-project-name", "--value", "integration-test"])
            _run(["--devforge-dir", str(devforge), "set-mode", "--value", "greenfield"])
            _run(["--devforge-dir", str(devforge), "set-dates",
                  "--generated", "2026-05-10", "--updated", "2026-05-10"])
            state = constitute_helper._load(str(devforge))
            self.assertEqual(state["project_name"], "integration-test")
            self.assertEqual(state["mode"], "greenfield")
            self.assertEqual(state["generated_date"], "2026-05-10")

    def test_all_4_add_section_buckets_loaded(self):
        """All 4 section buckets can be populated and reloaded."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            for bucket, number in [
                ("architecture", "1.0"),
                ("code-quality", "2.0"),
                ("domain", "3.0"),
                ("workflow", "4.0"),
            ]:
                _run(["--devforge-dir", str(devforge), "add-section",
                      "--bucket", bucket, "--number", number,
                      "--title", "Section {0}".format(number)])
            state = constitute_helper._load(str(devforge))
            self.assertEqual(len(state["architecture_rules"]), 1)
            self.assertEqual(len(state["code_quality_standards"]), 1)
            self.assertEqual(len(state["domain_rules"]), 1)
            self.assertEqual(len(state["workflow_rules"]), 1)

    def test_all_6_pattern_buckets_populated(self):
        """All 6 patterns_and_antipatterns buckets can be populated."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            combos = [
                ("always", "universal"),
                ("always", "project-specific"),
                ("never", "universal"),
                ("never", "project-specific"),
                ("prefer", "universal"),
                ("prefer", "project-specific"),
            ]
            for bucket, scope in combos:
                _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                      "--bucket", bucket, "--scope", scope,
                      "--tag", "extracted",
                      "--text", "Rule for {0} {1}".format(bucket, scope)])
            state = constitute_helper._load(str(devforge))
            for key in ["always_universal", "always_project_specific",
                        "never_universal", "never_project_specific",
                        "prefer_universal", "prefer_project_specific"]:
                self.assertEqual(len(state["patterns_and_antipatterns"][key]), 1)

    def test_scaffolding_guide_set_and_reset(self):
        """set-scaffolding-guide replaces on second call (no stale data)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            files1 = json.dumps([{"path": "a.py", "language": "python", "content": "# a"}])
            _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                  "--starter-dirs", "src", "--sample-files-json", files1])
            # Reset with empty sample files.
            _run(["--devforge-dir", str(devforge), "set-scaffolding-guide",
                  "--starter-dirs", "new_src", "--sample-files-json", "[]"])
            state = constitute_helper._load(str(devforge))
            self.assertEqual(state["scaffolding_guide"]["starter_directories"], ["new_src"])
            self.assertEqual(state["scaffolding_guide"]["sample_files"], [])

    def test_add_section_idempotency_preserves_rules_round_trip(self):
        """add-section idempotency: rules survive a metadata-update round-trip."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "code-quality", "--number", "2.1",
                  "--title", "Original"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "2.1", "--tag", "enforced",
                  "--text", "Max function length: 50 lines"])
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "code-quality", "--number", "2.1",
                  "--title", "Updated"])
            state = constitute_helper._load(str(devforge))
            secs = state["code_quality_standards"]
            self.assertEqual(len(secs), 1)
            self.assertEqual(secs[0]["title"], "Updated")
            self.assertEqual(secs[0]["rules"][0]["text"], "Max function length: 50 lines")


# ---------------------------------------------------------------------------
# Step 3 helpers.
# ---------------------------------------------------------------------------


def _fully_populated_state():
    """Return a state dict with all required fields populated.

    Includes one architecture section with a rule, table, and code example;
    one code-quality section with a tag; patterns in all 6 buckets;
    domain + workflow sections.
    """
    state = constitute_helper.default_state()
    state["project_name"] = "acme-api"
    state["generated_date"] = "2026-05-10"
    state["last_updated"] = "2026-05-10"
    state["mode"] = "existing-codebase"
    state["project_identity"] = {
        "name": "acme-api",
        "type": "Backend API",
        "domain": "E-commerce",
        "stack": "Python + FastAPI",
    }
    state["architecture_rules"] = [
        {
            "number": "2.1",
            "title": "Layer Boundaries",
            "tag": None,
            "description": "Clean architecture layers.",
            "rules": [
                {"tag": "extracted", "text": "Domain layer has zero deps."},
                {"tag": "enforced", "text": "No circular imports."},
            ],
            "tables": [
                {
                    "columns": ["Layer", "Path"],
                    "rows": [["domain", "src/domain"], ["data", "src/data"]],
                }
            ],
            "code_examples": [
                {
                    "label": "CORRECT",
                    "language": "python",
                    "code": "from domain import Entity\n",
                    "annotation": "Correct import direction",
                },
                {
                    "label": "WRONG",
                    "language": "python",
                    "code": "from data import Repo  # FORBIDDEN\n",
                    "annotation": None,
                },
            ],
        }
    ]
    state["code_quality_standards"] = [
        {
            "number": "3.1",
            "title": "Type Safety",
            "tag": "project-specific",
            "description": None,
            "rules": [{"tag": "enforced", "text": "strict: true in tsconfig"}],
            "tables": [],
            "code_examples": [],
        }
    ]
    pat = state["patterns_and_antipatterns"]
    pat["always_universal"] = [{"tag": "universal", "text": "Read before write."}]
    pat["always_project_specific"] = [{"tag": "extracted", "text": "Use Either for errors."}]
    pat["never_universal"] = [{"tag": "universal", "text": "Never commit secrets."}]
    pat["never_project_specific"] = [{"tag": "project-specific", "text": "No raw any types."}]
    pat["prefer_universal"] = [{"tag": "universal", "text": "Prefer explicit over implicit."}]
    pat["prefer_project_specific"] = [{"tag": "extracted", "text": "Prefer purify-ts Either."}]
    state["domain_rules"] = [
        {
            "number": "5.1",
            "title": "Entity Rules",
            "tag": None,
            "description": None,
            "rules": [{"tag": "extracted", "text": "Entities are immutable."}],
            "tables": [],
            "code_examples": [],
        }
    ]
    state["workflow_rules"] = [
        {
            "number": "6.1",
            "title": "PR Rules",
            "tag": None,
            "description": None,
            "rules": [{"tag": "enforced", "text": "No PRs without tests."}],
            "tables": [],
            "code_examples": [],
        }
    ]
    return state


def _run_render(devforge_dir, install_root):
    return _run([
        "--devforge-dir", str(devforge_dir),
        "--install-root", str(install_root),
        "render",
    ])


def _run_verify(devforge_dir, install_root=None):
    argv = ["--devforge-dir", str(devforge_dir)]
    if install_root:
        argv += ["--install-root", str(install_root)]
    argv.append("verify")
    return _run(argv)


def _run_summary(devforge_dir):
    return _run(["--devforge-dir", str(devforge_dir), "summary"])


def _write_state_for_test(devforge_dir, state):
    """Write state dict directly as constitute.json for test setup."""
    devforge_dir = Path(devforge_dir)
    devforge_dir.mkdir(parents=True, exist_ok=True)
    target = devforge_dir / "constitute.json"
    target.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 3 — render tests.
# ---------------------------------------------------------------------------


class TestStep3Render(unittest.TestCase):
    def test_render_fully_populated_contains_all_headers(self):
        """Fully populated state → constitution.md contains H2 sections 1-6."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            constitution = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("## 1. Project Identity", constitution)
            self.assertIn("## 2. Architecture Rules (NON-NEGOTIABLE)", constitution)
            self.assertIn("## 3. Code Quality Standards", constitution)
            self.assertIn("## 4. Patterns & Anti-Patterns", constitution)
            self.assertIn("## 5. Domain Rules", constitution)
            self.assertIn("## 6. Workflow Rules", constitution)

    def test_render_greenfield_with_scaffolding_includes_section_7(self):
        """Greenfield mode + scaffolding_guide → Section 7 present."""
        state = _fully_populated_state()
        state["mode"] = "greenfield"
        state["scaffolding_guide"] = {
            "starter_directories": ["src", "tests"],
            "sample_files": [
                {"path": "src/main.py", "language": "python", "content": "# main\n"}
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            constitution = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("## 7. Scaffolding Guide [greenfield-only]", constitution)
            self.assertIn("src/main.py", constitution)
            self.assertIn("```python", constitution)

    def test_render_existing_codebase_no_section_7(self):
        """existing-codebase mode → Section 7 absent."""
        state = _fully_populated_state()
        state["mode"] = "existing-codebase"
        state["scaffolding_guide"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            constitution = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertNotIn("## 7.", constitution)

    def test_render_empty_section_bucket_shows_empty_marker(self):
        """Empty section bucket → _(no rules defined)_ marker."""
        state = _fully_populated_state()
        state["domain_rules"] = []
        state["workflow_rules"] = []
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            constitution = (install_root / "constitution.md").read_text(encoding="utf-8")
            # Both domain and workflow should show empty marker
            self.assertIn("_(no rules defined)_", constitution)

    def test_render_section_with_description_rules_table_code_example(self):
        """Section with all sub-elements → each rendered correctly."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("### 2.1 Layer Boundaries", text)
            self.assertIn("Clean architecture layers.", text)
            self.assertIn("- [extracted] Domain layer has zero deps.", text)
            self.assertIn("- [enforced] No circular imports.", text)
            # Table rendered
            self.assertIn("| Layer | Path |", text)
            self.assertIn("| domain | src/domain |", text)
            # Code example with annotation
            self.assertIn("**CORRECT** — Correct import direction", text)
            self.assertIn("```python", text)
            self.assertIn("from domain import Entity", text)
            # Code example without annotation
            self.assertIn("**WRONG**\n", text)
            self.assertIn("from data import Repo  # FORBIDDEN", text)

    def test_render_table_2col_and_3col(self):
        """Tables with 2 and 3 columns render GFM correctly."""
        state = _fully_populated_state()
        state["architecture_rules"][0]["tables"] = [
            {
                "columns": ["Col1", "Col2", "Col3"],
                "rows": [["a", "b, with comma", "c"]],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("| Col1 | Col2 | Col3 |", text)
            # Internal comma in cell preserved
            self.assertIn("| a | b, with comma | c |", text)

    def test_render_code_example_without_annotation(self):
        """Code example with annotation=None → no dash-annotation in output."""
        state = _fully_populated_state()
        state["architecture_rules"][0]["code_examples"] = [
            {"label": "EXAMPLE", "language": "python", "code": "x = 1\n", "annotation": None}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("**EXAMPLE**\n", text)
            self.assertNotIn("**EXAMPLE** —", text)

    def test_render_all_6_pattern_buckets(self):
        """All 6 pattern buckets appear in Section 4."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("### Always Do (Universal)", text)
            self.assertIn("### Always Do (Project-Specific)", text)
            self.assertIn("### Never Do (Universal)", text)
            self.assertIn("### Never Do (Project-Specific)", text)
            self.assertIn("### Prefer (Universal)", text)
            self.assertIn("### Prefer (Project-Specific)", text)

    def test_render_missing_required_field_exits_2(self):
        """Missing required field → exit 2 with stderr listing it."""
        state = _fully_populated_state()
        state["project_name"] = None  # Remove required field
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("project_name", result.stderr)

    def test_render_missing_state_file_exits_2(self):
        """State file missing (default state has no required fields set) → exits 2 (missing fields)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            # Don't write any state — _load returns default_state with all nulls
            result = _run_render(devforge, install_root)
            # Missing required fields → exit 2
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("project_name", result.stderr)

    def test_render_atomic_write_no_temp_file_left(self):
        """After successful render, no .tmp files remain in install_root."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            tmp_files = list(Path(install_root).glob("*.tmp"))
            self.assertEqual(tmp_files, [], "Temp files not cleaned up: {0}".format(tmp_files))

    def test_render_idempotent_byte_identical(self):
        """Two consecutive renders produce byte-identical output."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            r1 = _run_render(devforge, install_root)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first_bytes = (install_root / "constitution.md").read_bytes()
            r2 = _run_render(devforge, install_root)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second_bytes = (install_root / "constitution.md").read_bytes()
            self.assertEqual(first_bytes, second_bytes)

    def test_render_rule_text_with_internal_comma_preserved(self):
        """Rule text containing TS generic syntax (internal commas) renders verbatim."""
        state = _fully_populated_state()
        rule_text = "Use Either<DataError, T> for fallible operations, never throw."
        state["architecture_rules"][0]["rules"] = [{"tag": "extracted", "text": rule_text}]
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("Either<DataError, T>", text)
            self.assertIn("operations, never throw", text)

    def test_render_code_example_multiline_whitespace_preserved(self):
        """Multi-line code example preserves internal indentation verbatim."""
        state = _fully_populated_state()
        code = "def foo():\n    if x:\n        return 42\n    return 0\n"
        state["architecture_rules"][0]["code_examples"] = [{
            "label": "CORRECT",
            "language": "python",
            "code": code,
            "annotation": None,
        }]
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("    if x:\n        return 42", text)

    def test_render_code_quality_section_includes_tag_suffix(self):
        """Code Quality section title includes [tag] suffix when tag is set."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            install_root = Path(tmp)
            _write_state_for_test(devforge, state)
            result = _run_render(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = (install_root / "constitution.md").read_text(encoding="utf-8")
            # code_quality_standards section 3.1 has tag=project-specific
            self.assertIn("### 3.1 Type Safety [project-specific]", text)


# ---------------------------------------------------------------------------
# Step 3 — verify tests.
# ---------------------------------------------------------------------------


class TestStep3Verify(unittest.TestCase):
    def test_verify_fully_populated_exits_0(self):
        """Fully populated state → verify exits 0 with 'verify: ok' on stderr."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("verify: ok", result.stderr)

    def test_verify_missing_required_scalar_exits_2(self):
        """Missing required scalar → exit 2, stderr names the field."""
        state = _fully_populated_state()
        state["generated_date"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("generated_date", result.stderr)

    def test_verify_bad_rule_tag_exits_2(self):
        """Section rule with bad tag → exit 2 with description."""
        state = _fully_populated_state()
        state["architecture_rules"][0]["rules"][0]["tag"] = "INVALID_TAG"
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("INVALID_TAG", result.stderr)

    def test_verify_section_missing_title_exits_2(self):
        """Section missing title → exit 2."""
        state = _fully_populated_state()
        state["architecture_rules"][0]["title"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("title", result.stderr)

    def test_verify_pattern_bucket_bad_tag_exits_2(self):
        """Pattern bucket rule with bad tag → exit 2."""
        state = _fully_populated_state()
        state["patterns_and_antipatterns"]["always_universal"][0]["tag"] = "bad-tag"
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("bad-tag", result.stderr)

    def test_verify_table_mismatched_row_col_count_exits_2(self):
        """Table row with wrong cell count → exit 2."""
        state = _fully_populated_state()
        state["architecture_rules"][0]["tables"][0]["rows"] = [
            ["only_one_cell"]  # columns has 2 entries: Layer, Path
        ]
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("cells", result.stderr)

    def test_verify_scaffolding_malformed_sample_file_exits_2(self):
        """ScaffoldingGuide with missing required key → exit 2."""
        state = _fully_populated_state()
        state["mode"] = "greenfield"
        state["scaffolding_guide"] = {
            "starter_directories": ["src"],
            "sample_files": [{"path": "main.py"}],  # missing language + content
        }
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("missing keys", result.stderr)

    def test_verify_scaffolding_null_in_existing_codebase_ok(self):
        """scaffolding_guide null in existing-codebase mode → exit 0 (acceptable)."""
        state = _fully_populated_state()
        state["mode"] = "existing-codebase"
        state["scaffolding_guide"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_verify_scaffolding_null_in_greenfield_exits_2(self):
        """scaffolding_guide null in greenfield mode → exit 2 (required)."""
        state = _fully_populated_state()
        state["mode"] = "greenfield"
        state["scaffolding_guide"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("greenfield", result.stderr)

    def test_verify_round_trip_identity(self):
        """Verify performs round-trip: project_name and section count match."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("verify: ok", result.stderr)

    def test_verify_clean_forcing_functions_exits_0(self):
        """Fully populated state with valid forcing_functions → verify exits 0."""
        state = _fully_populated_state()
        state["forcing_functions"] = {
            "magic_enum_duplication": {
                "enabled": True,
                "generated_types_dirs": ["packages/types/src"],
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("verify: ok", result.stderr)

    def test_verify_absent_forcing_functions_exits_0(self):
        """State without forcing_functions key → verify exits 0 (block is optional)."""
        state = _fully_populated_state()
        # forcing_functions key entirely absent — validate_forcing_functions(None) = []
        state.pop("forcing_functions", None)
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("verify: ok", result.stderr)

    def test_verify_malformed_forcing_functions_exits_2(self):
        """State with malformed forcing_functions block → verify exits 2, stderr names the field."""
        state = _fully_populated_state()
        state["forcing_functions"] = {
            "magic_enum_duplication": {
                "enabled": True,
                # missing generated_types_dirs → validate_forcing_functions raises error
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_verify(devforge)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("generated_types_dirs", result.stderr)


# ---------------------------------------------------------------------------
# Step 3 — summary tests.
# ---------------------------------------------------------------------------


class TestStep3Summary(unittest.TestCase):
    def test_summary_all_unset_shows_unset_markers(self):
        """All-unset state → '(unset)' in every relevant line."""
        state = constitute_helper.default_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("(unset)", result.stdout)
            self.assertIn("Project Name:        (unset)", result.stdout)
            self.assertIn("Generated:           (unset)", result.stdout)
            self.assertIn("Last Updated:        (unset)", result.stdout)
            self.assertIn("Mode:                (unset)", result.stdout)

    def test_summary_fully_populated_shows_values(self):
        """Fully populated state → values shown."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("acme-api", result.stdout)
            self.assertIn("2026-05-10", result.stdout)
            self.assertIn("existing-codebase", result.stdout)

    def test_summary_section_count_and_per_section_line(self):
        """Section count and per-section detail line appear in output."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Architecture Rules:  1 sections", result.stdout)
            self.assertIn("2.1 Layer Boundaries: 2 rules, 1 tables, 2 code examples", result.stdout)

    def test_summary_all_6_pattern_buckets_shown(self):
        """All 6 pattern bucket counts appear in summary."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Always (Universal):         1 rules", result.stdout)
            self.assertIn("Always (Project-Specific):  1 rules", result.stdout)
            self.assertIn("Never (Universal):          1 rules", result.stdout)
            self.assertIn("Never (Project-Specific):   1 rules", result.stdout)
            self.assertIn("Prefer (Universal):         1 rules", result.stdout)
            self.assertIn("Prefer (Project-Specific):  1 rules", result.stdout)

    def test_summary_stable_across_reruns(self):
        """Running summary twice produces identical output."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            r1 = _run_summary(devforge)
            r2 = _run_summary(devforge)
            self.assertEqual(r1.stdout, r2.stdout)

    def test_summary_scaffolding_unset(self):
        """Scaffolding guide unset → 'unset' in summary."""
        state = _fully_populated_state()
        state["scaffolding_guide"] = None
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scaffolding Guide:   unset", result.stdout)

    def test_summary_scaffolding_set(self):
        """Scaffolding guide set → 'set' with counts in summary."""
        state = _fully_populated_state()
        state["scaffolding_guide"] = {
            "starter_directories": ["src", "tests"],
            "sample_files": [{"path": "main.py", "language": "python", "content": "# hi"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scaffolding Guide:   set", result.stdout)
            self.assertIn("Starter Dirs:      2", result.stdout)
            self.assertIn("Sample Files:      1", result.stdout)

    def test_summary_returns_exit_0(self):
        """Summary always exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # No state file — uses defaults
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 0)

    def test_summary_output_to_stdout_not_stderr(self):
        """Summary output goes to stdout; stderr is empty on success."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_summary(devforge)
            self.assertNotEqual(result.stdout, "", "Expected stdout output")
            self.assertIn("## Constitute Helper Summary", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_summary_corrupted_json_exits_1(self):
        """Corrupted constitute.json exits 1 with stderr message (matches init/configure)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir(parents=True, exist_ok=True)
            (devforge / "constitute.json").write_text("{not valid json", encoding="utf-8")
            result = _run_summary(devforge)
            self.assertEqual(result.returncode, 1)
            self.assertIn("cannot load constitute.json", result.stderr)


# ---------------------------------------------------------------------------
# Step 4 — validate tests (4-dimension quality framework).
# ---------------------------------------------------------------------------


def _run_validate(devforge_dir, install_root=None):
    """Run constitute_helper validate; install_root defaults to parent of devforge_dir."""
    argv = ["--devforge-dir", str(devforge_dir)]
    if install_root is not None:
        argv += ["--install-root", str(install_root)]
    argv.append("validate")
    return _run(argv)


class TestStep4SlotFill(unittest.TestCase):
    """Slot-fill rate (dim 1) — 6 tests."""

    def test_slot_fill_fully_populated_existing_codebase(self):
        """Fully-populated existing-codebase state → slot_fill score == 1.0 (9/9)."""
        state = _fully_populated_state()
        filled, total, failed = constitute_helper._count_slot_fill(state)
        self.assertEqual(total, 9)
        self.assertEqual(filled, 9)
        self.assertAlmostEqual(filled / total, 1.0)
        self.assertEqual(failed, [])

    def test_slot_fill_missing_project_identity_subfield(self):
        """Missing 1 of 4 project_identity subfields → 8/9 = 0.888."""
        state = _fully_populated_state()
        # Remove one subfield (domain).
        state["project_identity"]["domain"] = None
        filled, total, failed = constitute_helper._count_slot_fill(state)
        self.assertEqual(total, 9)
        self.assertEqual(filled, 8)
        self.assertAlmostEqual(filled / total, 8 / 9)
        self.assertTrue(any("domain" in f for f in failed))

    def test_slot_fill_empty_section_5_domain_rules(self):
        """Empty domain_rules → 8/9 = 0.888."""
        state = _fully_populated_state()
        state["domain_rules"] = []
        filled, total, failed = constitute_helper._count_slot_fill(state)
        self.assertEqual(total, 9)
        self.assertEqual(filled, 8)
        self.assertTrue(any("domain_rules" in f for f in failed))

    def test_slot_fill_greenfield_with_scaffolding_present(self):
        """Greenfield mode + scaffolding present → 10/10 = 1.0."""
        state = _fully_populated_state()
        state["mode"] = "greenfield"
        state["scaffolding_guide"] = {
            "starter_directories": ["src"],
            "sample_files": [],
        }
        filled, total, failed = constitute_helper._count_slot_fill(state)
        self.assertEqual(total, 10)
        self.assertEqual(filled, 10)
        self.assertEqual(failed, [])

    def test_slot_fill_greenfield_without_scaffolding(self):
        """Greenfield mode + no scaffolding content → 9/10 = 0.9."""
        state = _fully_populated_state()
        state["mode"] = "greenfield"
        state["scaffolding_guide"] = {
            "starter_directories": [],
            "sample_files": [],
        }
        filled, total, failed = constitute_helper._count_slot_fill(state)
        self.assertEqual(total, 10)
        self.assertEqual(filled, 9)
        self.assertTrue(any("scaffolding_guide" in f for f in failed))

    def test_slot_fill_existing_codebase_ignores_section_7(self):
        """Existing-codebase mode → section 7 slot NOT counted (total=9)."""
        state = _fully_populated_state()
        state["mode"] = "existing-codebase"
        state["scaffolding_guide"] = None
        filled, total, failed = constitute_helper._count_slot_fill(state)
        # Section 7 not counted, so total is 9 and 9/9 filled.
        self.assertEqual(total, 9)
        self.assertEqual(filled, 9)


class TestStep4CitationValidity(unittest.TestCase):
    """Citation validity (dim 2) — 6 tests."""

    def test_citation_rule_refs_real_file_resolves(self):
        """Rule referencing a real file (created in tmpdir) → score 1.0."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            # Create the referenced file.
            ref_file = install_root / "src" / "domain" / "entity.py"
            ref_file.parent.mkdir(parents=True, exist_ok=True)
            ref_file.write_text("# entity\n", encoding="utf-8")

            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [{"tag": "extracted", "text": "See src/domain/entity.py for entities."}],
                "tables": [], "code_examples": [],
            }]
            devforge = install_root / ".devforge"
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            self.assertAlmostEqual(score, 1.0)
            self.assertEqual(unresolved, 0)

    def test_citation_rule_refs_nonexistent_path(self):
        """Rule referencing a non-existent path → score 0.0."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [{"tag": "extracted", "text": "See missing/file.py always."}],
                "tables": [], "code_examples": [],
            }]
            devforge = install_root / ".devforge"
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            self.assertAlmostEqual(score, 0.0)
            self.assertEqual(resolved, 0)
            self.assertTrue(len(failed) > 0)

    def test_citation_no_path_tokens_is_na(self):
        """Rule with no path-like tokens → N/A (score 1.0, zero extracted)."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [{"tag": "extracted", "text": "Always read before write."}],
                "tables": [], "code_examples": [],
            }]
            devforge = install_root / ".devforge"
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            self.assertAlmostEqual(score, 1.0)
            self.assertEqual(resolved, 0)
            self.assertEqual(unresolved, 0)

    def test_citation_mix_resolved_and_unresolved(self):
        """Mix of resolved + unresolved paths → fractional score."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            # Create one real file.
            real_file = install_root / "real.py"
            real_file.write_text("# real\n", encoding="utf-8")

            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [
                    {"tag": "extracted", "text": "See real.py for pattern."},
                    {"tag": "extracted", "text": "See missing.py for antipattern."},
                ],
                "tables": [], "code_examples": [],
            }]
            devforge = install_root / ".devforge"
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            self.assertEqual(resolved, 1)
            self.assertEqual(unresolved, 1)
            self.assertAlmostEqual(score, 0.5)

    def test_citation_package_name_lookup_via_init_yaml(self):
        """Package directory resolved via pkg_map from init.yaml.

        Asserts the package-name lookup mechanism end-to-end:
        1) _build_package_name_map populates the map from init.yaml.
        2) A rule citing a path inside the package dir resolves
           (direct existence check; no pkg_map lookup needed).
        3) Score is exactly 1.0 (resolved == 1, unresolved == 0).
        """
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            pkg_dir = install_root / "packages" / "my-lib"
            pkg_dir.mkdir(parents=True)
            devforge = install_root / ".devforge"
            devforge.mkdir()
            # Hand-write minimal init.yaml matching init_helper's emit shape.
            (devforge / "init.yaml").write_text(
                "workspace_mode: standalone\n"
                "project_root: \".\"\n"
                "project_state: brownfield\n"
                "default_branch: main\n"
                "packages_detected:\n"
                "  - path: packages/my-lib\n"
                "    manifest: package.json\n",
                encoding="utf-8",
            )
            # Verify pkg_map mechanism directly.
            pkg_map = constitute_helper._build_package_name_map(
                devforge / "init.yaml"
            )
            self.assertIn("my-lib", pkg_map)
            self.assertEqual(pkg_map["my-lib"], "packages/my-lib")

            # Cite a real file inside the package — direct resolution.
            (pkg_dir / "index.ts").write_text("export {};\n", encoding="utf-8")
            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [{"tag": "extracted",
                           "text": "See packages/my-lib/index.ts for setup."}],
                "tables": [], "code_examples": [],
            }]
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            self.assertEqual(resolved, 1)
            self.assertEqual(unresolved, 0)
            self.assertAlmostEqual(score, 1.0)

    def test_citation_wrapper_mode_inner_project_paths_resolve(self):
        """Wrapper-mode: citations resolve relative to install_root/project_root, not install_root."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            # Wrapper layout: install_root/db-cse-ui-strata/packages/.../BLoC.ts
            inner_project = install_root / "db-cse-ui-strata"
            pkg_dir = inner_project / "packages" / "pkg-cse-common" / "src" / "classes"
            pkg_dir.mkdir(parents=True)
            (pkg_dir / "BLoC.ts").write_text("export class BLoC {}", encoding="utf-8")

            devforge = install_root / ".devforge"
            devforge.mkdir()
            # init.yaml declares wrapper mode + project_root.
            (devforge / "init.yaml").write_text(
                "workspace_mode: wrapper\n"
                "project_root: db-cse-ui-strata\n"
                "project_state: brownfield\n"
                "default_branch: main\n"
                "packages_detected: []\n",
                encoding="utf-8",
            )
            # Rule cites BLoC.ts as a bare basename (typical of architecture.md prose).
            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [{"tag": "extracted", "text": "Every BLoC extends base BLoC.ts pattern."}],
                "tables": [], "code_examples": [],
            }]
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge,
            )
            # Without wrapper-aware resolution, BLoC.ts would be unresolved
            # (install_root/BLoC.ts doesn't exist). With it, rglob inside
            # install_root/db-cse-ui-strata finds the file.
            self.assertEqual(resolved, 1, "expected wrapper-mode rglob to resolve BLoC.ts; failed={0}".format(failed))
            self.assertEqual(unresolved, 0)

    def test_citation_annotation_included_in_scan(self):
        """code_example.annotation IS scanned for path tokens (INCLUDE behavior)."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            # Create a real file referenced in annotation.
            ref = install_root / "src" / "helpers.py"
            ref.parent.mkdir(parents=True)
            ref.write_text("# helpers\n", encoding="utf-8")

            state = constitute_helper.default_state()
            state["architecture_rules"] = [{
                "number": "2.1", "title": "T", "tag": None, "description": None,
                "rules": [],
                "tables": [],
                "code_examples": [{
                    "label": "EXAMPLE", "language": "python",
                    "code": "pass",
                    "annotation": "Pattern from src/helpers.py",
                }],
            }]
            devforge = install_root / ".devforge"
            score, resolved, unresolved, failed = constitute_helper._count_citations(
                state, install_root, devforge
            )
            # src/helpers.py exists → resolved.
            self.assertEqual(resolved, 1)
            self.assertEqual(unresolved, 0)
            self.assertAlmostEqual(score, 1.0)


class TestStep4CodeExampleSyntax(unittest.TestCase):
    """Code-example syntax (dim 3) — 7 tests."""

    def test_syntax_valid_python(self):
        """Valid Python code → syntax check passes."""
        self.assertTrue(constitute_helper._check_python_syntax("x = 1\n"))
        self.assertTrue(constitute_helper._check_python_syntax("def foo():\n    return 42\n"))

    def test_syntax_invalid_python(self):
        """Invalid Python (def with no body in one context) → fails."""
        # A def statement alone without a body is a SyntaxError in older Pythons
        # but ast.parse handles "def foo(): pass" fine. Use truly invalid syntax.
        invalid = "def foo(:\n    pass\n"
        self.assertFalse(constitute_helper._check_python_syntax(invalid))

    def test_syntax_valid_json(self):
        """Valid JSON → syntax check passes."""
        self.assertTrue(constitute_helper._check_json_syntax('{"key": "value"}'))
        self.assertTrue(constitute_helper._check_json_syntax('["a", "b"]'))

    def test_syntax_invalid_json_unclosed_brace(self):
        """Invalid JSON (unclosed brace) → fails."""
        self.assertFalse(constitute_helper._check_json_syntax('{"key": "value"'))

    def test_syntax_ts_balanced_braces_pass(self):
        """TypeScript with balanced braces → passes."""
        code = "const fn = (x: string): string => { return x; }"
        self.assertTrue(constitute_helper._check_balanced_braces(code))
        self.assertTrue(constitute_helper._check_code_example_syntax("ts", code))

    def test_syntax_ts_unbalanced_braces_fail(self):
        """TypeScript with unbalanced braces (off by 2+) → fails."""
        code = "const fn = (x: string) => {{ return x;"
        self.assertFalse(constitute_helper._check_code_example_syntax("ts", code))

    def test_syntax_ts_off_by_one_brace_passes(self):
        """TypeScript with 1-brace imbalance (e.g., string-literal `{`) → tolerance allows it."""
        code = "if (x) { console.log('open: {'); }"  # 2 open, 1 close → diff = 1
        self.assertTrue(constitute_helper._check_balanced_braces(code))
        self.assertTrue(constitute_helper._check_code_example_syntax("ts", code))

    def test_syntax_non_empty_exotic_language_passes(self):
        """Non-empty exotic language (dockerfile) → non-empty heuristic → pass."""
        code = "FROM python:3.11\nRUN pip install -r requirements.txt\n"
        self.assertTrue(constitute_helper._check_code_example_syntax("dockerfile", code))

    def test_syntax_empty_exotic_language_fails(self):
        """Empty code for any language → fails."""
        self.assertFalse(constitute_helper._check_code_example_syntax("dockerfile", ""))
        self.assertFalse(constitute_helper._check_code_example_syntax("bash", "   "))

    def test_syntax_count_all_pass(self):
        """_count_code_syntax on state with valid examples → score 1.0."""
        state = constitute_helper.default_state()
        state["architecture_rules"] = [{
            "number": "2.1", "title": "T", "tag": None, "description": None,
            "rules": [],
            "tables": [],
            "code_examples": [
                {"label": "CORRECT", "language": "python", "code": "x = 1\n", "annotation": None},
                {"label": "CORRECT", "language": "json", "code": '{"a": 1}', "annotation": None},
            ],
        }]
        score, parsed, total, failed = constitute_helper._count_code_syntax(state)
        self.assertEqual(total, 2)
        self.assertEqual(parsed, 2)
        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(failed, [])

    def test_syntax_count_one_failure(self):
        """_count_code_syntax with one failure → fractional score."""
        state = constitute_helper.default_state()
        state["architecture_rules"] = [{
            "number": "2.1", "title": "T", "tag": None, "description": None,
            "rules": [],
            "tables": [],
            "code_examples": [
                {"label": "CORRECT", "language": "python", "code": "x = 1\n", "annotation": None},
                {"label": "WRONG", "language": "python", "code": "def foo(:\n    pass", "annotation": None},
            ],
        }]
        score, parsed, total, failed = constitute_helper._count_code_syntax(state)
        self.assertEqual(total, 2)
        self.assertEqual(parsed, 1)
        self.assertAlmostEqual(score, 0.5)
        self.assertEqual(len(failed), 1)

    def test_syntax_zero_examples_is_na(self):
        """Zero code examples → N/A → score 1.0."""
        state = constitute_helper.default_state()
        score, parsed, total, failed = constitute_helper._count_code_syntax(state)
        self.assertEqual(total, 0)
        self.assertAlmostEqual(score, 1.0)


class TestStep4RuleTagValidity(unittest.TestCase):
    """Rule-tag validity (dim 4) — 3 tests."""

    def test_rule_tag_all_valid(self):
        """All tags from enum → score 1.0."""
        state = _fully_populated_state()
        score, valid, total, failed = constitute_helper._count_rule_tags(state)
        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(failed, [])
        self.assertEqual(valid, total)

    def test_rule_tag_one_bad_tag(self):
        """One invalid tag → fractional score."""
        state = _fully_populated_state()
        # Insert a rule with invalid tag.
        state["architecture_rules"][0]["rules"].append({"tag": "INVALID-TAG", "text": "something"})
        score, valid, total, failed = constitute_helper._count_rule_tags(state)
        self.assertLess(score, 1.0)
        self.assertEqual(len(failed), 1)
        self.assertIn("INVALID-TAG", failed[0])

    def test_rule_tag_zero_rules_is_na(self):
        """Zero rules → N/A → score 1.0."""
        state = constitute_helper.default_state()
        score, valid, total, failed = constitute_helper._count_rule_tags(state)
        self.assertEqual(total, 0)
        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(failed, [])


class TestStep4CompositeAndExitCode(unittest.TestCase):
    """Composite score + exit code — 5 tests."""

    def test_composite_all_pass_exits_0(self):
        """All dimensions pass → composite >= 0.95 → exit 0."""
        state = _fully_populated_state()
        # Ensure valid Python code examples.
        state["architecture_rules"][0]["code_examples"] = [
            {"label": "CORRECT", "language": "python", "code": "x = 1\n", "annotation": None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            devforge = install_root / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_validate(devforge, install_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertGreaterEqual(data["composite"], 0.95)

    def test_composite_one_dimension_fails_exits_2(self):
        """One dimension failing → composite < 0.95 → exit 2."""
        state = constitute_helper.default_state()
        # Deliberately leave most slots empty → slot_fill very low.
        # All other dims are N/A (1.0) but slot_fill near 0.
        # The composite = 0.3 * 0 + 0.25 * 1.0 + 0.25 * 1.0 + 0.2 * 1.0 = 0.70 < 0.95.
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            devforge = install_root / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_validate(devforge, install_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            data = json.loads(result.stdout)
            self.assertLess(data["composite"], 0.95)

    def test_composite_stdout_json_structure(self):
        """stdout always contains valid JSON with composite + dimensions + failed_items."""
        state = _fully_populated_state()
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            devforge = install_root / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_validate(devforge, install_root)
            # Should not raise.
            data = json.loads(result.stdout)
            self.assertIn("composite", data)
            self.assertIn("dimensions", data)
            self.assertIn("failed_items", data)
            self.assertIsInstance(data["composite"], float)
            for dim in ("slot_fill", "citation", "code_syntax", "rule_tag"):
                self.assertIn(dim, data["dimensions"])
                self.assertIn("score", data["dimensions"][dim])
                self.assertIn("pass", data["dimensions"][dim])
            self.assertIsInstance(data["failed_items"], list)

    def test_composite_stderr_enumerates_failed_items(self):
        """When failing, stderr enumerates per-dimension scores and failed items."""
        state = constitute_helper.default_state()
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            devforge = install_root / ".devforge"
            _write_state_for_test(devforge, state)
            result = _run_validate(devforge, install_root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("FAIL", result.stderr)
            # At least one slot_fill failure item expected.
            self.assertIn("slot_fill", result.stderr)

    def test_composite_state_file_unreadable_exits_1(self):
        """Corrupted constitute.json → exit 1."""
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp)
            devforge = install_root / ".devforge"
            devforge.mkdir(parents=True, exist_ok=True)
            (devforge / "constitute.json").write_text("{not valid json", encoding="utf-8")
            result = _run_validate(devforge, install_root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("cannot load constitute.json", result.stderr)

    def test_composite_formula_verification(self):
        """Verify composite = sum(weight * score for each dim)."""
        scores = {
            "slot_fill":   1.0,
            "citation":    0.8,
            "code_syntax": 0.9,
            "rule_tag":    1.0,
        }
        expected = 0.30 * 1.0 + 0.25 * 0.8 + 0.25 * 0.9 + 0.20 * 1.0
        result = constitute_helper._compute_composite(scores)
        self.assertAlmostEqual(result, expected, places=6)


# ---------------------------------------------------------------------------
# TestParseUniversalBlocks — _parse_universal_blocks
# ---------------------------------------------------------------------------


class TestParseUniversalBlocks(unittest.TestCase):
    """Tests for _parse_universal_blocks(constitution_md_path).

    Uses the real on-disk src/constitution.md as the only fixture — no
    hand-authored markdown bypasses the real producer (the constitution IS
    the producer for this parser).

    NOTE on §3.6 rule count: the brief's example shows 4 sub-rules and the
    inline sanity check uses `== 4`.  The actual constitution has 5 SOLID
    sub-principles (Single Responsibility + OCP + LSP + ISP + DIP) plus DRY
    and KISS = 7 total.  The implementation is faithful to the real file.
    Tests check for presence of the 4 labels named in the brief and assert
    ``>= 4`` (not ``== 4``) to avoid brittleness when the constitution is
    extended.
    """

    _CONSTITUTION_PATH = _REPO_ROOT / "src" / "constitution.md"

    def test_happy_path_all_10_sections_present(self):
        """Real constitution.md → all 10 universal sections in result dict."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        expected_keys = {
            "§3.5", "§3.6", "§3.7",
            "§4.1", "§4.2", "§4.3",
            "§6.1", "§6.2", "§6.3", "§6.4",
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_happy_path_each_section_has_heading(self):
        """Every returned section has a non-empty heading string."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        for key, val in d.items():
            self.assertIn("heading", val, msg=key)
            self.assertIsInstance(val["heading"], str, msg=key)
            self.assertTrue(val["heading"].strip(), msg="{0} heading is empty".format(key))

    def test_happy_path_each_section_has_rules_list(self):
        """Every returned section has a non-empty rules list."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        for key, val in d.items():
            self.assertIn("rules", val, msg=key)
            self.assertIsInstance(val["rules"], list, msg=key)
            self.assertGreater(len(val["rules"]), 0,
                               msg="{0} rules list is empty".format(key))

    def test_happy_path_every_rule_has_nonempty_body(self):
        """Every rule in every section has a non-empty stripped body."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        for sect_key, val in d.items():
            for i, rule in enumerate(val["rules"]):
                self.assertIn("body", rule, msg="{0}[{1}]".format(sect_key, i))
                self.assertTrue(
                    rule["body"].strip(),
                    msg="{0}[{1}] body is empty".format(sect_key, i),
                )

    def test_happy_path_every_rule_has_nonempty_tag_or_label(self):
        """Every rule in every section has a non-empty tag_or_label."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        for sect_key, val in d.items():
            for i, rule in enumerate(val["rules"]):
                self.assertIn("tag_or_label", rule,
                              msg="{0}[{1}]".format(sect_key, i))
                self.assertTrue(
                    rule["tag_or_label"].strip(),
                    msg="{0}[{1}] tag_or_label is empty".format(sect_key, i),
                )

    def test_section_36_solid_sub_rules_present(self):
        """§3.6 rules contain at least 4 entries including the 4 SOLID OCP/LSP/ISP/DIP sub-rules.

        The brief example shows 4 labels (Open/Closed, LSP, ISP, Dependency
        Inversion).  The real constitution also includes Single Responsibility,
        DRY, and KISS, giving >= 4 total (currently 7).  We assert >= 4 and
        check all 4 named labels are present.
        """
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        self.assertIn("§3.6", d)
        rules = d["§3.6"]["rules"]
        self.assertGreaterEqual(len(rules), 4)
        labels = {r["tag_or_label"] for r in rules}
        # The four SOLID sub-rules explicitly named in the brief spec.
        for expected_label in ("Open/Closed", "Liskov Substitution",
                               "Interface Segregation", "Dependency Inversion"):
            self.assertIn(expected_label, labels,
                          msg="Missing SOLID sub-rule: {0!r}".format(expected_label))

    def test_section_43_prefer_bullets_split(self):
        """§4.3 rules contain >= 1 PREFER bullet entry with non-empty body."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        self.assertIn("§4.3", d)
        rules = d["§4.3"]["rules"]
        self.assertGreaterEqual(len(rules), 1)
        for rule in rules:
            self.assertTrue(rule["body"].strip(),
                            msg="§4.3 rule {0!r} has empty body".format(
                                rule.get("tag_or_label")))

    def test_missing_file_raises_file_not_found(self):
        """Non-existent path raises FileNotFoundError (clear failure signal)."""
        missing = Path("/nonexistent/path/to/constitution.md")
        with self.assertRaises(FileNotFoundError):
            constitute_helper._parse_universal_blocks(missing)

    def test_section_35_single_rule_entry(self):
        """§3.5 has no sub-rule splitting; emits exactly one rule with heading as label."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        self.assertIn("§3.5", d)
        rules = d["§3.5"]["rules"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["tag_or_label"], d["§3.5"]["heading"])

    def test_workflow_sections_have_single_rule(self):
        """§6.1-§6.4 (plain prose sections) each emit exactly one rule entry."""
        d = constitute_helper._parse_universal_blocks(self._CONSTITUTION_PATH)
        for sect_key in ("§6.1", "§6.2", "§6.3", "§6.4"):
            self.assertIn(sect_key, d, msg=sect_key)
            rules = d[sect_key]["rules"]
            self.assertEqual(
                len(rules), 1,
                msg="{0} should emit 1 rule, got {1}".format(sect_key, len(rules)),
            )


# ---------------------------------------------------------------------------
# TestExtractUniversalRulesFromState — _extract_universal_rules_from_state
# ---------------------------------------------------------------------------


def _build_real_constitute_state(devforge_dir: Path) -> None:
    """Use the real constitute_helper CLI to populate a state file.

    Adds one universal section (3.5) + one project-specific section (3.1)
    to code_quality_standards, and one universal pattern rule (always) +
    one project-specific pattern rule, to exercise filtering.
    """
    helper = str(_HELPER_PY)
    base = [sys.executable, helper, "--devforge-dir", str(devforge_dir)]

    def run(*args):
        r = subprocess.run(base + list(args), capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(
                "constitute_helper {0} failed (exit {1}): {2}".format(
                    args[0], r.returncode, r.stderr
                )
            )

    run("reset")
    # Universal section in code_quality_standards.
    run("add-section", "--bucket", "code-quality", "--number", "3.5",
        "--title", "Universal Code Quality", "--tag", "universal")
    run("add-rule", "--section", "3.5", "--tag", "universal",
        "--text", "No dead code. Delete unused functions.")
    # Project-specific section (should be filtered out).
    run("add-section", "--bucket", "code-quality", "--number", "3.1",
        "--title", "Type Safety", "--tag", "project-specific")
    run("add-rule", "--section", "3.1", "--tag", "project-specific",
        "--text", "Use strict TypeScript settings.")
    # Universal always-pattern.
    run("add-pattern-rule", "--bucket", "always", "--scope", "universal",
        "--tag", "universal", "--text", "Read before write.")
    # Project-specific always-pattern (should be filtered out).
    run("add-pattern-rule", "--bucket", "always", "--scope", "project-specific",
        "--tag", "project-specific", "--text", "Always use the API client.")


class TestExtractUniversalRulesFromState(unittest.TestCase):
    """Tests for _extract_universal_rules_from_state(constitute_json_path).

    Real-producer principle: fixture states are built via the actual
    constitute_helper CLI (reset + add-section + add-rule + add-pattern-rule)
    rather than hand-authored JSON.
    """

    def test_happy_path_real_producer(self):
        """Round-trip via real producer: universal sections extracted, non-empty rules."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_real_constitute_state(devforge)
            state_path = devforge / "constitute.json"

            result = constitute_helper._extract_universal_rules_from_state(
                state_path
            )

            # §3.5 came from code_quality_standards with tag=universal.
            self.assertIn("§3.5", result)
            self.assertEqual(result["§3.5"]["heading"], "Universal Code Quality")
            self.assertGreater(len(result["§3.5"]["rules"]), 0)
            # §4.1 came from patterns_and_antipatterns.always_universal.
            self.assertIn("§4.1", result)
            self.assertGreater(len(result["§4.1"]["rules"]), 0)
            # All rule bodies non-empty.
            for sect_key, val in result.items():
                for rule in val["rules"]:
                    self.assertTrue(
                        rule["body"].strip(),
                        msg="{0} has empty body".format(sect_key),
                    )

    def test_filters_non_universal_sections(self):
        """Project-specific sections do NOT appear in the result."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_real_constitute_state(devforge)
            state_path = devforge / "constitute.json"

            result = constitute_helper._extract_universal_rules_from_state(
                state_path
            )

            # §3.1 has tag=project-specific and must be excluded.
            self.assertNotIn("§3.1", result)
            # §4.1 should be present (always_universal), but always_project_specific
            # rules must NOT be merged into it.
            if "§4.1" in result:
                bodies = [r["body"] for r in result["§4.1"]["rules"]]
                self.assertNotIn("Always use the API client.", bodies)

    def test_empty_state_returns_empty_dict(self):
        """Freshly-reset state (no sections populated) returns {} cleanly."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            helper = str(_HELPER_PY)
            subprocess.run(
                [sys.executable, helper, "--devforge-dir", str(devforge), "reset"],
                check=True, capture_output=True,
            )
            state_path = devforge / "constitute.json"
            result = constitute_helper._extract_universal_rules_from_state(
                state_path
            )
            # Default state has no sections and no pattern rules populated.
            self.assertEqual(result, {})

    def test_missing_file_raises_file_not_found(self):
        """Non-existent path raises FileNotFoundError."""
        missing = Path("/nonexistent/path/constitute.json")
        with self.assertRaises(FileNotFoundError):
            constitute_helper._extract_universal_rules_from_state(missing)

    def test_malformed_json_raises_decode_error(self):
        """Malformed JSON raises json.JSONDecodeError."""
        import json
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "constitute.json"
            bad_path.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                constitute_helper._extract_universal_rules_from_state(bad_path)

    def test_workflow_section_universal_is_extracted(self):
        """Universal sections in workflow_rules bucket are extracted."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            helper = str(_HELPER_PY)
            base = [sys.executable, helper, "--devforge-dir", str(devforge)]

            def run(*args):
                r = subprocess.run(base + list(args), capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr)

            run("reset")
            run("add-section", "--bucket", "workflow", "--number", "6.1",
                "--title", "Minimal Changes", "--tag", "universal")
            run("add-rule", "--section", "6.1", "--tag", "universal",
                "--text", "Every code change MUST impact as little code as possible.")

            state_path = devforge / "constitute.json"
            result = constitute_helper._extract_universal_rules_from_state(
                state_path
            )

            self.assertIn("§6.1", result)
            self.assertEqual(result["§6.1"]["heading"], "Minimal Changes")
            self.assertEqual(len(result["§6.1"]["rules"]), 1)
            self.assertEqual(
                result["§6.1"]["rules"][0]["body"],
                "Every code change MUST impact as little code as possible.",
            )


# ---------------------------------------------------------------------------
# forge-internal:verify-universal-defaults.
# ---------------------------------------------------------------------------


def _build_in_sync_constitute_json(devforge_dir: Path) -> None:
    """Write a constitute.json whose universal-rule bodies match the canonical
    src/constitution.md exactly for ALL universal sections.

    The fixture is hand-authored (not via setters) because:
    - ``add-rule --tag`` is constrained to enum values (extracted | enforced |
      universal | project-specific), so principle names like "Single
      Responsibility" cannot be stored as the rule tag via the CLI.
    - ``_extract_universal_rules_from_state`` maps rule.tag → tag_or_label, so
      for the canonical and consumer tag_or_label keys to match, the JSON rule
      records must carry the principle name as the ``tag`` field.
    - Hand-authored JSON is explicitly permitted by the real-producer principle
      where setters can't naturally produce the required shape.

    Body text is sourced directly from ``_parse_universal_blocks`` output on the
    real ``src/constitution.md`` — no body values are invented.

    Sections populated:
    - code_quality_standards: §3.5, §3.6, §3.7
    - patterns_and_antipatterns universal buckets: §4.1, §4.2, §4.3
    - workflow_rules: §6.1, §6.2, §6.3, §6.4
    """
    canonical = constitute_helper._parse_universal_blocks(
        _REPO_ROOT / "src" / "constitution.md"
    )

    state = constitute_helper.default_state()

    # --- code_quality_standards sections: §3.5, §3.6, §3.7 ---
    for number in ("3.5", "3.6", "3.7"):
        sect_key = "§" + number
        sec = canonical.get(sect_key, {})
        rules = [
            {"tag": r["tag_or_label"], "text": r["body"]}
            for r in sec.get("rules", [])
        ]
        state["code_quality_standards"].append(
            {
                "number": number,
                "title": sec.get("heading", number),
                "tag": "universal",
                "description": None,
                "rules": rules,
                "tables": [],
                "code_examples": [],
            }
        )

    # --- patterns_and_antipatterns universal buckets: §4.1, §4.2, §4.3 ---
    _SECT_TO_BUCKET = {"§4.1": "always_universal", "§4.2": "never_universal",
                       "§4.3": "prefer_universal"}
    for sect_key, bucket_name in _SECT_TO_BUCKET.items():
        sec = canonical.get(sect_key, {})
        rules = [
            {"tag": r["tag_or_label"], "text": r["body"]}
            for r in sec.get("rules", [])
        ]
        state["patterns_and_antipatterns"][bucket_name] = rules

    # --- workflow_rules sections: §6.1, §6.2, §6.3, §6.4 ---
    for number in ("6.1", "6.2", "6.3", "6.4"):
        sect_key = "§" + number
        sec = canonical.get(sect_key, {})
        rules = [
            {"tag": r["tag_or_label"], "text": r["body"]}
            for r in sec.get("rules", [])
        ]
        state["workflow_rules"].append(
            {
                "number": number,
                "title": sec.get("heading", number),
                "tag": "universal",
                "description": None,
                "rules": rules,
                "tables": [],
                "code_examples": [],
            }
        )

    devforge_dir.mkdir(parents=True, exist_ok=True)
    out = devforge_dir / "constitute.json"
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


class TestForgeInternalVerifyUniversalDefaults(unittest.TestCase):
    """Tests for forge-internal:verify-universal-defaults subcommand.

    Fixture strategy:
    - All 3 tests use hand-authored constitute.json fixtures because the
      ``add-rule`` setter constrains ``--tag`` to enum values, so principle
      names like "Single Responsibility" cannot be stored via the CLI.
      Body text is always sourced from the real canonical parser output.
    - test_verify_universal_defaults_in_sync: fixture bodies match canonical
      (exit 0, zero findings).
    - test_verify_universal_defaults_missing_section: §3.6 entirely absent
      (exit 2, MISSING §3.6 finding).
    - test_verify_universal_defaults_drift_one_rule: §3.6 present but one
      rule body differs (exit 2, DRIFT §3.6 finding).
    """

    def _invoke(self, consumer_path: Path, canonical_path: Path):
        """Invoke forge-internal:verify-universal-defaults via subprocess."""
        return subprocess.run(
            [
                sys.executable,
                str(_HELPER_PY),
                "forge-internal:verify-universal-defaults",
                "--consumer-path", str(consumer_path),
                "--canonical-path", str(canonical_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_verify_universal_defaults_in_sync(self):
        """In-sync fixture: bodies match canonical → exit 0, empty findings."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = consumer_root / ".devforge"
            _build_in_sync_constitute_json(devforge)

            canonical_path = _REPO_ROOT / "src" / "constitution.md"
            result = self._invoke(consumer_root, canonical_path)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(
                result.stderr.strip(), "",
                msg="Expected empty stderr on in-sync fixture"
            )

            report = json.loads(result.stdout)
            self.assertIn("findings", report)
            self.assertEqual(
                report["findings"], [],
                msg="Expected zero findings on in-sync fixture"
            )

    def test_verify_universal_defaults_missing_section(self):
        """§3.6 absent in consumer → exit 2, MISSING §3.6 in findings."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = consumer_root / ".devforge"

            # Build a state with §3.6 INTENTIONALLY absent.
            state = constitute_helper.default_state()
            devforge.mkdir(parents=True, exist_ok=True)
            out = devforge / "constitute.json"
            out.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            canonical_path = _REPO_ROOT / "src" / "constitution.md"
            result = self._invoke(consumer_root, canonical_path)

            self.assertEqual(result.returncode, 2, msg=result.stderr)
            self.assertIn("MISSING", result.stderr)
            self.assertIn("§3.6", result.stderr)

            report = json.loads(result.stdout)
            missing_entries = [
                f for f in report["findings"]
                if f.get("kind") == "MISSING" and f.get("section") == "§3.6"
            ]
            self.assertGreater(
                len(missing_entries), 0,
                msg="Expected at least one MISSING entry for §3.6 in JSON findings"
            )

    def test_verify_universal_defaults_drift_one_rule(self):
        """§3.6 present but one rule body differs → exit 2, DRIFT §3.6 finding."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = consumer_root / ".devforge"

            canonical = constitute_helper._parse_universal_blocks(
                _REPO_ROOT / "src" / "constitution.md"
            )
            sec36 = canonical.get("§3.6", {})

            # Build rules identical to canonical EXCEPT for the first rule,
            # whose body is replaced with pre-strengthening generic text.
            rules_36 = [
                {"tag": r["tag_or_label"], "text": r["body"]}
                for r in sec36.get("rules", [])
            ]
            if rules_36:
                rules_36[0] = {
                    "tag": rules_36[0]["tag"],
                    "text": "Depend on abstractions, not on concretions.",
                }

            state = constitute_helper.default_state()
            state["code_quality_standards"].append(
                {
                    "number": "3.6",
                    "title": sec36.get("heading", "Design Principles"),
                    "tag": "universal",
                    "description": None,
                    "rules": rules_36,
                    "tables": [],
                    "code_examples": [],
                }
            )

            devforge.mkdir(parents=True, exist_ok=True)
            out = devforge / "constitute.json"
            out.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            canonical_path = _REPO_ROOT / "src" / "constitution.md"
            result = self._invoke(consumer_root, canonical_path)

            self.assertEqual(result.returncode, 2, msg=result.stderr)
            self.assertIn("DRIFT", result.stderr)
            self.assertIn("§3.6", result.stderr)

            report = json.loads(result.stdout)
            drift_entries = [
                f for f in report["findings"]
                if f.get("kind") == "DRIFT" and f.get("section") == "§3.6"
            ]
            self.assertGreater(
                len(drift_entries), 0,
                msg="Expected at least one DRIFT entry for §3.6 in JSON findings"
            )


if __name__ == "__main__":
    unittest.main()
