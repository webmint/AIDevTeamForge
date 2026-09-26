"""Shared token-overlap utilities.

tokenize_for_overlap is the shared tokenizer that _research (imported as
_tokenize_hypothesis) and _specify use for token-overlap matching.
_discover/_topic.py keeps its own _tokenize_for_conflict rather than
importing this module. It splits on non-alphanumeric boundaries, lowercases,
and drops tokens shorter than min_len and any stopword. New callers should
import from here rather than adding another divergent copy.

Technique mirrors the two prior implementations this module consolidates:
_discover/_topic.py:_tokenize_for_conflict (NOT migrated — tracked as a
follow-up) and the former _research/_cmds_render_verify.py:_tokenize_hypothesis
(migrated — that module now imports tokenize_for_overlap under the same name).

The stopword set is the union of the two prior sets, expanded to cover common
English function words that add no discriminating signal for vocabulary-overlap
detection:
  - _discover/_topic.py set: short connective words (a, an, the, or, and, etc.)
  - _research/_cmds_render_verify.py set: auxiliary verbs + determiners
    (that, this, from, are, was, has, have, had, its, their, into, when,
     will, been, also, such, more, they)
  - Codebase-specific boilerplate: "scope", "shall", "system" — these are
    universal in spec/EARS prose ("The system shall…", "…— out of scope") and
    carry zero discriminating signal for overlap detection. Without them, every
    EARS-formatted AC shares "system" and "shall" with every OOS entry that
    contains those words, producing universal false positives.

This module's defaults are the LOOSE end of the tree's overlap-detection
policies. The hypothesis-suppression gate in _research/_cmds_render_verify.py
applies a stricter policy on top of this tokenizer: it subtracts tokens
already grounded in recorded evidence rows, then fires only when a surviving
overlapping token is 8+ characters long. _specify's AC-vs-OOS check
(_specify/_cmds_phase4_verify.py, verify-scope-coherence) uses this module's
defaults as-is, with no additional layer.

The check catches IDENTIFIER/VOCABULARY reuse only: two texts that reuse the
same identifier or word trip it. Pure semantic paraphrase — the same
mechanism described in different vocabulary — shares no token and does not
trip it. That bound is intentional; this module names no downstream gate as
catching paraphrase.
"""

from __future__ import annotations

import re
from typing import List

# Union of stopwords from _discover/_topic.py and _research/_cmds_render_verify.py.
# These are high-frequency English function words that add no discriminating
# signal for identifier/vocabulary-overlap detection.
_OVERLAP_STOPWORDS = frozenset({
    # Short connectives (from _discover)
    "a", "an", "the", "or", "and", "to", "of", "for",
    "with", "in", "on", "at", "by", "is", "as", "but", "not", "no",
    # Auxiliary verbs + determiners (from _research)
    "that", "this", "from", "are", "was", "has", "have", "had",
    "its", "their", "into", "when", "will", "been", "also",
    "such", "more", "they",
    # Codebase-specific boilerplate: universal in spec/EARS prose, zero
    # discriminating signal — "The system shall…" / "…— out of scope" appear
    # in almost every EARS AC and OOS entry respectively.
    "scope", "shall", "system",
})

# Minimum token length. Tokens shorter than this are typically prepositions
# or articles and add noise to overlap matching.
_OVERLAP_MIN_TOKEN_LEN = 4


def tokenize_for_overlap(text, min_len=_OVERLAP_MIN_TOKEN_LEN):
    # type: (str, int) -> List[str]
    """Split text into lowercase tokens for overlap matching.

    Splits on any non-alphanumeric character sequence, lowercases, then
    drops tokens shorter than min_len and stopwords.

    This is a literal-vocabulary check: two texts share a token when they
    use the SAME identifier or word, not when they describe the same concept
    in different words (paraphrase is not detected).

    Args:
        text: Input string to tokenize.
        min_len: Minimum token length to keep (default 4). Tokens shorter
                 than this are dropped regardless of stopword list.

    Returns:
        List of lowercase tokens passing the length and stopword filters.
        Order is preserved; duplicates are retained (caller dedupes via set()
        if set-intersection is needed).
    """
    raw = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [
        t for t in raw
        if len(t) >= min_len and t not in _OVERLAP_STOPWORDS
    ]
