#!/usr/bin/env python3
"""Nested-wait guard (PreToolUse hook, matcher SubagentHandback, Forge-owned).

A runner (a subagent) hands its result back with the tool `SubagentHandback`; the call ends its run. When the runner
launched an agent or a background shell and has not yet seen its final completion notification, handing back early
leaves that work running unwatched, and the next phase starts in a tree it still writes to (`_autonomous-mode.md` ->
"Wait for nested agents"). Text rules did not stop it; this hook does, from the runner's own transcript.

Input: the PreToolUse JSON on stdin (`tool_input.message`, `tool_use_id`, `agent_id`, `session_id`, `transcript_path`,
`cwd`, optional `agent_transcript_path`). Exit codes: 0 allow (silent, or one warning line on stderr when the guard
fails open); 2 deny, with the reason on stderr (the model reads it). The message text is never printed back.

How the pending work is found: the calling subagent's own transcript (JSONL) is replayed in order. Launches are
`Agent` results with `toolUseResult.agentId` and `isAsync`/`status == "async_launched"`, and any tool result with a
`toolUseResult.backgroundTaskId` (a `run_in_background` shell, or a foreground one that timed out and was moved to
the background). Completions are task notifications and peer hand-backs, taken only from trusted record shapes (a
record whose `origin.kind` is `task-notification`, a `queued_command` attachment with `commandMode`
`task-notification`, or an `isMeta` user record that starts with the tag), never from tool output text, which can quote
the tag. A notification with a final status ends the item unless its summary or note says the agent is "waiting on its
own background work" (it stopped with background work of its own and may resume) or its status is still in flight
(running, pending, in_progress, queued); every other status is final. `TaskStop`/`KillShell` ends an item;
`SendMessage` to a finished agent makes it pending again (the only way an agent is re-pended). Only the first launch
record of an id counts: a later echo of a `backgroundTaskId` (an output-reading tool) or a launch record seen after the
item's final notification does not make it pending again. Both the current `Agent` tool and the legacy `Task` tool
name are recognised.

Allowed anyway:
  - a real STOP: the message has a `status: blocked` field, a `blockers:` field with a STOP number, and a `nested:`
    field that names every pending id (a bare `status: blocked` plus a vague nested line is not enough). A field is its
    `key:` line plus the continuation lines up to the next `key:` line, and markdown bold or backticks around a key
    (`**status**: blocked`) are tolerated;
  - the loop guard: after LOOP_LIMIT refused hand-backs since the last notification or peer hand-back (other tool calls
    between the attempts do not reset the count), the guard lets the call through with a logged warning, so a runner
    trapped by a false pending is not stuck;
  - fail open: the transcript cannot be found or read, or the hook itself fails. One warning line goes to stderr and a
    line (ids, paths and the reason only) to the guard log, `<git common dir>/forge/nested-wait-guard.log` of the
    project (outside the working tree; no log when the project is not a git repository).

Activation (as the push guard): active only when `.claude/project-config.json` (under $CLAUDE_PROJECT_DIR; when that is
unset, the first one found walking up from the payload's cwd to the git toplevel) has DELIVERY_MODE "autonomous", or
when the environment sets FORGE_NESTED_WAIT_GUARD=1. FORGE_NESTED_WAIT_GUARD=0 forces it off. A missing or invalid
config file counts as interactive (inactive). Inactive = exit 0, silent.

Deliberately NO SubagentStop/Stop hook: ending a turn without a hand-back is the correct way to wait. The harness marks
the runner as waiting and the completion notification wakes it. Blocking the stop would force the runner to keep acting,
that is, to sleep-poll.

The parser (`scan`, `pending_work`, `launched_work`) is pure and importable (scripts/forge/nested-pending.py loads it
by path). Python 3.9+, standard library only.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import subprocess
import sys
from typing import Any, NamedTuple

TOOL_NAME = "SubagentHandback"
ENV_SWITCH = "FORGE_NESTED_WAIT_GUARD"
CONFIG_FILE = os.path.join(".claude", "project-config.json")
LOG_NAME = os.path.join("forge", "nested-wait-guard.log")
# Refused hand-backs since the last notification or peer hand-back (other tool calls between them do not reset the
# count; a successful hand-back does) after which the guard lets the call through.
LOOP_LIMIT = 5
# Newest subagent transcripts searched for this call's tool_use_id when no direct path is known.
SEARCH_CAP = 32
SEARCH_CHUNK = 1 << 20
# The tool that launches an agent: the current name and the legacy one.
AGENT_TOOLS = frozenset({"Agent", "Task"})
# Notification statuses that mean "not finished yet"; every other status is final.
IN_FLIGHT_STATUSES = frozenset({"running", "pending", "in_progress", "queued"})
WAITING_MARKERS = ("waiting on its own background work", "may resume on its own")
STOP_TOOLS = frozenset({"TaskStop", "KillShell"})
# A line must hold one of these to be worth decoding (most lines of a long transcript hold none).
PREFILTER = ("tool_result", "tool_use", "task-notification", "handback")
NOTIFICATION_BLOCK = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
STOP_NUMBER = re.compile(r"STOP\s*\d")
# A result-block field line: `key: value`, with optional list marker and markdown bold/backticks around the key.
# The key has no digits, so a continuation line such as `STOP 3: ...` is not taken for a key.
FIELD_LINE = re.compile(r"^[\s>\-]*[*`_]*([A-Za-z][A-Za-z _-]*?)[*`_]*\s*:[*`_]*\s*(.*)$")
# The keys of a result block (`_autonomous-mode.md` -> "Result block"). Only these start a field, so a continuation
# line such as `- implementer: still running` stays inside the field above it.
RESULT_KEYS = frozenset({"phase", "spec", "status", "artifacts", "gates", "decisions logged", "blockers", "duration",
                         "nested", "next"})
TOP_LIST_ITEM = re.compile(r"[-*>+]\s")


class Pending(NamedTuple):
    """One unit of launched work: an agent or a background shell."""

    kind: str  # "agent" | "shell"
    id: str
    label: str  # agent type for an agent, tool name for a shell
    launched: str  # timestamp of the launch (or of the last resume), as written in the transcript


class Scan(NamedTuple):
    """Result of replaying a transcript."""

    pending: list[Pending]  # launched and not finished, in launch order
    launched: list[Pending]  # everything launched, in launch order (finished or not)
    denials: int  # refused SubagentHandback results since the last notification or peer hand-back of tracked work, or a successful hand-back


def decode_lines(lines) -> list[dict[str, Any]]:
    """Decode JSONL lines into dict records; undecodable lines are skipped individually."""
    records: list[dict[str, Any]] = []
    for line in lines:
        if not isinstance(line, str):
            line = line.decode("utf-8", errors="replace")
        if not any(marker in line for marker in PREFILTER):
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def message_blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The content blocks of a record's message (empty when it has none)."""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def message_texts(record: dict[str, Any]) -> list[str]:
    """Every text of a record's message: its string content, or all of its text blocks."""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [content]
    return [block["text"] for block in message_blocks(record)
            if block.get("type") == "text" and isinstance(block.get("text"), str)]


def notification_text(record: dict[str, Any]) -> str | None:
    """The `<task-notification>` text of a record (all its text blocks joined) when it comes from a trusted shape, else
    None."""
    origin = record.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else None
    attachment = record.get("attachment")
    if record.get("type") == "attachment" and isinstance(attachment, dict):
        if attachment.get("type") == "queued_command" and attachment.get("commandMode") == "task-notification":
            prompt = attachment.get("prompt")
            return prompt if isinstance(prompt, str) else ""
        return None
    if record.get("type") != "user":
        return None
    texts = message_texts(record)
    if kind == "task-notification":
        return "\n".join(texts)
    if record.get("isMeta") is True and any(text.lstrip().startswith("<task-notification>") for text in texts):
        return "\n".join(texts)
    return None


def tag(block: str, name: str) -> str:
    """The text inside `<name>...</name>` of a notification block (empty when absent)."""
    match = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return match.group(1).strip() if match else ""


def is_final(block: str) -> bool:
    """Whether a notification block ends its item. It does not when the summary or note carries a waiting marker (the
    agent stopped with background work of its own) or the status is still in flight; every other status is final."""
    status = re.sub(r"[\s-]+", "_", tag(block, "status").lower())
    if status in IN_FLIGHT_STATUSES:
        return False
    text = (tag(block, "summary") + " " + tag(block, "note")).lower()
    return not any(marker in text for marker in WAITING_MARKERS)


def is_peer_handback(record: dict[str, Any]) -> str | None:
    """The sender id of a peer hand-back record (a subagent's report arriving), else None."""
    origin = record.get("origin")
    if record.get("type") != "user" or not isinstance(origin, dict):
        return None
    if origin.get("kind") != "peer" or not origin.get("handback"):
        return None
    sender = origin.get("from") or origin.get("senderTaskId")
    return sender if isinstance(sender, str) and sender else None


GONE_TASK = re.compile(r"No task found|is not running", re.I)


def result_text(block: dict[str, Any]) -> str:
    """The text of a tool_result block (a string, or the text parts of a list)."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content
                        if isinstance(part, dict) and isinstance(part.get("text"), str))
    return ""


def scan(records: list[dict[str, Any]]) -> Scan:
    """Replay decoded transcript records in order and return the pending work, all launches and the denial count."""
    uses: dict[str, tuple[str, dict[str, Any]]] = {}  # tool_use id -> (tool name, input)
    items: dict[str, Pending] = {}  # work id -> launch
    state: dict[str, bool] = {}  # work id -> still pending
    by_use: dict[str, str] = {}  # launching tool_use id -> work id
    names: dict[str, str] = {}  # agent name -> agent id
    finalised: set[str] = set()  # ids a final notification has ended (also when it came before the launch record)
    denials = 0

    def resolve(ref: Any) -> str | None:
        if not isinstance(ref, str):
            return None
        return ref if ref in items else names.get(ref)

    def launch(item: Pending, use_id: str) -> None:
        """Record a launch. Only the first record of an id counts; a later echo never re-pends it."""
        by_use.setdefault(use_id, item.id)
        if item.id in items:
            return
        items[item.id] = item
        state[item.id] = item.id not in finalised

    for record in records:
        timestamp = record.get("timestamp") if isinstance(record.get("timestamp"), str) else ""
        text = notification_text(record)
        sender = is_peer_handback(record)
        if text is not None:
            for block in NOTIFICATION_BLOCK.findall(text):
                raw_id = tag(block, "task-id")
                work_id = resolve(raw_id) or by_use.get(tag(block, "tool-use-id")) or raw_id
                if work_id in items:
                    denials = 0  # news about work this runner launched; events of other ids (Monitor) do not count
                if work_id and is_final(block):
                    finalised.add(work_id)
                    if work_id in items:
                        state[work_id] = False
        if sender is not None and sender in items:
            denials = 0
            state[sender] = False
        if record.get("type") == "assistant":
            for block in message_blocks(record):
                if block.get("type") == "tool_use" and isinstance(block.get("id"), str):
                    tool_input = block.get("input")
                    uses[block["id"]] = (str(block.get("name")), tool_input if isinstance(tool_input, dict) else {})
            continue
        if record.get("type") != "user":
            continue
        result = record.get("toolUseResult")
        result = result if isinstance(result, dict) else {}
        for block in message_blocks(record):
            if block.get("type") != "tool_result":
                continue
            use_id = block.get("tool_use_id") if isinstance(block.get("tool_use_id"), str) else ""
            name, tool_input = uses.get(use_id, ("", {}))
            failed = block.get("is_error") is True
            if name == TOOL_NAME:
                # Other tool calls between refusals do not reset the count: a runner trapped by a false pending
                # usually does other work between its attempts, and the guard must still release it.
                denials = denials + 1 if failed else 0
            agent_id = result.get("agentId")
            shell_id = result.get("backgroundTaskId") or result.get("shellId")
            if name in AGENT_TOOLS and isinstance(agent_id, str) and (
                    result.get("isAsync") is True or result.get("status") == "async_launched"):
                label = tool_input.get("subagent_type")
                launch(Pending("agent", agent_id, label if isinstance(label, str) and label else "unspecified",
                               timestamp), use_id)
                if isinstance(tool_input.get("name"), str):
                    names[tool_input["name"]] = agent_id
            elif isinstance(shell_id, str) and shell_id and name and name not in STOP_TOOLS and not failed:
                launch(Pending("shell", shell_id, name, timestamp), use_id)
            if failed:
                if name in STOP_TOOLS and GONE_TASK.search(result_text(block)):
                    gone = resolve(tool_input.get("task_id") or tool_input.get("shell_id"))
                    if gone:
                        finalised.add(gone)
                        state[gone] = False
                continue
            if name in STOP_TOOLS:
                stopped = resolve(tool_input.get("task_id") or tool_input.get("shell_id"))
                if stopped:
                    state[stopped] = False
            elif name == "SendMessage":
                target = resolve(tool_input.get("to"))
                if target and items[target].kind == "agent" and not state.get(target, False):
                    state[target] = True
                    items[target] = items[target]._replace(launched=timestamp or items[target].launched)
    pending = [item for key, item in items.items() if state.get(key)]
    return Scan(pending, list(items.values()), denials)


def pending_work(records: list[dict[str, Any]]) -> list[Pending]:
    """The launched agents and background shells that have not finished, in launch order."""
    return scan(records).pending


def launched_work(records: list[dict[str, Any]]) -> list[Pending]:
    """Every agent and background shell the transcript launched, finished or not, in launch order."""
    return scan(records).launched


def describe(item: Pending) -> str:
    """One pending item as `agent <id> (<type>, launched <ts>)` or `shell <id> (<tool>, launched <ts>)`."""
    return f"{item.kind} {item.id} ({item.label}, launched {item.launched or 'unknown'})"


def message_fields(message: str) -> list[tuple[str, str]]:
    """The `key: value` fields of a result block as (lowercase key, text). A field's text is its first line's value plus
    the continuation lines up to the next field line: a result-block key (RESULT_KEYS) anywhere, or any other key on an
    unindented line that is not a list item."""
    fields: list[tuple[str, list[str]]] = []
    for line in message.splitlines():
        match = FIELD_LINE.match(line)
        # A known key starts a field anywhere; another key only on an unindented line that is no list item, so
        # `- implementer: still running a1` stays a continuation while a top-level `notes: ...` ends the field above.
        top_level = not line[:1].isspace() and not TOP_LIST_ITEM.match(line)
        if match and (match.group(1).strip().lower() in RESULT_KEYS or top_level):
            fields.append((match.group(1).strip().lower(), [match.group(2)]))
        elif fields:
            fields[-1][1].append(line)
    return [(key, "\n".join(parts)) for key, parts in fields]


def stop_exempt(message: str, pending: list[Pending]) -> bool:
    """Whether a hand-back message is a real STOP report: a `status: blocked` field, a STOP number in a `blockers:`
    field, and a `nested:` field naming every pending id."""
    if not isinstance(message, str):
        return False
    fields = message_fields(message)
    blocked = any(key == "status" and re.match(r"\W*blocked\b", text, re.I) for key, text in fields)
    stop_number = any(key == "blockers" and STOP_NUMBER.search(text) for key, text in fields)
    names_all = any(key == "nested" and all(item.id in text for item in pending) for key, text in fields)
    return blocked and stop_number and names_all


def deny_reason(pending: list[Pending]) -> str:
    """The text the model reads when the hand-back is refused. It names ids, kinds and timestamps only."""
    listing = "; ".join(describe(item) for item in pending)
    return (f"[nested-wait-guard] Hand-back refused: work you launched has no final completion notification yet: "
            f"{listing}. Wait for each completion notification: end your turn without calling {TOOL_NAME}; "
            f"the notification wakes you. Do not sleep-poll. Stop work you no longer need with TaskStop; a wait "
            f"loop you started never ends on its own.")


def load_config(project_dir: str) -> dict[str, Any] | None:
    """The parsed project config (a dict), or None when it is missing or invalid."""
    try:
        with open(os.path.join(project_dir, CONFIG_FILE), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def find_config(start: str) -> dict[str, Any] | None:
    """The project config found walking up from start to the git toplevel, or None."""
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, CONFIG_FILE)):
            return load_config(folder)
        parent = os.path.dirname(folder)
        if os.path.exists(os.path.join(folder, ".git")) or parent == folder:
            return None
        folder = parent


def is_active(env, cwd: str) -> bool:
    """Whether the guard runs: FORGE_NESTED_WAIT_GUARD=0 forces it off, =1 on; otherwise DELIVERY_MODE autonomous."""
    force = env.get(ENV_SWITCH, "").strip()
    if force == "0":
        return False
    if force == "1":
        return True
    project = env.get("CLAUDE_PROJECT_DIR")
    data = (load_config(project) if project else find_config(cwd)) or {}
    mode = data.get("DELIVERY_MODE")
    return isinstance(mode, str) and mode.strip().lower() == "autonomous"


def log_path(root: str) -> str | None:
    """The guard log of the repository at ``root``: `<git common dir>/forge/nested-wait-guard.log`, or None when
    ``root`` is not inside a git repository."""
    try:
        result = subprocess.run(["git", "-C", root, "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                                timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    common = result.stdout.strip()
    if result.returncode != 0 or not common:
        return None
    return os.path.join(root, common, LOG_NAME)


def log_event(root: str, event: str, **fields: str) -> None:
    """Append one line to the guard log, best effort; never raises, never writes transcript text."""
    try:
        path = log_path(root)
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        details = " ".join(f"{key}={value}" for key, value in fields.items() if value)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {event} {details}\n")
    except Exception:  # noqa: BLE001 - logging is best effort
        return


def fail_open(root: str, reason: str, **fields: str) -> int:
    """Allow the call, with a one-line warning on stderr and a log line."""
    print(f"[nested-wait-guard] warning: {reason}; hand-back allowed unchecked", file=sys.stderr)
    log_event(root, "fail-open", reason=reason, **fields)
    return 0


def find_transcript(payload: dict[str, Any]) -> str | None:
    """The calling subagent's own transcript path, or None. Tries the payload path, then the path built from the ids,
    then a search of the newest subagent transcripts of the session for this call's tool_use_id."""
    direct = payload.get("agent_transcript_path")
    if isinstance(direct, str) and os.path.isfile(direct):
        return direct
    main_path = payload.get("transcript_path")
    session = payload.get("session_id")
    if not (isinstance(main_path, str) and main_path and isinstance(session, str) and session):
        return None
    folder = os.path.join(os.path.dirname(main_path), session, "subagents")
    agent_id = payload.get("agent_id")
    if isinstance(agent_id, str) and agent_id:
        candidate = os.path.join(folder, f"agent-{agent_id}.jsonl")
        if os.path.isfile(candidate):
            return candidate
    use_id = payload.get("tool_use_id")
    if not (isinstance(use_id, str) and use_id):
        return None
    files = sorted(glob.glob(os.path.join(folder, "*.jsonl")), key=os.path.getmtime, reverse=True)[:SEARCH_CAP]
    needle = use_id.encode("utf-8")
    for path in files:
        if file_contains(path, needle):
            return path
    return None


def file_contains(path: str, needle: bytes) -> bool:
    """Whether the file holds ``needle``, streamed in chunks (an overlap of len(needle) - 1 bytes joins the chunks) and
    stopped at the first hit; an unreadable file holds nothing."""
    keep = len(needle) - 1
    tail = b""
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(SEARCH_CHUNK)
                if not chunk:
                    return False
                window = tail + chunk
                if needle in window:
                    return True
                tail = window[-keep:] if keep > 0 else b""
    except OSError:
        return False


def load_records(path: str) -> list[dict[str, Any]]:
    """Decode the transcript at ``path``; raises OSError when it cannot be read."""
    with open(path, "rb") as handle:
        return decode_lines(handle)


def check(payload: Any, root: str) -> int:
    """The guard on one parsed payload (the guard is active): 0 allow, 2 deny."""
    if not isinstance(payload, dict):
        return fail_open(root, "payload is not a JSON object")
    if payload.get("tool_name") not in (None, TOOL_NAME):
        return 0
    ids = {"agent": str(payload.get("agent_id") or ""), "session": str(payload.get("session_id") or "")}
    path = find_transcript(payload)
    if not path:
        return fail_open(root, "subagent transcript not found", **ids)
    try:
        records = load_records(path)
    except OSError as error:
        return fail_open(root, f"transcript unreadable ({error.__class__.__name__})", path=path, **ids)
    if not records:
        return fail_open(root, "transcript has no parseable record", path=path, **ids)
    result = scan(records)
    if not result.pending:
        return 0
    tool_input = payload.get("tool_input")
    message = tool_input.get("message") if isinstance(tool_input, dict) else ""
    if stop_exempt(message, result.pending):
        log_event(root, "allow-stop", path=path, **ids)
        return 0
    if result.denials >= LOOP_LIMIT:
        print(f"[nested-wait-guard] warning: {result.denials} refusals without a notification; hand-back allowed",
              file=sys.stderr)
        log_event(root, "allow-loop-guard", path=path, pending=",".join(item.id for item in result.pending), **ids)
        return 0
    log_event(root, "deny", path=path, pending=",".join(item.id for item in result.pending), **ids)
    print(deny_reason(result.pending), file=sys.stderr)
    return 2


def main() -> int:
    """Entry point: inactive = 0; the hook never crashes the session, any unexpected error fails open."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or "."
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            payload = json.loads(sys.stdin.read())
        except ValueError:
            payload = None
        cwd = payload.get("cwd") if isinstance(payload, dict) else None
        cwd = cwd if isinstance(cwd, str) and cwd else os.getcwd()
        root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
        if not is_active(os.environ, cwd):
            return 0
        if payload is None:
            return fail_open(root, "payload is not JSON")
        return check(payload, root)
    except Exception as error:  # noqa: BLE001 - a guard must not break the runner it guards
        return fail_open(root, f"unexpected {error.__class__.__name__}")


if __name__ == "__main__":
    sys.exit(main())
