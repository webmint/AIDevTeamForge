#!/usr/bin/env python3
"""Tests for scripts/forge/quality_profile.py: unset keys, the new-project skeleton and the binding consumers
(stdlib unittest; Python 3.9+).

A throwaway repository root holds invented consumer files and scripts. One test runs the check on this repository.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

BINDING = "`.claude/quality-profile.json`"
SHIPPED_KEYS = {
    "$comment", "searchScopes", "generatedDirs", "integrationRef", "auditGate", "baselineFile", "ratchets",
    "enforcementMap", "catalogTests", "layers", "planningSources", "canonicalSources", "newExports",
    "decisionRecords", "semanticClones", "hubFiles",
}


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp(prefix="quality-profile-")
        self.addCleanup(shutil.rmtree, self.repo)

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


class LocationTests(unittest.TestCase):
    """The module sits in <project>/scripts/forge/; the binding is <project>/.claude/quality-profile.json."""

    def test_the_project_root_is_three_levels_above_the_module(self) -> None:
        self.assertEqual(os.path.realpath(quality_profile.REPO), os.path.realpath(REPO))
        self.assertEqual(quality_profile.DEFAULT_PROFILE, os.path.join(quality_profile.REPO, ".claude", "quality-profile.json"))
        self.assertEqual(quality_profile.HARNESS_SCRIPTS, "scripts/forge")

    def test_the_shipped_keys(self) -> None:
        self.assertEqual(set(quality_profile.TOP_LEVEL), SHIPPED_KEYS)
        self.assertEqual(set(quality_profile.CONSUMERS), SHIPPED_KEYS - {"$comment"})


class LayersScopeTests(RepoCase):
    """`layers.scope` is a directory glob or a list of them."""

    def scope_problems(self, scope: object) -> list[str]:
        os.makedirs(os.path.join(self.repo, "src", "a"), exist_ok=True)
        layers = {"scope": scope, "layers": [], "sharedDirs": []}
        return quality_profile.validate({"layers": layers}, repo=self.repo)

    def test_a_string_scope_must_end_in_a_slash_and_match_a_directory(self) -> None:
        self.assertEqual(self.scope_problems("src/a/"), [])
        self.assertIn("layers.scope: must end in '/'", self.scope_problems("src/a"))
        self.assertIn("layers.scope: src/gone/ matches no directory", self.scope_problems("src/gone/"))

    def test_a_list_scope_may_name_a_zone_that_does_not_exist_yet(self) -> None:
        self.assertEqual(self.scope_problems(["src/a/", "src/later/"]), [])

    def test_a_list_scope_is_checked(self) -> None:
        self.assertIn("layers.scope: src/a must end in '/'", self.scope_problems(["src/a"]))
        self.assertIn("layers.scope: no entry matches a directory", self.scope_problems(["src/x/", "src/y/"]))
        self.assertIn(
            "layers.scope: expected a string or a non-empty list of strings", self.scope_problems([]),
        )
        self.assertIn(
            "layers.scope: expected a string or a non-empty list of strings", self.scope_problems([1]),
        )


class UnsetKeyTests(RepoCase):
    def test_the_skeleton_has_every_key_and_is_valid(self) -> None:
        data = quality_profile.skeleton()
        self.assertEqual(set(data), set(quality_profile.TOP_LEVEL))
        self.assertEqual(quality_profile.validate(data, repo=self.repo), [])
        self.assertEqual(quality_profile.configured(data), {})
        self.assertIn("python3 scripts/forge/quality_profile.py validate", data["$comment"])

    def test_empty_sections_are_unset_and_not_checked(self) -> None:
        profile = {"canonicalSources": {}, "planningSources": [], "auditGate": {}, "integrationRef": ""}
        self.assertEqual(quality_profile.validate(profile, repo=self.repo), [])

    def test_a_partly_filled_section_is_still_checked(self) -> None:
        found = quality_profile.validate({"canonicalSources": {"doc": ""}}, repo=self.repo)
        self.assertIn("canonicalSources.heading: expected a non-empty str", found)

    def test_an_empty_value_of_the_wrong_type_is_a_type_error(self) -> None:
        self.assertIn("searchScopes: expected list", quality_profile.validate({"searchScopes": ""}, repo=self.repo))

    def test_a_removed_or_unknown_key_is_reported(self) -> None:
        self.assertIn("unknown key: nonsense", quality_profile.validate({"nonsense": {}}, repo=self.repo))

    def test_init_writes_once_and_refuses_to_overwrite(self) -> None:
        path = os.path.join(self.repo, ".claude", "quality-profile.json")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(quality_profile.main(["init", "--profile", path]), 0)
            self.assertEqual(quality_profile.main(["validate", "--profile", path]), 0)
            self.assertEqual(quality_profile.main(["init", "--profile", path]), 1)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["searchScopes"], [])

    def test_validate_of_a_missing_or_broken_file_is_unusable(self) -> None:
        path = os.path.join(self.repo, ".claude", "quality-profile.json")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(quality_profile.main(["validate", "--profile", path]), 2)
            self.write(".claude/quality-profile.json", "{not json")
            self.assertEqual(quality_profile.main(["validate", "--profile", path]), 2)


class DefaultAuditGateTests(RepoCase):
    """`init --integration-ref` makes the audit gate a default, active from the first spec."""

    def test_init_with_an_integration_ref_sets_the_default_audit_gate(self) -> None:
        path = os.path.join(self.repo, ".claude", "quality-profile.json")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(quality_profile.main(["init", "--profile", path, "--integration-ref", "origin/main"]), 0)
            self.assertEqual(quality_profile.main(["validate", "--profile", path]), 0)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["integrationRef"], "origin/main")
        self.assertEqual(data["auditGate"], quality_profile.DEFAULT_AUDIT_GATE)
        self.assertEqual(data["auditGate"]["every"], 3)
        self.assertEqual(data["searchScopes"], [])

    def test_the_blocking_issues_come_from_a_profile_command(self) -> None:
        issues = quality_profile.DEFAULT_AUDIT_GATE["blockingIssues"]
        self.assertEqual(issues["command"], "gh issue list --state open --label source:audit --label severity:critical "
                                            "--json number,title,labels --limit 200")
        self.assertEqual(issues["labels"], ["source:audit", "severity:critical"])

    def test_the_skeleton_without_a_ref_leaves_the_gate_unset(self) -> None:
        self.assertEqual(quality_profile.skeleton()["auditGate"], {})

    def test_an_audit_gate_needs_an_integration_ref(self) -> None:
        found = quality_profile.validate({"auditGate": dict(quality_profile.DEFAULT_AUDIT_GATE)}, repo=self.repo)
        self.assertEqual(found, ["integrationRef: required by auditGate"])


class HubFilesTests(RepoCase):
    """The `hubFiles` binding is validated."""

    def setUp(self) -> None:
        super().setUp()
        os.makedirs(os.path.join(self.repo, "src"))
        self.good = {"commitPattern": "^feat", "window": 10, "threshold": 4, "paths": ["src/"], "ignore": ["src/gen/*"]}

    def test_a_valid_section_passes(self) -> None:
        self.assertEqual(quality_profile.validate({"hubFiles": self.good}, repo=self.repo), [])

    def test_invalid_entries_are_reported(self) -> None:
        bad = dict(self.good, commitPattern="(", threshold=11, paths=["nowhere/"], extra=1, ignore=[""])
        found = quality_profile.validate({"hubFiles": bad}, repo=self.repo)
        for message in ("hubFiles: unknown key: extra", "hubFiles.threshold: must be at least 1 and at most window",
                        "hubFiles.paths: nowhere/ does not exist under the source root", "hubFiles.ignore: must be a list of strings"):
            self.assertIn(message, found)
        self.assertTrue(any(m.startswith("hubFiles.commitPattern:") for m in found))
        self.assertIn("hubFiles.window: expected int",
                      quality_profile.validate({"hubFiles": dict(self.good, window=True)}, repo=self.repo))


class GeneratedDirsTests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        os.makedirs(os.path.join(self.repo, "pkg", "gen"))
        os.makedirs(os.path.join(self.repo, "other"))

    def problems(self, dirs: list, scopes: list | None = None) -> list[str]:
        profile = {"searchScopes": scopes if scopes is not None else ["pkg/", "other/"], "generatedDirs": dirs}
        return quality_profile.validate(profile, repo=self.repo)

    def test_a_directory_strictly_inside_a_scope_is_valid(self) -> None:
        self.assertEqual(self.problems(["pkg/gen/"]), [])

    def test_invalid_entries_are_reported(self) -> None:
        self.assertIn("generatedDirs: 'pkg/gen' must be a directory path ending in '/'", self.problems(["pkg/gen"]))
        self.assertIn("generatedDirs: pkg/none/ does not exist", self.problems(["pkg/none/"]))
        self.assertIn("generatedDirs: pkg/ must lie strictly inside one of searchScopes", self.problems(["pkg/"]))
        self.assertIn("generatedDirs: pkg/gen/ must lie strictly inside one of searchScopes", self.problems(["pkg/gen/"], ["other/"]))

    def test_search_pathspecs_adds_one_exclude_per_directory(self) -> None:
        profile = {"searchScopes": ["pkg/", "other/"], "generatedDirs": ["pkg/gen/"]}
        self.assertEqual(quality_profile.search_pathspecs(profile), ["pkg/", "other/", ":(exclude)pkg/gen/"])
        self.assertEqual(quality_profile.search_pathspecs({"searchScopes": ["pkg/"]}), ["pkg/"])
        self.assertEqual(quality_profile.search_pathspecs({}), [])

    def test_the_scopes_command_prints_the_resolved_scopes(self) -> None:
        path = os.path.join(self.repo, "profile.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"searchScopes": ["pkg/"], "generatedDirs": ["pkg/gen/"]}, handle)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(quality_profile.main(["scopes", "--profile", path]), 0)
        self.assertEqual(out.getvalue().split(), ["pkg/", ":(exclude)pkg/gen/"])


class ConsumerTests(RepoCase):
    CONSUMERS = {key: [] for key in quality_profile.TOP_LEVEL if key != "$comment"}

    def consumers(self, **overrides: list[str]) -> dict[str, list[str]]:
        data = dict(self.CONSUMERS)
        data.update(overrides)
        return data

    def check(self, profile: dict | None = None, readers: dict[str, str] | None = None, **overrides: list[str]) -> list[str]:
        return quality_profile.check_consumers(profile or {}, repo=self.repo, consumers=self.consumers(**overrides),
                                               readers=readers or {}, scripts_dir="scripts")

    def test_a_command_that_names_the_binding_and_the_key_passes(self) -> None:
        self.write("cmds/a.md", f"Step 2: read {BINDING}: `searchScopes` bounds every search.\n")
        self.assertEqual(self.check(searchScopes=["cmds/a.md"]), [])

    def test_a_command_without_the_key_or_the_binding_fails(self) -> None:
        self.write("cmds/a.md", "Step 2: search the source directories.\n")
        found = self.check(searchScopes=["cmds/a.md"], ratchets=["cmds/a.md"])
        self.assertIn("consumers: cmds/a.md: reads the binding but does not name it (quality-profile.json)", found)
        self.assertIn("consumers: cmds/a.md: does not name the key `searchScopes` at the step that reads it", found)
        self.assertIn("consumers: cmds/a.md: does not name the key `ratchets` at the step that reads it", found)
        self.assertEqual(sum("does not name it" in p for p in found), 1)

    def test_a_key_in_prose_without_backticks_does_not_count(self) -> None:
        self.write("cmds/a.md", f"{BINDING}: the searchScopes key.\n")
        self.assertEqual(len(self.check(searchScopes=["cmds/a.md"])), 1)

    def test_a_python_consumer_must_import_the_loader(self) -> None:
        self.write("scripts/reader.py", 'import json\n\ndef f(p):\n    return p.get("ratchets")\n')
        found = self.check(ratchets=["scripts/reader.py"])
        self.assertIn("consumers: scripts/reader.py: reads the binding but does not name it (import quality_profile)", found)
        self.write("scripts/reader.py", 'import quality_profile\n\ndef f(p):\n    return p.get("ratchets")\n')
        self.assertEqual(self.check(ratchets=["scripts/reader.py"]), [])

    def test_the_loader_itself_counts_as_naming_the_binding(self) -> None:
        self.write("scripts/quality_profile.py", 'def f(p):\n    return p.get("searchScopes")\n')
        self.assertEqual(self.check(searchScopes=["scripts/quality_profile.py"]), [])

    def test_a_set_key_needs_an_existing_consumer_and_missing_files_are_skipped(self) -> None:
        self.assertEqual(self.check(searchScopes=["gone.md"]), [])
        found = self.check({"searchScopes": ["src/"]}, searchScopes=["gone.md"])
        self.assertIn("consumers: searchScopes: set, but no consumer file exists", found)

    def test_every_binding_key_declares_consumers(self) -> None:
        data = self.consumers()
        del data["layers"]
        data["nonsense"] = []
        found = quality_profile.check_consumers({}, repo=self.repo, consumers=data, readers={}, scripts_dir="scripts")
        self.assertIn("consumers: layers: no consumer declared (add it to CONSUMERS)", found)
        self.assertIn("consumers: nonsense: not a binding key", found)

    def test_a_script_reading_the_binding_file_directly_fails(self) -> None:
        self.write("scripts/direct.py", '"""Reads .claude/quality-profile.json (docstrings may name it)."""\nimport json\n'
                   'PATH = ".claude/quality-profile.json"\n')
        self.write("scripts/tests/test_x.py", 'P = "quality-profile.json"\n')
        found = self.check()
        self.assertEqual(found, ["loader: scripts/direct.py:3: names the binding file; load it through quality_profile.load"])

    def test_a_non_python_reader_must_be_declared(self) -> None:
        self.write("scripts/zones.ts", "readFileSync('.claude/quality-profile.json')\n")
        self.assertEqual(self.check(), ["loader: scripts/zones.ts: reads the binding but is not a declared non-Python reader"])
        self.assertEqual(self.check(readers={"scripts/zones.ts": "lint config is TypeScript"}), [])

    def test_the_consumers_command_treats_a_missing_binding_as_unset(self) -> None:
        path = os.path.join(self.repo, ".claude", "quality-profile.json")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(quality_profile.main(["consumers", "--profile", path]), 0)
            self.write(".claude/quality-profile.json", "{not json")
            self.assertEqual(quality_profile.main(["consumers", "--profile", path]), 2)

    def test_this_repository_holds(self) -> None:
        path = quality_profile.DEFAULT_PROFILE
        profile = quality_profile.load(path) if os.path.exists(path) else {}
        self.assertEqual(quality_profile.check_consumers(profile), [])

    def test_the_listed_command_files_are_shipped(self) -> None:
        # Missing consumer files are skipped (generated agents); the commands and the template are always shipped.
        listed = {f for files in quality_profile.CONSUMERS.values() for f in files if f.startswith(".claude/")}
        self.assertTrue(listed)
        self.assertEqual(sorted(f for f in listed if not os.path.isfile(os.path.join(REPO, f))), [])


class MissingBindingTests(unittest.TestCase):
    """A project updated from an older Forge has no binding file: every script a command calls treats that as every
    key unset (one line, exit 0); an existing but invalid file still exits 2, and `validate` exits 2 on a missing one."""

    CALLS = (
        ("quality_profile.py", "scopes"), ("ratchet.py", "check"), ("ratchet.py", "report"),
        ("ratchet.py", "copies", "--files", "src/a.ts"), ("new-exports.py",), ("hub-files.py", "list"),
        ("audit-gate.py", "start-line"), ("check-canonical-sources.py",), ("check-enforcement-map.py",),
        ("check-task-evidence.py",), ("check-decision-records.py",),
    )

    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.profile = os.path.join(self.repo, ".claude", "quality-profile.json")

    def run_script(self, script: str, *args: str) -> subprocess.CompletedProcess:
        # quality_profile.py takes --profile after the subcommand; the other scripts before it (or have none).
        if script == "quality_profile.py":
            argv = [args[0], "--profile", self.profile, *args[1:]]
        else:
            argv = ["--profile", self.profile, *args]
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *argv], capture_output=True, text=True,
                              cwd=self.repo)

    def test_a_missing_binding_prints_one_line_and_exits_0(self) -> None:
        for call in self.CALLS:
            with self.subTest(call=call):
                done = self.run_script(*call)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                text = (done.stdout + done.stderr).splitlines()
                self.assertEqual(len(text), 1, text)
                self.assertTrue(text[0].endswith(quality_profile.MISSING), text)
        self.assertEqual(self.run_script("quality_profile.py", "scopes").stdout, "")
        self.assertEqual(self.run_script("quality_profile.py", "validate").returncode, 2)

    def test_an_invalid_binding_still_exits_2(self) -> None:
        os.makedirs(os.path.dirname(self.profile))
        with open(self.profile, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        for call in self.CALLS:
            with self.subTest(call=call):
                self.assertEqual(self.run_script(*call).returncode, 2)



class WorkflowWordingTests(unittest.TestCase):
    """The harness scripts describe the interactive workflow (the user in the `/audit` triage, `/review`'s Structural
    Check before `/finalize`), not an orchestrator or a steward that the workflow does not have."""

    def test_no_script_names_an_orchestrator_or_a_steward(self) -> None:
        for name in sorted(os.listdir(SCRIPTS)):
            if name.endswith(".py"):
                with open(os.path.join(SCRIPTS, name), encoding="utf-8") as handle:
                    text = handle.read().lower()
                with self.subTest(script=name):
                    self.assertNotIn("orchestrator", text)
                    self.assertNotIn("steward", text)


if __name__ == "__main__":
    unittest.main()
