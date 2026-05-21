"""Tests for validate_forcing_functions() in _constitute._schema (Phase 5a).

Coverage
--------
Positive cases
  test_none_input_valid                  -- None → no errors
  test_empty_dict_valid                  -- {} → no errors
  test_magic_enum_enabled_valid          -- full valid block
  test_magic_enum_disabled_no_dirs_valid -- disabled + no dirs OK
  test_cross_layer_enabled_valid         -- full valid cross_layer block
  test_cross_layer_disabled_valid        -- disabled cross_layer block
  test_any_leak_enabled_valid            -- full valid any_leak block
  test_any_leak_disabled_valid           -- disabled any_leak block
  test_unknown_rule_tolerated            -- future rule ignored (forward-compat)

Negative cases — magic_enum_duplication
  test_magic_enum_enabled_field_not_bool   -- enabled is string → error
  test_magic_enum_enabled_no_dirs          -- enabled=true + no dirs → error
  test_magic_enum_empty_dirs               -- enabled=true + dirs=[] → error
  test_magic_enum_dirs_not_list            -- dirs = string → error
  test_magic_enum_dirs_nonstr_item         -- dirs item is int → error
  test_magic_enum_allowlist_not_list       -- allowlist = string → error

Negative cases — cross_layer_imports
  test_cross_layer_enabled_no_graph        -- enabled + no layer_graph → error
  test_cross_layer_enabled_no_dirs         -- enabled + no layer_dirs → error
  test_cross_layer_mismatched_keys         -- key mismatch → error
  test_cross_layer_graph_bad_value         -- layer_graph value is string → error
  test_cross_layer_dirs_bad_value          -- layer_dirs value is list → error

Negative cases — any_with_generated_available
  test_any_leak_enabled_no_dirs            -- enabled + no dirs → error
  test_any_leak_empty_dirs                 -- enabled + dirs=[] → error

Rule-block type error
  test_rule_block_not_dict                 -- rule value is a list → error
"""

from __future__ import annotations

import os
import sys
import unittest

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._schema import validate_forcing_functions  # noqa: E402


def _valid_magic_enum_block(enabled=True):
    return {
        "enabled": enabled,
        "generated_types_dirs": ["packages/types/src"],
        "allowlist_paths": ["scripts/**"],
    }


def _valid_cross_layer_block(enabled=True):
    return {
        "enabled": enabled,
        "layer_graph": {"domain": [], "infra": ["domain"]},
        "layer_dirs": {
            "domain": "packages/domain/**",
            "infra": "packages/infra/**",
        },
    }


def _valid_any_leak_block(enabled=True):
    return {
        "enabled": enabled,
        "generated_types_dirs": ["packages/types/src"],
    }


class TestValidFFNoneAndEmpty(unittest.TestCase):

    def test_none_input_valid(self):
        self.assertEqual(validate_forcing_functions(None), [])

    def test_empty_dict_valid(self):
        self.assertEqual(validate_forcing_functions({}), [])

    def test_non_dict_input_tolerated(self):
        # A non-dict value at the top level (edge case) → no errors (treated as absent)
        self.assertEqual(validate_forcing_functions("not-a-dict"), [])
        self.assertEqual(validate_forcing_functions(42), [])


class TestValidMagicEnum(unittest.TestCase):

    def test_magic_enum_enabled_valid(self):
        ff = {"magic_enum_duplication": _valid_magic_enum_block(True)}
        self.assertEqual(validate_forcing_functions(ff), [])

    def test_magic_enum_disabled_no_dirs_valid(self):
        ff = {"magic_enum_duplication": {"enabled": False}}
        self.assertEqual(validate_forcing_functions(ff), [])

    def test_magic_enum_disabled_with_dirs_valid(self):
        ff = {"magic_enum_duplication": _valid_magic_enum_block(False)}
        self.assertEqual(validate_forcing_functions(ff), [])


class TestInvalidMagicEnum(unittest.TestCase):

    def test_magic_enum_enabled_not_bool(self):
        ff = {"magic_enum_duplication": {"enabled": "yes",
                                          "generated_types_dirs": ["t"]}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("enabled" in e and "bool" in e for e in errs),
                        errs)

    def test_magic_enum_enabled_no_dirs(self):
        ff = {"magic_enum_duplication": {"enabled": True}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e and "required" in e
                            for e in errs), errs)

    def test_magic_enum_empty_dirs(self):
        ff = {"magic_enum_duplication": {"enabled": True,
                                          "generated_types_dirs": []}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e for e in errs), errs)

    def test_magic_enum_dirs_not_list(self):
        ff = {"magic_enum_duplication": {"enabled": True,
                                          "generated_types_dirs": "not-a-list"}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e for e in errs), errs)

    def test_magic_enum_dirs_nonstr_item(self):
        ff = {"magic_enum_duplication": {"enabled": True,
                                          "generated_types_dirs": [123]}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e for e in errs), errs)

    def test_magic_enum_allowlist_not_list(self):
        ff = {"magic_enum_duplication": {"enabled": True,
                                          "generated_types_dirs": ["t"],
                                          "allowlist_paths": "not-a-list"}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("allowlist_paths" in e for e in errs), errs)


class TestValidCrossLayer(unittest.TestCase):

    def test_cross_layer_enabled_valid(self):
        ff = {"cross_layer_imports": _valid_cross_layer_block(True)}
        self.assertEqual(validate_forcing_functions(ff), [])

    def test_cross_layer_disabled_valid(self):
        ff = {"cross_layer_imports": {"enabled": False}}
        self.assertEqual(validate_forcing_functions(ff), [])


class TestInvalidCrossLayer(unittest.TestCase):

    def test_cross_layer_enabled_no_graph(self):
        ff = {"cross_layer_imports": {
            "enabled": True,
            "layer_dirs": {"domain": "pkg/domain/**"},
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("layer_graph" in e and "required" in e for e in errs), errs)

    def test_cross_layer_enabled_no_dirs(self):
        ff = {"cross_layer_imports": {
            "enabled": True,
            "layer_graph": {"domain": []},
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("layer_dirs" in e and "required" in e for e in errs), errs)

    def test_cross_layer_mismatched_keys(self):
        ff = {"cross_layer_imports": {
            "enabled": True,
            "layer_graph": {"domain": [], "infra": ["domain"]},
            "layer_dirs": {"domain": "pkg/domain/**"},  # missing infra
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("keys must match" in e for e in errs), errs)

    def test_cross_layer_graph_value_not_list(self):
        ff = {"cross_layer_imports": {
            "enabled": True,
            "layer_graph": {"domain": "should-be-list"},
            "layer_dirs": {"domain": "pkg/domain/**"},
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("layer_graph" in e and "list" in e for e in errs), errs)

    def test_cross_layer_dirs_value_not_string(self):
        ff = {"cross_layer_imports": {
            "enabled": True,
            "layer_graph": {"domain": []},
            "layer_dirs": {"domain": ["should", "be", "string"]},
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("layer_dirs" in e and "string" in e for e in errs), errs)


class TestValidAnyLeak(unittest.TestCase):

    def test_any_leak_enabled_valid(self):
        ff = {"any_with_generated_available": _valid_any_leak_block(True)}
        self.assertEqual(validate_forcing_functions(ff), [])

    def test_any_leak_disabled_valid(self):
        ff = {"any_with_generated_available": {"enabled": False}}
        self.assertEqual(validate_forcing_functions(ff), [])


class TestInvalidAnyLeak(unittest.TestCase):

    def test_any_leak_enabled_no_dirs(self):
        ff = {"any_with_generated_available": {"enabled": True}}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e and "required" in e
                            for e in errs), errs)

    def test_any_leak_enabled_empty_dirs(self):
        ff = {"any_with_generated_available": {
            "enabled": True,
            "generated_types_dirs": [],
        }}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("generated_types_dirs" in e for e in errs), errs)


class TestRuleBlockNotDict(unittest.TestCase):

    def test_rule_block_not_dict(self):
        ff = {"magic_enum_duplication": ["wrong", "type"]}
        errs = validate_forcing_functions(ff)
        self.assertTrue(any("dict" in e for e in errs), errs)


class TestUnknownRuleTolerated(unittest.TestCase):
    """Forward-compat: unknown rules are ignored, not errored."""

    def test_unknown_rule_tolerated(self):
        ff = {
            "future_detector_v2": {"enabled": True, "some_field": "x"},
            "magic_enum_duplication": _valid_magic_enum_block(True),
        }
        errs = validate_forcing_functions(ff)
        # No errors from the unknown rule; magic_enum_duplication also valid
        self.assertEqual(errs, [])


class TestMultipleRulesMixed(unittest.TestCase):
    """Both valid and invalid rules present → collects errors from all."""

    def test_collects_errors_across_rules(self):
        ff = {
            "magic_enum_duplication": {"enabled": True},  # missing dirs
            "cross_layer_imports": {"enabled": True},      # missing both maps
        }
        errs = validate_forcing_functions(ff)
        has_magic = any("magic_enum_duplication" in e for e in errs)
        has_cross = any("cross_layer_imports" in e for e in errs)
        self.assertTrue(has_magic, "Expected magic_enum error in: " + str(errs))
        self.assertTrue(has_cross, "Expected cross_layer error in: " + str(errs))


if __name__ == "__main__":
    unittest.main()
