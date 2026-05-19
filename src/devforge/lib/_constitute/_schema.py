"""Schema constants — top-level shape + enums + bucket mappings + universal sections."""

from __future__ import annotations

OUTPUT_FILE_NAME = "constitute.json"

# Top-level key order is locked. Reordering changes on-disk byte order.
# Kind abbreviations:
#   "scalar"           — string-or-None
#   "date_scalar"      — string-or-None expected as YYYY-MM-DD
#   "enum_scalar"      — string-or-None restricted by ENUM_FIELDS["mode"]
#   "nullable_record"  — None or a nested record. Step 2 setters populate
#                        the dict shape (project_identity = 4 subfields;
#                        scaffolding_guide = 2 subfields). Both default to
#                        None — greenfield mode may legitimately leave
#                        scaffolding_guide null until set, and project_identity
#                        is null until set-project-identity runs in Phase 2.
#   "section_array"    — list of section records (default [])
#   "patterns_section" — dict with 6 named buckets, each a rule_array
FIELD_SCHEMA = (
    ("project_name",              "scalar"),
    ("generated_date",            "date_scalar"),
    ("last_updated",              "date_scalar"),
    ("mode",                      "enum_scalar"),
    ("project_identity",          "nullable_record"),
    ("architecture_rules",        "section_array"),
    ("code_quality_standards",    "section_array"),
    ("patterns_and_antipatterns", "patterns_section"),
    ("domain_rules",              "section_array"),
    ("workflow_rules",            "section_array"),
    ("scaffolding_guide",         "nullable_record"),
)

# Closed enum sets. Step 2 setters enforce these at set-time.
ENUM_FIELDS = {
    "mode":        {"existing-codebase", "greenfield"},
    "rule_tag":    {"extracted", "enforced", "universal", "project-specific"},
    "section_tag": {"universal", "project-specific", "greenfield-only"},
    "code_label":  {"CORRECT", "WRONG", "EXAMPLE"},
}

# Patterns-and-antipatterns bucket names (locked order for deterministic JSON).
_PATTERNS_BUCKETS = (
    "always_universal",
    "always_project_specific",
    "never_universal",
    "never_project_specific",
    "prefer_universal",
    "prefer_project_specific",
)

_SECTION_BUCKET_TO_KEY = {
    "architecture":  "architecture_rules",
    "code-quality":  "code_quality_standards",
    "domain":        "domain_rules",
    "workflow":      "workflow_rules",
}

_PATTERN_SCOPE_TO_SUFFIX = {
    "universal":        "universal",
    "project-specific": "project_specific",
}

# Closed list of universal section numbers (§-prefixed, as used in return shapes).
_UNIVERSAL_SECTIONS = (
    "§3.5", "§3.6", "§3.7",
    "§4.1", "§4.2", "§4.3",
    "§6.1", "§6.2", "§6.3", "§6.4",
)

# Maps patterns_and_antipatterns bucket names to §-number keys.
_PATTERNS_BUCKET_TO_SECTION = {
    "always_universal":  "§4.1",
    "never_universal":   "§4.2",
    "prefer_universal":  "§4.3",
}
