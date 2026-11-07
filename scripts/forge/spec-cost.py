#!/usr/bin/env python3
"""Spec cost: tokens, USD cost and wall time of the Claude Code work in this project, read from its transcripts.

Reads the Claude Code session transcripts of this project (main sessions and every subagent, nested ones included,
which land flat in `<session>/subagents/`), counts every API response whose timestamp falls inside the window,
attributes it by the transcript line's `gitBranch` and prices it with the prices file.

Usage:
  python3 scripts/forge/spec-cost.py --since <ISO-8601 UTC> [--until <ISO-8601 UTC>] [options]
  python3 scripts/forge/spec-cost.py --since-first-prompt <session uuid> [--until <ISO-8601 UTC>] [options]
      --project-dir <dir>          transcript dir (default: `~/.claude/projects/<project path, every non-alphanumeric
                                   character replaced by ->`; `CLAUDE_CONFIG_DIR` replaces `~/.claude`)
      --all-trees                  also read the transcript dirs of every git worktree of this project
      --branch <name>              (repeatable) count only calls made on that git branch; `(none)` is allowed
      --by-branch                  add a per-branch breakdown (cost, calls, active span)
      --by-phase                   add a per-phase breakdown of the subagent runs and one TIMING line per spec branch
      --integration-branch <name>  the branch that carries the conductor's own calls (default: `DEFAULT_BRANCH` of
                                   `.claude/project-config.json`, else `main`)
      --prices <file>              prices file (default: `model-prices.json` next to this script)
  After a spec merges: `--by-phase --all-trees --branch <spec branch> --since <start> --until <merge>`.

Output: a `window` line (start, end, wall time, the dirs read), one line per model (calls, input, cache write, cache
read and output tokens, cost), a `total` line, a `prices` line (the file's `verified` date), the optional breakdowns,
and a closing `SUMMARY wall=<h:mm> cost=$<usd>` line. A model the prices file does not name is counted in tokens and
shown as `cost unknown`; its calls are left out of every dollar figure, and each row that left calls out says
`unpriced <n>`, the total line lists the models and SUMMARY ends with `unpriced=yes`. No unpriced call is counted as $0.
Exit codes: 0 the report was printed; 2 bad arguments (a bad timestamp, an empty window, a missing transcript dir or
session) or an unreadable prices file or project config.

Prices (`model-prices.json`): USD per million tokens under `models`, keyed by model id or by model family (a key
that is a prefix of the id up to a `-`; the exact id wins, then the longest family). Each entry has `input`,
`output`, `cache_write_5m`, `cache_write_1h` and `cache_read`; an optional `long_context` entry (`threshold` plus the
same five rates) applies when a request's prompt (input + cache write + cache read) exceeds `threshold` tokens.
`fast_multiplier` prices fast-mode calls (`usage.speed == "fast"`); without it they are unpriced. `verified` (the
date the numbers were checked against `source`, or `UNVERIFIED`) and `source` (the price list URL) are required.
Before a call is priced, a context-size tag (`[1m]`) and a date suffix (`-20260101`) are stripped from its model id.

All-trees rule: the main worktree is the first entry of `git worktree list --porcelain`; the tree roots are every
listed worktree plus the historical ones recorded under `<git common dir>/worktrees`. A transcript dir is read when it
is a tree root's dir name, or when its name is the main worktree's dir name or that name followed by `-` and a suffix
(the dir of a removed `../<repo>-<name>` worktree, or of a session started in a subdirectory). A project whose name
merely shares the prefix (`<repo>2`) does not match. Within those dirs a call counts only when the line's `cwd` is a
tree root, a subdirectory of one, or a sibling `<main>-<suffix>` path. Calls are deduplicated across dirs, so nothing
is counted twice. Lines without `gitBranch` are reported under `(none)`.

Notes:
- One API response is often written as several JSONL lines (streamed content blocks); lines are deduplicated by
  (message.id, requestId) and the largest value of each usage counter is kept (output_tokens grows across them).
- Wall time is `until - since` (`until` defaults to now), not the sum of API time.
- Cache writes the transcript does not split into 5m and 1h are priced as 5m.
- Standard library only; Python 3.9+.

By-phase rule (`--by-phase`):
- Subagent layout: every subagent, nested ones included, is written to
  `<project dir>/<session uuid>/subagents/agent-<agentId>.jsonl` with a sidecar `agent-<agentId>.meta.json`. A nested
  agent's sidecar carries `parentAgentId`, the agentId of the subagent that launched it in the same dir; a transcript
  without a sidecar or without a parent there is a depth-1 run (launched by the main session). A nested agent rolls
  up into its depth-1 ancestor, except that a gate reviewer is a run of its own: a nested agent rolls up into the
  outermost gate reviewer between it and the depth-1 run when there is one. Main-session transcripts
  (`<session>.jsonl`) are the conductor (`/conduct`) and belong to no phase.
- Phase label: the first line of a run's first user message.
  `Forge conductor mode, phase runner. Phase: <phase>[ task <NNN>| wave W<n>]. …` gives `/<command>` for a Forge
  command (`/research`, `/specify`, `/plan`, `/breakdown`, `/execute-task` for task and wave runners, `/review`,
  `/verify`, `/fix`, `/summarize`, `/finalize`), `closing` when the phase field names the closing phase, and the
  field's first word otherwise (e.g. `rebase`). `Independent gate reviewer. Gate: <gate>[, lens <lens>]. …` (the
  prompt of `.claude/commands/_independent-gate.md`) gives `<gate>` or `<gate>-<lens>`. Any other prompt (chores,
  probes, an unlabeled run) is `other`. A later message to a running agent (a gate-fix or "resume" message) does not
  change its phase.
- A run's wall time is the span from its first to its last API call, nested agents included (a runner waits for
  them); a runner resumed via SendMessage keeps one run, so the idle gap before the resume counts. The time a runner
  waits on its own gate reviewers (the union of their spans inside its span) is the gates' time and is taken out of
  the runner's wall. A phase's `wall` is the sum over its runs; `span` is first start to last end.
- Branch: with `--branch`, a run is included whole when any of its calls (nested included) was made on a named
  branch, so a `/specify` runner that starts on the integration branch counts fully. Per-phase totals can therefore
  differ from the per-call totals above them. A run's spec is the branch with most of its calls: a named branch
  first, then any branch other than the integration branch, `HEAD` and `(none)`.
- Per spec (`TIMING`): wall = the sum of its labeled runs' walls (`other` runs excluded); gates = every gate
  reviewer run (parallel lenses are summed); rework = every `/fix` run, every `/fix` runner nested in another phase
  (e.g. launched by `/verify`), and the `/verify` runs after the spec's first one; waves = `/execute-task`;
  unlabeled = its `other` runs, which make the timing partial when they did phase work.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# This file sits in <project>/scripts/forge/, so the project root is three levels up.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PRICES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model-prices.json")
DEFAULT_INTEGRATION_BRANCH = "main"

# Prices-file rate names -> internal token fields.
RATE_FIELDS = {"input": "in", "cache_write_5m": "cw5m", "cache_write_1h": "cw1h", "cache_read": "cr", "output": "out"}
TOKEN_FIELDS = ("in", "cw5m", "cw1h", "cr", "out")

# Synthetic assistant entries written by Claude Code itself, not API calls.
SKIP_MODELS = {"<synthetic>"}

# Prefixes of user-message text that are not typed by the user (commands, hooks, reminders).
NON_PROMPT_PREFIXES = (
    "<command-name>", "<command-message>", "<command-args>", "<local-command-",
    "<user-prompt-submit-hook>", "<system-reminder>", "<bash-stdout>", "<bash-stderr>",
    "<task-notification>",
)

# Run labels (see "By-phase rule" in the module docstring).
RUNNER_LABEL = re.compile(r"Forge conductor mode, phase runner\. Phase: ([^\n]*)")
GATE_LABEL = re.compile(r"Independent gate reviewer\. Gate: ([a-z][a-z0-9-]*)(?:, lens ([a-z][a-z-]*))?")
COMMAND_PHASES = ("research", "specify", "plan", "breakdown", "execute-task", "review", "verify", "fix",
                  "summarize", "finalize")
GATE_PHASES = ("spec-gate", "plan-gate", "breakdown-gate")
PHASE_ORDER = ("/research", "/specify", "spec-gate", "/plan", "plan-gate", "/breakdown", "breakdown-gate",
               "/execute-task", "/review", "/verify", "/fix", "/summarize", "/finalize", "closing")
ISO = "%Y-%m-%dT%H:%M:%SZ"


class UsageError(Exception):
    """A bad argument, an unreadable prices file or project config: exit 2."""


# ---------------------------------------------------------------------------------------------------------------------
# Prices


def _rates(entry: object, where: str) -> dict:
    """The five rates of a prices entry as internal token fields; raise UsageError when one is missing or invalid."""
    if not isinstance(entry, dict):
        raise UsageError(f"{where} is not an object")
    rates = {}
    for name, field in RATE_FIELDS.items():
        value = entry.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise UsageError(f"{where}: {name} must be a non-negative number")
        rates[field] = float(value)
    return rates


def load_prices(path: str) -> dict:
    """Read and validate a prices file: `{"models": {key: rates}, "fast_multiplier": float | None, "verified",
    "source"}`; rates may carry `long_threshold` and `long`. Raise UsageError when the file is unusable."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise UsageError(f"prices file unreadable: {path}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise UsageError(f"prices file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise UsageError(f"prices file {path}: top level is not an object")
    for key in ("verified", "source"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise UsageError(f"prices file {path}: `{key}` must be a non-empty string")
    models = data.get("models")
    if not isinstance(models, dict) or not models:
        raise UsageError(f"prices file {path}: `models` must be a non-empty object")
    table = {}
    for model, entry in models.items():
        rates = _rates(entry, f"prices file {path}: models.{model}")
        long_ctx = entry.get("long_context")
        if long_ctx is not None:
            where = f"prices file {path}: models.{model}.long_context"
            threshold = long_ctx.get("threshold") if isinstance(long_ctx, dict) else None
            if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold <= 0:
                raise UsageError(f"{where}: threshold must be a positive integer")
            rates["long_threshold"] = threshold
            rates["long"] = _rates(long_ctx, where)
        table[model] = rates
    fast = data.get("fast_multiplier")
    if fast is not None and (isinstance(fast, bool) or not isinstance(fast, (int, float)) or fast <= 0):
        raise UsageError(f"prices file {path}: `fast_multiplier` must be a positive number")
    return {"models": table, "fast_multiplier": None if fast is None else float(fast),
            "verified": data["verified"].strip(), "source": data["source"].strip()}


def normalize_model(model: str) -> str:
    """Strip a context-size tag like "[1m]" and a date suffix like "-20260101"."""
    model = re.sub(r"\[.*?\]$", "", model)
    return re.sub(r"-\d{8}$", "", model)


def model_rates(model: str, prices: dict) -> dict | None:
    """Rates of a model: the exact id first, then the longest family key (a prefix up to a `-`); None when unpriced."""
    name = normalize_model(model)
    models = prices["models"]
    if name in models:
        return models[name]
    families = [key for key in models if name.startswith(key + "-")]
    return models[max(families, key=len)] if families else None


def call_cost(model: str, tokens: dict, speed: str | None, prices: dict) -> float | None:
    """USD cost of one API call, or None when the model (or its fast mode) has no price."""
    rates = model_rates(model, prices)
    if rates is None:
        return None
    multiplier = 1.0
    if speed == "fast":
        if prices["fast_multiplier"] is None:
            return None
        multiplier = prices["fast_multiplier"]
    prompt = tokens["in"] + tokens["cw5m"] + tokens["cw1h"] + tokens["cr"]
    if "long" in rates and prompt > rates["long_threshold"]:
        rates = rates["long"]
    return sum(tokens[f] * rates[f] for f in TOKEN_FIELDS) / 1_000_000 * multiplier


# ---------------------------------------------------------------------------------------------------------------------
# Transcripts


def parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; naive values are taken as UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def transcript_dir_name(path: str) -> str:
    """Claude Code's project dir name for a working directory (every non-alphanumeric character -> -)."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def default_project_dir() -> str:
    """Claude Code transcript dir of this project."""
    config = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    return os.path.join(config, "projects", transcript_dir_name(REPO))


def integration_branch(repo: str = REPO) -> str:
    """`DEFAULT_BRANCH` of `<repo>/.claude/project-config.json`, `main` when the file or the key is absent.
    Raise UsageError when the file is not JSON or the value is not a non-empty string."""
    path = os.path.join(repo, ".claude", "project-config.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return DEFAULT_INTEGRATION_BRANCH
    except OSError as exc:
        raise UsageError(f"project config unreadable: {path}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise UsageError(f"project config is not valid JSON: {path}: {exc}") from exc
    value = data.get("DEFAULT_BRANCH") if isinstance(data, dict) else None
    if value is None:
        return DEFAULT_INTEGRATION_BRANCH
    if not isinstance(value, str) or not value.strip():
        raise UsageError(f"{path}: DEFAULT_BRANCH must be a non-empty string, got {value!r}")
    return value.strip()


def message_text(entry: dict) -> str | None:
    """Text of a user entry, or None when it carries tool results or no text."""
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_result":
            return None
        if block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(parts)


def first_prompt_ts(project_dir: str, session: str) -> datetime:
    """Timestamp of the first user-typed prompt in a main session transcript."""
    path = os.path.join(project_dir, f"{session}.jsonl")
    if not os.path.isfile(path):
        raise UsageError(f"transcript not found: {path}")
    fallback = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if '"user"' not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "user" or entry.get("isSidechain") or entry.get("isMeta"):
                continue
            if entry.get("isCompactSummary") or not entry.get("timestamp"):
                continue
            origin = entry.get("origin")
            if isinstance(origin, dict) and origin.get("kind") == "human":
                return parse_ts(entry["timestamp"])
            # Fallback for transcripts that do not record origin.kind.
            if fallback is None and not isinstance(origin, dict):
                text = message_text(entry)
                if text and text.strip() and not text.lstrip().startswith(NON_PROMPT_PREFIXES):
                    fallback = parse_ts(entry["timestamp"])
    if fallback is None:
        raise UsageError(f"no user prompt found in {path}")
    return fallback


def git_out(*args: str, repo: str = REPO) -> str:
    """stdout of a git command in `repo`; empty on failure."""
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""


def tree_roots(repo: str = REPO) -> tuple[str, list[str]]:
    """(main worktree, every worktree root of the repo: current, pruned and removed ones). Works from any worktree."""
    listed = [line[9:].strip() for line in git_out("worktree", "list", "--porcelain", repo=repo).splitlines()
              if line.startswith("worktree ")]
    main = listed[0] if listed else repo
    roots = {main, repo, *listed}
    common = git_out("rev-parse", "--path-format=absolute", "--git-common-dir", repo=repo).strip()
    for gitdir in glob.glob(os.path.join(common or os.path.join(main, ".git"), "worktrees", "*", "gitdir")):
        try:
            with open(gitdir, encoding="utf-8") as fh:
                roots.add(os.path.dirname(fh.read().strip()))  # <worktree>/.git -> <worktree>
        except OSError:
            continue
    return main, sorted(roots)


def cwd_allowed(cwd: str | None, roots: list[str], main: str) -> bool:
    """True when cwd is inside the main repo, a known worktree, or a sibling `<main>-<suffix>`."""
    if not cwd:
        return False
    cwd = os.path.normpath(cwd)
    for root in roots:
        if cwd == root or cwd.startswith(root + os.sep):
            return True
    return cwd.startswith(main + "-")  # removed/pruned worktrees follow the ../<repo>-<name> convention


def tree_project_dirs(projects_root: str, roots: list[str], main: str) -> list[str]:
    """Transcript dirs of every worktree of the repo (see "All-trees rule")."""
    dirs = {os.path.join(projects_root, transcript_dir_name(root)) for root in roots}
    name = transcript_dir_name(main)
    if os.path.isdir(projects_root):
        dirs.update(os.path.join(projects_root, d) for d in os.listdir(projects_root)
                    if d == name or d.startswith(name + "-"))
    return sorted(d for d in dirs if os.path.isdir(d))


def collect(project_dirs: list[str], since: datetime, until: datetime, cwd_filter=None) -> dict:
    """Deduplicated API calls inside [since, until]; `cwd_filter(cwd) -> bool` optionally restricts them by the
    line's cwd. The dedupe table is shared across dirs."""
    since_epoch = since.timestamp()
    calls: dict = {}
    files = [(d, f) for d in project_dirs for f in sorted(glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True))]
    for project_dir, path in files:
        if os.path.relpath(path, project_dir).split(os.sep)[0] == "memory":
            continue
        try:
            if os.path.getmtime(path) < since_epoch:
                continue  # file last written before the window: nothing inside it
        except OSError:
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant" or not entry.get("timestamp"):
                    continue
                msg = entry.get("message") or {}
                usage = msg.get("usage")
                model = msg.get("model") or "unknown"
                if not isinstance(usage, dict) or model in SKIP_MODELS:
                    continue
                try:
                    ts = parse_ts(entry["timestamp"])
                except (TypeError, ValueError):
                    continue
                if ts < since or ts > until:
                    continue
                if cwd_filter is not None and not cwd_filter(entry.get("cwd")):
                    continue
                cc = usage.get("cache_creation") or {}
                cw_total = usage.get("cache_creation_input_tokens") or 0
                cw1h = cc.get("ephemeral_1h_input_tokens") or 0
                cw5m = cc.get("ephemeral_5m_input_tokens") or 0
                cw5m += max(cw_total - cw1h - cw5m, 0)  # unsplit remainder priced as 5m
                tokens = {"in": usage.get("input_tokens") or 0, "cw5m": cw5m, "cw1h": cw1h,
                          "cr": usage.get("cache_read_input_tokens") or 0, "out": usage.get("output_tokens") or 0}
                key = (msg.get("id"), entry.get("requestId"))
                if not all(key):
                    key = (path, entry.get("uuid"))
                prev = calls.get(key)
                if prev is None:
                    calls[key] = {"model": model, "file": path, "speed": usage.get("speed"),
                                  "branch": entry.get("gitBranch") or "(none)", "first": ts, "last": ts,
                                  "tokens": tokens}
                else:
                    prev["first"], prev["last"] = min(prev["first"], ts), max(prev["last"], ts)
                    for field in TOKEN_FIELDS:
                        prev["tokens"][field] = max(prev["tokens"][field], tokens[field])
    return calls


# ---------------------------------------------------------------------------------------------------------------------
# Formatting


def fmt_tokens(n: int) -> str:
    """Compact token count: 950, 12.3k, 4.56M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def fmt_wall(seconds: float) -> str:
    """h:mm (hours may exceed 24)."""
    minutes = max(int(seconds // 60), 0)
    return f"{minutes // 60}:{minutes % 60:02d}"


def unpriced_note(count: int) -> str:
    """Suffix of a row whose dollar figure leaves unpriced calls out."""
    return f"  unpriced {count}" if count else ""


def share(part: float, whole: float) -> str:
    """`h:mm (x%)` of `part` relative to `whole` (seconds)."""
    return f"{fmt_wall(part)} ({100 * part / whole:.0f}%)" if whole else fmt_wall(part)


# ---------------------------------------------------------------------------------------------------------------------
# By phase


def parse_label(text: str | None) -> tuple[str, str]:
    """(phase, kind) of a run from its first prompt; kind is `runner`, `gate` or `other` (see "By-phase rule")."""
    text = (text or "").lstrip()
    gate = GATE_LABEL.match(text)
    if gate:
        return gate.group(1) + (f"-{gate.group(2)}" if gate.group(2) else ""), "gate"
    runner = RUNNER_LABEL.match(text)
    if not runner:
        return "other", "other"
    field = runner.group(1).split(". ")[0].strip().lower()
    word = re.match(r"/?([a-z][a-z-]*)", field)
    if not word:
        return "other", "other"
    if re.search(r"\bclosing\b", field):
        return "closing", "runner"
    name = word.group(1)
    return ("/" + name if name in COMMAND_PHASES else name), "runner"


def phase_label(text: str | None) -> str:
    """Normalized phase of a run from its first prompt."""
    return parse_label(text)[0]


def first_user_text(path: str) -> str | None:
    """Text of the first user entry of a transcript (the run's prompt)."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "user":
                    return message_text(entry)
    except OSError:
        return None
    return None


class RunIndex:
    """Maps a transcript to the run it belongs to (see "By-phase rule"), caching sidecars and labels."""

    def __init__(self) -> None:
        self.chains: dict = {}
        self.labels: dict = {}

    def label(self, path: str) -> tuple[str, str]:
        if path not in self.labels:
            self.labels[path] = parse_label(first_user_text(path))
        return self.labels[path]

    def chain(self, path: str) -> list[str]:
        """`[path, parent, …, depth-1 runner]` by `parentAgentId`; `[]` for a main session."""
        if path in self.chains:
            return self.chains[path]
        if os.path.basename(os.path.dirname(path)) != "subagents":
            self.chains[path] = []
            return []
        chain = [path]
        while True:
            try:
                with open(chain[-1][:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                    parent = json.load(fh).get("parentAgentId")
            except (OSError, ValueError, AttributeError):
                break  # no sidecar: a depth-1 run
            parent_path = os.path.join(os.path.dirname(path), f"agent-{parent}.jsonl")
            if not parent or not os.path.isfile(parent_path) or parent_path in chain:
                break
            chain.append(parent_path)
        self.chains[path] = chain
        return chain

    def run_of(self, path: str) -> tuple[str, str | None] | None:
        """(run transcript, depth-1 runner it is nested in or None) of a call's transcript; None for a main session."""
        chain = self.chain(path)
        if not chain:
            return None
        top = chain[-1]
        for candidate in reversed(chain[:-1]):  # the outermost gate reviewer below the depth-1 run
            if self.label(candidate)[1] == "gate":
                return candidate, top
        return top, None


def group_runs(calls: dict, branches: list[str], prices: dict):
    """Roll calls up into runs. Returns `(runs, nested, main)`: runs keyed by the run transcript, each with its
    `label`, `kind` and `parent` (the runner a nested gate reviewer ran in); nested transcript -> [run key, first
    call, last call]; main = [calls, cost, unpriced calls] of the main sessions. With `branches`, a run is kept whole
    when any of its calls was on a named branch."""
    index = RunIndex()
    runs: dict = {}
    nested: dict = {}
    main = [0, 0.0, 0]
    for call in calls.values():
        cost = call_cost(call["model"], call["tokens"], call["speed"], prices)
        found = index.run_of(call["file"])
        if found is None:
            if not branches or call["branch"] in branches:
                main[0] += 1
                if cost is None:
                    main[2] += 1
                else:
                    main[1] += cost
            continue
        key, parent = found
        if call["file"] != key:
            span = nested.setdefault(call["file"], [key, call["first"], call["last"]])
            span[1], span[2] = min(span[1], call["first"]), max(span[2], call["last"])
        label, kind = index.label(key)
        run = runs.setdefault(key, {"calls": 0, "cost": 0.0, "unpriced": 0, "tokens": 0, "first": call["first"],
                                    "last": call["last"], "branches": {}, "label": label, "kind": kind,
                                    "parent": parent})
        run["calls"] += 1
        if cost is None:
            run["unpriced"] += 1
        else:
            run["cost"] += cost
        run["tokens"] += sum(call["tokens"].values())
        run["first"], run["last"] = min(run["first"], call["first"]), max(run["last"], call["last"])
        run["branches"][call["branch"]] = run["branches"].get(call["branch"], 0) + 1
    if branches:
        runs = {k: r for k, r in runs.items() if any(b in r["branches"] for b in branches)}
    return runs, nested, main


def run_spec(run: dict, branches: list[str], integration: str) -> str:
    """Branch with most of the run's calls: a named branch first, then one other than the conductor's."""
    ranked = sorted(run["branches"].items(), key=lambda kv: (
        kv[0] not in branches, kv[0] in (integration, "HEAD", "(none)"), -kv[1]))
    return ranked[0][0]


def covered(intervals: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> float:
    """Seconds of [start, end] covered by the union of `intervals`."""
    total, cursor = 0.0, start
    for lo, hi in sorted(intervals):
        lo, hi = max(lo, cursor), min(hi, end)
        if hi > lo:
            total += (hi - lo).total_seconds()
            cursor = hi
    return total


def tally_runs(runs: dict, nested: dict, branches: list[str], integration: str):
    """Per-phase totals and per-spec timing buckets (`--by-phase`)."""
    inner: dict = {}
    for run in runs.values():
        if run["parent"] in runs:
            inner.setdefault(run["parent"], []).append((run["first"], run["last"]))
    phases: dict = {}
    specs: dict = {}
    for key, run in sorted(runs.items(), key=lambda kv: kv[1]["first"]):
        phase = run["label"]
        wall = (run["last"] - run["first"]).total_seconds() - covered(inner.get(key, []), run["first"], run["last"])
        p = phases.setdefault(phase, {"runs": 0, "wall": 0.0, "calls": 0, "tokens": 0, "cost": 0.0, "unpriced": 0,
                                      "first": run["first"], "last": run["last"]})
        p["runs"] += 1
        p["wall"] += wall
        for field in ("calls", "tokens", "cost", "unpriced"):
            p[field] += run[field]
        p["first"], p["last"] = min(p["first"], run["first"]), max(p["last"], run["last"])
        s = specs.setdefault(run_spec(run, branches, integration), {
            "wall": 0.0, "gates": 0.0, "rework": 0.0, "waves": 0.0, "other": 0.0, "other_runs": 0,
            "verify_seen": False})
        if phase != "other":
            s["wall"] += wall
        if run["kind"] == "gate":
            s["gates"] += wall
        elif phase == "/execute-task":
            s["waves"] += wall
        elif phase == "/fix" or (phase == "/verify" and s["verify_seen"]):
            s["rework"] += wall
            run["is_rework"] = True
        elif phase == "other":
            s["other"] += wall
            s["other_runs"] += 1
        if phase == "/verify":
            s["verify_seen"] = True
    # /fix runners launched inside another phase (e.g. by /verify) are rework too.
    nested_fix = {"runs": 0, "wall": 0.0}
    for path, (key, first, last) in nested.items():
        run = runs.get(key)
        if run is None or run["label"] == "/fix" or phase_label(first_user_text(path)) != "/fix":
            continue
        wall = (last - first).total_seconds()
        nested_fix["runs"] += 1
        nested_fix["wall"] += wall
        if not run.get("is_rework"):
            specs[run_spec(run, branches, integration)]["rework"] += wall
    return phases, specs, nested_fix


def phase_sort_key(name: str) -> tuple:
    """Pipeline order; a gate lens sorts right after its gate."""
    base = next((g for g in GATE_PHASES if name.startswith(g + "-")), name)
    return (PHASE_ORDER.index(base) if base in PHASE_ORDER else len(PHASE_ORDER), name)


def print_by_phase(calls: dict, branches: list[str], integration: str, prices: dict) -> None:
    """Per-phase breakdown of subagent runs and per-spec TIMING lines (`--by-phase`)."""
    runs, nested, main = group_runs(calls, branches, prices)
    phases, specs, nested_fix = tally_runs(runs, nested, branches, integration)
    print("by phase (subagent runs; nested agents rolled up into their runner, gate reviewers their own runs; "
          "wall = sum of run spans, span = first start to last end):")
    for name, p in sorted(phases.items(), key=lambda kv: phase_sort_key(kv[0])):
        span = fmt_wall((p["last"] - p["first"]).total_seconds())
        print(f"  {name:<22} runs {p['runs']:>3}  wall {fmt_wall(p['wall']):>6}  span {span:>6}"
              f"  calls {p['calls']:>5}  tokens {fmt_tokens(p['tokens']):>7}  ${p['cost']:>8.2f}"
              f"  {p['first'].strftime(ISO)} -> {p['last'].strftime(ISO)}{unpriced_note(p['unpriced'])}")
    print(f"  {'(nested /fix)':<22} runs {nested_fix['runs']:>3}"
          f"  wall {fmt_wall(nested_fix['wall']):>6}  inside the phases above; counted as rework")
    print(f"  {'(main sessions)':<22} conductor, no phase: calls {main[0]}  ${main[1]:.2f}{unpriced_note(main[2])}")
    for name, s in sorted(specs.items()):
        print(f"TIMING {name} wall {fmt_wall(s['wall'])}; gates {share(s['gates'], s['wall'])}; "
              f"rework {share(s['rework'], s['wall'])}; waves {fmt_wall(s['waves'])}; "
              f"unlabeled {s['other_runs']} runs {fmt_wall(s['other'])}")


# ---------------------------------------------------------------------------------------------------------------------
# Main


def report(args: argparse.Namespace) -> int:
    prices = load_prices(args.prices)
    if args.all_trees:
        main_tree, roots = tree_roots()
        dirs = tree_project_dirs(os.path.dirname(args.project_dir.rstrip(os.sep)), roots, main_tree)
        if not dirs:
            raise UsageError(f"no transcript dir found for the worktrees of {main_tree}")
    else:
        if not os.path.isdir(args.project_dir):
            raise UsageError(f"transcript dir not found: {args.project_dir}")
        dirs = [args.project_dir]
    try:
        if args.since:
            since = parse_ts(args.since)
        else:  # with --all-trees the session may live in any tree's dir
            session_dir = next((d for d in [args.project_dir, *dirs] if os.path.isfile(
                os.path.join(d, f"{args.since_first_prompt}.jsonl"))), args.project_dir)
            since = first_prompt_ts(session_dir, args.since_first_prompt)
        until = parse_ts(args.until) if args.until else datetime.now(timezone.utc)
    except ValueError as exc:
        raise UsageError(f"bad timestamp: {exc}") from exc
    if until < since:
        raise UsageError("--until is before the window start")
    integration = None
    if args.by_branch or args.by_phase:
        integration = args.integration_branch or integration_branch()

    if args.all_trees:
        calls = collect(dirs, since, until, lambda cwd: cwd_allowed(cwd, roots, main_tree))
    else:
        calls = collect(dirs, since, until)
    all_calls = calls  # --by-phase attributes whole runs, so it needs the unfiltered calls
    if args.branch:
        calls = {k: v for k, v in calls.items() if v["branch"] in args.branch}

    per_model: dict = {}
    unknown: set = set()
    total = 0.0
    for call in calls.values():
        row = per_model.setdefault(call["model"], {"calls": 0, "cost": 0.0, "unpriced": 0,
                                                   **{f: 0 for f in TOKEN_FIELDS}})
        row["calls"] += 1
        for field in TOKEN_FIELDS:
            row[field] += call["tokens"][field]
        cost = call_cost(call["model"], call["tokens"], call["speed"], prices)
        if cost is None:
            row["unpriced"] += 1
            unknown.add(call["model"])
        else:
            row["cost"] += cost
            total += cost

    wall = fmt_wall((until - since).total_seconds())
    print(f"window {since.strftime(ISO)} -> {until.strftime(ISO)}  wall {wall}"
          f"  dirs {', '.join(os.path.basename(d.rstrip(os.sep)) for d in dirs)}")
    for model, row in sorted(per_model.items(), key=lambda kv: (-kv[1]["cost"], kv[0])):
        if row["unpriced"] == row["calls"]:
            cost = "cost unknown"
        else:
            cost = f"${row['cost']:.2f}{unpriced_note(row['unpriced'])}"
        print(f"  {model:<18} calls {row['calls']:>4}  in {fmt_tokens(row['in'])}"
              f"  cache-write {fmt_tokens(row['cw5m'] + row['cw1h'])}"
              f"  cache-read {fmt_tokens(row['cr'])}  out {fmt_tokens(row['out'])}  {cost}")
    files = len({call["file"] for call in calls.values()})
    print(f"total ${total:.2f}  api calls {len(calls)}  transcript files {files}"
          + (f"  unpriced models: {', '.join(sorted(unknown))}" if unknown else ""))
    shown = os.path.abspath(args.prices)
    shown = os.path.relpath(shown, REPO) if shown.startswith(REPO + os.sep) else args.prices
    print(f"prices {shown} verified {prices['verified']}")
    if args.branch and calls:
        span = fmt_wall((max(c["last"] for c in calls.values())
                         - min(c["first"] for c in calls.values())).total_seconds())
        print(f"branch {', '.join(args.branch)}: window wall {wall}, active span {span}")
    if args.by_branch:
        rows: dict = {}
        for call in calls.values():
            r = rows.setdefault(call["branch"], {"calls": 0, "cost": 0.0, "unpriced": 0, "first": call["first"],
                                                 "last": call["last"]})
            r["calls"] += 1
            cost = call_cost(call["model"], call["tokens"], call["speed"], prices)
            if cost is None:
                r["unpriced"] += 1
            else:
                r["cost"] += cost
            r["first"], r["last"] = min(r["first"], call["first"]), max(r["last"], call["last"])
        print(f"by branch ({integration} = conductor overhead):")
        for name, r in sorted(rows.items(), key=lambda kv: (kv[0] != integration, -kv[1]["cost"], kv[0])):
            sp = fmt_wall((r["last"] - r["first"]).total_seconds())
            print(f"  {name:<34} ${r['cost']:>8.2f}  calls {r['calls']:>5}  span {sp}"
                  f"  {r['first'].strftime(ISO)} -> {r['last'].strftime(ISO)}{unpriced_note(r['unpriced'])}")
    if args.by_phase:
        print_by_phase(all_calls, args.branch, integration, prices)
    print(f"SUMMARY wall={wall} cost=${total:.2f}" + (" unpriced=yes" if unknown else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    start = parser.add_mutually_exclusive_group(required=True)
    start.add_argument("--since", help="window start, ISO-8601 UTC")
    start.add_argument("--since-first-prompt", metavar="SESSION_UUID",
                       help="window starts at the first user prompt of this main session")
    parser.add_argument("--until", help="window end, ISO-8601 UTC (default: now)")
    parser.add_argument("--project-dir", default=default_project_dir(),
                        help="Claude Code transcript directory (default: derived from the project path)")
    parser.add_argument("--all-trees", action="store_true", help="include the transcript dirs of all worktrees")
    parser.add_argument("--branch", action="append", default=[], metavar="NAME",
                        help="count only calls with this gitBranch (repeatable; '(none)' allowed)")
    parser.add_argument("--by-branch", action="store_true", help="print a per-gitBranch breakdown")
    parser.add_argument("--by-phase", action="store_true",
                        help="print a per-phase breakdown of subagent runs and per-spec TIMING lines")
    parser.add_argument("--integration-branch", metavar="NAME",
                        help="the conductor's branch (default: DEFAULT_BRANCH of .claude/project-config.json, "
                             "else main)")
    parser.add_argument("--prices", default=DEFAULT_PRICES, metavar="FILE", help="prices file (default: %(default)s)")
    args = parser.parse_args(argv)
    try:
        return report(args)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
