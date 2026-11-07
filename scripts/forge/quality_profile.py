#!/usr/bin/env python3
"""Loader and validator of the per-project quality binding `.claude/quality-profile.json`.

The structural-quality mechanisms of the harness are generic: role files, checklists and scripts name concepts only.
Every project-specific value they need (search scopes, glob patterns, thresholds, the integration ref) lives in this
one file, so the same mechanisms run unchanged on any project and any stack.

A key whose value is empty (`[]`, `{}` or `""`) is unset: its mechanism runs in its manual form, and the run report
says so. `/setup-wizard` writes every key empty (`init`); `/constitute` and `/onboard` fill them.

Binding consumers: `CONSUMERS` lists, per key, the harness files that read it. Each consumer names the binding file
and the key at the step where it reads them, and scripts load the binding only through this module.

Usage:
  python3 scripts/forge/quality_profile.py validate [--profile <path>]
  python3 scripts/forge/quality_profile.py consumers [--profile <path>]
  python3 scripts/forge/quality_profile.py scopes [--profile <path>]
  python3 scripts/forge/quality_profile.py init [--profile <path>] [--integration-ref <ref>]

`consumers` checks the harness files, not the values: a missing binding counts as every key unset (the template
repository itself has none).

Exit codes: 0 valid / consumers hold / skeleton written; 1 invalid, a consumer problem (one line each) or the file
exists already (init); 2 the file is missing (validate, scopes) or is not JSON.
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys

# This file sits in <project>/scripts/forge/, so the project root is three levels up.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BINDING_NAME = "quality-profile.json"
DEFAULT_PROFILE = os.path.join(REPO, ".claude", BINDING_NAME)
# The harness scripts directory (relative to the repository root): scripts there load the binding through this module.
HARNESS_SCRIPTS = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), REPO).replace(os.sep, "/")

# Top-level keys and their JSON types. A key this list does not name is reported, so a typo cannot silently disable
# a mechanism. Keys are added here when their mechanism lands.
TOP_LEVEL = {
    "$comment": str,
    "searchScopes": list,
    "generatedDirs": list,
    "integrationRef": str,
    "auditGate": dict,
    "baselineFile": str,
    "ratchets": list,
    "enforcementMap": dict,
    "catalogTests": list,
    "layers": dict,
    "planningSources": list,
    "canonicalSources": dict,
    "newExports": dict,
    "decisionRecords": dict,
    "semanticClones": dict,
    "hubFiles": dict,
}

# ratchets: each entry is a named metric and the shell command that prints its current value.
RATCHET = {
    "name": str,
    "countCommand": str,
}
# Optional ratchet keys: `locationsCommand` prints the locations behind the count, one per line, largest first
# (the duplicate detector's clone list, the suppression entries); the audit's structural lens reports them.
# `groupsCommand` (the third-copy trigger) prints one line per copy group of a clone-detector ratchet,
# `<copies> <lines> <file>:<start>-<end> ...` (`scripts/forge/count-tools.py clone-groups`); `ratchet.py copies`
# reads it.
RATCHET_OPTIONAL = {
    "locationsCommand": str,
    "groupsCommand": str,
    "redefinitions": dict,
}
# ratchets[].redefinitions: for a clone-detector ratchet, the files where a later definition of an object supersedes
# an earlier one (database migrations), and the regex whose one capture group is the defined object's qualified name.
# A clone pair whose two sides define the same object is a redefinition, not a duplicate
# (`count-tools.py clone-lines` / `clone-rows`).
REDEFINITIONS = {
    "files": list,
    "definition": str,
}

# enforcementMap: where the rule table is and where its `lint:` and `gate:` references must resolve.
ENFORCEMENT_MAP = {
    "doc": str,
    "heading": str,
    "rulePattern": str,
    "lintConfigs": list,
    "gateFiles": list,
}
# Optional enforcementMap keys: `rulesDoc` is the document that declares the rule ids (`rulePattern`) when the map
# lives in a document of its own; when unset, `doc` declares them.
ENFORCEMENT_MAP_OPTIONAL = {
    "rulesDoc": str,
}

# layers: the layer directions of a feature-sliced module, enforced by the module-boundary lint.
# `scope` is one directory glob (a string) or a list of them; it is validated apart.
LAYERS = {
    "layers": list,
    "sharedDirs": list,
}
LAYER = {
    "name": str,
    "dirs": list,
    "mayImport": list,
}

# canonicalSources: where the canonical sources registry table is (a markdown table under a heading of a doc).
CANONICAL_SOURCES = {
    "doc": str,
    "heading": str,
}

# decisionRecords: the frozen decision history log, its freeze date, and the directory and name pattern of the
# per-unit fragment files that take new decision rows (`scripts/forge/check-decision-records.py`).
DECISION_RECORDS = {
    "log": str,
    "frozenOn": str,
    "fragments": str,
    "fragmentName": str,
}

# semanticClones: the optional `/audit` step that lists semantic (Type-4) clone candidates with jscpd `--semantic`.
# `enabled` switches the step on; `paths` are the directories scanned (they exist); `scope` is the kinds of pair
# reported; `model` is the embedding model, downloaded once by the user. Optional: `ignore` (file globs left out),
# `threshold` (the lowest cosine similarity reported, in (0, 1]).
SEMANTIC_CLONES = {
    "enabled": bool,
    "paths": list,
    "scope": str,
    "model": str,
}
SEMANTIC_CLONES_OPTIONAL = {
    "ignore": list,
    "threshold": (int, float),
    "$comment": str,
}
SEMANTIC_SCOPES = ("all", "same", "cross")

# hubFiles (structural check): a hub is a file that most feature changes edit (a composition root, a route list, a
# shared seed), the Open/Closed smell the per-spec structural check looks for (`scripts/forge/hub-files.py`).
# `commitPattern` is a regex on the subject of the integration ref's feature commits (one squashed commit per
# feature); `window` is how many of the newest such commits are read; `threshold` is how many of them must edit a file
# for it to be a hub; `paths` are the directories counted (they exist). Optional: `ignore` (file globs left out, e.g.
# generated files).
HUB_FILES = {
    "commitPattern": str,
    "window": int,
    "threshold": int,
    "paths": list,
}
HUB_FILES_OPTIONAL = {
    "ignore": list,
    "$comment": str,
}

# newExports: which declarations count as exports, per language, for the reviewer's new-exports check
# (`scripts/forge/new-exports.py`). Each entry names its files (globs as git's `:(glob)` pathspec reads them),
# optional exclusions, and either a regex whose first group is the exported name or `"kind": "file"` (every added
# file is one export, named by its stem).
NEW_EXPORT_PATTERN = {
    "files": list,
}
NEW_EXPORT_OPTIONAL = {
    "exclude": list,
    "regex": str,
    "kind": str,
    "$comment": str,
}

# auditGate: every key is required when the section is present.
AUDIT_GATE = {
    "every": int,
    "auditReports": str,
    "triageHeading": str,
    "mergedSpecMarker": str,
    "specFile": str,
    "blockingIssues": dict,
}

# auditGate.blockingIssues: a command printing a JSON array of issues ({number, title, labels}) and the labels an open
# issue must all carry to block.
BLOCKING_ISSUES = {
    "command": str,
    "labels": list,
}


# Binding consumers: per key, the harness files that read it (Forge commands, agents, role files, harness scripts;
# the same paths on every project). A markdown consumer names the binding file and the key in backticks at the step
# where it reads it; a Python script imports this module and names the key; another script names the binding file and
# the key. A consumer file that does not exist is skipped (agents are generated per stack, and some harness scripts
# are listed ahead of being shipped), but a key that is set must have at least one existing consumer, and every key
# of TOP_LEVEL must be listed here.
# Per-task agents (implementers, the per-task code reviewer) are not consumers: the runner that launches them resolves
# `searchScopes` into the prompt, and they consult the registry through the lookup of check-canonical-sources.py
# (`--concepts`, `--rows`), so they never read the binding file.
# Command files (`.claude/commands/*.md`) are not listed yet; they are added when the commands name the binding.
# Until then a key with no script consumer has an empty list.
CONSUMERS: dict[str, list[str]] = {
    "searchScopes": ["scripts/forge/quality_profile.py"],
    "generatedDirs": ["scripts/forge/quality_profile.py"],
    "integrationRef": [
        "scripts/forge/audit-gate.py",
        "scripts/forge/check-decision-records.py",
        "scripts/forge/check-task-evidence.py",
        "scripts/forge/hub-files.py",
        "scripts/forge/new-exports.py",
    ],
    "auditGate": ["scripts/forge/audit-gate.py"],
    "baselineFile": ["scripts/forge/ratchet.py"],
    "ratchets": [
        "scripts/forge/ratchet.py",
        "scripts/forge/count-tools.py",
        "scripts/forge/check-enforcement-map.py",
    ],
    "enforcementMap": ["scripts/forge/check-enforcement-map.py"],
    "catalogTests": [],
    "layers": [],
    "planningSources": [],
    "canonicalSources": ["scripts/forge/check-canonical-sources.py"],
    "newExports": ["scripts/forge/new-exports.py"],
    "decisionRecords": ["scripts/forge/check-decision-records.py"],
    "semanticClones": [],
    "hubFiles": ["scripts/forge/hub-files.py"],
}

# Scripts other than Python that read the binding file themselves, with the reason they cannot use the loader.
NON_PYTHON_READERS: dict[str, str] = {}


class ProfileError(Exception):
    """The profile file is missing or is not valid JSON."""


def load(path: str = DEFAULT_PROFILE) -> dict:
    """Read the profile; raise ProfileError when it is missing or not a JSON object."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ProfileError(f"quality profile not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"quality profile is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"quality profile must be a JSON object: {path}")
    return data


def is_unset(key: str, value: object) -> bool:
    """Whether a top-level value is empty of its own type (`[]`, `{}`, `""`): the key is not configured yet."""
    expected = TOP_LEVEL.get(key)
    return expected is not None and isinstance(value, expected) and not isinstance(value, bool) and len(value) == 0


def configured(profile: dict) -> dict:
    """The profile without its unset keys (see `is_unset`) and without `$comment`."""
    return {k: v for k, v in profile.items() if k != "$comment" and not is_unset(k, v)}


def validate(profile: dict, repo: str = REPO) -> list[str]:
    """Return one message per problem; an empty list means the profile is valid. Unset keys are not checked."""
    problems: list[str] = []
    for key, value in profile.items():
        expected = TOP_LEVEL.get(key)
        if expected is None:
            problems.append(f"unknown key: {key}")
        elif not isinstance(value, expected):
            problems.append(f"{key}: expected {expected.__name__}")
    profile = {k: v for k, v in profile.items() if not is_unset(k, v)}

    scopes = profile.get("searchScopes")
    if isinstance(scopes, list):
        for scope in scopes:
            if not isinstance(scope, str) or not scope.endswith("/"):
                problems.append(f"searchScopes: {scope!r} must be a directory path ending in '/'")
            elif not os.path.isdir(os.path.join(repo, scope)):
                problems.append(f"searchScopes: {scope} does not exist")

    problems.extend(_validate_generated_dirs(profile, repo))

    gate = profile.get("auditGate")
    if isinstance(gate, dict):
        for key, expected in AUDIT_GATE.items():
            if key not in gate:
                problems.append(f"auditGate.{key}: missing")
            # bool is a subclass of int; `true` is not a threshold.
            elif not isinstance(gate[key], expected) or isinstance(gate[key], bool):
                problems.append(f"auditGate.{key}: expected {expected.__name__}")
        for key in gate:
            if key not in AUDIT_GATE and key != "$comment":
                problems.append(f"auditGate: unknown key: {key}")
        issues = gate.get("blockingIssues")
        if isinstance(issues, dict):
            for key, expected in BLOCKING_ISSUES.items():
                if not isinstance(issues.get(key), expected):
                    problems.append(f"auditGate.blockingIssues.{key}: expected {expected.__name__}")
            labels = issues.get("labels")
            if isinstance(labels, list) and (not labels or not all(isinstance(x, str) for x in labels)):
                problems.append("auditGate.blockingIssues.labels: must be a non-empty list of strings")
        every = gate.get("every")
        if isinstance(every, int) and not isinstance(every, bool) and every < 1:
            problems.append("auditGate.every: must be at least 1")
        if "auditGate" in profile and "integrationRef" not in profile:
            problems.append("integrationRef: required by auditGate")

    problems.extend(_validate_ratchets(profile))
    problems.extend(_validate_enforcement_map(profile, repo))
    problems.extend(_validate_catalog_tests(profile, repo))
    problems.extend(_validate_layers(profile, repo))
    problems.extend(_validate_planning_sources(profile, repo))
    problems.extend(_validate_canonical_sources(profile, repo))
    problems.extend(_validate_new_exports(profile))
    problems.extend(_validate_decision_records(profile, repo))
    problems.extend(_validate_semantic_clones(profile, repo))
    problems.extend(_validate_hub_files(profile, repo))
    return problems


def _validate_generated_dirs(profile: dict, repo: str) -> list[str]:
    """`generatedDirs`: existing directories ending in '/', each strictly inside one of the `searchScopes`."""
    dirs = profile.get("generatedDirs")
    if not isinstance(dirs, list):
        return []
    scopes = [s for s in profile.get("searchScopes") or [] if isinstance(s, str)]
    problems: list[str] = []
    for entry in dirs:
        if not isinstance(entry, str) or not entry.endswith("/"):
            problems.append(f"generatedDirs: {entry!r} must be a directory path ending in '/'")
        elif not os.path.isdir(os.path.join(repo, entry)):
            problems.append(f"generatedDirs: {entry} does not exist")
        elif not any(entry != scope and entry.startswith(scope) for scope in scopes):
            problems.append(f"generatedDirs: {entry} must lie strictly inside one of searchScopes")
    return problems


def search_pathspecs(profile: dict) -> list[str]:
    """Where agents search: each `searchScopes` entry plus one `:(exclude)<dir>` per `generatedDirs` entry."""
    scopes = [s for s in profile.get("searchScopes") or [] if isinstance(s, str)]
    excludes = [f":(exclude){d}" for d in profile.get("generatedDirs") or [] if isinstance(d, str)]
    return scopes + excludes if scopes else []


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x for x in value)


def _validate_ratchets(profile: dict) -> list[str]:
    problems: list[str] = []
    ratchets = profile.get("ratchets")
    if not isinstance(ratchets, list):
        return problems
    if not isinstance(profile.get("baselineFile"), str):
        problems.append("baselineFile: required by ratchets")
    names: set[str] = set()
    for index, entry in enumerate(ratchets):
        if not isinstance(entry, dict):
            problems.append(f"ratchets[{index}]: expected object")
            continue
        for key, expected in RATCHET.items():
            if not isinstance(entry.get(key), expected) or not entry.get(key):
                problems.append(f"ratchets[{index}].{key}: expected non-empty {expected.__name__}")
        for key, expected in RATCHET_OPTIONAL.items():
            if key in entry and (not isinstance(entry[key], expected) or not entry[key]):
                problems.append(f"ratchets[{index}].{key}: expected non-empty {expected.__name__}")
        for key in entry:
            if key not in RATCHET and key not in RATCHET_OPTIONAL and key != "$comment":
                problems.append(f"ratchets[{index}]: unknown key: {key}")
        if isinstance(entry.get("redefinitions"), dict):
            problems.extend(_validate_redefinitions(entry["redefinitions"], f"ratchets[{index}].redefinitions"))
        name = entry.get("name")
        if isinstance(name, str):
            if name in names:
                problems.append(f"ratchets: duplicate name: {name}")
            names.add(name)
    return problems


def _validate_redefinitions(section: dict, where: str) -> list[str]:
    problems: list[str] = []
    for key, expected in REDEFINITIONS.items():
        if not isinstance(section.get(key), expected) or not section.get(key):
            problems.append(f"{where}.{key}: expected non-empty {expected.__name__}")
    for key in section:
        if key not in REDEFINITIONS and key != "$comment":
            problems.append(f"{where}: unknown key: {key}")
    files = section.get("files")
    if isinstance(files, list) and files and not _is_str_list(files):
        problems.append(f"{where}.files: must be a list of strings")
    pattern = section.get("definition")
    if isinstance(pattern, str) and pattern:
        try:
            if re.compile(pattern).groups != 1:
                problems.append(f"{where}.definition: needs exactly one capture group (the object name)")
        except re.error as exc:
            problems.append(f"{where}.definition: invalid regex: {exc}")
    return problems


def _validate_enforcement_map(profile: dict, repo: str) -> list[str]:
    problems: list[str] = []
    section = profile.get("enforcementMap")
    if not isinstance(section, dict):
        return problems
    for key, expected in ENFORCEMENT_MAP.items():
        if key not in section:
            problems.append(f"enforcementMap.{key}: missing")
        elif not isinstance(section[key], expected):
            problems.append(f"enforcementMap.{key}: expected {expected.__name__}")
    for key, expected in ENFORCEMENT_MAP_OPTIONAL.items():
        if key in section and not isinstance(section[key], expected):
            problems.append(f"enforcementMap.{key}: expected {expected.__name__}")
    for key in section:
        if key not in ENFORCEMENT_MAP and key not in ENFORCEMENT_MAP_OPTIONAL and key != "$comment":
            problems.append(f"enforcementMap: unknown key: {key}")
    for key in ("doc", "rulesDoc"):
        doc = section.get(key)
        if isinstance(doc, str) and not os.path.isfile(os.path.join(repo, doc)):
            problems.append(f"enforcementMap.{key}: {doc} does not exist")
    for key in ("lintConfigs", "gateFiles"):
        patterns = section.get(key)
        if isinstance(patterns, list):
            if not _is_str_list(patterns):
                problems.append(f"enforcementMap.{key}: must be a non-empty list of strings")
            elif not any(glob.glob(os.path.join(repo, p), recursive=True) for p in patterns):
                problems.append(f"enforcementMap.{key}: no pattern matches a file")
    return problems


def _validate_new_exports(profile: dict) -> list[str]:
    problems: list[str] = []
    section = profile.get("newExports")
    if not isinstance(section, dict):
        return problems
    for key in section:
        if key not in ("patterns", "$comment"):
            problems.append(f"newExports: unknown key: {key}")
    patterns = section.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        return problems + ["newExports.patterns: must be a non-empty list"]
    for i, entry in enumerate(patterns):
        where = f"newExports.patterns[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: expected dict")
            continue
        for key in entry:
            if key not in NEW_EXPORT_PATTERN and key not in NEW_EXPORT_OPTIONAL:
                problems.append(f"{where}: unknown key: {key}")
        for key in ("files", "exclude"):
            if key in entry and (not _is_str_list(entry[key]) or (key == "files" and not entry[key])):
                problems.append(f"{where}.{key}: must be a non-empty list of strings" if key == "files"
                                else f"{where}.{key}: must be a list of strings")
        if "files" not in entry:
            problems.append(f"{where}.files: missing")
        kind, regex = entry.get("kind"), entry.get("regex")
        if kind is not None and kind != "file":
            problems.append(f"{where}.kind: the only kind is \"file\"")
        if (kind is None) == (regex is None):
            problems.append(f"{where}: give either a regex or \"kind\": \"file\"")
        elif isinstance(regex, str):
            try:
                if re.compile(regex).groups < 1:
                    problems.append(f"{where}.regex: needs a capture group for the exported name")
            except re.error as exc:
                problems.append(f"{where}.regex: does not compile: {exc}")
    return problems


def _validate_catalog_tests(profile: dict, repo: str) -> list[str]:
    problems: list[str] = []
    tests = profile.get("catalogTests")
    if not isinstance(tests, list):
        return problems
    for entry in tests:
        if not isinstance(entry, str) or not os.path.isfile(os.path.join(repo, entry)):
            problems.append(f"catalogTests: {entry!r} is not an existing file")
    return problems


def _validate_layers_scope(scope: object, repo: str) -> list[str]:
    """Validate `layers.scope`: a directory glob ending in '/', or a non-empty list of them.

    A single string must match a directory. In a list, every entry must end in '/' and at least one
    must match a directory: an entry may name a zone that a later task creates.
    """
    if scope is None:
        return ["layers.scope: missing"]
    if isinstance(scope, str):
        if not scope.endswith("/"):
            return ["layers.scope: must end in '/'"]
        if not glob.glob(os.path.join(repo, scope)):
            return [f"layers.scope: {scope} matches no directory"]
        return []
    if not isinstance(scope, list) or not scope or not all(isinstance(x, str) for x in scope):
        return ["layers.scope: expected a string or a non-empty list of strings"]
    problems = [f"layers.scope: {x} must end in '/'" for x in scope if not x.endswith("/")]
    if not problems and not any(glob.glob(os.path.join(repo, x)) for x in scope):
        problems.append("layers.scope: no entry matches a directory")
    return problems


def _validate_layers(profile: dict, repo: str) -> list[str]:
    problems: list[str] = []
    section = profile.get("layers")
    if not isinstance(section, dict):
        return problems
    for key, expected in LAYERS.items():
        if key not in section:
            problems.append(f"layers.{key}: missing")
        elif not isinstance(section[key], expected):
            problems.append(f"layers.{key}: expected {expected.__name__}")
    for key in section:
        if key not in LAYERS and key not in ("$comment", "scope"):
            problems.append(f"layers: unknown key: {key}")
    problems.extend(_validate_layers_scope(section.get("scope"), repo))
    shared = section.get("sharedDirs")
    if isinstance(shared, list) and not all(isinstance(x, str) for x in shared):
        problems.append("layers.sharedDirs: expected a list of strings")
    layers = section.get("layers")
    if not isinstance(layers, list):
        return problems
    names: list[str] = []
    dirs: list[str] = []
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            problems.append(f"layers.layers[{index}]: expected object")
            continue
        for key, expected in LAYER.items():
            if not isinstance(layer.get(key), expected):
                problems.append(f"layers.layers[{index}].{key}: expected {expected.__name__}")
        for key in layer:
            if key not in LAYER and key != "$comment":
                problems.append(f"layers.layers[{index}]: unknown key: {key}")
        if isinstance(layer.get("name"), str):
            names.append(layer["name"])
        layer_dirs = layer.get("dirs")
        if isinstance(layer_dirs, list):
            if not _is_str_list(layer_dirs):
                problems.append(f"layers.layers[{index}].dirs: must be a non-empty list of strings")
            else:
                dirs.extend(layer_dirs)
    if len(set(names)) != len(names):
        problems.append("layers.layers: duplicate layer name")
    if len(set(dirs)) != len(dirs):
        problems.append("layers.layers: a directory belongs to two layers")
    for index, layer in enumerate(layers):
        if isinstance(layer, dict) and isinstance(layer.get("mayImport"), list):
            for target in layer["mayImport"]:
                if target not in names:
                    problems.append(f"layers.layers[{index}].mayImport: unknown layer: {target}")
                elif target == layer.get("name"):
                    problems.append(f"layers.layers[{index}].mayImport: a layer lists itself")
    if isinstance(shared, list) and set(shared) & set(dirs):
        problems.append("layers.sharedDirs: a shared directory is also a layer directory")
    return problems


def _validate_planning_sources(profile: dict, repo: str) -> list[str]:
    """planningSources: the documents that declare future variations (plans, briefs, open questions)."""
    problems: list[str] = []
    sources = profile.get("planningSources")
    if not isinstance(sources, list):
        return problems
    if not _is_str_list(sources):
        problems.append("planningSources: must be a non-empty list of strings")
        return problems
    for entry in sources:
        if not os.path.isfile(os.path.join(repo, entry)):
            problems.append(f"planningSources: {entry} does not exist")
    return problems


def _validate_canonical_sources(profile: dict, repo: str) -> list[str]:
    problems: list[str] = []
    section = profile.get("canonicalSources")
    if not isinstance(section, dict):
        return problems
    for key, expected in CANONICAL_SOURCES.items():
        if not isinstance(section.get(key), expected) or not section.get(key):
            problems.append(f"canonicalSources.{key}: expected a non-empty {expected.__name__}")
    for key in section:
        if key not in CANONICAL_SOURCES and key != "$comment":
            problems.append(f"canonicalSources: unknown key: {key}")
    doc = section.get("doc")
    if isinstance(doc, str) and doc and not os.path.isfile(os.path.join(repo, doc)):
        problems.append(f"canonicalSources.doc: {doc} does not exist")
    return problems


def _validate_decision_records(profile: dict, repo: str) -> list[str]:
    """decisionRecords: every key present and non-empty, the log exists, the date and the pattern parse."""
    problems: list[str] = []
    section = profile.get("decisionRecords")
    if not isinstance(section, dict):
        return problems
    for key, expected in DECISION_RECORDS.items():
        if not isinstance(section.get(key), expected) or not section.get(key):
            problems.append(f"decisionRecords.{key}: expected a non-empty {expected.__name__}")
    for key in section:
        if key not in DECISION_RECORDS and key != "$comment":
            problems.append(f"decisionRecords: unknown key: {key}")
    log = section.get("log")
    if isinstance(log, str) and log and not os.path.isfile(os.path.join(repo, log)):
        problems.append(f"decisionRecords.log: {log} does not exist")
    frozen = section.get("frozenOn")
    if isinstance(frozen, str) and frozen and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", frozen):
        problems.append("decisionRecords.frozenOn: expected a date YYYY-MM-DD")
    pattern = section.get("fragmentName")
    if isinstance(pattern, str) and pattern:
        try:
            re.compile(pattern)
        except re.error as exc:
            problems.append(f"decisionRecords.fragmentName: invalid pattern: {exc}")
    return problems


def _validate_hub_files(profile: dict, repo: str) -> list[str]:
    """hubFiles: the required keys have their types, `commitPattern` compiles, `1 <= threshold <= window`, `paths`
    exist, `ignore` is a list of strings."""
    problems: list[str] = []
    section = profile.get("hubFiles")
    if not isinstance(section, dict):
        return problems
    for key, expected in HUB_FILES.items():
        value = section.get(key)
        if not isinstance(value, expected) or isinstance(value, bool):
            problems.append(f"hubFiles.{key}: expected {expected.__name__}")
    for key in section:
        if key not in HUB_FILES and key not in HUB_FILES_OPTIONAL:
            problems.append(f"hubFiles: unknown key: {key}")
    pattern = section.get("commitPattern")
    if isinstance(pattern, str):
        try:
            re.compile(pattern)
        except re.error as exc:
            problems.append(f"hubFiles.commitPattern: {exc}")
    window, threshold = section.get("window"), section.get("threshold")
    if isinstance(window, int) and isinstance(threshold, int) and not 1 <= threshold <= window:
        problems.append("hubFiles.threshold: must be at least 1 and at most window")
    for key in ("paths", "ignore"):
        value = section.get(key)
        if key in section and (not isinstance(value, list) or not all(isinstance(x, str) and x for x in value)
                               or (key == "paths" and not value)):
            problems.append(f"hubFiles.{key}: must be a {'non-empty ' if key == 'paths' else ''}list of strings")
    paths = section.get("paths")
    if isinstance(paths, list):
        for path in paths:
            if isinstance(path, str) and path and not os.path.exists(os.path.join(repo, path)):
                problems.append(f"hubFiles.paths: {path} does not exist")
    return problems


def _validate_semantic_clones(profile: dict, repo: str) -> list[str]:
    """semanticClones: the required keys have their types, `paths` exist, `scope` is one of the three scopes,
    `threshold` lies in (0, 1]."""
    problems: list[str] = []
    section = profile.get("semanticClones")
    if not isinstance(section, dict):
        return problems
    for key, expected in SEMANTIC_CLONES.items():
        if not isinstance(section.get(key), expected):
            problems.append(f"semanticClones.{key}: expected {expected.__name__}")
    for key, expected in SEMANTIC_CLONES_OPTIONAL.items():
        value = section.get(key)
        if key in section and (not isinstance(value, expected) or isinstance(value, bool)):
            problems.append(f"semanticClones.{key}: expected {'number' if key == 'threshold' else expected.__name__}")
    for key in section:
        if key not in SEMANTIC_CLONES and key not in SEMANTIC_CLONES_OPTIONAL:
            problems.append(f"semanticClones: unknown key: {key}")
    for key in ("paths", "ignore"):
        value = section.get(key)
        if isinstance(value, list) and (not all(isinstance(x, str) and x for x in value) or (key == "paths" and not value)):
            problems.append(f"semanticClones.{key}: must be a {'non-empty ' if key == 'paths' else ''}list of strings")
    paths = section.get("paths")
    if isinstance(paths, list):
        for path in paths:
            if isinstance(path, str) and path and not os.path.exists(os.path.join(repo, path)):
                problems.append(f"semanticClones.paths: {path} does not exist")
    scope = section.get("scope")
    if isinstance(scope, str) and scope not in SEMANTIC_SCOPES:
        problems.append(f"semanticClones.scope: must be one of {', '.join(SEMANTIC_SCOPES)}")
    threshold = section.get("threshold")
    if isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and not 0 < threshold <= 1:
        problems.append("semanticClones.threshold: must be in (0, 1]")
    return problems


# The Forge default audit gate: active from the first feature spec. `init --integration-ref` writes it, so a new
# project audits after its first `every` merged feature specs instead of after an audit nobody scheduled. The blocking
# issues come from a profile command, so a project on another issue tracker replaces only the command.
DEFAULT_AUDIT_GATE = {
    "every": 3,
    "auditReports": "audits/*-audit.md",
    "triageHeading": "## Theme triage",
    "mergedSpecMarker": "specs/*/summary.md",
    "specFile": "specs/*/spec.md",
    "blockingIssues": {
        "command": "gh issue list --state open --label source:audit --label severity:critical "
                   "--json number,title,labels --limit 200",
        "labels": ["source:audit", "severity:critical"],
    },
}


def skeleton(integration_ref: str = "") -> dict:
    """The binding of a new project: every key present and unset, for `/constitute` and `/onboard` to fill. With an
    integration ref, `integrationRef` and the default `auditGate` are set, so the audit gate runs from the first spec."""
    data: dict = {
        "$comment": "Project binding of the generic structural-quality mechanisms. Empty keys are unset (the mechanism "
        "runs in its manual form). /constitute and /onboard fill them; validate with: "
        "python3 scripts/forge/quality_profile.py validate",
    }
    for key, expected in TOP_LEVEL.items():
        if key != "$comment":
            data[key] = expected()
    if integration_ref:
        data["integrationRef"] = integration_ref
        data["auditGate"] = json.loads(json.dumps(DEFAULT_AUDIT_GATE))
    return data


def _references_key(text: str, key: str, markdown: bool) -> bool:
    if markdown:
        return re.search(r"`" + re.escape(key) + r"[`.]", text) is not None
    return re.search(r"\b" + re.escape(key) + r"\b", text) is not None


def _docstring_nodes(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _direct_reads(path: str) -> list[int]:
    """Lines of a Python script where a string other than a docstring names the binding file."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    docstrings = _docstring_nodes(tree)
    return sorted({
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and BINDING_NAME in node.value
        and id(node) not in docstrings
    })


def check_consumers(profile: dict, repo: str = REPO, consumers: dict[str, list[str]] | None = None,
                    readers: dict[str, str] | None = None, scripts_dir: str = HARNESS_SCRIPTS) -> list[str]:
    """Return one message per binding-consumer problem; an empty list means every consumer names its keys."""
    consumers = CONSUMERS if consumers is None else consumers
    readers = NON_PYTHON_READERS if readers is None else readers
    problems: list[str] = []
    for key in TOP_LEVEL:
        if key != "$comment" and key not in consumers:
            problems.append(f"consumers: {key}: no consumer declared (add it to CONSUMERS)")
    for key in consumers:
        if key not in TOP_LEVEL:
            problems.append(f"consumers: {key}: not a binding key")
    active = configured(profile)
    unnamed: set[str] = set()
    for key, files in consumers.items():
        existing = [f for f in files if os.path.isfile(os.path.join(repo, f))]
        if key in active and not existing:
            problems.append(f"consumers: {key}: set, but no consumer file exists")
        for rel in existing:
            with open(os.path.join(repo, rel), encoding="utf-8") as handle:
                text = handle.read()
            markdown = rel.endswith(".md")
            if rel.endswith(".py"):
                names_binding = rel == f"{scripts_dir}/quality_profile.py" or re.search(
                    r"^\s*import quality_profile\b", text, re.MULTILINE) is not None
            else:
                names_binding = BINDING_NAME in text
            if not names_binding and rel not in unnamed:
                unnamed.add(rel)
                how = "import quality_profile" if rel.endswith(".py") else BINDING_NAME
                problems.append(f"consumers: {rel}: reads the binding but does not name it ({how})")
            if not _references_key(text, key, markdown):
                form = f"`{key}`" if markdown else key
                problems.append(f"consumers: {rel}: does not name the key {form} at the step that reads it")
    root = os.path.join(repo, scripts_dir)
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in ("tests", "node_modules", "__pycache__"))
        for name in sorted(files):
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, repo).replace(os.sep, "/")
            if name.endswith(".py"):
                if name == "quality_profile.py":
                    continue
                try:
                    lines = _direct_reads(path)
                except (SyntaxError, UnicodeDecodeError) as exc:
                    problems.append(f"loader: {rel}: cannot parse: {exc}")
                    continue
                for line in lines:
                    problems.append(f"loader: {rel}:{line}: names the binding file; load it through quality_profile.load")
            elif name.endswith((".ts", ".js", ".cjs", ".mjs", ".sh")) and rel not in readers:
                try:
                    with open(path, encoding="utf-8") as handle:
                        if BINDING_NAME in handle.read():
                            problems.append(f"loader: {rel}: reads the binding but is not a declared non-Python reader")
                except UnicodeDecodeError:
                    continue
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (("validate", "validate the profile"),
                       ("consumers", "check that every consumer names the keys it reads"),
                       ("scopes", "print the resolved search scopes: searchScopes plus an exclude per generatedDirs"),
                       ("init", "write the empty binding of a new project")):
        command = sub.add_parser(name, help=text)
        command.add_argument("--profile", default=DEFAULT_PROFILE)
        if name == "init":
            command.add_argument("--integration-ref", default="",
                                 help="set integrationRef and the default auditGate (active from the first spec)")
    args = parser.parse_args(argv)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(args.profile)))

    if args.command == "init":
        if os.path.exists(args.profile):
            print(f"quality-profile: {args.profile} exists; init writes only a new binding")
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(args.profile)), exist_ok=True)
        with open(args.profile, "w", encoding="utf-8") as handle:
            json.dump(skeleton(args.integration_ref), handle, indent=2)
            handle.write("\n")
        state = "integrationRef and auditGate set, other keys unset" if args.integration_ref else "all keys unset"
        print(f"quality-profile: wrote {args.profile} ({state})")
        return 0
    try:
        profile = load(args.profile)
    except ProfileError as exc:
        # `consumers` checks harness files, not values: without a binding every key is unset.
        if args.command != "consumers" or os.path.exists(args.profile):
            print(exc, file=sys.stderr)
            return 2
        profile = {}
    if args.command == "scopes":
        print("\n".join(search_pathspecs(profile)))
        return 0
    if args.command == "consumers":
        problems = check_consumers(profile, repo=repo)
        for problem in problems:
            print(f"quality-profile: {problem}")
        if problems:
            return 1
        print(f"quality-profile: consumers ok ({len(CONSUMERS)} keys)")
        return 0
    problems = validate(profile, repo=repo)
    for problem in problems:
        print(f"quality-profile: {problem}")
    if problems:
        return 1
    unset = sorted(k for k, v in profile.items() if is_unset(k, v))
    print("quality-profile: valid" + (f" (unset: {', '.join(unset)})" if unset else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
