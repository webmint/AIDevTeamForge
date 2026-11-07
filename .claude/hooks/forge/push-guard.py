#!/usr/bin/env python3
"""Push guard (PreToolUse hook, matcher Bash, Forge-owned).

During autonomous delivery an agent pushes its own branch and opens a pull request; everything
past that is the user's. This hook refuses the Bash commands that would go past it. It stops
accidental and instruction-following actions, not a hostile agent: what it cannot see
(interpreters such as `python -c`, script files, edits of git or gh configuration files and of
this hook) is covered by the written rule only (.claude/commands/_autonomous-mode.md ->
"Pull requests").

Rules (a denial names one):
- G1  push only to PUSH_REMOTE, only with an explicit literal refspec, only to a branch whose
      destination starts with one of PUSH_BRANCH_PREFIXES (checked by name). DEFAULT_BRANCH is
      never a destination. Plumbing pushes (send-pack, http-push) and `--repo` are refused.
- G2  no force push: -f, --force, --force-with-lease, --force-if-includes, `+refspec`.
- G3  no tags or bulk pushes: --tags, --follow-tags, --all, --branches, --mirror,
      refs/tags/ destinations, `gh release create|delete|edit|upload`.
- G4  no remote branch deletion: -d, --delete, --prune, `:branch`, `gh pr close --delete-branch`,
      `gh api -X DELETE .../git/refs/...`.
- G5  no merges or repository writes through gh: `gh pr merge`, `gh api` with a non-GET method
      (-f/-F/--input imply POST; GraphQL only as one literal read-only query), repo
      edit/delete/rename/archive, any `gh secret` / `gh variable`, `gh workflow
      run|enable|disable` and `gh run rerun|cancel` (a dispatch or rerun can deploy),
      alias/extension/config writes.
- G6  no credential or token reads: `git credential*`, `gh auth token|login|logout|refresh|
      setup-git|switch`, `gh auth status --show-token`.
- G7  no git configuration that re-routes pushes or hooks: `git config` of alias.*,
      remote.*.push|pushurl|url|mirror, remote.pushDefault, branch.*.pushRemote, push.*,
      url.*.insteadOf|pushInsteadOf, include*, core.hooksPath; the same keys through `git -c`
      or `--config-env`; GIT_CONFIG_* assignments in a command that runs git; `git remote
      add|set-url|rename`.

The shell text is tokenized (quotes, heredocs, here-strings, $( ) and backticks), split at
`;`, `&&`, `||`, `|` and newlines, and each simple command is unwrapped (NAME=value prefixes,
env, sudo, nice, timeout, nohup, command, exec, xargs, rtk, package runners) before the rules
apply. `bash -c`, `sh -c`, `eval`, `env -S` and shells fed by a heredoc are analysed in turn
(up to 5 levels); a shell fed by a pipe, a non-literal command word or deeper nesting in a
command that mentions git or gh is refused (G1). Command words match case-insensitively.

Activation (Forge decision): active only when `.claude/project-config.json` (under
$CLAUDE_PROJECT_DIR, else the working directory) has DELIVERY_MODE "autonomous", or when the
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
import re
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
GUARDED_WORD = re.compile(r"\b(git|gh|push)\b", re.I)
BAD_CFG_KEY = re.compile(
    r"^(alias\..+|remote\..+\.(push|pushurl|url|mirror)|remote\.pushdefault"
    r"|branch\..+\.pushremote|push\..+|url\..+\.(insteadof|pushinsteadof)"
    r"|include\..+|includeif\..+|core\.hookspath)$")
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
              "lit": True, "has": False, "drop": False}
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
                    st["words"].append(("".join(st["cur"]), st["lit"]))
            st["cur"], st["lit"], st["has"] = [], True, False

        def end_seg(next_piped):
            end_word()
            if st["words"] or st["heres"]:
                segs.append(Seg(st["words"], st["piped"], st["heres"], st["subs"]))
            st["words"], st["heres"], st["subs"] = [], [], []
            st["piped"], st["drop"] = next_piped, False

        def sub_at(j):
            tk = Tokenizer(t, j, True)
            st["subs"].append(tk.parse())
            return tk.i

        def backtick_at(j):
            k = j + 1
            while k < n and t[k] != "`":
                k += 2 if t[k] == "\\" else 1
            if k >= n:
                raise Untokenizable()
            st["subs"].append(Tokenizer(t[j + 1:k].replace("\\`", "`")).parse())
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
                    for ph, delim, strip in pending:
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
                        delim, i = t[i + 1:k], k + 1
                    else:
                        k = i
                        while k < n and t[k] not in " \t\n;|&()<>":
                            k += 1
                        delim, i = t[i:k].replace("\\", ""), k
                    ph = []
                    st["heres"].append(ph)
                    pending.append((ph, delim, strip))
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
        return re.search(r"\b%s\b" % w, raw, re.I) is not None
    if has("git") and (has("push") or has("config") or has("credential") or has("remote")):
        return True
    return has("gh") and re.search(
        r"\b(pr|api|secret|variable|repo|workflow|release|alias|extension|ext|auth|config)\b",
        raw, re.I) is not None


def note_assign(word, ctx):
    """Record a GIT_CONFIG_* assignment (G7 fires when the same command runs git)."""
    if GIT_CFG_ENV.match(word):
        ctx["cfg_env"] = True


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


def unwrap(words, ctx):
    """Strip assignments, keywords and wrappers; return (remaining words, under_xargs)."""
    rest, xargs = list(words), False
    # A leading NAME=value word is an assignment even when its value is non-literal
    # (FOO="$X" git status); only a non-assignment non-literal word stops the unwrap.
    while rest and (rest[0][1] or ASSIGN.match(rest[0][0])):
        w = rest[0][0]
        b = basename(w)
        if ASSIGN.match(w):
            note_assign(w, ctx)
            rest = rest[1:]
        elif w in KEYWORDS or b in ("command", "builtin", "exec", "noglob", "nohup", "time"):
            rest = skip_opts(rest[1:])
        elif b == "env":
            rest = rest[1:]
            while rest and (rest[0][0].startswith("-") or ASSIGN.match(rest[0][0])):
                if ASSIGN.match(rest[0][0]):
                    note_assign(rest[0][0], ctx)
                    rest = rest[1:]
                elif rest[0][0] in ("-S", "--split-string") and len(rest) > 1:
                    # env -S "git push ...": the string is split into a command line.
                    analyse_text(rest[1][0], ctx, MAX_DEPTH - 1)
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


def check_push(args, cfg):
    """Rules G1-G4 for `git push <args>`."""
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
            raise Deny("G1", "push refspec %s is not a literal" % w)
        if w.startswith("+"):
            raise Deny("G2", "force push (+ refspec %s)" % w)
        if ":" in w:
            src, dst = w.split(":", 1)
        elif w == "HEAD":
            raise Deny("G1", "push of bare HEAD without a destination")
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


def do_git(args, ctx):
    """Skip git's global options (checking -c / --config-env), then apply G1-G4, G6, G7."""
    ctx["git"] = True
    i = 0
    while i < len(args):
        w = args[i][0]
        nxt = args[i + 1] if i + 1 < len(args) else ("", True)
        if w == "-c" or (w.startswith("-c") and not w.startswith("--")):
            cfg_key_check((nxt[0] if w == "-c" else w[2:]).split("=", 1)[0])
            i += 2 if w == "-c" else 1
        elif w == "--config-env" or w.startswith("--config-env="):
            val = nxt[0] if w == "--config-env" else w.split("=", 1)[1]
            cfg_key_check(val.split("=", 1)[0])
            i += 2 if w == "--config-env" else 1
        elif w in ("-C", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                   "--super-prefix"):
            i += 2
        elif w.startswith("-"):
            i += 1
        else:
            break
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]
    if not sub[1]:
        raise Deny("G1", "git subcommand %s is not a literal" % sub[0])
    if sub[0] == "push":
        check_push(rest, ctx["config"])
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


def do_gh(args):
    """Rules G3 (releases), G4 (pr close -d), G5 (merge, api, repo writes), G6 (auth) for gh."""
    rest, i = [], 0
    while i < len(args):
        w = args[i][0]
        if w in ("-R", "--repo"):
            i += 2
            continue
        if not (w.startswith("--repo=") or (w.startswith("-R") and not w.startswith("--"))):
            rest.append(args[i])
        i += 1
    pos = [a[0] for a in rest if not a[0].startswith("-")]
    g, v = (pos + ["", ""])[:2]
    flags = [a[0] for a in rest if a[0].startswith("-")]
    if g == "pr" and v == "merge":
        raise Deny("G5", "gh pr merge", ALT_MERGE)
    if g == "pr" and v == "close" and any(
            f == "--delete-branch" or (not f.startswith("--") and "d" in f[1:]) for f in flags):
        raise Deny("G4", "gh pr close with branch deletion")
    if g == "api":
        gh_api(rest[[a[0] for a in rest].index("api") + 1:])
        return
    if g == "release" and v in ("create", "delete", "edit", "upload"):
        raise Deny("G3", "gh release %s (creates or changes a tag)" % v, ALT_USER)
    if g == "auth" and (v in ("token", "login", "logout", "refresh", "setup-git", "switch")
                        or (v == "status" and any(f in ("-t", "--show-token") for f in flags))):
        raise Deny("G6", "gh auth %s" % v, ALT_USER)
    bad = (
        (g == "repo" and v in ("edit", "delete", "rename", "archive", "unarchive"))
        or g in ("secret", "variable")
        or (g == "workflow" and v in ("enable", "disable", "run"))
        or (g == "run" and v in ("rerun", "cancel"))
        or (g == "alias" and v in ("set", "import", "delete"))
        or (g in ("extension", "ext") and v in ("install", "upgrade", "exec", "create", "remove"))
        or (g == "config" and v == "set"))
    if bad:
        raise Deny("G5", "gh %s %s" % (g, v), ALT_USER)


def do_pkg(args, ctx, depth):
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
            run_segment(Seg(args[i:], False, [], []), ctx, depth + 1)
            return


def do_shell(seg, args, ctx, depth):
    """`bash -c '<script>'` and shells fed by a heredoc are analysed; a shell fed by a pipe in a
    command that mentions git or gh is refused."""
    for i, (w, _lit) in enumerate(args):
        if w.startswith("-") and not w.startswith("--") and "c" in w[1:]:
            # Further options may sit between -c and the script (`bash -c -l 'script'`).
            script = [a for a in args[i + 1:] if not (a[0].startswith("-") and a[0] != "-")]
            if script:
                analyse_text(script[0][0], ctx, depth + 1)
            return
    for ph in seg.heres:
        for body in ph:
            analyse_text(body, ctx, depth + 1)
    if seg.piped and guarded_pair(ctx["raw"]):
        raise Deny("G1", "a shell fed from a pipe in a command that mentions git or gh")


def run_segment(seg, ctx, depth):
    """Apply the rules to one simple command (after analysing its nested substitutions)."""
    for inner in seg.subs:
        analyse_segs(inner, ctx, depth + 1)
    rest, xargs = unwrap(seg.words, ctx)
    if not rest:
        return
    cmd, lit = rest[0]
    args = rest[1:]
    if not lit:
        if GUARDED_WORD.search(" ".join(w for w, _ in rest)) or guarded_pair(ctx["raw"]):
            raise Deny("G1", "command word %s is not a literal in a segment that mentions "
                       "git, gh or push" % cmd)
        return
    b = basename(cmd)
    if b in ("export", "declare", "typeset"):
        for w, _ in args:
            note_assign(w, ctx)
    elif b == "git":
        if xargs and any(a[0] == "push" for a in args):
            raise Deny("G1", "git push under xargs (operands unknown)")
        do_git(args, ctx)
    elif b == "gh":
        do_gh(args)
    elif b in PKG_RUNNERS:
        do_pkg(args, ctx, depth)
    elif b in SHELLS:
        do_shell(seg, args, ctx, depth)
    elif b == "eval":
        analyse_text(" ".join(w for w, _ in args), ctx, depth + 1)


def analyse_segs(segs, ctx, depth):
    """Run every segment of a tokenized command in order."""
    if depth > MAX_DEPTH:
        if guarded_pair(ctx["raw"]):
            raise Deny("G1", "command nesting deeper than %d with git or gh in it" % MAX_DEPTH)
        return
    for seg in segs:
        run_segment(seg, ctx, depth)


def analyse_text(text, ctx, depth):
    """Tokenize text and analyse it."""
    analyse_segs(Tokenizer(text).parse(), ctx, depth)


def check_command(command, cfg):
    """Whole-command analysis; raises Deny (or Untokenizable, handled by the caller)."""
    ctx = {"config": cfg, "raw": command, "cfg_env": False, "git": False}
    analyse_text(command, ctx, 0)
    if ctx["cfg_env"] and ctx["git"]:
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


def settings(env):
    """(active, Config) from the environment and the project config."""
    force = env.get("FORGE_PUSH_GUARD", "").strip()
    if force == "0":
        return False, None
    data = load_config(env.get("CLAUDE_PROJECT_DIR") or os.getcwd()) or {}
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
    active, cfg = settings(env)
    if not active:
        return 0, ""
    try:
        check_command(command, cfg)
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
