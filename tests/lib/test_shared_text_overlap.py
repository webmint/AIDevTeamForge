"""Tests for src/devforge/lib/_shared/text_overlap.py.

Covers tokenize_for_overlap: happy path, empty/whitespace, stopword filtering,
min_len boundary, camelCase splitting, and the known-limitation documentation
(pure paraphrase passes through).

Stdlib only. Python 3.8+.
"""

import sys
import unittest
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.text_overlap import tokenize_for_overlap, _OVERLAP_STOPWORDS, _OVERLAP_MIN_TOKEN_LEN  # noqa: E402


class TestTokenizeForOverlap(unittest.TestCase):

    # ------------------------------------------------------------------
    # Happy-path: basic tokenization
    # ------------------------------------------------------------------

    def test_basic_split_and_lowercase(self):
        tokens = tokenize_for_overlap("getConfigurationItems returns Promise")
        # Split on non-alnum: getconfigurationitems, returns, promise
        self.assertIn("getconfigurationitems", tokens)
        self.assertIn("returns", tokens)
        self.assertIn("promise", tokens)

    def test_camelcase_identifier_is_single_token(self):
        # camelCase is NOT split — only non-alnum boundaries split.
        tokens = tokenize_for_overlap("getConfigurationItems")
        self.assertEqual(tokens, ["getconfigurationitems"])

    def test_short_tokens_dropped(self):
        # "void" is 4 chars = exactly min_len, so it passes.
        tokens = tokenize_for_overlap("Promise void returns")
        self.assertIn("void", tokens)     # len==4, passes
        # "or" is 2 chars, dropped.
        tokens2 = tokenize_for_overlap("success or failure")
        self.assertNotIn("or", tokens2)

    def test_stopwords_dropped(self):
        # "from" is in stopwords AND len>=4 — must be dropped.
        tokens = tokenize_for_overlap("data from cache")
        self.assertNotIn("from", tokens)
        self.assertIn("data", tokens)
        self.assertIn("cache", tokens)

    def test_order_preserved(self):
        tokens = tokenize_for_overlap("alpha bravo charlie")
        self.assertEqual(tokens, ["alpha", "bravo", "charlie"])

    def test_duplicates_retained(self):
        # Caller dedupes; tokenizer preserves.
        tokens = tokenize_for_overlap("sort sort comparator")
        self.assertEqual(tokens.count("sort"), 2)

    # ------------------------------------------------------------------
    # Empty and whitespace inputs
    # ------------------------------------------------------------------

    def test_empty_string_returns_empty(self):
        self.assertEqual(tokenize_for_overlap(""), [])

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(tokenize_for_overlap("   \t\n  "), [])

    def test_all_short_tokens_returns_empty(self):
        # "a b c" — all length 1, below default min_len=4.
        self.assertEqual(tokenize_for_overlap("a b c"), [])

    # ------------------------------------------------------------------
    # min_len parameter
    # ------------------------------------------------------------------

    def test_custom_min_len_includes_short_tokens(self):
        tokens = tokenize_for_overlap("a b fix bug", min_len=2)
        self.assertIn("fix", tokens)
        self.assertIn("bug", tokens)
        # "a" len==1 < 2 → still dropped.
        self.assertNotIn("a", tokens)

    def test_default_min_len_is_4(self):
        self.assertEqual(_OVERLAP_MIN_TOKEN_LEN, 4)

    # ------------------------------------------------------------------
    # Overlap detection use-case (the set-intersection pattern)
    # ------------------------------------------------------------------

    def test_overlap_fires_on_shared_identifier(self):
        # Concrete trip-wire: cause and rationale share "getconfigurationitems".
        cause = "getConfigurationItems returns Promise void"
        rationale = "widen getConfigurationItems to a discriminated outcome carrying items inline"
        cause_tokens = set(tokenize_for_overlap(cause))
        rationale_tokens = set(tokenize_for_overlap(rationale))
        overlap = cause_tokens & rationale_tokens
        self.assertIn("getconfigurationitems", overlap,
                      "shared API identifier must fire overlap")

    def test_no_overlap_on_disjoint_vocabulary(self):
        cause = "cache invalidation stale data"
        rationale = "move sort logic into derived computed property"
        cause_tokens = set(tokenize_for_overlap(cause))
        rationale_tokens = set(tokenize_for_overlap(rationale))
        self.assertEqual(cause_tokens & rationale_tokens, set())

    def test_pure_paraphrase_no_overlap_known_limitation(self):
        """KNOWN LIMITATION: pure paraphrase shares no token → no overlap detected.

        The cause 'getConfigurationItems returns Promise void' and the rationale
        'widen the outcome to carry success or failure inline' encode the same
        mechanism (widen the return type) but share NO significant token after
        filtering. This is a documented gap in the mechanical check; it is caught
        by the Step-5 intake echo-back human gate, not by token-overlap.
        """
        cause = "getConfigurationItems returns Promise void"
        # Pure-paraphrase: same mechanism, entirely different vocabulary.
        rationale = "widen the outcome to carry success or failure inline"
        cause_tokens = set(tokenize_for_overlap(cause))
        rationale_tokens = set(tokenize_for_overlap(rationale))
        overlap = cause_tokens & rationale_tokens
        # KNOWN LIMITATION: no shared identifier → no overlap → gate would exit 0.
        self.assertEqual(overlap, set(),
                         "pure paraphrase produces empty overlap (known limitation)")

    # ------------------------------------------------------------------
    # Stopword set sanity
    # ------------------------------------------------------------------

    def test_stopword_set_contains_union_members(self):
        # Verify both source sets are represented.
        # From _discover/_topic.py set.
        for word in ("with", "from"):
            self.assertIn(word, _OVERLAP_STOPWORDS)
        # From _research/_cmds_render_verify.py set.
        for word in ("that", "this", "been", "also", "such", "more", "they"):
            self.assertIn(word, _OVERLAP_STOPWORDS)

    def test_stopwords_are_all_lowercase(self):
        for word in _OVERLAP_STOPWORDS:
            self.assertEqual(word, word.lower(),
                             "stopword {0!r} must be lowercase".format(word))


if __name__ == "__main__":
    unittest.main()
