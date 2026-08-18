"""4-dimension content quality metrics for cmd_validate.

Dimensions:
  Dim 1 slot_fill — required sections/fields populated
  Dim 2 citation  — path-like tokens resolve under install_root (recursive, bounded;
                    placeholder/fragment tokens filtered; devforge-namespace tokens exempt)
  Dim 3 code_syntax — code_example.code parses as declared language
  Dim 4 rule_tag  — every rule tag in closed enum
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import init_helper  # type: ignore  # noqa: E402

from ._render import _IDENTITY_REQUIRED_SUBFIELDS
from ._schema import ENUM_FIELDS, _PATTERNS_BUCKETS


# Regex to extract path-like tokens that look like source/doc file references.
# Matches tokens with a common code/doc extension. Applied to rule text,
# table cells, and code_example annotations.
#
# Alternation order matters: longer suffixes MUST come first so the regex
# engine matches `.tsx` before `.ts`, `.json` before `.js`, `.jsx` before
# `.js`, `.yaml` before `.yml`. Otherwise `tsconfig.json` extracts as
# `tsconfig.js` and the existence check fails on the wrong path. This
# ordered tuple is the single source for both the regex alternation and
# the segment-artifact citation-token filter (filter (d) below) — the two
# must never drift apart.
_PATH_EXTENSIONS = (
    "tsx", "ts", "jsx", "json", "yaml", "js", "vue", "py", "md", "yml", "toml",
)

_PATH_TOKEN_RE = re.compile(
    r"[\w\-\./]+"
    r"\.(?:" + "|".join(_PATH_EXTENSIONS) + r")"
)

# Composite weights (must sum to 1.0).
_VALIDATE_WEIGHTS = {
    "slot_fill":   0.30,
    "citation":    0.25,
    "code_syntax": 0.25,
    "rule_tag":    0.20,
}

# Composite pass threshold.
_COMPOSITE_PASS_THRESHOLD = 0.95

# Per-dimension pass thresholds. rule_tag is mechanical (any invalid tag is
# a helper bug); the other 3 dimensions allow up to 5% slop.
_DIM_PASS_THRESHOLDS = {
    "slot_fill":   0.95,
    "citation":    0.95,
    "code_syntax": 0.95,
    "rule_tag":    1.0,
}


# ---------------------------------------------------------------------------
# Dim 1 — Slot-fill rate.
# ---------------------------------------------------------------------------


def _count_slot_fill(state: dict) -> "tuple":
    """Return (filled_slots, total_slots, list_of_failed_slot_names).

    Required slots:
      - project_identity 4 subfields (4 slots)
      - architecture_rules: ≥1 section (1 slot)
      - code_quality_standards: ≥1 section (1 slot)
      - patterns_and_antipatterns: ≥1 rule across 6 buckets (1 slot)
      - domain_rules: ≥1 section (1 slot)
      - workflow_rules: ≥1 section (1 slot)
      - scaffolding_guide (greenfield only): ≥1 starter_directory OR ≥1 sample_file (1 slot)
    Total: 9 (existing-codebase) or 10 (greenfield)
    """
    filled = 0
    total = 0
    failed = []  # type: List[str]

    identity = state.get("project_identity") or {}
    for subfield in _IDENTITY_REQUIRED_SUBFIELDS:
        total += 1
        val = identity.get(subfield)
        if val and str(val).strip():
            filled += 1
        else:
            failed.append("project_identity.{0}".format(subfield))

    for bucket_key, label in [
        ("architecture_rules", "Section 2"),
        ("code_quality_standards", "Section 3"),
        ("domain_rules", "Section 5"),
        ("workflow_rules", "Section 6"),
    ]:
        total += 1
        sections = state.get(bucket_key) or []
        if sections:
            filled += 1
        else:
            failed.append("{0} ({1}): no sub-sections".format(label, bucket_key))

    total += 1
    pat = state.get("patterns_and_antipatterns") or {}
    any_rule = any(
        isinstance(pat.get(b), list) and pat.get(b)
        for b in _PATTERNS_BUCKETS
    )
    if any_rule:
        filled += 1
    else:
        failed.append("Section 4 (patterns_and_antipatterns): no rules in any bucket")

    mode = state.get("mode")
    if mode == "greenfield":
        total += 1
        scaffolding = state.get("scaffolding_guide") or {}
        starter_dirs = scaffolding.get("starter_directories") or []
        sample_files = scaffolding.get("sample_files") or []
        if starter_dirs or sample_files:
            filled += 1
        else:
            failed.append("Section 7 (scaffolding_guide): no starter_directory or sample_file")

    return filled, total, failed


# ---------------------------------------------------------------------------
# Dim 2 — Citation validity.
# ---------------------------------------------------------------------------


def _extract_path_tokens(text: str) -> "List[str]":
    """Return list of path-like tokens extracted from text using _PATH_TOKEN_RE."""
    if not text:
        return []
    return _PATH_TOKEN_RE.findall(text)


def _collect_citation_texts(state: dict) -> "List[str]":
    """Collect all text fields that may contain path references.

    Walks:
    - rule.text in all section buckets + patterns buckets
    - table cell strings (all cells in all rows)
    - code_example.annotation strings

    Returns list of individual text strings (one per field value, not per token).
    """
    texts = []  # type: List[str]

    def _add_rule(rule: dict) -> None:
        t = rule.get("text")
        if t:
            texts.append(t)

    def _add_section(section: dict) -> None:
        for rule in section.get("rules", []):
            _add_rule(rule)
        for table in section.get("tables", []):
            for row in table.get("rows", []):
                for cell in row:
                    if cell:
                        texts.append(str(cell))
        for ex in section.get("code_examples", []):
            ann = ex.get("annotation")
            if ann:
                texts.append(ann)

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            _add_section(section)

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for rule in pat.get(bucket) or []:
            _add_rule(rule)

    return texts


def _resolve_effective_root(
    install_root: "Union[str, os.PathLike[str]]",
    init_yaml_path: "Optional[Path]",
) -> "Optional[Path]":
    """Return wrapper-mode effective root, or None for standalone."""
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return None
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return None
    if state.get("workspace_mode") != "wrapper":
        return None
    project_root = state.get("project_root") or ""
    if not project_root or project_root == ".":
        return None
    return Path(install_root) / project_root


# Directory NAMES excluded from the recursive citation-fallback search, at
# any depth. A directory whose basename is a member of this set is never
# descended into, so a file that exists ONLY beneath one of these can never
# resolve a citation token via `_try_resolve`'s bounded-walk stages. Applies
# identically to standalone and wrapper mode (plan 80 Phase 2 OQ-2/OQ-4) —
# a token resolvable today only via a file inside `node_modules` stops
# resolving; that is a deliberate behavioral change, not a regression.
_EXCLUDED_DIR_NAMES = frozenset([
    ".git", "node_modules", "dist", "build", "target", "vendor",
    ".venv", "venv", "__pycache__", ".next", "coverage",
])


def _bounded_walk_has_match(root: "Path", predicate) -> bool:
    """Walk `root` recursively, pruning `_EXCLUDED_DIR_NAMES` at any depth,
    and return True on the first entry (file or directory) for which
    `predicate(name, rel_parts)` is True.

    `predicate` is called with the entry's bare basename and its path
    segments relative to `root` (a tuple). This helper is generic — it
    knows nothing about `Path.rglob` semantics; the rglob-equivalence
    (exact trailing-segments / slash-free-basename-suffix) is a property
    of the two predicates `_try_resolve` composes it with over
    Phase-1-filtered tokens, not of this function.

    Uses `os.walk`, not `Path.rglob` + post-filtering: pruning `dirnames`
    in place stops the walk from ever descending into an excluded
    directory, rather than discarding matches found inside one after the
    fact. `os.walk`'s default `onerror=None` already swallows an
    `OSError` raised while listing an unreadable subdirectory — it skips
    that subtree and continues, so a permission-denied directory cannot
    crash the walk and no extra `try/except` is needed here (unlike
    `Path.rglob`, which propagates that `OSError` to the caller).
    """
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIR_NAMES]
        for name in dirnames + filenames:
            rel_parts = (Path(dirpath) / name).relative_to(root).parts
            if predicate(name, rel_parts):
                return True
    return False


def _build_package_name_map(init_yaml_path: "Optional[Path]") -> "Dict[str, str]":
    """Build {package_name: path} from init.yaml packages_detected list."""
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return {}
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return {}
    result = {}  # type: Dict[str, str]
    for record in state.get("packages_detected") or []:
        p = record.get("path", "")
        name = Path(p).name if p else ""
        if name and p:
            result[name] = p
    return result


# Framework runtime-namespace allowance (D6) — a resolver, NOT one of the
# four filters below. It counts a token RESOLVED; the filters below count
# a token as neither resolved nor unresolved. Keep the two mechanisms
# apart: this function must run (and win) BEFORE a namespace token could
# ever reach `_classify_filtered`.
def _is_devforge_namespace_token(
    token: str,
    devforge_dir: "Union[str, os.PathLike[str]]",
) -> bool:
    """Framework runtime-namespace citation allowance (plan 80 Phase 3 /
    WI-3, ratified design D6, namespace-wide arm).

    True when `token`'s FIRST path segment equals `Path(devforge_dir).name`
    — segment equality, not a string prefix (`.devforgex/foo.md` does NOT
    match a `.devforge` namespace). The namespace name is DERIVED from the
    `devforge_dir` argument the caller already has; no literal directory
    name appears here. A slash-free token exactly equal to the namespace
    (e.g. bare `.devforge`) also matches — the "first path segment" of a
    single-segment token is the whole token — but `_PATH_TOKEN_RE` never
    extracts a bare `.devforge` (no recognized extension), so this case is
    intentional and unreachable in production, not a gap.

    Some framework runtime files (e.g. `.devforge/session-state.md`,
    `.devforge/wip.md`) are created LATER by the pipeline, not at
    constitution-authoring time — a constitution rule citing one is
    correct even though the file does not yet exist on disk (root cause
    RC5). A token matching this check is therefore counted RESOLVED with
    NO filesystem check at all, unlike every other citation-token path.

    Named, accepted recall cost (D6): a genuinely hallucinated
    `.devforge/never-exists.md` citation also resolves silently under
    this rule — that is the ratified trade-off for the namespace-wide
    allowance, not an oversight.
    """
    namespace = Path(devforge_dir).name
    if not namespace:
        return False
    first_segment = token.split("/", 1)[0]
    return first_segment == namespace


# ---------------------------------------------------------------------------
# Citation-token filters — naming-convention placeholders and regex-
# extraction fragments that look like path tokens but are not real
# citations. Applied inside `_count_citations`; a token matching one of
# these counts toward NEITHER `resolved` NOR `unresolved` and produces NO
# `failed_items` entry.
# ---------------------------------------------------------------------------


def _is_placeholder_citation_token(token: str) -> bool:
    """Filter (a) — naming-convention placeholder, e.g. `PageXxx.vue`.

    `Xxx` (case-sensitive) is the framework-wide placeholder-name
    convention used in prose to describe a naming pattern, not a specific
    file (`PageXxx.vue`, `UiXxx.vue`).
    """
    return "Xxx" in token


def _is_extension_only_citation_token(token: str) -> bool:
    """Filter (b) — bare extension fragment with no path, e.g. `.spec.ts`.

    A token with no `/` whose basename starts with `.` is a dotfile-shaped
    extension fragment, not a citation. A token WITH a `/`
    (`.devforge/session-state.md`) is a real relative path and must NOT
    match this filter.
    """
    return "/" not in token and Path(token).name.startswith(".")


def _is_leading_slash_citation_token(token: str) -> bool:
    """Filter (c) — absolute-looking fragment, e.g. `/index.md`.

    Also sidesteps a latent bug (F1): `Path(install_root) / "/index.md"`
    silently discards the left operand for an absolute right operand,
    resolving against filesystem root instead of `install_root`. Filter
    (c) runs BEFORE `_try_resolve` in `_count_citations` so a
    leading-slash token never reaches that join.
    """
    return token.startswith("/")


def _is_pure_extension_chain_segment(segment: str) -> bool:
    """True if `segment` is a dot-prefixed chain of known extensions.

    E.g. `.ts` (parts=["ts"]) or `.spec.ts` (parts=["spec", "ts"]) — true
    only when EVERY dot-separated part after the leading `.` is a member
    of `_PATH_EXTENSIONS`. Used by filter (d) to tell a stray extension
    fragment apart from a real directory segment: `.devforge` and
    `.github` do NOT match (`devforge`/`github` aren't extensions).
    """
    if not segment.startswith("."):
        return False
    rest = segment[1:]
    if not rest:
        return False
    return all(part in _PATH_EXTENSIONS for part in rest.split("."))


def _is_segment_artifact_citation_token(token: str) -> bool:
    """Filter (d) — cross-slash regex artifact, e.g. `.ts/.vue`.

    True when `token` contains a `/` AND at least one NON-FINAL segment is
    a pure-extension chain (see `_is_pure_extension_chain_segment`).
    Catches a token the regex stitched together across an unrelated `/`
    in prose (`.ts/.vue`) without catching a real relative path whose
    leading segment happens to start with `.`
    (`.devforge/session-state.md`, `.github/workflows/ci.yaml`).
    """
    if "/" not in token:
        return False
    segments = token.split("/")
    return any(_is_pure_extension_chain_segment(seg) for seg in segments[:-1])


def _count_citations(
    state: dict,
    install_root: "Union[str, os.PathLike[str]]",
    devforge_dir: "Union[str, os.PathLike[str]]",
    filtered_out: "Optional[List[str]]" = None,
) -> "tuple":
    """Return (score_float, resolved, unresolved, failed_items).

    score = resolved / (resolved + unresolved); if 0 tokens found → 1.0 (N/A).
    failed_items is a list of strings describing unresolved references.

    A token matching one of the four citation-token filters above
    (placeholder / extension-only / leading-slash / segment-artifact)
    counts toward NEITHER `resolved` NOR `unresolved` and produces NO
    `failed_items` entry — nothing is filtered silently, though: pass a
    list via `filtered_out` to collect one string per filtered token
    (token + which filter class a/b/c/d matched it).

    Separately, a token under the `devforge_dir` runtime namespace
    (`_is_devforge_namespace_token`) always counts RESOLVED, never
    filtered and never subject to a filesystem check — see that
    function's docstring for the ratified design (D6).
    """
    install_root_path = Path(install_root)
    init_yaml_path = Path(devforge_dir) / init_helper.OUTPUT_FILE_NAME
    pkg_map = _build_package_name_map(init_yaml_path)
    effective_root = _resolve_effective_root(install_root, init_yaml_path)

    texts = _collect_citation_texts(state)
    all_tokens = []  # type: List[str]
    for text in texts:
        all_tokens.extend(_extract_path_tokens(text))

    # Filter URL remnants — see original docstring for the URL-stripping
    # logic. `_PATH_TOKEN_RE` strips the `https:` prefix; the remainder
    # `//example.com/x.json` would resolve to a bogus absolute path.
    all_tokens = [t for t in all_tokens if not t.startswith("//") and ":" not in t]

    if not all_tokens:
        return 1.0, 0, 0, []

    resolved = 0
    unresolved = 0
    failed_items = []  # type: List[str]

    def _try_resolve(token):
        # Framework runtime-namespace allowance (plan 80 Phase 3 / WI-3,
        # D6) runs BEFORE every filesystem check: a token under the
        # `devforge_dir` namespace is always resolved, even when the
        # cited file does not exist yet — see `_is_devforge_namespace_token`.
        if _is_devforge_namespace_token(token, devforge_dir):
            return True
        if (install_root_path / token).exists():
            return True
        if effective_root is not None and (effective_root / token).exists():
            return True
        token_name = Path(token).name
        if token_name in pkg_map:
            if (install_root_path / pkg_map[token_name]).exists():
                return True
            if effective_root is not None and (effective_root / pkg_map[token_name]).exists():
                return True
        # Bounded recursive fallback — root-agnostic (plan 80 Phase 2 D5):
        # wrapper mode searches `effective_root`, standalone searches
        # `install_root_path`. Both stages are pruned by
        # `_EXCLUDED_DIR_NAMES` in `_bounded_walk_has_match` (OQ-2/OQ-4).
        search_root = effective_root if effective_root is not None else install_root_path
        token_segments = tuple(token.split("/"))
        n = len(token_segments)
        if _bounded_walk_has_match(
            search_root,
            lambda name, rel_parts: len(rel_parts) >= n and rel_parts[-n:] == token_segments,
        ):
            return True
        if "/" not in token:
            if _bounded_walk_has_match(
                search_root,
                lambda name, rel_parts: name.endswith(token),
            ):
                return True
        return False

    def _classify_filtered(token):
        """Return (letter, label) for a post-resolve filter match, else None.

        Checked only after `_try_resolve` has already failed for `token` —
        a token that resolves is never classified (a real citation always
        wins over a filter shape). Order among (a)/(b)/(d) is fixed but
        immaterial to correctness: a token can match more than one
        predicate (e.g. `.Xxx.ts` matches both (a) and (b)) — whichever
        runs first decides the recorded label, but every branch excludes
        the token from resolved/unresolved identically, so the label
        choice never affects the score.
        """
        if _is_placeholder_citation_token(token):
            return "a", "placeholder"
        if _is_extension_only_citation_token(token):
            return "b", "extension-only"
        if _is_segment_artifact_citation_token(token):
            return "d", "segment-artifact"
        return None

    seen = set()  # type: set
    for token in all_tokens:
        if token in seen:
            continue
        seen.add(token)

        # Filter (c) runs BEFORE resolution — see F1 note on
        # `_is_leading_slash_citation_token`.
        if _is_leading_slash_citation_token(token):
            if filtered_out is not None:
                filtered_out.append(
                    "filtered (c leading-slash): {0!r}".format(token)
                )
            continue

        if _try_resolve(token):
            resolved += 1
            continue

        classified = _classify_filtered(token)
        if classified is not None:
            letter, label = classified
            if filtered_out is not None:
                filtered_out.append(
                    "filtered ({0} {1}): {2!r}".format(letter, label, token)
                )
            continue

        unresolved += 1
        failed_items.append("citation unresolved: {0!r}".format(token))

    total = resolved + unresolved
    score = resolved / total if total > 0 else 1.0
    return score, resolved, unresolved, failed_items


# ---------------------------------------------------------------------------
# Dim 3 — Code-example syntax.
# ---------------------------------------------------------------------------


def _check_python_syntax(code: str) -> bool:
    """Return True if code parses as valid Python via ast.parse."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _check_json_syntax(code: str) -> bool:
    """Return True if code parses as valid JSON via json.loads."""
    try:
        json.loads(code)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _check_balanced_braces(code: str) -> bool:
    """Return True if brace count is balanced (abs(open - close) <= 1) and code is non-empty.

    Used for TS/JS/TSX/JSX — tolerates single-brace imbalance from string literals.
    """
    stripped = code.strip()
    if not stripped:
        return False
    count_open = stripped.count("{")
    count_close = stripped.count("}")
    return abs(count_open - count_close) <= 1


def _check_code_example_syntax(lang: str, code: str) -> bool:
    """Check syntax for a single code example given its language tag.

    python/python3/py → ast.parse
    json → json.loads
    ts/tsx/typescript/js/jsx/javascript → balanced-brace + non-empty heuristic
    other → non-empty heuristic only
    """
    lang_lower = (lang or "").strip().lower()
    if lang_lower in ("python", "python3", "py"):
        return _check_python_syntax(code)
    if lang_lower == "json":
        return _check_json_syntax(code)
    if lang_lower in ("ts", "tsx", "typescript", "js", "jsx", "javascript"):
        return _check_balanced_braces(code)
    return bool(code.strip())


def _collect_code_examples(state: dict) -> "List[dict]":
    """Collect all code_example records from all section buckets."""
    examples = []  # type: List[dict]
    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            examples.extend(section.get("code_examples") or [])
    return examples


def _count_code_syntax(state: dict) -> "tuple":
    """Return (score_float, parsed_clean, total, failed_items).

    score = parsed_clean / total; total == 0 → 1.0 (N/A).
    failed_items lists examples that failed syntax check.
    """
    examples = _collect_code_examples(state)
    if not examples:
        return 1.0, 0, 0, []

    parsed_clean = 0
    failed_items = []  # type: List[str]
    for i, ex in enumerate(examples):
        lang = ex.get("language") or ""
        code = ex.get("code") or ""
        label = ex.get("label") or "?"
        if _check_code_example_syntax(lang, code):
            parsed_clean += 1
        else:
            failed_items.append(
                "code_example[{0}] label={1!r} lang={2!r}: syntax check failed".format(
                    i, label, lang
                )
            )

    total = len(examples)
    score = parsed_clean / total if total > 0 else 1.0
    return score, parsed_clean, total, failed_items


# ---------------------------------------------------------------------------
# Dim 4 — Rule-tag validity.
# ---------------------------------------------------------------------------


def _collect_all_rule_tags(state: dict) -> "List[tuple]":
    """Collect all (tag, context_label) from all rule records in all buckets.

    Used to validate every rule tag against the closed enum.
    """
    entries = []  # type: List[tuple]

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for i, section in enumerate(state.get(bucket_key) or []):
            for j, rule in enumerate(section.get("rules") or []):
                label = "{0}[{1}].rules[{2}]".format(bucket_key, i, j)
                entries.append((rule.get("tag"), label))

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for j, rule in enumerate(pat.get(bucket) or []):
            label = "patterns_and_antipatterns.{0}[{1}]".format(bucket, j)
            entries.append((rule.get("tag"), label))

    return entries


def _count_rule_tags(state: dict) -> "tuple":
    """Return (score_float, valid_count, total_count, failed_items).

    score = valid_tags / total_tags. Zero tags → 1.0 (N/A).
    Pass threshold = 1.0 (mechanical check; failure indicates helper bug).
    """
    entries = _collect_all_rule_tags(state)
    if not entries:
        return 1.0, 0, 0, []

    valid_enum = ENUM_FIELDS["rule_tag"]
    valid_count = 0
    failed_items = []  # type: List[str]
    for tag, label in entries:
        if tag in valid_enum:
            valid_count += 1
        else:
            failed_items.append(
                "{0}: invalid rule tag {1!r} (allowed: {2})".format(
                    label, tag, sorted(valid_enum)
                )
            )

    total = len(entries)
    score = valid_count / total if total > 0 else 1.0
    return score, valid_count, total, failed_items


def _compute_composite(scores: "Dict[str, float]") -> float:
    """Compute weighted composite score from per-dimension float scores."""
    return sum(_VALIDATE_WEIGHTS[d] * scores[d] for d in _VALIDATE_WEIGHTS)
