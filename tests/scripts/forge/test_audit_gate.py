#!/usr/bin/env python3
"""Tests for scripts/forge/audit-gate.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway git repository with its own `.claude/quality-profile.json`; the blocking-issues command
is a stub (`cat` of a file kept under `.git`, outside the history, or a command that fails), so nothing here reads
this repository's history or calls an issue tracker. All names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
GATE = os.path.join(SCRIPTS, "audit-gate.py")
sys.path.insert(0, SCRIPTS)
import quality_profile  # noqa: E402

TRIAGE = "## Theme triage"
BLOCKING = ["source:audit", "severity:critical"]
STUB = "cat .git/issues.json"
PROFILE = {
    "searchScopes": ["specs/"],
    "integrationRef": "main",
    "auditGate": {
        "every": 3,
        "auditReports": "audits/*-audit.md",
        "triageHeading": TRIAGE,
        "mergedSpecMarker": "specs/*/summary.md",
        "specFile": "specs/*/spec.md",
        "blockingIssues": {"command": STUB, "labels": BLOCKING},
    },
}


def profile_with(command: str) -> dict:
    data = json.loads(json.dumps(PROFILE))
    data["auditGate"]["blockingIssues"]["command"] = command
    return data


class Repo:
    """A temporary git repository on branch `main` with the test profile committed."""

    def __init__(self) -> None:
        self.path = tempfile.mkdtemp(prefix="audit-gate-")
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        os.makedirs(os.path.join(self.path, "specs"))
        self.write(".claude/quality-profile.json", json.dumps(PROFILE))
        self.commit("profile")
        self.git("branch", "-M", "main")
        self.issues([])

    def issues(self, rows: list[dict]) -> None:
        """Set the open issues the stub tracker command returns (kept under .git, outside the history)."""
        with open(os.path.join(self.path, ".git", "issues.json"), "w", encoding="utf-8") as handle:
            json.dump([{**row, "labels": [{"name": n} for n in row["labels"]]} if "labels" in row else row
                       for row in rows], handle)

    def tracker(self, command: str) -> None:
        """Replace the blocking-issues command in the working-tree profile."""
        self.write(".claude/quality-profile.json", json.dumps(profile_with(command)))

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", self.path, *args], check=True, capture_output=True, text=True).stdout

    def write(self, rel: str, text: str) -> None:
        full = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", message)

    def merge_spec(self, name: str, header: str = "") -> None:
        self.write(f"specs/{name}/spec.md", "# spec\n" + header)
        self.write(f"specs/{name}/summary.md", "# summary\n")
        self.commit(f"feat: {name}")

    def audit(self, date: str, triage: bool = True) -> None:
        self.write(f"audits/{date}-audit.md", "# Audit\n\n" + (f"{TRIAGE}\n\n- theme\n" if triage else ""))
        self.commit(f"chore: audit {date}")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        profile = os.path.join(self.path, ".claude", "quality-profile.json")
        return subprocess.run(
            [sys.executable, GATE, "--profile", profile, *args], cwd=self.path, capture_output=True, text=True
        )

    def state(self) -> dict:
        result = self.run("status", "--json")
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


class CounterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.cleanup()

    def test_no_audit_counts_every_merged_spec(self) -> None:
        self.repo.merge_spec("001-a")
        state = self.repo.state()
        self.assertEqual((state["specsSinceAudit"], state["auditsOnRef"], state["blocked"]), (1, 0, False))
        self.assertIsNone(state["lastAudit"])
        self.assertIsNone(state["blockingIssuesUnknown"])
        start = self.repo.run("start-line")
        self.assertEqual(start.returncode, 0)
        self.assertEqual(start.stdout.strip(), "Audit gate: started at 1/3 after none")

    def test_audit_resets_the_counter(self) -> None:
        for name in ("001-a", "002-b", "003-c"):
            self.repo.merge_spec(name)
        self.assertTrue(self.repo.state()["blocked"])
        self.repo.audit("2026-01-10")
        self.repo.merge_spec("004-d")
        state = self.repo.state()
        self.assertEqual(state["specs"], ["specs/004-d"])
        self.assertEqual(state["lastAudit"]["report"], "audits/2026-01-10-audit.md")
        self.assertEqual((state["auditsOnRef"], state["triage"], state["blocked"]), (1, True, False))
        start = self.repo.run("start-line")
        self.assertEqual(start.stdout.strip(), "Audit gate: started at 1/3 after audits/2026-01-10-audit.md")

    def test_threshold_blocks_the_start(self) -> None:
        self.repo.audit("2026-01-10")
        for name in ("001-a", "002-b", "003-c"):
            self.repo.merge_spec(name)
        start = self.repo.run("start-line")
        self.assertEqual(start.returncode, 1)
        self.assertIn("BLOCKED", start.stdout)
        self.assertIn("blocked: 3 specs merged since the last audit (threshold 3)", start.stdout)

    def test_audit_without_triage_blocks(self) -> None:
        self.repo.audit("2026-01-10", triage=False)
        state = self.repo.state()
        self.assertEqual((state["specsSinceAudit"], state["triage"], state["blocked"]), (0, False, True))
        self.assertEqual(self.repo.run("start-line").returncode, 1)

    def test_triage_with_an_unfiled_theme_blocks(self) -> None:
        self.repo.write("audits/2026-01-10-audit.md",
                        f"# Audit\n\n{TRIAGE}\n\n| Theme | Issue |\n|---|---|\n| T1 | (to file) |\n| T2 | #4 |\n\n"
                        "## Later\n\nnot a theme row (to file)\n")
        self.repo.commit("chore: audit draft")
        state = self.repo.state()
        self.assertEqual((state["triage"], state["triagePending"], state["blocked"]), (False, 1, True))
        self.assertIn("has 1 theme(s) (to file)", " ".join(state["reasons"]))
        self.assertIn("triage: pending (1 (to file))", self.repo.run("status").stdout)
        self.assertEqual(self.repo.run("start-line", "--remediation", "#4").returncode, 1)
        self.repo.write("audits/2026-01-10-audit.md", f"# Audit\n\n{TRIAGE}\n\n| T1 | #3 |\n| T2 | #4 |\n")
        self.repo.commit("chore: audit filed")
        state = self.repo.state()
        self.assertEqual((state["triage"], state["triagePending"], state["blocked"]), (True, 0, False))

    def test_newest_audit_wins_and_all_are_counted(self) -> None:
        self.repo.audit("2026-01-10")
        self.repo.merge_spec("001-a")
        self.repo.audit("2026-01-20")
        state = self.repo.state()
        self.assertEqual((state["auditsOnRef"], state["specsSinceAudit"]), (2, 0))
        self.assertEqual(state["lastAudit"]["report"], "audits/2026-01-20-audit.md")

    def test_a_nested_or_misnamed_file_is_not_an_audit_or_a_spec(self) -> None:
        self.repo.write("audits/old/2026-01-10-audit.md", f"{TRIAGE}\n")
        self.repo.write("specs/001-a/notes/summary.md", "x\n")
        self.repo.commit("noise")
        state = self.repo.state()
        self.assertEqual((state["auditsOnRef"], state["specsSinceAudit"]), (0, 0))


class FixesTest(unittest.TestCase):
    """The gate stays blocked until the audit's blocking issues are closed."""

    def setUp(self) -> None:
        self.repo = Repo()
        self.repo.audit("2026-01-10")

    def tearDown(self) -> None:
        self.repo.cleanup()

    def test_open_blocking_issue_blocks_and_others_do_not(self) -> None:
        self.repo.issues(
            [
                {"number": 7, "title": "theme", "labels": BLOCKING},
                {"number": 8, "title": "minor", "labels": ["source:audit", "severity:warning"]},
            ]
        )
        state = self.repo.state()
        self.assertTrue(state["blocked"])
        self.assertEqual(state["blockingIssues"], [{"number": 7, "title": "theme"}])
        self.assertEqual(state["reasons"], ["1 blocking audit issue(s) open: #7"])
        self.repo.issues([])
        self.assertFalse(self.repo.state()["blocked"])

    def test_a_row_without_labels_was_filtered_by_the_command_and_blocks(self) -> None:
        self.repo.issues([{"number": 5, "title": "theme"}])
        state = self.repo.state()
        self.assertEqual(state["blockingIssues"], [{"number": 5, "title": "theme"}])
        self.assertTrue(state["blocked"])

    def test_plain_string_labels_are_read(self) -> None:
        with open(os.path.join(self.repo.path, ".git", "issues.json"), "w", encoding="utf-8") as handle:
            json.dump([{"number": 6, "title": "theme", "labels": BLOCKING}], handle)
        self.assertEqual(self.repo.state()["blockingIssues"], [{"number": 6, "title": "theme"}])

    def test_remediation_start_line(self) -> None:
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING}])
        self.assertEqual(self.repo.run("start-line").returncode, 1)
        ok = self.repo.run("start-line", "--remediation", "#7")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(ok.stdout.strip(), "Audit gate: remediation of audits/2026-01-10-audit.md (#7)")
        wrong = self.repo.run("start-line", "--remediation", "#9")
        self.assertEqual(wrong.returncode, 1)
        self.assertIn("refused: #9 is not an open blocking issue", wrong.stdout)

    def test_remediation_refused_before_triage(self) -> None:
        self.repo.audit("2026-01-20", triage=False)
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING}])
        result = self.repo.run("start-line", "--remediation", "7")
        self.assertEqual(result.returncode, 1)
        self.assertIn("refused: the last audit is not triaged yet", result.stdout)

    def test_merged_remediation_spec_is_not_counted(self) -> None:
        self.repo.merge_spec("001-fix", "Audit gate: remediation of audits/2026-01-10-audit.md (#7)\n")
        self.repo.merge_spec("002-feature", "Audit gate: started at 0/3 after audits/2026-01-10-audit.md\n")
        state = self.repo.state()
        self.assertEqual(state["specs"], ["specs/002-feature"])
        self.assertEqual(state["remediationSpecs"], ["specs/001-fix"])
        self.assertEqual(state["specsSinceAudit"], 1)


class UnknownIssuesTest(unittest.TestCase):
    """When the blocking-issues command cannot answer, the issues are unknown: reported, never blocking."""

    def setUp(self) -> None:
        self.repo = Repo()
        self.repo.audit("2026-01-10")

    def tearDown(self) -> None:
        self.repo.cleanup()

    def test_each_failure_is_unknown_with_its_reason(self) -> None:
        for command, reason in (("false", "false exited 1"),
                                ("no-such-tracker-cli issue list", "no-such-tracker-cli: command not found"),
                                ("printf nope", "printf printed no JSON"),
                                ("printf '{}'", "printf printed no JSON array"),
                                ("""printf '[{"title": "x"}]'""", "issue 0 has no integer number")):
            with self.subTest(command=command):
                self.repo.tracker(command)
                state = self.repo.state()
                self.assertIn(reason, state["blockingIssuesUnknown"])
                self.assertEqual((state["blockingIssues"], state["blocked"]), ([], False))
                status = self.repo.run("status")
                self.assertEqual(status.returncode, 0)
                self.assertEqual(len(status.stdout.splitlines()), 1)
                self.assertIn("blocking issues open: unknown (", status.stdout)

    def test_the_stderr_reason_is_one_line(self) -> None:
        self.repo.tracker("sh -c 'echo; echo not a repository >&2; echo more >&2; exit 4'")
        self.assertEqual(self.repo.state()["blockingIssuesUnknown"], "sh exited 4: not a repository")

    def test_an_open_gate_still_starts_and_says_the_issues_are_unknown(self) -> None:
        self.repo.tracker("false")
        start = self.repo.run("start-line")
        self.assertEqual(start.returncode, 0, start.stdout)
        self.assertEqual(start.stdout.strip(), "Audit gate: started at 0/3 after audits/2026-01-10-audit.md")
        self.assertIn("blocking issues unknown (false exited 1); not counted", start.stderr)

    def test_the_other_reasons_still_block(self) -> None:
        self.repo.tracker("false")
        for name in ("001-a", "002-b", "003-c"):
            self.repo.merge_spec(name)
        start = self.repo.run("start-line")
        self.assertEqual(start.returncode, 1)
        self.assertIn("blocked: 3 specs merged since the last audit (threshold 3)", start.stdout)
        self.assertIn("blocking issues open: unknown (false exited 1)", start.stdout)

    def test_a_remediation_line_names_its_issues_unverified(self) -> None:
        self.repo.tracker("false")
        result = self.repo.run("start-line", "--remediation", "#7,#8")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), "Audit gate: remediation of audits/2026-01-10-audit.md (#7, #8)")
        self.assertIn("#7, #8 not verified as open blocking issues", result.stderr)

    def test_an_unparsable_command_is_a_profile_error(self) -> None:
        self.repo.tracker("cat 'unclosed")
        result = self.repo.run("status")
        self.assertEqual(result.returncode, 2)
        self.assertIn("auditGate.blockingIssues.command", result.stderr)


class CheckPrTest(unittest.TestCase):
    """check-pr runs on a feature branch against the integration ref."""

    def setUp(self) -> None:
        self.repo = Repo()
        self.repo.audit("2026-01-10")
        self.repo.merge_spec("001-a")
        self.repo.merge_spec("002-b")

    def tearDown(self) -> None:
        self.repo.cleanup()

    def branch(self, name: str, files: dict[str, str]) -> None:
        self.repo.git("switch", "-q", "-c", name, "main")
        for rel, text in files.items():
            self.repo.write(rel, text)
        self.repo.commit(name)

    def block(self) -> None:
        """Merge a third spec on main, so the gate is blocked."""
        self.repo.git("switch", "-q", "main")
        self.repo.merge_spec("003-c")

    def check(self) -> subprocess.CompletedProcess:
        return self.repo.run("check-pr", "--base", "main", "--head", "HEAD")

    def test_new_spec_passes_while_open(self) -> None:
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n"})
        self.assertEqual(self.check().returncode, 0)

    def test_new_spec_without_start_line_fails_when_blocked(self) -> None:
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n"})
        self.block()
        self.repo.git("switch", "-q", "spec/004-d")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("specs/004-d/spec.md: new development is blocked", result.stdout)

    def test_in_flight_spec_started_legally_passes(self) -> None:
        line = "- Audit gate: started at 2/3 after audits/2026-01-10-audit.md\n"
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n" + line})
        self.block()
        self.repo.git("switch", "-q", "spec/004-d")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("in flight — allowed", result.stdout)

    def test_start_line_after_an_older_audit_is_still_in_flight(self) -> None:
        line = "Audit gate: started at 1/3 after audits/2025-12-01-audit.md\n"
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n" + line})
        self.block()
        self.repo.git("switch", "-q", "spec/004-d")
        self.assertEqual(self.check().returncode, 0)

    def test_remediation_spec_passes_while_blocked_by_issues(self) -> None:
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING}])
        line = "Audit gate: remediation of audits/2026-01-10-audit.md (#7)\n"
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n" + line})
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("remediation of audits/2026-01-10-audit.md — allowed", result.stdout)

    def test_feature_spec_fails_while_blocking_issue_is_open(self) -> None:
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING}])
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n"})
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 blocking audit issue(s) open: #7", result.stdout + self.repo.run("start-line").stdout)

    def test_start_line_at_the_threshold_fails(self) -> None:
        line = "Audit gate: started at 3/3 after audits/2026-01-10-audit.md\n"
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n" + line})
        self.block()
        self.repo.git("switch", "-q", "spec/004-d")
        self.assertEqual(self.check().returncode, 1)

    def test_unknown_issues_block_neither_a_fix_nor_a_spec_on_an_open_gate(self) -> None:
        os.remove(os.path.join(self.repo.path, ".git", "issues.json"))
        self.branch("fix/y", {"src.txt": "y\n"})
        fixed = self.check()
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertIn("blocking issues unknown (cat exited 1", fixed.stdout)
        self.repo.git("switch", "-q", "main")
        self.branch("spec/004-d", {"specs/004-d/spec.md": "# d\n"})
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("new spec allowed", result.stdout)

    def test_change_without_a_new_spec_passes_when_blocked(self) -> None:
        self.block()
        self.branch("fix/x", {"specs/001-a/spec.md": "# a, amended\n", "src.txt": "x\n"})
        result = self.check()
        self.assertEqual(result.returncode, 0)
        self.assertIn("BLOCKED — specs since last audit 3/3", result.stdout)
        self.assertIn("no new spec in this change", result.stdout)


TABLE_HEAD = "| Theme | Findings | Disposition | Blocks | Escalated | Machine check | Issue |\n|---|---|---|---|---|---|---|\n"


def triage_report(*rows: str) -> str:
    """An audit report whose triage table holds the given rows."""
    return f"# Audit\n\n{TRIAGE}\n\n{TABLE_HEAD}" + "".join(row + "\n" for row in rows) + "\n## Not Audited\n"


class TriageCheckTest(unittest.TestCase):
    """Every row names a machine check; every blocking row names an open blocking issue."""

    def setUp(self) -> None:
        self.repo = Repo()
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING},
                          {"number": 8, "title": "older warning", "labels": ["source:review", "severity:warning"]}])

    def tearDown(self) -> None:
        self.repo.cleanup()

    def check(self, text: str) -> subprocess.CompletedProcess:
        self.repo.write("audits/2026-02-01-audit.md", text)
        return self.repo.run("triage-check", "--report", "audits/2026-02-01-audit.md")

    def test_a_complete_triage_passes(self) -> None:
        result = self.check(triage_report(
            "| T1 copies | F-1 | class-guard | yes | no | ratchet duplicates | #7 |",
            "| T2 naming | F-2 | touch-rule | no | no | none: one-off wording | — |"))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("passed (0 problem(s))", result.stdout)

    def test_a_blocking_row_that_continues_a_warning_issue_fails(self) -> None:
        result = self.check(triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | #8 |"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("T1 copies: blocks but names no open blocking issue (#8)", result.stdout)

    def test_a_blocking_row_passes_when_one_named_issue_blocks(self) -> None:
        result = self.check(triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | #8, #7 |"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_an_unfiled_blocking_row_fails(self) -> None:
        result = self.check(triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | (to file) |"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocks but names no open blocking issue", result.stdout)

    def test_a_row_without_a_machine_check_fails(self) -> None:
        result = self.check(triage_report(
            "| T1 copies | F-1 | fix | yes | no | — | #7 |",
            "| T2 naming | F-2 | touch-rule | no | no | none | — |",
            "| T3 drift | F-3 | fix | yes | no | none: hard to check | #7 |"))
        self.assertEqual(result.returncode, 1)
        for theme in ("T1 copies", "T2 naming", "T3 drift"):
            self.assertIn(f"{theme}: no machine check", result.stdout)

    def test_a_table_without_the_machine_check_column_fails(self) -> None:
        old = f"# Audit\n\n{TRIAGE}\n\n| Theme | Blocks | Issue |\n|---|---|---|\n| T1 | yes | #7 |\n"
        result = self.check(old)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no column: machine check", result.stdout)

    def test_unknown_issues_only_require_a_blocking_row_to_name_an_issue(self) -> None:
        self.repo.tracker("false")
        named = self.check(triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | #8 |"))
        self.assertEqual(named.returncode, 0, named.stdout)
        self.assertIn("blocking issues unknown (false exited 1)", named.stdout)
        unfiled = self.check(triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | (to file) |"))
        self.assertEqual(unfiled.returncode, 1)
        self.assertIn("T1 copies: blocks but names no issue ((to file))", unfiled.stdout)

    def test_check_pr_runs_the_triage_check_on_an_added_report(self) -> None:
        self.repo.audit("2026-01-10")
        self.repo.git("switch", "-q", "-c", "chore/audit-2026-02-01", "main")
        self.repo.write("audits/2026-02-01-audit.md",
                        triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | #8 |"))
        self.repo.commit("audit")
        result = self.repo.run("check-pr", "--base", "main", "--head", "HEAD")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("audits/2026-02-01-audit.md: triage: T1 copies: blocks but names no open blocking issue",
                      result.stdout)
        self.repo.write("audits/2026-02-01-audit.md",
                        triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | #7 |"))
        self.repo.commit("audit filed")
        result = self.repo.run("check-pr", "--base", "main", "--head", "HEAD")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("triage check passed", result.stdout)


def no_tracker_profile(form: str) -> dict:
    """The test profile without an issue tracker: `absent` drops `blockingIssues`, `empty` sets its command to ""."""
    data = json.loads(json.dumps(PROFILE))
    if form == "absent":
        del data["auditGate"]["blockingIssues"]
    else:
        data["auditGate"]["blockingIssues"] = {"command": ""}
    return data


class NoTrackerTest(unittest.TestCase):
    """`blockingIssues` absent or its command empty: no issue tracker. The cadence and the triage still run, there are
    no blocking issues (never unknown), and a blocking triage row writes `-` in its Issue cell."""

    FORMS = ("absent", "empty")

    def setUp(self) -> None:
        self.repo = Repo()
        # A tracker answer that would block if it were read.
        self.repo.issues([{"number": 7, "title": "theme", "labels": BLOCKING}])

    def tearDown(self) -> None:
        self.repo.cleanup()

    def use(self, form: str) -> None:
        self.repo.write(".claude/quality-profile.json", json.dumps(no_tracker_profile(form)))

    def triage(self, issue: str) -> subprocess.CompletedProcess:
        self.repo.write("audits/2026-02-01-audit.md",
                        triage_report(f"| T1 copies | F-1 | fix | yes | no | lint no-copy | {issue} |"))
        return self.repo.run("triage-check", "--report", "audits/2026-02-01-audit.md")

    def test_both_forms_validate(self) -> None:
        for form in self.FORMS:
            with self.subTest(form=form):
                self.assertEqual(quality_profile.validate(no_tracker_profile(form), repo=self.repo.path), [])

    def test_the_status_says_no_issue_tracker_and_nothing_blocks_on_issues(self) -> None:
        self.repo.audit("2026-01-10")
        for form in self.FORMS:
            with self.subTest(form=form):
                self.use(form)
                state = self.repo.state()
                self.assertEqual((state["blockingIssues"], state["blockingIssuesUnknown"]), ([], None))
                self.assertEqual((state["issueTracker"], state["blocked"]), (False, False))
                status = self.repo.run("status")
                self.assertEqual(status.returncode, 0, status.stderr)
                self.assertEqual(len(status.stdout.splitlines()), 1)
                self.assertIn("blocking issues open: 0 (no issue tracker)", status.stdout)
                start = self.repo.run("start-line")
                self.assertEqual(start.returncode, 0, start.stdout)
                self.assertEqual(start.stdout.strip(), "Audit gate: started at 0/3 after audits/2026-01-10-audit.md")
                self.assertEqual(start.stderr, "")

    def test_the_cadence_still_blocks(self) -> None:
        for name in ("001-a", "002-b", "003-c"):
            self.repo.merge_spec(name)
        for form in self.FORMS:
            with self.subTest(form=form):
                self.use(form)
                start = self.repo.run("start-line")
                self.assertEqual(start.returncode, 1)
                self.assertIn("blocked: 3 specs merged since the last audit (threshold 3)", start.stdout)
                self.assertNotIn("unknown", start.stdout + start.stderr)

    def test_a_blocking_row_writes_a_dash_in_the_issue_column(self) -> None:
        for form in self.FORMS:
            with self.subTest(form=form):
                self.use(form)
                dash = self.triage("-")
                self.assertEqual(dash.returncode, 0, dash.stdout)
                self.assertIn("passed (0 problem(s))", dash.stdout)
                self.assertNotIn("unknown", dash.stdout)
                for issue in ("(to file)", "#7", ""):
                    with self.subTest(issue=issue):
                        result = self.triage(issue)
                        self.assertEqual(result.returncode, 1, result.stdout)
                        self.assertIn("T1 copies: blocks but its Issue cell is", result.stdout)

    def test_a_machine_check_is_still_required(self) -> None:
        self.use("empty")
        self.repo.write("audits/2026-02-01-audit.md",
                        triage_report("| T1 copies | F-1 | fix | yes | no | — | - |"))
        result = self.repo.run("triage-check", "--report", "audits/2026-02-01-audit.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("T1 copies: no machine check", result.stdout)

    def test_check_pr_accepts_an_added_report_with_a_dash(self) -> None:
        self.repo.audit("2026-01-10")
        self.repo.git("switch", "-q", "-c", "chore/audit-2026-02-01", "main")
        self.repo.write("audits/2026-02-01-audit.md",
                        triage_report("| T1 copies | F-1 | fix | yes | no | lint no-copy | - |"))
        self.repo.commit("audit")
        for form in self.FORMS:
            with self.subTest(form=form):
                self.use(form)
                result = self.repo.run("check-pr", "--base", "main", "--head", "HEAD")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("triage check passed", result.stdout)
                self.assertIn("blocking issues open: 0 (no issue tracker)", result.stdout)
                self.assertNotIn("unknown", result.stdout)


class ProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="quality-profile-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.makedirs(os.path.join(self.dir, "specs"))
        self.path = os.path.join(self.dir, ".claude", "quality-profile.json")
        os.makedirs(os.path.dirname(self.path))

    def gate(self, profile: dict, *args: str) -> subprocess.CompletedProcess:
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(profile, handle)
        return subprocess.run([sys.executable, GATE, "--profile", self.path, *(args or ("status",))],
                              capture_output=True, text=True)

    def test_valid_profile(self) -> None:
        self.assertEqual(quality_profile.validate(PROFILE, repo=self.dir), [])

    def test_problems_are_listed(self) -> None:
        bad = json.loads(json.dumps(PROFILE))
        bad["auditGate"]["every"] = 0
        bad["auditGate"].pop("specFile")
        bad["auditGate"]["extra"] = 1
        bad["auditGate"]["blockingIssues"] = {"command": "x", "labels": []}
        self.assertEqual(
            sorted(quality_profile.validate(bad, repo=self.dir)),
            sorted([
                "auditGate.specFile: missing",
                "auditGate: unknown key: extra",
                "auditGate.every: must be at least 1",
                "auditGate.blockingIssues.labels: must be a non-empty list of strings",
            ]),
        )

    def test_a_tracker_command_still_needs_its_labels(self) -> None:
        bad = json.loads(json.dumps(PROFILE))
        bad["auditGate"]["blockingIssues"] = {"command": STUB}
        self.assertEqual(quality_profile.validate(bad, repo=self.dir), ["auditGate.blockingIssues.labels: expected list"])
        bad["auditGate"]["blockingIssues"] = {"labels": BLOCKING}
        self.assertEqual(quality_profile.validate(bad, repo=self.dir), ["auditGate.blockingIssues.command: expected str"])
        bad["auditGate"]["blockingIssues"] = []
        self.assertEqual(quality_profile.validate(bad, repo=self.dir), ["auditGate.blockingIssues: expected dict"])

    def test_boolean_threshold_is_rejected(self) -> None:
        bad = json.loads(json.dumps(PROFILE))
        bad["auditGate"]["every"] = True
        self.assertIn("auditGate.every: expected int", quality_profile.validate(bad, repo=self.dir))

    def test_gate_refuses_an_invalid_profile(self) -> None:
        result = self.gate({"auditGate": PROFILE["auditGate"]})
        self.assertEqual(result.returncode, 2)
        self.assertIn("integrationRef: required by auditGate", result.stderr)

    def test_an_unset_gate_says_so_on_one_line_and_exits_0(self) -> None:
        for command in (("status",), ("start-line",), ("check-pr", "--base", "HEAD"), ("triage-check",)):
            with self.subTest(command=command[0]):
                result = self.gate(quality_profile.skeleton(), *command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(result.stdout.splitlines()), 1)
                self.assertIn("auditGate is unset", result.stdout)

    def test_a_binding_without_the_gate_key_is_an_error(self) -> None:
        result = self.gate({"integrationRef": "main"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("no auditGate section", result.stderr)

    def test_a_missing_report_file_is_an_error(self) -> None:
        repo = Repo()
        self.addCleanup(repo.cleanup)
        result = repo.run("triage-check", "--report", "audits/nothing-audit.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("audit-gate: error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
