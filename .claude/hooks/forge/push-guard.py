#!/usr/bin/env python3
"""Push guard (PreToolUse hook, matcher Bash, Forge-owned).

During autonomous delivery an agent pushes its own branch and opens a pull request; everything
past that is the user's. This hook refuses the Bash commands that would go past it. It stops
accidental and instruction-following actions, not a hostile agent. Out of scope, covered by
the written rule only (.claude/commands/_autonomous-mode.md -> "Pull requests"): interpreters
(`python -c`, `node -e`) and script files, edits of git or gh configuration files and of this
hook, reading token environment variables or gh's hosts file, and `--no-verify` (local hooks
are the project's, not a push boundary).

Rules (a denial names one):
- G1  push only to PUSH_REMOTE, only with an explicit literal refspec, only to a branch whose
      destination starts with one of PUSH_BRANCH_PREFIXES (checked by name). DEFAULT_BRANCH is
      never a destination. A bare `HEAD` refspec, `$(git branch --show-current)`,
      `$(git rev-parse --abbrev-ref HEAD)` and `$(git symbolic-ref --short HEAD)` resolve to the
      current branch (`git -C <dir> rev-parse --abbrev-ref HEAD`, <dir> from `git -C`, a literal
      `cd` or the hook's cwd), which then must pass the same rules; an unresolvable directory, a
      failed lookup or a detached HEAD is refused. Plumbing pushes (send-pack, http-push) and
      `--repo` are refused.
- G2  no force push: -f, --force, --force-with-lease, --force-if-includes, `+refspec`.
- G3  no tags or bulk pushes: --tags, --follow-tags, --all, --branches, --mirror,
      refs/tags/ destinations, `gh release create|delete|edit|upload`.
- G4  no remote branch deletion or rewrite: -d, --delete, --prune, `:branch`, `gh pr close
      --delete-branch`, `gh api -X DELETE .../git/refs/...`, `gh repo sync`.
- G5  no merges or repository writes through gh: `gh pr merge`, `gh api` with a non-GET method
      (-f/-F/--input imply POST; GraphQL only as one literal read-only query), repo
      edit/delete/rename/archive, any `gh secret` / `gh variable`, `gh workflow
      run|enable|disable` and `gh run rerun|cancel|delete` (a dispatch or rerun can deploy),
      `gh label create|edit|delete|clone`, alias/extension/config writes. A gh command group or
      verb that is not a literal is refused too.
- G6  no credential or token reads or key changes: `git credential*`, `gh auth token|login|
      logout|refresh|setup-git|switch`, `gh auth status --show-token`, `gh ssh-key add|delete`,
      `gh repo deploy-key add|delete`.
- G7  no git configuration that re-routes pushes, credentials or hooks: `git config` of alias.*,
      remote.*.push|pushurl|url|mirror, remote.pushDefault, branch.*.pushRemote|remote|merge,
      push.*, url.*.insteadOf|pushInsteadOf, include*, core.hooksPath, core.sshCommand,
      credential.*helper; the same keys through `git -c`
      or `--config-env`; GIT_CONFIG_* assignments in a command that runs git; `git remote
      add|set-url|rename`.

The shell text is tokenized (quotes, heredocs, here-strings, $( ) and backticks), split at
`;`, `&&`, `||`, `|` and newlines, and each simple command is unwrapped (NAME=value prefixes,
env, sudo, nice, timeout, nohup, command, exec, xargs, rtk, package runners) before the rules
apply. `bash -c` (options after -c skipped), `sh -c`, `eval`, `env -S`, `su|runuser|script|
flock -c`, the string arguments of `watch` and `parallel`, shells fed by a heredoc and the
substitutions inside an unquoted heredoc body are analysed in turn (up to 5 levels). Any other
command that is not a plain data command (echo, cat, grep, ...) is searched for a later literal
word naming git or gh, and the words from there are analysed as a command (`find -exec`,
`setsid`, `arch`, `ionice`, `chronic`, ...). git or gh under xargs without a literal guarded
verb, a shell fed by a pipe, a non-literal command word or deeper nesting in a command that
mentions git or gh is refused (G1, G5 for gh). Command words match case-insensitively.

Activation (Forge decision): active only when `.claude/project-config.json` (under
$CLAUDE_PROJECT_DIR; when that is unset, the first one found walking up from the hook's cwd to
the git toplevel) has DELIVERY_MODE "autonomous", or when the
environment sets FORGE_PUSH_GUARD=1. FORGE_PUSH_GUARD=0 forces it off. A missing or invalid
config file counts as interactive (inactive) unless FORGE_PUSH_GUARD=1. Inactive = exit 0.

Configuration (`.claude/project-config.json`; every value is a JSON string):
- PUSH_REMOTE           the one remote agents push to (default "origin").
- PUSH_BRANCH_PREFIXES  space-separated allowed destination prefixes (default
                        "spec/ fix/ refactor/ chore/"); a JSON list of strings is accepted too.
                        Missing, blank or malformed means the default.
- DEFAULT_BRANCH        the integration branch (default "main"); never an allowed destination.

Output: allow = exit 0, silent. Deny = exit 2 plus one stderr line
`push guard [G<n>]: <what was refused>. <alternative>.`, which Claude Code shows to Claude.
There is no override flag beyond FORGE_PUSH_GUARD.

Errors never block: an unreadable payload, an unreadable config or a bug in the analysis
allows the command (exit 0). One deliberate exception: a command the tokenizer cannot parse
(unbalanced quotes, unterminated substitution) that mentions git or gh with a guarded verb is
denied (G1); bash would refuse most such text too, and the rest is where tokenizer and shell
disagree. Python 3.9+, standard library only.
"""
import json
import os
import posixpath
import re
import subprocess
import sys

MAX_DEPTH = 5
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
KEYWORDS = {"if", "then", "do", "else", "elif", "while", "until", "!", "{", "}", "fi", "done"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
GIT_CFG_ENV = re.compile(r"^GIT_CONFIG_(COUNT|KEY_.*|VALUE_.*|PARAMETERS|GLOBAL|SYSTEM)=")
PUSH_LONG = ("--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete",
             "--prune", "--tags", "--follow-tags", "--all", "--branches", "--repo",
             "--push-option", "--receive-pack", "--exec")
FORCE_OPTS = ("--force", "--force-with-lease", "--force-if-includes")
DELETE_OPTS = ("--delete", "--prune")
BULK_OPTS = ("--tags", "--follow-tags", "--all", "--branches", "--mirror")
DST_CHARS = re.compile(r"^[A-Za-z0-9._/-]+$")
# A word boundary for the pre-filters: `-`, `.` and a following `/` count as part of the word,
# so `test-push-guard.py` and `.git/` do not match; a leading `/` does (`/usr/bin/git`).
WORD_L, WORD_R = r"(?<![\w.-])", r"(?![\w./-])"
GUARDED_WORD = re.compile(WORD_L + r"(git|gh|push)" + WORD_R, re.I)
CURRENT_BRANCH_SUBS = ("git branch --show-current", "git rev-parse --abbrev-ref HEAD",
                       "git symbolic-ref --short HEAD")
DATA_COMMANDS = {"echo", "printf", "cat", "grep", "egrep", "fgrep", "rg", "ag", "sed", "awk",
                 "head", "tail", "less", "more", "wc", "sort", "uniq", "cut", "tr", "ls", "test",
                 "[", "[[", "true", "false", ":", "mkdir", "rmdir", "rm", "cp", "mv", "touch",
                 "ln", "chmod", "type", "which", "whereis", "man", "tee", "diff", "jq", "read",
                 "unset", "set", "alias", "basename", "dirname", "realpath", "readlink", "stat",
                 "file", "du", "df", "pwd", "date", "sleep", "exit", "return", "local"}
DASH_C_RUNNERS = ("su", "runuser", "script", "flock")
STRING_RUNNERS = ("watch", "parallel")
BAD_CFG_KEY = re.compile(
    r"^(alias\..+|remote\..+\.(push|pushurl|url|mirror)|remote\.pushdefault"
    r"|branch\..+\.(pushremote|remote|merge)|push\..+|url\..+\.(insteadof|pushinsteadof)"
    r"|include\..+|includeif\..+|core\.hookspath|core\.sshcommand|credential\.(.+\.)?helper)$")
PKG_RUNNERS = ("pnpm", "npx", "npm", "yarn", "bunx", "pnpx")
PKG_OPT_ARG = ("--filter", "-F", "-C", "--dir", "--package", "-p", "--prefix", "--workspace",
               "-w", "--call")

CONFIG_FILE = os.path.join(".claude", "project-config.json")
DEFAULT_REMOTE = "origin"
DEFAULT_PREFIXES = ("spec/", "fix/", "refactor/", "chore/")
DEFAULT_BRANCH = "main"

FLOW_REF = '.claude/commands/_autonomous-mode.md -> "Pull requests"'
USER_ONLY = "only the user merges, force-pushes, tags or changes settings"
ALT_PUSH = "push"            # alternative built from the config (see Deny.line)
ALT_MERGE = ("Report the pull request as ready for the user to merge instead; %s (%s)"
             % (USER_ONLY, FLOW_REF))
ALT_USER = "Report the blocked action instead; %s (%s)" % (USER_ONLY, FLOW_REF)


class Config:
    """The push destination rules in effect."""

    def __init__(self, remote=DEFAULT_REMOTE, prefixes=DEFAULT_PREFIXES,
                 default_branch=DEFAULT_BRANCH):
        self.remote = remote
        self.prefixes = tuple(prefixes)
        self.default_branch = default_branch


class Deny(Exception):
    """A rule refused the command; carries the rule id, what was refused and the alternative."""

    def __init__(self, rule, refused, alt=ALT_PUSH):
        super().__init__(refused)
        self.rule = rule
        self.refused = " ".join(refused.split())
        self.alt = alt

    def line(self, cfg):
        """The one stderr line."""
        alt = self.alt
        if alt == ALT_PUSH:
            alt = ("Push a %s branch to %s by name without force (git push -u %s <branch>) and "
                   "open a pull request; %s (%s)"
                   % (" ".join(p + "*" for p in cfg.prefixes), cfg.remote, cfg.remote,
                      USER_ONLY, FLOW_REF))
        return "push guard [%s]: %s. %s." % (self.rule, self.refused, alt)


class Untokenizable(Exception):
    """The command text has unbalanced quotes or an unterminated substitution."""


class SubWord(str):
    """A word that is exactly one command substitution; `raw` is the substituted text."""

    raw = ""


def body_subs(body):
    """The $( ) and backtick substitutions of an unquoted heredoc body, as segment lists."""
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if c == "\\":
            i += 2
        elif body.startswith("$(", i):
            tk = Tokenizer(body, i + 2, True)
            out.append(tk.parse())
            i = tk.i
        elif c == "`":
            k = i + 1
            while k < n and body[k] != "`":
                k += 2 if body[k] == "\\" else 1
            if k >= n:
                raise Untokenizable()
            out.append(Tokenizer(body[i + 1:k].replace("\\`", "`")).parse())
            i = k + 1
        else:
            i += 1
    return out


class Seg:
    """One simple command: its words as (text, literal) pairs and what hangs off it."""

    def __init__(self, words, piped, heres, subs):
        self.words = words    # list of (text, is_literal)
        self.piped = piped    # fed by a pipe from the previous segment
        self.heres = heres    # heredoc and here-string bodies (list of one-element lists)
        self.subs = subs      # nested segment lists from $( ) and backticks


class Tokenizer:
    """Splits shell text into segments of words; quotes, heredocs, redirects and
    substitutions are resolved as far as the rules need them."""

    def __init__(self, text, pos=0, sub=False):
        self.t = text
        self.i = pos
        self.sub = sub

    def parse(self):
        """Tokenize from self.i; in sub mode stop after the matching `)`."""
        t, n = self.t, len(self.t)
        segs = []
        st = {"words": [], "heres": [], "subs": [], "piped": False, "cur": [],
              "lit": True, "has": False, "drop": False, "sub_raw": None}
        pending = []
        depth = 0

        def end_word():
            if st["has"]:
                if st["drop"]:
                    if st["drop"] == "here":
                        # here-string operand: kept like a heredoc body so a shell fed by it is analysed
                        st["heres"].append(["".join(st["cur"])])
                    st["drop"] = False
                else:
                    word = "".join(st["cur"])
                    if word == "$SUB" and st["sub_raw"] is not None:
                        word = SubWord(word)
                        word.raw = st["sub_raw"]
                    st["words"].append((word, st["lit"]))
            st["cur"], st["lit"], st["has"], st["sub_raw"] = [], True, False, None

        def end_seg(next_piped):
            end_word()
            if st["words"] or st["heres"]:
                segs.append(Seg(st["words"], st["piped"], st["heres"], st["subs"]))
            st["words"], st["heres"], st["subs"] = [], [], []
            st["piped"], st["drop"] = next_piped, False

        def sub_at(j):
            tk = Tokenizer(t, j, True)
            st["subs"].append(tk.parse())
            st["sub_raw"] = t[j:tk.i - 1]
            return tk.i

        def backtick_at(j):
            k = j + 1
            while k < n and t[k] != "`":
                k += 2 if t[k] == "\\" else 1
            if k >= n:
                raise Untokenizable()
            st["subs"].append(Tokenizer(t[j + 1:k].replace("\\`", "`")).parse())
            st["sub_raw"] = t[j + 1:k]
            return k + 1

        def drop_fd_or_end():
            if st["has"] and "".join(st["cur"]).isdigit():
                st["cur"], st["lit"], st["has"] = [], True, False
            else:
                end_word()

        i = self.i
        while i < n:
            c = t[i]
            if c == "\\":
                if i + 1 < n and t[i + 1] != "\n":
                    st["cur"].append(t[i + 1])
                    st["has"] = True
                i += 2
            elif c == "'":
                j = t.find("'", i + 1)
                if j < 0:
                    raise Untokenizable()
                st["cur"].append(t[i + 1:j])
                st["has"] = True
                i = j + 1
            elif c == '"':
                st["has"] = True
                i += 1
                while True:
                    if i >= n:
                        raise Untokenizable()
                    d = t[i]
                    if d == '"':
                        i += 1
                        break
                    if d == "\\" and i + 1 < n:
                        nx = t[i + 1]
                        if nx in '"\\$`':
                            st["cur"].append(nx)
                        elif nx != "\n":
                            st["cur"].append(d + nx)
                        i += 2
                    elif d == "$" and t.startswith("$(", i):
                        i = sub_at(i + 2)
                        st["cur"].append("$SUB")
                        st["lit"] = False
                    elif d == "`":
                        i = backtick_at(i)
                        st["cur"].append("$SUB")
                        st["lit"] = False
                    else:
                        if d == "$":
                            st["lit"] = False
                        st["cur"].append(d)
                        i += 1
            elif c == "`":
                i = backtick_at(i)
                st["cur"].append("$SUB")
                st["lit"], st["has"] = False, True
            elif c == "$":
                st["has"] = True
                if t.startswith("$(", i):
                    i = sub_at(i + 2)
                    st["cur"].append("$SUB")
                    st["lit"] = False
                elif t.startswith("$'", i):
                    j = i + 2
                    while j < n and t[j] != "'":
                        j += 2 if t[j] == "\\" else 1
                    if j >= n:
                        raise Untokenizable()
                    st["cur"].append(t[i + 2:j])
                    i = j + 1
                else:
                    st["lit"] = False
                    st["cur"].append("$")
                    i += 1
            elif c in " \t\r":
                end_word()
                i += 1
            elif c == "\n":
                end_seg(False)
                i += 1
                if pending:
                    for ph, delim, strip, quoted, subs in pending:
                        lines = []
                        while i < n:
                            k = t.find("\n", i)
                            k = n if k < 0 else k
                            line = t[i:k]
                            i = k + 1
                            if (line.lstrip("\t") if strip else line) == delim:
                                break
                            lines.append(line)
                        ph.append("\n".join(lines))
                        if not quoted:  # bash expands $( ) and backticks in an unquoted body
                            subs.extend(body_subs(ph[-1]))
                    pending = []
                    i = min(i, n)
            elif c == ";":
                end_seg(False)
                i += 1
            elif c == "|":
                if t.startswith("||", i):
                    end_seg(False)
                    i += 2
                else:
                    end_seg(True)
                    i += 2 if t.startswith("|&", i) else 1
            elif c == "&":
                if t.startswith("&>", i):
                    end_word()
                    i += 3 if t.startswith("&>>", i) else 2
                    st["drop"] = True
                else:
                    end_seg(False)
                    i += 2 if t.startswith("&&", i) else 1
            elif c == "(":
                depth += 1 if self.sub else 0
                end_seg(False)
                i += 1
            elif c == ")":
                end_seg(False)
                i += 1
                if self.sub:
                    if depth == 0:
                        self.i = i
                        return segs
                    depth -= 1
            elif c == "#" and not st["has"]:
                k = t.find("\n", i)
                i = n if k < 0 else k
            elif c in "<>":
                if t.startswith("<<<", i):
                    drop_fd_or_end()
                    i += 3
                    st["drop"] = "here"
                elif t.startswith("<<", i):
                    drop_fd_or_end()
                    i += 2
                    strip = t.startswith("-", i)
                    i += 1 if strip else 0
                    while i < n and t[i] in " \t":
                        i += 1
                    if i < n and t[i] in "'\"":
                        k = t.find(t[i], i + 1)
                        if k < 0:
                            raise Untokenizable()
                        delim, i, quoted = t[i + 1:k], k + 1, True
                    else:
                        k = i
                        while k < n and t[k] not in " \t\n;|&()<>":
                            k += 1
                        quoted = any(q in t[i:k] for q in "\\'\"")
                        delim, i = re.sub(r"[\\'\"]", "", t[i:k]), k
                    ph = []
                    st["heres"].append(ph)
                    pending.append((ph, delim, strip, quoted, st["subs"]))
                else:
                    drop_fd_or_end()
                    i += 1
                    if i < n and ((c == ">" and t[i] in ">&|") or (c == "<" and t[i] in "&>")):
                        i += 1
                    st["drop"] = True
            else:
                st["cur"].append(c)
                st["has"] = True
                i += 1
        if self.sub:
            raise Untokenizable()
        end_seg(False)
        self.i = n
        return segs


def guarded_pair(raw):
    """True when the raw text pairs git or gh with a verb the rules guard (fail-closed test)."""
    def has(w):
        return re.search(WORD_L + w + WORD_R, raw, re.I) is not None
    if has("git") and (has("push") or has("config") or has("credential") or has("remote")):
        return True
    return has("gh") and re.search(
        WORD_L + r"(pr|api|secret|variable|repo|workflow|run|release|alias|extension|ext|auth"
        r"|config|label|ssh-key)" + WORD_R, raw, re.I) is not None


class State:
    """Effective directory (None = unknown), the pushd stack, and the flags and config shared by
    one whole command (item access reaches the shared dict)."""

    def __init__(self, cwd, shared, stack=None):
        self.cwd = cwd
        self.shared = shared
        self.stack = stack or []

    def fork(self):
        """A copy for a subshell: own directory state, shared flags."""
        return State(self.cwd, self.shared, list(self.stack))

    def __getitem__(self, key):
        return self.shared[key]

    def __setitem__(self, key, value):
        self.shared[key] = value


def resolve(base, target, literal=True):
    """Directory after `cd target` from base; None when it cannot be known literally."""
    if not literal or target in ("-", "") or target.startswith("~"):
        return None
    if posixpath.isabs(target):
        return posixpath.normpath(target)
    return posixpath.normpath(posixpath.join(base, target)) if base else None


def note_assign(word, st):
    """Record GIT_CONFIG_* (G7 fires when the same command runs git) and GIT_DIR/GIT_WORK_TREE
    assignments (the current branch can then not be resolved)."""
    if GIT_CFG_ENV.match(word):
        st["cfg_env"] = True
    if re.match(r"^GIT_(DIR|WORK_TREE)=", word):
        st["git_dir_env"] = True


def basename(w):
    """Final path component of a command word, lower-cased: a case-insensitive file system runs
    `GH` and `Git` as the real tools. Only command words go through here; arguments keep case."""
    return w.rsplit("/", 1)[-1].lower()


def skip_opts(rest, with_arg=()):
    """Drop leading `-x` options (and the argument of those named in with_arg)."""
    while rest and rest[0][0].startswith("-") and rest[0][0] != "-":
        w = rest[0][0]
        rest = rest[2:] if w in with_arg else rest[1:]
    return rest


def unwrap(words, st):
    """Strip assignments, keywords and wrappers; return (remaining words, under_xargs)."""
    rest, xargs = list(words), False
    # A leading NAME=value word is an assignment even when its value is non-literal
    # (FOO="$X" git status); only a non-assignment non-literal word stops the unwrap.
    while rest and (rest[0][1] or ASSIGN.match(rest[0][0])):
        w = rest[0][0]
        b = basename(w)
        if ASSIGN.match(w):
            note_assign(w, st)
            rest = rest[1:]
        elif w in KEYWORDS or b in ("command", "builtin", "exec", "noglob", "nohup", "time"):
            rest = skip_opts(rest[1:])
        elif b == "env":
            rest = rest[1:]
            while rest and (rest[0][0].startswith("-") or ASSIGN.match(rest[0][0])):
                if ASSIGN.match(rest[0][0]):
                    note_assign(rest[0][0], st)
                    rest = rest[1:]
                elif rest[0][0] in ("-S", "--split-string") and len(rest) > 1:
                    # env -S "git push ...": the string is split into a command line.
                    analyse_text(rest[1][0], st.fork(), MAX_DEPTH - 1)
                    rest = rest[2:]
                else:
                    rest = rest[2:] if rest[0][0] in ("-u", "-C") else rest[1:]
        elif b == "sudo":
            rest = skip_opts(rest[1:], ("-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U"))
        elif b == "nice":
            rest = skip_opts(rest[1:], ("-n",))
        elif b == "timeout":
            rest = skip_opts(rest[1:], ("-s", "-k"))[1:]
        elif b == "caffeinate":
            rest = skip_opts(rest[1:], ("-t", "-w"))
        elif b == "stdbuf":
            rest = skip_opts(rest[1:], ("-i", "-o", "-e"))
        elif b == "rtk":
            rest = rest[1:]
            if rest and rest[0][0] == "proxy":
                rest = rest[1:]
        elif b == "xargs":
            xargs = True
            rest = skip_opts(rest[1:], ("-I", "-n", "-P", "-d", "-L", "-E", "-s", "-a"))
        else:
            break
    return rest, xargs


def check_dst(dst, cfg):
    """G1/G3 for one push destination (refs/heads/ already stripped)."""
    if dst.startswith("refs/tags/"):
        raise Deny("G3", "push of %s (tags stay local)" % dst)
    if dst == cfg.default_branch:
        raise Deny("G1", "push to the default branch %s" % dst)
    allowed = any(dst.startswith(p) and len(dst) > len(p) for p in cfg.prefixes)
    if ".." in dst or not DST_CHARS.match(dst) or not allowed:
        raise Deny("G1", "push to %s (only %s on %s)"
                   % (dst, ", ".join(p + "*" for p in cfg.prefixes), cfg.remote))


def current_branch(cwd, st):
    """G1: the branch checked out in cwd (`git rev-parse --abbrev-ref HEAD`); any doubt denies."""
    if cwd is None or st["git_dir_env"]:
        raise Deny("G1", "push of HEAD in a repository that cannot be determined literally")
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    try:
        p = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=5, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Deny("G1", "push of HEAD: the current branch could not be resolved")
    name = p.stdout.strip()
    if p.returncode != 0 or not name:
        raise Deny("G1", "push of HEAD: the current branch could not be resolved")
    if name == "HEAD":
        raise Deny("G1", "push of a detached HEAD")
    return name


def is_current_branch_sub(word):
    """True for a refspec that is exactly `$(git branch --show-current)` or an equivalent."""
    return isinstance(word, SubWord) and " ".join(word.raw.split()) in CURRENT_BRANCH_SUBS


def check_push(args, st, eff):
    """Rules G1-G4 for `git push <args>` run in directory eff (None = unknown)."""
    cfg = st["config"]
    pos, repo, i = [], None, 0
    while i < len(args):
        w, lit = args[i]
        if w == "--":
            pos += args[i + 1:]
            break
        if w.startswith("--"):
            name, eq, val = w.partition("=")
            # git accepts any unambiguous prefix of a long option (`--dele`, `--force-w`), so every
            # option that `name` is a prefix of counts; an ambiguous prefix fails in git anyway.
            hits = [o for o in PUSH_LONG if len(name) >= 3 and o.startswith(name)]
            for o in hits:
                if o in FORCE_OPTS:
                    raise Deny("G2", "force push (%s)" % name)
                if o in DELETE_OPTS:
                    raise Deny("G4", "remote branch deletion (%s)" % name)
                if o in BULK_OPTS:
                    raise Deny("G3", "push of tags, all branches or a mirror (%s)" % name)
            if "--repo" in hits:
                repo = val if eq else (args[i + 1][0] if i + 1 < len(args) else "")
                i += 0 if eq else 1
            elif any(o in ("--push-option", "--receive-pack", "--exec") for o in hits) and not eq:
                i += 1
        elif w.startswith("-") and len(w) > 1:
            letters = w[1:].split("o")[0]
            if "f" in letters:
                raise Deny("G2", "force push (%s)" % w)
            if "d" in letters:
                raise Deny("G4", "remote branch deletion (%s)" % w)
            if w.endswith("o"):
                i += 1
        else:
            pos.append((w, lit))
        i += 1
    if repo is not None:
        raise Deny("G1", "push with --repo=%s (only %s is allowed)" % (repo, cfg.remote))
    if not pos:
        raise Deny("G1", "push without an explicit remote and refspec")
    if pos[0][0] != cfg.remote or not pos[0][1]:
        raise Deny("G1", "push to remote %s (only %s is allowed)" % (pos[0][0], cfg.remote))
    if len(pos) == 1:
        raise Deny("G1", "push without an explicit refspec")
    for w, lit in pos[1:]:
        if not lit:
            if not is_current_branch_sub(w):
                raise Deny("G1", "push refspec %s is not a literal" % w)
            w = "HEAD"
        if w.startswith("+"):
            raise Deny("G2", "force push (+ refspec %s)" % w)
        if ":" in w:
            src, dst = w.split(":", 1)
        elif w == "HEAD":
            src, dst = w, current_branch(eff, st)
        else:
            src = dst = w
        if not src or not dst:
            raise Deny("G4", "remote branch deletion (refspec %s)" % w)
        dst = dst[len("refs/heads/"):] if dst.startswith("refs/heads/") else dst
        check_dst(dst, cfg)


def cfg_key_check(key):
    """G7: refuse a git configuration key that re-routes pushes or hooks."""
    if BAD_CFG_KEY.match(key.strip().lower()):
        raise Deny("G7", "git configuration of %s" % key, ALT_USER)


def check_config(args):
    """G7: `git config` forms that set a guarded key."""
    pos, adds, i = [], False, 0
    reads = ("--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--unset",
             "--unset-all", "--remove-section", "--rename-section", "--edit", "-e")
    while i < len(args):
        w = args[i][0]
        if w in reads:
            return
        if w in ("--add", "--replace-all"):
            adds = True
        if w in ("-f", "--file", "--blob", "--default", "--type", "-t", "--comment"):
            i += 1
        elif not w.startswith("-"):
            pos.append(w)
        i += 1
    if pos and pos[0] == "set":
        pos = pos[1:]
        adds = True
    if pos and (len(pos) >= 2 or adds) and pos[0] not in ("get", "list", "unset", "edit"):
        cfg_key_check(pos[0])


def do_git(args, st, xargs=False):
    """Skip git's global options (checking -c / --config-env, following -C), then apply G1-G4,
    G6 and G7. Under xargs, a missing subcommand or one whose operands matter is refused."""
    st["git"] = True
    eff, i = st.cwd, 0
    while i < len(args):
        w = args[i][0]
        nxt = args[i + 1] if i + 1 < len(args) else ("", True)
        if w == "-C":
            eff = resolve(eff, nxt[0], nxt[1])
            i += 2
        elif w == "-c" or (w.startswith("-c") and not w.startswith("--")):
            cfg_key_check((nxt[0] if w == "-c" else w[2:]).split("=", 1)[0])
            i += 2 if w == "-c" else 1
        elif w == "--config-env" or w.startswith("--config-env="):
            val = nxt[0] if w == "--config-env" else w.split("=", 1)[1]
            cfg_key_check(val.split("=", 1)[0])
            i += 2 if w == "--config-env" else 1
        elif w in ("--git-dir", "--work-tree"):
            eff = None
            i += 2
        elif w.startswith(("--git-dir=", "--work-tree=")):
            eff = None
            i += 1
        elif w in ("--namespace", "--exec-path", "--super-prefix"):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            break
    if i >= len(args):
        if xargs:
            raise Deny("G1", "git under xargs without a literal subcommand (operands unknown)")
        return
    sub, rest = args[i], args[i + 1:]
    if not sub[1]:
        raise Deny("G1", "git subcommand %s is not a literal" % sub[0])
    if xargs and sub[0] in ("push", "config", "remote", "send-pack", "http-push"):
        raise Deny("G1", "git %s under xargs (operands unknown)" % sub[0])
    if sub[0] == "push":
        check_push(rest, st, eff)
    elif sub[0] == "config":
        check_config(rest)
    elif sub[0] in ("send-pack", "http-push"):
        raise Deny("G1", "git %s (plumbing push)" % sub[0])
    elif sub[0].startswith("credential"):
        raise Deny("G6", "git credential (prints stored credentials)", ALT_USER)
    elif sub[0] == "remote":
        verbs = [a[0] for a in rest if not a[0].startswith("-")]
        if verbs and verbs[0] in ("set-url", "add", "rename"):
            raise Deny("G7", "git remote %s" % verbs[0], ALT_USER)


def gh_api(args):
    """G5 (and G4 for ref deletion): REST method rules and the GraphQL literal-query rule."""
    method, body, endpoint, fields, inp, i = None, False, None, [], False, 0
    while i < len(args):
        w, lit = args[i]
        kind = val = None
        if w.startswith("--"):
            name, eq, val = w.partition("=")
            kind = {"--method": "X", "--field": "F", "--raw-field": "f", "--input": "I"}.get(name)
            if name in ("--header", "--jq", "--template", "--cache", "--hostname", "--preview"):
                kind = "-"
            if kind and not eq:
                i += 1
                val, lit = (args[i] if i < len(args) else ("", True))
        elif w.startswith("-") and len(w) > 1:
            # A cluster of short flags (`-iXPUT`): boolean letters are skipped; the first letter that
            # takes a value ends the cluster, its value being the rest of the word or the next word.
            for pos_, ch in enumerate(w[1:], 1):
                if ch in "XfFHqtp":
                    kind = ch if ch in "XfF" else "-"
                    if len(w) > pos_ + 1:
                        val = w[pos_ + 1:]
                    else:
                        i += 1
                        val, lit = (args[i] if i < len(args) else ("", True))
                    break
        elif endpoint is None:
            endpoint = w.lstrip("/")
        if kind == "X":
            method = (val, lit)
        elif kind in ("f", "F"):
            body = True
            fields.append((kind, val, lit))
        elif kind == "I":
            body = inp = True
        i += 1
    if endpoint == "graphql":
        q = [f for f in fields if f[1].partition("=")[0] == "query"]
        ok = (not inp and len(q) == 1 and q[0][0] == "f" and q[0][2]
              and not re.search(r"mutation", q[0][1], re.I))
        if not ok:
            raise Deny("G5", "gh api graphql without a single literal read-only query", ALT_MERGE)
        return
    if method is not None:
        if not method[1]:
            raise Deny("G5", "gh api with a non-literal --method", ALT_MERGE)
        m = method[0].upper()
    else:
        m = "POST" if body else "GET"
    if m != "GET":
        rule = "G4" if m == "DELETE" and "git/refs" in (endpoint or "") else "G5"
        raise Deny(rule, "gh api %s %s" % (m, endpoint or ""), ALT_MERGE)


def do_gh(args, xargs=False):
    """Rules G3 (releases), G4 (pr close -d, repo sync), G5 (merge, api, repository writes,
    non-literal or xargs-supplied verbs) and G6 (auth, keys) for gh."""
    rest, i = [], 0
    while i < len(args):
        w = args[i][0]
        if w in ("-R", "--repo"):
            i += 2
            continue
        if not (w.startswith("--repo=") or (w.startswith("-R") and not w.startswith("--"))):
            rest.append(args[i])
        i += 1
    pos = [a for a in rest if not a[0].startswith("-")]
    g, v, third = [a[0] for a in pos[:3]] + [""] * (3 - len(pos[:3]))
    if any(not lit for _w, lit in pos[:1 if g == "api" else 2]):
        raise Deny("G5", "gh with a command group or verb that is not a literal", ALT_USER)
    if xargs and (len(pos) < 2 or g == "api" or (g, v) == ("pr", "close")):
        raise Deny("G5", "gh %s under xargs (operands unknown)" % " ".join([g, v]).strip(),
                   ALT_USER)
    flags = [a[0] for a in rest if a[0].startswith("-")]
    if g == "pr" and v == "merge":
        raise Deny("G5", "gh pr merge", ALT_MERGE)
    if g == "pr" and v == "close" and any(
            f == "--delete-branch" or (not f.startswith("--") and "d" in f[1:]) for f in flags):
        raise Deny("G4", "gh pr close with branch deletion")
    if g == "api":
        gh_api(rest[[a[0] for a in rest].index("api") + 1:])
        return
    if g == "repo" and v == "sync":
        raise Deny("G4", "gh repo sync (rewrites remote branches)", ALT_USER)
    if g == "release" and v in ("create", "delete", "edit", "upload"):
        raise Deny("G3", "gh release %s (creates or changes a tag)" % v, ALT_USER)
    if g == "auth" and (v in ("token", "login", "logout", "refresh", "setup-git", "switch")
                        or (v == "status" and any(f in ("-t", "--show-token") for f in flags))):
        raise Deny("G6", "gh auth %s" % v, ALT_USER)
    if (g in ("ssh-key", "gpg-key") and v in ("add", "delete")) or (
            g == "repo" and v == "deploy-key" and third in ("add", "delete")):
        raise Deny("G6", "gh %s %s%s" % (g, v, " " + third if g == "repo" else ""), ALT_USER)
    bad = (
        (g == "repo" and v in ("edit", "delete", "rename", "archive", "unarchive"))
        or g in ("secret", "variable")
        or (g == "workflow" and v in ("enable", "disable", "run"))
        or (g == "run" and v in ("rerun", "cancel", "delete"))
        or (g == "label" and v in ("create", "edit", "delete", "clone"))
        or (g == "alias" and v in ("set", "import", "delete"))
        or (g in ("extension", "ext") and v in ("install", "upgrade", "exec", "create", "remove"))
        or (g == "config" and v == "set"))
    if bad:
        raise Deny("G5", "gh %s %s" % (g, v), ALT_USER)


def do_pkg(args, st, depth):
    """Package runners (pnpm [--filter p] exec|dlx, npx, npm exec, yarn, bunx): the command they
    run is analysed like any other (`pnpm exec git push ...`, `npx sh -c "..."`)."""
    i, dropped = 0, False
    while i < len(args):
        w = args[i][0]
        if w == "--":
            i += 1
        elif w in PKG_OPT_ARG:
            i += 2
        elif w.startswith("-"):
            i += 1
        elif not dropped and w in ("exec", "dlx", "x"):
            dropped = True
            i += 1
        else:
            run_segment(Seg(args[i:], False, [], []), st.fork(), depth + 1)
            return


def shell_script(args, i):
    """The script word of `<shell> ... -c [options] <script>`: options after -c (and the
    argument of -o/+o/-O/+O, also at the end of a cluster) are skipped."""
    j = i + 1
    while j < len(args):
        a = args[j][0]
        if a == "--":
            j += 1
            break
        if a in ("-", "+") or not a.startswith(("-", "+")):
            break
        j += 2 if a[-1] in "oO" else 1
    return args[j] if j < len(args) else None


def do_shell(seg, args, st, depth):
    """`bash -c '<script>'` and shells fed by a heredoc are analysed; a shell fed by a pipe in a
    command that mentions git or gh is refused."""
    for i, (w, _lit) in enumerate(args):
        if w.startswith("-") and not w.startswith("--") and "c" in w[1:]:
            script = shell_script(args, i)
            if script:
                analyse_text(script[0], st.fork(), depth + 1)
            return
    for ph in seg.heres:
        for body in ph:
            analyse_text(body, st.fork(), depth + 1)
    if seg.piped and guarded_pair(st["raw"]):
        raise Deny("G1", "a shell fed from a pipe in a command that mentions git or gh")


def run_other(b, args, st, depth):
    """Any other command: shell strings of su/runuser/script/flock -c and of watch/parallel are
    analysed, then the words from the first literal git or gh word are analysed as a command
    (`find -exec git push ... ;`, `setsid git push ...`, `arch -arm64 git push ...`)."""
    for i, (w, lit) in enumerate(args):
        if b in DASH_C_RUNNERS and w in ("-c", "--command") and i + 1 < len(args):
            analyse_text(args[i + 1][0], st.fork(), depth + 1)
        elif b in DASH_C_RUNNERS and w.startswith("--command="):
            analyse_text(w.split("=", 1)[1], st.fork(), depth + 1)
        elif b in STRING_RUNNERS and lit and re.search(r"\s", w):
            analyse_text(w, st.fork(), depth + 1)
    for i, (w, lit) in enumerate(args):
        if lit and basename(w) in ("git", "gh"):
            words = args[i:]
            if b == "find":
                ends = [k for k, (x, _l) in enumerate(words) if x in (";", "+")]
                words = words[:ends[0]] if ends else words
            run_segment(Seg(words, False, [], []), st.fork(), depth + 1)
            return


def run_segment(seg, st, depth):
    """Apply the rules to one simple command (after analysing its nested substitutions)."""
    for inner in seg.subs:
        analyse_segs(inner, st.fork(), depth + 1)
    rest, xargs = unwrap(seg.words, st)
    if not rest:
        return
    cmd, lit = rest[0]
    args = rest[1:]
    if not lit:
        if GUARDED_WORD.search(" ".join(w for w, _ in rest)) or guarded_pair(st["raw"]):
            raise Deny("G1", "command word %s is not a literal in a segment that mentions "
                       "git, gh or push" % cmd)
        return
    b = basename(cmd)
    if b in ("cd", "pushd"):
        tgt = [a for a in args if not a[0].startswith("-") or a[0] == "-"]
        if b == "pushd":
            st.stack.append(st.cwd)
        st.cwd = resolve(st.cwd, tgt[0][0], tgt[0][1]) if tgt else None
    elif b == "popd":
        st.cwd = st.stack.pop() if st.stack else None
    elif b in ("export", "declare", "typeset"):
        for w, _ in args:
            note_assign(w, st)
    elif b == "git":
        do_git(args, st, xargs)
    elif b == "gh":
        do_gh(args, xargs)
    elif b in PKG_RUNNERS:
        do_pkg(args, st, depth)
    elif b in SHELLS:
        do_shell(seg, args, st, depth)
    elif b == "eval":
        analyse_text(" ".join(w for w, _ in args), st.fork(), depth + 1)
    elif b not in DATA_COMMANDS:
        run_other(b, args, st, depth)


def analyse_segs(segs, st, depth):
    """Run every segment of a tokenized command in order (directory state flows through)."""
    if depth > MAX_DEPTH:
        if guarded_pair(st["raw"]):
            raise Deny("G1", "command nesting deeper than %d with git or gh in it" % MAX_DEPTH)
        return
    for seg in segs:
        run_segment(seg, st, depth)


def analyse_text(text, st, depth):
    """Tokenize text and analyse it."""
    analyse_segs(Tokenizer(text).parse(), st, depth)


def check_command(command, cfg, cwd=None):
    """Whole-command analysis in directory cwd (None = unknown); raises Deny (or
    Untokenizable, handled by the caller)."""
    shared = {"config": cfg, "raw": command, "cfg_env": False, "git": False,
              "git_dir_env": False}
    analyse_text(command, State(cwd, shared), 0)
    if shared["cfg_env"] and shared["git"]:
        raise Deny("G7", "GIT_CONFIG_* environment assignment in a command that runs git",
                   ALT_USER)


def parse_prefixes(value):
    """PUSH_BRANCH_PREFIXES: a space-separated string or a list of strings; else the default."""
    if isinstance(value, str):
        items = value.split()
    elif isinstance(value, list):
        items = [v.strip() for v in value if isinstance(v, str)]
    else:
        items = []
    items = [p for p in items if p]
    return tuple(items) or DEFAULT_PREFIXES


def text_value(data, key, default):
    """A non-blank string value of the config, else the default."""
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def load_config(project_dir):
    """The parsed project config (a dict), or None when it is missing or invalid."""
    try:
        with open(os.path.join(project_dir, CONFIG_FILE), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def find_config(start):
    """The project config found walking up from start to the git toplevel, or None."""
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, CONFIG_FILE)):
            return load_config(d)
        parent = os.path.dirname(d)
        if os.path.exists(os.path.join(d, ".git")) or parent == d:
            return None
        d = parent


def settings(env, cwd):
    """(active, Config) from the environment and the project config."""
    force = env.get("FORGE_PUSH_GUARD", "").strip()
    if force == "0":
        return False, None
    project = env.get("CLAUDE_PROJECT_DIR")
    data = (load_config(project) if project else find_config(cwd)) or {}
    mode = data.get("DELIVERY_MODE")
    active = force == "1" or (isinstance(mode, str) and mode.strip().lower() == "autonomous")
    cfg = Config(text_value(data, "PUSH_REMOTE", DEFAULT_REMOTE),
                 parse_prefixes(data.get("PUSH_BRANCH_PREFIXES")),
                 text_value(data, "DEFAULT_BRANCH", DEFAULT_BRANCH))
    return active, cfg


def decide(raw, env):
    """(exit code, stderr line) for one PreToolUse payload."""
    try:
        data = json.loads(raw)
    except ValueError:
        return 0, ""
    if not isinstance(data, dict) or data.get("tool_name") != "Bash":
        return 0, ""
    tool_input = data.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return 0, ""
    cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else os.getcwd()
    active, cfg = settings(env, cwd)
    if not active:
        return 0, ""
    try:
        check_command(command, cfg, cwd)
    except Deny as d:
        return 2, d.line(cfg)
    except Untokenizable:
        if guarded_pair(command):
            return 2, Deny("G1", "a command that could not be parsed and mentions git or gh "
                           "with a guarded verb").line(cfg)
    return 0, ""


def main():
    """Read the payload; allow (exit 0) or deny (exit 2). Any internal error allows."""
    try:
        code, line = decide(sys.stdin.read(), os.environ)
    except Exception:  # a bug in the guard must never block the tool call
        return 0
    if code:
        sys.stderr.write(line + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
