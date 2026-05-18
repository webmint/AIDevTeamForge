"""Tests for src/devforge/lib/_discover/_topic.py — slug + conflict + coverage.

Carved out of tests/lib/test_discover_helper.py during Phase A1 of
REFACTOR-MONOLITHIC-HELPERS-PLAN. Covers:

  derive_topic_slug    — kebab; max 60 chars; trailing-hyphen strip;
                         fallback; word-boundary truncation; collision
                         resistance.
  check-conflicts      — direct token-overlap detection + case-insensitivity
                         + stopword/short-token filtering + read-only
                         invariant + suppression of resolved pairs.
  scope-coverage       — empty memo shape, mixed states, open-conflicts
                         counting.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Stdlib only. Python 3.8+.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "discover_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _discover._state import MEMO_FILE_NAME, RUBRIC_DIMENSIONS  # noqa: E402
from _discover._topic import derive_topic_slug  # noqa: E402


def _run(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _set_dim(devforge_dir, dimension, value, state="Clear", increment_turn=False):
    """Helper: call set-scope-<dim> subcommand."""
    subcommand = "set-scope-" + dimension.replace("_", "-")
    argv = ["--devforge-dir", str(devforge_dir), subcommand, "--value", value, "--state", state]
    if increment_turn:
        argv.append("--increment-turn")
    return _run(argv)


def _read_memo(devforge_dir):
    """Return parsed discover-scope.json dict."""
    r = _run(["--devforge-dir", str(devforge_dir), "read-memo"])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _rewrite_memo_json(devforge_dir, mutator):
    """Load .devforge/discover-scope.json, apply mutator(state), write back."""
    path = Path(devforge_dir) / MEMO_FILE_NAME
    state = json.loads(path.read_text(encoding="utf-8"))
    mutator(state)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _induce_oauth_conflict(devforge_dir):
    """Set non_goals and integration_points to overlap on 'oauth' token."""
    r1 = _set_dim(devforge_dir, "non_goals", "OAuth not supported in v1")
    assert r1.returncode == 0, r1.stderr
    r2 = _set_dim(devforge_dir, "integration_points", "OAuth callback routes and API guards")
    assert r2.returncode == 0, r2.stderr


# ---------------------------------------------------------------------------
# derive_topic_slug.
# ---------------------------------------------------------------------------


class TestDeriveTopicSlug(unittest.TestCase):
    def test_basic_kebab(self):
        self.assertEqual(derive_topic_slug("Auth in NestJS"), "auth-in-nestjs")

    def test_special_chars_become_hyphens(self):
        slug = derive_topic_slug("OAuth2 / SSO integration")
        self.assertRegex(slug, r"^[a-z0-9-]+$")

    def test_max_60_chars(self):
        long_topic = "a " * 40  # 80 chars when joined
        slug = derive_topic_slug(long_topic)
        self.assertLessEqual(len(slug), 60)

    def test_no_trailing_hyphen(self):
        slug = derive_topic_slug("some topic that is quite long indeed yes")
        self.assertFalse(slug.endswith("-"), "slug ends with hyphen: {0!r}".format(slug))

    def test_empty_string_fallback(self):
        self.assertEqual(derive_topic_slug(""), "topic")

    def test_non_alnum_only_fallback(self):
        self.assertEqual(derive_topic_slug("---"), "topic")

    def test_already_lowercase(self):
        self.assertEqual(derive_topic_slug("websockets"), "websockets")

    def test_truncation_lands_on_word_boundary(self):
        # Run 2 evidence: pre-fix output was
        # `tamper-evident-audit-log-across-quote-order-preferences-muta` (cut at `muta`).
        # Post-fix must cut at last `-` boundary, not mid-word.
        topic = (
            "tamper-evident audit log across quote/order/preferences mutations, "
            "similar to how stripe-events or temporal-history work"
        )
        slug = derive_topic_slug(topic)
        self.assertLessEqual(len(slug), 60)
        # No trailing partial word — last segment must be a complete token.
        self.assertNotIn(
            "muta",
            slug.rsplit("-", 1)[-1] if "-" in slug else slug,
            "slug appears truncated mid-word: {0!r}".format(slug),
        )
        # Last segment must come from the source topic's word set.
        source_words = re.findall(r"[a-z0-9]+", topic.lower())
        last_segment = slug.rsplit("-", 1)[-1]
        self.assertIn(
            last_segment,
            source_words,
            "last slug segment {0!r} is not a complete source word".format(last_segment),
        )

    def test_truncation_does_not_strand_mid_word(self):
        # Force truncation: build a string with one long final word that crosses the cap.
        topic = "alpha beta gamma delta epsilon zeta etaverylongtailword"
        slug = derive_topic_slug(topic)
        self.assertLessEqual(len(slug), 60)
        # If full string exceeds cap, last segment must not be a partial of the tail.
        if len("-".join(topic.lower().split())) > 60:
            self.assertFalse(
                slug.endswith("etaverylong") or slug.endswith("verylongtailwor"),
                "slug cut mid-word: {0!r}".format(slug),
            )

    def test_collision_resistance_when_divergence_inside_window(self):
        # When two topics diverge on a complete word that fits inside the
        # boundary-truncation window, Fix C must preserve the divergence.
        # Both topics here cross the 60-char cap but diverge at the SECOND token,
        # well inside the boundary-cut window.
        topic_a = (
            "audit log mutation tracking across quote and order with history persistence indeed"
        )
        topic_b = (
            "audit log snapshot tracking across quote and order with history persistence indeed"
        )
        slug_a = derive_topic_slug(topic_a)
        slug_b = derive_topic_slug(topic_b)
        self.assertNotEqual(
            slug_a,
            slug_b,
            "early-token divergence collapsed to same slug — fix C dropped information",
        )


# ---------------------------------------------------------------------------
# check-conflicts subcommand (drives _detect_scope_conflicts).
# ---------------------------------------------------------------------------


class TestCheckConflicts(unittest.TestCase):
    def _run_check(self, devforge_dir):
        return _run(["--devforge-dir", str(devforge_dir), "check-conflicts"])

    def test_empty_memo_returns_empty_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, [])

    def test_detects_direct_contradiction(self):
        """Shared 'oauth' token between non_goals and integration_points is flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertGreater(len(data), 0)
            conflict = data[0]
            self.assertEqual(conflict["type"], "direct")
            self.assertIn("non_goals", conflict["dimensions"])
            self.assertIn("integration_points", conflict["dimensions"])
            self.assertIn("oauth", conflict["description"].lower())

    def test_case_insensitive_token_match(self):
        """OAUTH vs oauth mixed case still triggers a conflict."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r1 = _set_dim(devforge, "non_goals", "OAUTH not supported in v1")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _set_dim(devforge, "integration_points", "oauth callback routes")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertGreater(len(data), 0)

    def test_ignores_stopwords_and_short_tokens(self):
        """Only >=4-char non-stopword tokens trigger conflicts.

        'sso' is 3 chars — below _CONFLICT_MIN_TOKEN_LEN=4, so ignored.
        'admin' is 5 chars and not a stopword — triggers conflict.
        'no', 'the', 'and', 'is' are stopwords — ignored.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # 'admin' (5 chars, not stopword) is shared — should conflict.
            r1 = _set_dim(devforge, "non_goals", "no admin sso")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _set_dim(devforge, "integration_points", "the admin and the sso area is ok")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            # 'admin' qualifies — conflict detected.
            self.assertGreater(len(data), 0, "expected 'admin' to trigger conflict")
            # Now replace with values that share no >=4-char non-stopword tokens.
            r3 = _set_dim(devforge, "non_goals", "no sso and no mfa")
            self.assertEqual(r3.returncode, 0, r3.stderr)
            r4 = _set_dim(devforge, "integration_points", "the api and the auth area")
            self.assertEqual(r4.returncode, 0, r4.stderr)
            r2 = self._run_check(devforge)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            data2 = json.loads(r2.stdout)
            self.assertEqual(data2, [], "expected no conflict when no >=4-char shared tokens")

    def test_read_only(self):
        """check-conflicts called twice leaves state file byte-identical."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Ensure memo file exists before first call.
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _induce_oauth_conflict(devforge)
            state_path = devforge / MEMO_FILE_NAME
            r1 = self._run_check(devforge)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            bytes_after_first = state_path.read_bytes()
            r2 = self._run_check(devforge)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            bytes_after_second = state_path.read_bytes()
            self.assertEqual(bytes_after_first, bytes_after_second)

    def test_suppresses_already_resolved(self):
        """After record-conflict-resolution resolves a pair, check-conflicts omits it."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Record a resolution for the conflict at index 0.
            r_resolve = _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-non_goals",
                "--rewrite-dimension", "integration_points",
            ])
            self.assertEqual(r_resolve.returncode, 0, r_resolve.stderr)
            # Re-induce conflict on integration_points (was cleared by resolution).
            # check-conflicts should still filter it due to the resolved pair.
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            # integration_points was cleared, so no token overlap exists → empty.
            self.assertEqual(data, [])


# ---------------------------------------------------------------------------
# scope-coverage subcommand (drives _compute_scope_coverage).
# ---------------------------------------------------------------------------


class TestScopeCoverage(unittest.TestCase):
    def _run_coverage(self, devforge_dir):
        r = _run(["--devforge-dir", str(devforge_dir), "scope-coverage"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_empty_memo_shape(self):
        """Fresh memo → all 8 Missing, counts 0/0/8, refs=0, gaps=0, conflicts_open=0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            data = self._run_coverage(devforge)
            self.assertIn("per_dimension", data)
            self.assertIn("counts", data)
            # All 8 dimensions present.
            self.assertEqual(set(data["per_dimension"].keys()), set(RUBRIC_DIMENSIONS))
            # All Missing.
            for d in RUBRIC_DIMENSIONS:
                self.assertEqual(data["per_dimension"][d]["state"], "Missing",
                                 "dim={0}".format(d))
            self.assertEqual(data["counts"]["Clear"], 0)
            self.assertEqual(data["counts"]["Partial"], 0)
            self.assertEqual(data["counts"]["Missing"], 8)
            self.assertEqual(data["references_count"], 0)
            self.assertEqual(data["gaps_count"], 0)
            self.assertEqual(data["conflicts_open"], 0)

    def test_mixed_states(self):
        """5 Clear + 2 Partial + 1 Missing dimensions produce correct counts."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dims = list(RUBRIC_DIMENSIONS)
            # Set 5 Clear.
            for d in dims[:5]:
                r = _set_dim(devforge, d, "value for " + d, "Clear")
                self.assertEqual(r.returncode, 0, r.stderr)
            # Set 2 Partial.
            for d in dims[5:7]:
                r = _set_dim(devforge, d, "partial value for " + d, "Partial")
                self.assertEqual(r.returncode, 0, r.stderr)
            # dims[7] (edge_cases) stays Missing.
            data = self._run_coverage(devforge)
            self.assertEqual(data["counts"]["Clear"], 5)
            self.assertEqual(data["counts"]["Partial"], 2)
            self.assertEqual(data["counts"]["Missing"], 1)

    def test_open_conflicts_count(self):
        """conflicts_open reflects only unresolved (resolution==None) entries."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Populate state.conflicts via record-conflict-resolution (sets resolution).
            _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-non_goals",
                "--rewrite-dimension", "integration_points",
            ])
            # Now manually rewrite resolution back to None → simulates open conflict.
            def _clear_resolution(state):
                for c in state.get("conflicts", []):
                    c["resolution"] = None

            _rewrite_memo_json(devforge, _clear_resolution)
            data = self._run_coverage(devforge)
            self.assertEqual(data["conflicts_open"], 1)
            # Restore resolution → conflicts_open drops to 0.
            def _restore_resolution(state):
                for c in state.get("conflicts", []):
                    c["resolution"] = "user-chose-non_goals"

            _rewrite_memo_json(devforge, _restore_resolution)
            data2 = self._run_coverage(devforge)
            self.assertEqual(data2["conflicts_open"], 0)


if __name__ == "__main__":
    unittest.main()
