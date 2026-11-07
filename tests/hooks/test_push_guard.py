"""Tests for .claude/hooks/forge/push-guard.py (stdlib unittest; Python 3.9+).

The rule tables call check_command() in-process with the default config; the activation,
config and output tests run the hook as a subprocess against a throwaway project directory.
Nothing is pushed: the hook only analyses text.

Run: python3 -m unittest discover -s tests/hooks -v
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.path.join(REPO, ".claude", "hooks", "forge", "push-guard.py")
FRAGMENT = os.path.join(REPO, ".claude", "hooks", "forge", "settings-hooks.json")

spec = importlib.util.spec_from_file_location("push_guard", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

LINE = re.compile(r"^push guard \[G[1-7]\]: [^\n]+\. [^\n]+\.$")

# (command, expected rule or None for allow). Ported from the source guard's table where the
# rule is one of G1-G7; branch names follow the Forge defaults.
ROWS = [
    # --- G1: remote, refspec and destination by name ---
    ("git push origin main", "G1"),
    ("git push origin HEAD:main", "G1"),
    ("git push origin x:refs/heads/main", "G1"),
    ("git push origin refs/heads/main", "G1"),
    ("git push", "G1"),
    ("git push origin", "G1"),
    ("git push -u origin", "G1"),
    ("git push origin HEAD", "G1"),
    ("git push upstream spec/new", "G1"),
    ("git push https://example.com/r.git spec/new", "G1"),
    ("git push --repo=origin spec/new", "G1"),
    ("git push --rep=/x origin spec/new", "G1"),
    ("git push --dry-run origin HEAD:main", "G1"),
    ("git push origin spec/../main", "G1"),
    ('git push origin "$B"', "G1"),
    ("git push origin feature/x", "G1"),
    ("git push origin spec/", "G1"),
    ("git push origin v1.0", "G1"),
    ("git push origin HEAD:backup/x", "G1"),
    ("git send-pack /x main", "G1"),
    ("git http-push /x main", "G1"),
    ("GIT push origin main", "G1"),
    ("Git push origin main", "G1"),
    ("/usr/bin/GIT push origin HEAD:main", "G1"),
    ("env GiT push origin main", "G1"),
    ("git push -u origin spec/new", None),
    ("git push origin HEAD:spec/x", None),
    ("git push --set-upstream origin spec/new", None),
    ("git push --dry-run origin spec/new", None),
    ("git push --no-verify -u origin spec/new", None),
    ("git push origin fix/new", None),
    ("git push origin refactor/new", None),
    ("git push origin chore/new", None),
    ("git push origin refs/heads/spec/new:refs/heads/spec/new", None),
    ("git push -u origin spec/new 2>&1", None),
    ("git push origin HEAD:spec/015-some-feature", None),
    ("Git push origin spec/new", None),
    # --- G2: force ---
    ("git push -f origin spec/new", "G2"),
    ("git push --force origin spec/new", "G2"),
    ("git push --force-with-lease origin spec/new", "G2"),
    ("git push --force-with-lease=spec/new origin spec/new", "G2"),
    ("git push --force-if-includes origin spec/new", "G2"),
    ("git push --force-w origin spec/new", "G2"),
    ("git push origin +spec/new", "G2"),
    ("git push origin +HEAD:spec/x", "G2"),
    ("git push -uf origin spec/new", "G2"),
    # --- G3: tags and bulk pushes ---
    ("git push --tags origin", "G3"),
    ("git push --tag origin spec/new", "G3"),
    ("git push --follow-tags origin spec/new", "G3"),
    ("git push --all origin", "G3"),
    ("git push --branches origin", "G3"),
    ("git push --mirror origin", "G3"),
    ("git push origin HEAD:refs/tags/v1", "G3"),
    ("gh release create v1", "G3"),
    ("gh release upload v1 file", "G3"),
    ("git tag x", None),
    ("git branch backup/x", None),
    ("gh release list", None),
    # --- G4: remote deletion ---
    ("git push -d origin spec/x", "G4"),
    ("git push --delete origin spec/x", "G4"),
    ("git push --dele origin spec/new", "G4"),
    ("git push origin :spec/x", "G4"),
    ("git push --prune origin spec/new", "G4"),
    ("git push --prun origin spec/new", "G4"),
    ("gh pr close 12 -d", "G4"),
    ("gh pr close 12 --delete-branch", "G4"),
    ("gH pr close 12 --delete-branch", "G4"),
    ("gh api -X DELETE repos/o/r/git/refs/heads/spec/x", "G4"),
    ("git branch -D spec/old", None),
    ('gh pr close 12 --comment "Superseded by a new pull request"', None),
    # --- G5: merge, gh api writes, repository and settings writes ---
    ("gh pr merge 12", "G5"),
    ("gh pr merge --auto --squash 12", "G5"),
    ("gh pr -R x merge 12", "G5"),
    ("GH pr merge 12", "G5"),
    ("Gh pr merge --auto 12", "G5"),
    ("gh api -X PUT repos/o/r/pulls/1/merge", "G5"),
    ("gh api -XPUT repos/o/r/x", "G5"),
    ("gh api -iXPUT repos/o/r/pulls/1/merge", "G5"),
    ("gh api --method=put repos/o/r/x", "G5"),
    ("gh api repos/o/r/x -f a=b", "G5"),
    ("gh api repos/o/r/x -F a=b", "G5"),
    ("gh api repos/o/r/x --input body.json", "G5"),
    ('gh api graphql -f query="mutation { x }"', "G5"),
    ("gh api graphql -f query='MUTATION { x }'", "G5"),
    ("gh api graphql -F query=@q.graphql", "G5"),
    ("gh api graphql --input q.json", "G5"),
    ('gh api graphql -f query="$Q"', "G5"),
    ('gh api --method "$M" repos/o/r', "G5"),
    ("gh api -X PATCH repos/o/r/branches/main/protection", "G5"),
    ("gh api -X POST repos/o/r/rulesets", "G5"),
    ("gh api -X DELETE repos/o/r/environments/x", "G5"),
    ("gh api -X GET repos/o/r -X POST", "G5"),
    ("gh repo edit --enable-auto-merge", "G5"),
    ("gh repo delete x", "G5"),
    ("gh repo rename y", "G5"),
    ("gh repo archive", "G5"),
    ("gh secret set X", "G5"),
    ("gh secret list", "G5"),
    ("gh variable set X --body y", "G5"),
    ("gh workflow disable x", "G5"),
    ("gh workflow enable x", "G5"),
    ("gh workflow run deploy.yml", "G5"),
    ("gh -R o/r workflow run deploy -f env=prod", "G5"),
    ("gh run rerun 123", "G5"),
    ("gh run rerun 123 --failed", "G5"),
    ("gh run cancel 123", "G5"),
    ('bash -c "gh workflow run deploy"', "G5"),
    ("gh run watch 123", None),
    ("gh workflow view deploy.yml", None),
    ("gh alias set p 'pr merge'", "G5"),
    ("gh extension install x/y", "G5"),
    ("gh config set editor vim", "G5"),
    ("gh api repos/o/r/branches/main/protection", None),
    ("gh api -X GET repos/o/r/environments/x", None),
    ("gh api repos/o/r --jq .allow_rebase_merge", None),
    ("gh api -X GET search/issues -f q=x", None),
    ("gh api repos/o/r/rulesets", None),
    ("gh api graphql -f query='query { viewer { login } }'", None),
    ("gh pr view 12 --json mergedBy", None),
    ("gh pr create --base main --title x", None),
    ("gh pr checks 12 --watch", None),
    ("gh repo view", None),
    ("gh run list", None),
    ("gh run view 1 --log", None),
    ("gh workflow list", None),
    ("gh alias list", None),
    ("gh config get git_protocol", None),
    ("gh ruleset list", None),
    # --- G6: credentials and tokens ---
    ("git credential fill", "G6"),
    ("git credential-osxkeychain get", "G6"),
    ("gh auth token", "G6"),
    ("gh auth status -t", "G6"),
    ("gh auth status --show-token", "G6"),
    ("gh auth login", "G6"),
    ("gh auth setup-git", "G6"),
    ("gh auth status", None),
    # --- G7: configuration that re-routes pushes or hooks ---
    ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.p GIT_CONFIG_VALUE_0=push "
     "git push origin spec/new", "G7"),
    ("env GIT_CONFIG_COUNT=1 git status", "G7"),
    ("export GIT_CONFIG_COUNT=1; git status", "G7"),
    ("GIT_CONFIG_GLOBAL=/tmp/x git status", "G7"),
    ("git config include.path x", "G7"),
    ("git config core.hooksPath x", "G7"),
    ("git config alias.p push", "G7"),
    ("git config --add remote.origin.push x", "G7"),
    ("git config remote.origin.url x", "G7"),
    ("git config remote.pushDefault upstream", "G7"),
    ("git config branch.spec/x.pushRemote upstream", "G7"),
    ("git config push.default matching", "G7"),
    ("git config set alias.x y", "G7"),
    ("git config --global URL.x.pushInsteadOf y", "G7"),
    ("git -c alias.p=push p origin x", "G7"),
    ("git -c core.hooksPath=/x status", "G7"),
    ("git -ccore.hooksPath=/x status", "G7"),
    ("git --config-env=alias.p=VAR status", "G7"),
    ("git remote set-url origin x", "G7"),
    ("git remote add x y", "G7"),
    ("git remote rename a b", "G7"),
    ("git config user.name", None),
    ("git config user.name x", None),
    ("git config --get remote.origin.url", None),
    ("git remote -v", None),
    ("git -c color.ui=never log", None),
    ("GIT_CONFIG_COUNT=1 echo x", None),
    # --- wrappers, nesting and env-prefixed commands ---
    ("rtk git push origin main", "G1"),
    ("rtk proxy git push origin main", "G1"),
    ('bash -c "git push origin main"', "G1"),
    ('bash -c -l "git push origin main"', "G1"),
    ("bash -c 'bash -c \"git push origin main\"'", "G1"),
    ('sh -c "gh pr merge 3"', "G5"),
    ('env -S "git push origin main"', "G1"),
    ("eval git push origin main", "G1"),
    ("echo spec/x | xargs git push origin", "G1"),
    ("git -C /y push origin main", "G1"),
    ("git -C /y push --force origin spec/x", "G2"),
    ("git -C /y push -u origin spec/x", None),
    ("git --git-dir=/y/.git push origin spec/x", None),
    ("sudo git push origin main", "G1"),
    ("env FOO=1 git push origin main", "G1"),
    ("VAR=1 git push origin main", "G1"),
    ("FOO=1 BAR=2 git push -u origin spec/x", None),
    ("timeout 5 git push origin main", "G1"),
    ("nohup git push -f origin spec/x", "G2"),
    ("command git push origin main", "G1"),
    ("pnpm exec git push origin main", "G1"),
    ('npx sh -c "git push origin main"', "G1"),
    ('echo "git push origin main" | bash', "G1"),
    ("bash <<EOF\ngit push origin main\nEOF", "G1"),
    ('bash <<< "git push origin main"', "G1"),
    ("sh <<<'gh pr merge 3'", "G5"),
    ("X=git; $X push origin main", "G1"),
    ('g=git; FOO="$X" $g push origin main', "G1"),
    ("$G push origin main", "G1"),
    ("$(echo gh) pr merge 1", "G1"),
    ("echo $(git push origin main)", "G1"),
    ("echo `git push origin main`", "G1"),
    ("true && git push origin main", "G1"),
    ("git status; git push origin main", "G1"),
    ("git add -A && git commit -m x && git push -u origin spec/x", None),
    ("git status | cat && git push origin main", "G1"),
    ("if true; then git push origin main; fi", "G1"),
    ("rtk gh pr merge 3", "G5"),
    ('cat <<< "git push origin main"', None),
    ('FOO="$X" git status', None),
    ('GIT_AUTHOR_DATE="$d" git commit -m x', None),
    ("rtk git status", None),
    ('bash -c "git status"', None),
    ("echo hi | xargs echo", None),
    ("pnpm install", None),
    ("npm run build", None),
    # --- text that only mentions commands ---
    ('git commit -m "git push origin main"', None),
    ("git commit -m \"$(cat <<'EOF'\nfix: don't git push origin main\nEOF\n)\"", None),
    ('echo "gh pr merge 1"', None),
    ("cat <<EOF\ngit push origin main\nEOF", None),
    ("echo 'git push origin main' # git push origin main", None),
    # --- ordinary work ---
    ("git status", None),
    ("git log --oneline -5", None),
    ("git diff HEAD~1", None),
    ("git checkout -b spec/x", None),
    ('git commit -m "feat: x"', None),
    ("gh pr view 12", None),
    ("gh pr list", None),
    ("cd /tmp && git status", None),
    ("git fetch origin", None),
    ("git worktree list", None),
    ("git log --format='%H %s' | head", None),
    ("git merge --ff-only x", None),
    ("ls -la | head", None),
    ("$EDITOR file.txt", None),
]


def deny_of(command, cfg=None):
    """The Deny the guard raises for command, or None when it allows."""
    try:
        guard.check_command(command, cfg or guard.Config())
    except guard.Deny as d:
        return d
    return None


class RuleTableTest(unittest.TestCase):
    def test_rows(self):
        cfg = guard.Config()
        for command, rule in ROWS:
            with self.subTest(command=command):
                d = deny_of(command, cfg)
                self.assertEqual(d.rule if d else None, rule)
                if d:
                    line = d.line(cfg)
                    self.assertRegex(line, LINE)
                    self.assertIn("_autonomous-mode.md", line)
                    self.assertIn("only the user merges, force-pushes, tags or changes settings",
                                  line)

    def test_every_rule_has_allow_and_deny_rows(self):
        rules = {r for _c, r in ROWS if r}
        self.assertEqual(rules, {"G1", "G2", "G3", "G4", "G5", "G6", "G7"})
        self.assertTrue(any(r is None for _c, r in ROWS))

    def test_nesting_deeper_than_limit_is_refused(self):
        cmd = "git push origin main"
        for _ in range(guard.MAX_DEPTH + 2):
            cmd = "bash -c %s" % json.dumps(cmd)
        d = deny_of(cmd)
        self.assertIsNotNone(d)
        self.assertEqual(d.rule, "G1")


class ConfigTest(unittest.TestCase):
    def test_remote_from_config(self):
        cfg = guard.Config(remote="upstream")
        self.assertIsNone(deny_of("git push -u upstream spec/x", cfg))
        self.assertEqual(deny_of("git push -u origin spec/x", cfg).rule, "G1")
        self.assertIn("git push -u upstream <branch>", deny_of("git push", cfg).line(cfg))

    def test_prefixes_from_config(self):
        cfg = guard.Config(prefixes=guard.parse_prefixes("feat/ hotfix/"))
        self.assertIsNone(deny_of("git push origin HEAD:feat/x", cfg))
        self.assertIsNone(deny_of("git push origin hotfix/y", cfg))
        self.assertEqual(deny_of("git push origin spec/x", cfg).rule, "G1")

    def test_default_branch_is_never_a_destination(self):
        cfg = guard.Config(prefixes=("release/",), default_branch="release/main")
        self.assertIsNone(deny_of("git push origin release/1.2", cfg))
        d = deny_of("git push origin HEAD:release/main", cfg)
        self.assertEqual(d.rule, "G1")
        self.assertIn("default branch", d.refused)

    def test_parse_prefixes(self):
        self.assertEqual(guard.parse_prefixes("a/  b/ "), ("a/", "b/"))
        self.assertEqual(guard.parse_prefixes(["a/", " b/", 3]), ("a/", "b/"))
        self.assertEqual(guard.parse_prefixes(""), guard.DEFAULT_PREFIXES)
        self.assertEqual(guard.parse_prefixes(None), guard.DEFAULT_PREFIXES)
        self.assertEqual(guard.parse_prefixes({"a": 1}), guard.DEFAULT_PREFIXES)
        self.assertEqual(guard.DEFAULT_PREFIXES, ("spec/", "fix/", "refactor/", "chore/"))


class HookProcessTest(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="push-guard-")
        self.addCleanup(shutil.rmtree, self.project, True)
        os.makedirs(os.path.join(self.project, ".claude"))

    def config(self, data=None, raw=None):
        with open(os.path.join(self.project, ".claude", "project-config.json"), "w") as f:
            f.write(raw if raw is not None else json.dumps(data))

    def run_hook(self, command=None, stdin=None, tool="Bash", **env):
        full = {k: v for k, v in os.environ.items() if k != "FORGE_PUSH_GUARD"}
        full["CLAUDE_PROJECT_DIR"] = self.project
        full.update(env)
        if stdin is None:
            stdin = json.dumps({"tool_name": tool, "tool_input": {"command": command},
                                "cwd": self.project})
        proc = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True,
                              text=True, env=full, timeout=30)
        return proc.returncode, proc.stderr, proc.stdout

    def test_autonomous_denies_with_one_line(self):
        self.config({"DELIVERY_MODE": "autonomous"})
        code, err, out = self.run_hook("git push origin main")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.splitlines()), 1)
        self.assertRegex(err.strip(), LINE)
        self.assertTrue(err.startswith("push guard [G1]: "))

    def test_autonomous_allows_feature_branch(self):
        self.config({"DELIVERY_MODE": "autonomous"})
        self.assertEqual(self.run_hook("git push -u origin spec/x"), (0, "", ""))

    def test_interactive_is_inactive(self):
        self.config({"DELIVERY_MODE": "interactive"})
        self.assertEqual(self.run_hook("git push --force origin main"), (0, "", ""))

    def test_missing_config_is_inactive(self):
        self.assertEqual(self.run_hook("gh pr merge 1"), (0, "", ""))

    def test_invalid_config_is_inactive(self):
        self.config(raw="{not json")
        self.assertEqual(self.run_hook("gh pr merge 1"), (0, "", ""))
        self.config(["autonomous"])
        self.assertEqual(self.run_hook("gh pr merge 1"), (0, "", ""))
        self.config({"DELIVERY_MODE": 1})
        self.assertEqual(self.run_hook("gh pr merge 1"), (0, "", ""))

    def test_env_forces_on(self):
        self.config({"DELIVERY_MODE": "interactive"})
        code, err, _ = self.run_hook("gh pr merge 1", FORGE_PUSH_GUARD="1")
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("push guard [G5]: "))

    def test_env_forces_on_without_config_uses_defaults(self):
        code, err, _ = self.run_hook("git push origin main", FORGE_PUSH_GUARD="1")
        self.assertEqual(code, 2)
        self.assertIn("spec/* fix/* refactor/* chore/*", err)
        code, _, _ = self.run_hook("git push origin refactor/x", FORGE_PUSH_GUARD="1")
        self.assertEqual(code, 0)

    def test_env_forces_off(self):
        self.config({"DELIVERY_MODE": "autonomous"})
        self.assertEqual(self.run_hook("git push --force origin main", FORGE_PUSH_GUARD="0"),
                         (0, "", ""))

    def test_config_values_are_strings(self):
        self.config({"DELIVERY_MODE": "autonomous", "PUSH_REMOTE": "fork",
                     "PUSH_BRANCH_PREFIXES": "feat/ docs/", "DEFAULT_BRANCH": "develop"})
        self.assertEqual(self.run_hook("git push -u fork feat/x")[0], 0)
        self.assertEqual(self.run_hook("git push -u fork docs/y")[0], 0)
        code, err, _ = self.run_hook("git push -u origin feat/x")
        self.assertEqual(code, 2)
        self.assertIn("only fork is allowed", err)
        self.assertEqual(self.run_hook("git push fork spec/x")[0], 2)
        self.assertEqual(self.run_hook("git push fork HEAD:develop")[0], 2)

    def test_prefixes_as_json_list(self):
        self.config({"DELIVERY_MODE": "autonomous", "PUSH_BRANCH_PREFIXES": ["feat/"]})
        self.assertEqual(self.run_hook("git push origin feat/x")[0], 0)
        self.assertEqual(self.run_hook("git push origin spec/x")[0], 2)

    def test_blank_values_fall_back_to_defaults(self):
        self.config({"DELIVERY_MODE": "autonomous", "PUSH_REMOTE": " ",
                     "PUSH_BRANCH_PREFIXES": "", "DEFAULT_BRANCH": ""})
        self.assertEqual(self.run_hook("git push origin chore/x")[0], 0)
        self.assertEqual(self.run_hook("git push origin main")[0], 2)

    def test_other_tools_and_bad_payloads_are_allowed(self):
        self.config({"DELIVERY_MODE": "autonomous"})
        self.assertEqual(self.run_hook("git push origin main", tool="Write")[0], 0)
        self.assertEqual(self.run_hook(stdin="not json")[0], 0)
        self.assertEqual(self.run_hook(stdin="git push origin main {")[0], 0)
        bad = json.dumps({"tool_name": "Bash", "tool_input": "git push origin main"})
        self.assertEqual(self.run_hook(stdin=bad)[0], 0)
        self.assertEqual(self.run_hook("")[0], 0)

    def test_unparsable_guarded_command_is_denied(self):
        self.config({"DELIVERY_MODE": "autonomous"})
        for cmd in ('git push origin "main', "gh pr merge 'x", "git push origin main; echo $("):
            with self.subTest(command=cmd):
                code, err, _ = self.run_hook(cmd)
                self.assertEqual(code, 2)
                self.assertTrue(err.startswith("push guard [G1]: "))
        self.assertEqual(self.run_hook('echo "unbalanced')[0], 0)


class InternalErrorTest(unittest.TestCase):
    def run_main(self, stdin):
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch.object(sys, "stderr", err):
            code = guard.main()
        return code, err.getvalue()

    def payload(self, command):
        return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_crash_in_analysis_allows(self):
        with mock.patch.dict(os.environ, {"FORGE_PUSH_GUARD": "1"}), \
                mock.patch.object(guard, "analyse_text", side_effect=RuntimeError("bug")):
            self.assertEqual(self.run_main(self.payload("git push origin main")), (0, ""))

    def test_crash_in_settings_allows(self):
        with mock.patch.object(guard, "settings", side_effect=KeyError("x")):
            self.assertEqual(self.run_main(self.payload("gh pr merge 1")), (0, ""))

    def test_main_denies_in_process(self):
        with mock.patch.dict(os.environ, {"FORGE_PUSH_GUARD": "1"}):
            code, err = self.run_main(self.payload("gh pr merge 1"))
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("push guard [G5]: "))


class RegistrationTest(unittest.TestCase):
    def test_fragment_registers_the_guard(self):
        with open(FRAGMENT) as f:
            hooks = json.load(f)["hooks"]
        entries = [h for group in hooks.get("PreToolUse", []) if group.get("matcher") == "Bash"
                   for h in group["hooks"]]
        found = [h for h in entries if "push-guard.py" in h.get("command", "")]
        self.assertEqual(len(found), 1)
        hook = found[0]
        self.assertEqual(hook["type"], "command")
        self.assertEqual(hook["command"],
                         'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/forge/push-guard.py"')
        self.assertLessEqual(hook["timeout"], 10)
        self.assertNotIn("|| true", hook["command"])


if __name__ == "__main__":
    unittest.main()
