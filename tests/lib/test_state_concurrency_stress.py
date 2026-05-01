"""Cross-process stress tests for `_state_transaction()` + fcntl.flock.

Why this test file exists
=========================

The existing `StateConcurrencyTests` in `test_generate_docs_helper.py`
exercise concurrent invocations via `threading.Thread` — but threads in
the same Python process do NOT exercise cross-process file locking.
`fcntl.flock(LOCK_EX)` serializes flock holders ACROSS processes; within
a single process the same fd can hold the lock once and any nested
acquires are no-ops. The thread tests therefore can't observe the
cross-process race that surfaced on testForge20 (2026-05-01) where 7
parallel `Task`-spawned subagents each invoking `add-concern-export` /
`add-concern-dep` etc. produced 3 concerns reduced to empty shells in
the final state file.

This file hammers the helper with REAL `subprocess.Popen` invocations
of `python3 generate_docs_helper.py <subcommand>` so each setter holds
its own fd on the lock sidecar — the production lock surface. Each
test is wrapped in a 5-iteration loop because race conditions are
inherently nondeterministic; a single passing run is not proof. If any
iteration fails, we capture the corrupt state file contents in the
assertion message so the bug evidence is in-hand for the helper fix.

Stdlib only. Python 3.8+ compatible.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "generate_docs_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import generate_docs_helper as gdh  # noqa: E402


# Number of times each stress scenario is repeated. Race conditions are
# nondeterministic — a single passing iteration is not proof. We pick 5
# as the floor because: (a) testForge20's incident reproduced on a
# single 7-subagent dispatch, suggesting the failure rate when a real
# bug exists is well above 1-in-5; (b) total runtime budget per test is
# ~10s, so 5 iterations of 8 parallel subprocesses fits comfortably. If
# the lock has a subtler race that needs 10+ iterations to surface,
# bump this — DO NOT lower it.
_LOOP_ITERATIONS = 5


def _run_cli(devforge_dir, *args):
    """One-shot helper invocation; mirrors test_generate_docs_helper."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _spawn_parallel(devforge_dir, command_lists):
    """Start every command via Popen BEFORE waiting on any of them.

    Using `subprocess.run` in a loop would serialize: each call blocks
    until completion. We need real parallelism — every Popen spawned
    before the first .wait() — so the kernel actually races them on the
    lock acquisition. Returns list of (returncode, stdout, stderr) in
    submission order.
    """
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    procs = []
    for args in command_lists:
        procs.append(subprocess.Popen(
            [sys.executable, str(_HELPER_PY)] + list(args),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ))
    results = []
    for p in procs:
        out, err = p.communicate()
        results.append((p.returncode, out, err))
    return results


def _spawn_parallel_chains(devforge_dir, chains):
    """Each `chain` is a list of CLI arg-tuples to run sequentially in
    its OWN process.

    Implemented by running a tiny Python sub-program per chain that
    invokes the helper N times in series. All chain-driver subprocesses
    are spawned BEFORE any wait, so the chains race each other across
    setter boundaries — closest analogue to a Claude Code Agent tool
    dispatch where each subagent runs a sequence of helper CLIs.

    Returns list of (returncode, stdout, stderr) in chain submission
    order. Chain returncode is 0 iff every CLI in the chain returned 0;
    otherwise the first nonzero rc.
    """
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)

    driver = (
        "import subprocess, sys, json\n"
        "helper = sys.argv[1]\n"
        "chain = json.loads(sys.argv[2])\n"
        "for cmd in chain:\n"
        "    p = subprocess.run([sys.executable, helper] + cmd,\n"
        "                       stdout=subprocess.PIPE,\n"
        "                       stderr=subprocess.PIPE)\n"
        "    if p.returncode != 0:\n"
        "        sys.stderr.buffer.write(p.stderr)\n"
        "        sys.exit(p.returncode)\n"
        "sys.exit(0)\n"
    )

    procs = []
    for chain in chains:
        procs.append(subprocess.Popen(
            [sys.executable, "-c", driver, str(_HELPER_PY), json.dumps(chain)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ))
    results = []
    for p in procs:
        out, err = p.communicate()
        results.append((p.returncode, out, err))
    return results


class _SubprocessIsolationMixin:
    """Per-test tmp dir + DEVFORGE_DIR override.

    Mirrors `_EnvIsolationMixin` in test_generate_docs_helper but with
    the additional contract that subprocesses spawned during the test
    inherit the same DEVFORGE_DIR via env. We ALSO clear the env in the
    test process so any accidental direct-import call hits an unset
    state path (forces test author to pass devforge_dir explicitly).
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _reset_state(self):
        """Wipe state between loop iterations.

        We delete the state file + lock sidecar between iterations so
        each iteration starts from a known-clean slate. Without this,
        iteration N+1 sees iteration N's state and the test's
        "everything must be present" assertion is meaningless.
        """
        if self.state_file.exists():
            self.state_file.unlink()
        lock = self.state_file.with_suffix(".json.lock")
        if lock.exists():
            lock.unlink()


class LockSerializationStressTests(
    _SubprocessIsolationMixin, unittest.TestCase,
):
    """Empirical proof/disproof that `_state_transaction()` serializes
    cross-process writes.

    Each test wraps its body in a `_LOOP_ITERATIONS`-deep loop. A
    single passing iteration is not proof; nondeterministic races
    require repeated trials. Failure inside any iteration aborts the
    test and surfaces the corrupt state contents in the assertion.
    """

    # ------------------------------------------------------------------
    # Test 1: distinct concern names — all must survive.
    # ------------------------------------------------------------------

    def test_concurrent_add_concern_distinct_names_all_survive(self):
        n = 8
        for iteration in range(_LOOP_ITERATIONS):
            self._reset_state()
            pre = _run_cli(
                self.devforge_dir, "add-package",
                "--path", "pkg/foo", "--name", "foo",
            )
            self.assertEqual(
                pre.returncode, 0,
                "iter {0}: add-package failed: {1!r}".format(
                    iteration, pre.stderr,
                ),
            )
            commands = [
                ("add-concern", "--package", "pkg/foo",
                 "--concern", "concern-{0}".format(i))
                for i in range(n)
            ]
            results = _spawn_parallel(self.devforge_dir, commands)
            for i, (rc, _out, err) in enumerate(results):
                self.assertEqual(
                    rc, 0,
                    "iter {0}, proc {1}: add-concern returned {2}; "
                    "stderr={3!r}".format(iteration, i, rc, err),
                )
            state = self._read_state()
            concerns = state["packages"]["pkg/foo"]["concerns"]
            expected = {"concern-{0}".format(i) for i in range(n)}
            actual = set(concerns.keys())
            missing = expected - actual
            self.assertFalse(
                missing,
                "iter {0}: missing concerns {1!r}; state={2}".format(
                    iteration, sorted(missing), json.dumps(state, indent=2),
                ),
            )
            self.assertEqual(
                len(concerns), n,
                "iter {0}: expected {1} concerns, got {2}; state={3}".format(
                    iteration, n, len(concerns),
                    json.dumps(state, indent=2),
                ),
            )

    # ------------------------------------------------------------------
    # Test 2: same name — exactly one survives, the rest reject.
    # ------------------------------------------------------------------

    def test_concurrent_add_concern_same_name_only_one_succeeds(self):
        n = 8
        for iteration in range(_LOOP_ITERATIONS):
            self._reset_state()
            pre = _run_cli(
                self.devforge_dir, "add-package",
                "--path", "pkg/foo", "--name", "foo",
            )
            self.assertEqual(pre.returncode, 0)
            commands = [
                ("add-concern", "--package", "pkg/foo",
                 "--concern", "same-name")
                for _ in range(n)
            ]
            results = _spawn_parallel(self.devforge_dir, commands)
            zeros = [i for i, (rc, _o, _e) in enumerate(results) if rc == 0]
            twos = [i for i, (rc, _o, _e) in enumerate(results) if rc == 2]
            other = [
                (i, rc) for i, (rc, _o, _e) in enumerate(results)
                if rc not in (0, 2)
            ]
            self.assertEqual(
                len(zeros), 1,
                "iter {0}: expected exactly 1 success, got {1} (indices {2}); "
                "rcs={3}".format(
                    iteration, len(zeros), zeros,
                    [r[0] for r in results],
                ),
            )
            self.assertEqual(
                len(twos), n - 1,
                "iter {0}: expected {1} duplicate-rejections (rc=2), got {2} "
                "(indices {3}); rcs={4}".format(
                    iteration, n - 1, len(twos), twos,
                    [r[0] for r in results],
                ),
            )
            self.assertFalse(
                other,
                "iter {0}: unexpected non-(0,2) exits: {1}".format(
                    iteration, other,
                ),
            )
            for i, (_rc, _o, err) in enumerate(results):
                if i in twos:
                    self.assertIn(
                        b"already registered", err,
                        "iter {0}, proc {1}: rc=2 but stderr lacks "
                        "'already registered': {2!r}".format(
                            iteration, i, err,
                        ),
                    )
            state = self._read_state()
            concerns = state["packages"]["pkg/foo"]["concerns"]
            self.assertEqual(
                set(concerns.keys()), {"same-name"},
                "iter {0}: state has {1!r}, expected just 'same-name'; "
                "state={2}".format(
                    iteration, sorted(concerns.keys()),
                    json.dumps(state, indent=2),
                ),
            )

    # ------------------------------------------------------------------
    # Test 3: STRONGEST — chains of mixed setters must all land.
    #
    # This is the closest analogue to the testForge20 failure mode.
    # Each chain ≈ one Agent tool subagent: a sequence of helper
    # invocations against the same concern. If the lock fails to
    # serialize, late writers will overwrite earlier writers' work and
    # one or more of the unique exports/deps/hazards will be missing.
    # ------------------------------------------------------------------

    def test_concurrent_setter_chain_no_data_loss(self):
        n = 4  # number of parallel chains
        # Pre-create a tiny source file so cite-file values are
        # plausible. Set-time validation only checks string shape (not
        # filesystem); we add the file purely so a future render-time
        # validation could succeed without further setup. The cite-file
        # value passed into setters is a project-relative string.
        src_dir = self.devforge_dir.parent / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "main.ts").write_text(
            "export const x = 1;\n", encoding="utf-8",
        )
        for iteration in range(_LOOP_ITERATIONS):
            self._reset_state()
            pre1 = _run_cli(
                self.devforge_dir, "add-package",
                "--path", "pkg/foo", "--name", "foo",
            )
            self.assertEqual(
                pre1.returncode, 0,
                "iter {0}: add-package failed: {1!r}".format(
                    iteration, pre1.stderr,
                ),
            )
            pre2 = _run_cli(
                self.devforge_dir, "add-concern",
                "--package", "pkg/foo", "--concern", "shared",
            )
            self.assertEqual(
                pre2.returncode, 0,
                "iter {0}: add-concern failed: {1!r}".format(
                    iteration, pre2.stderr,
                ),
            )
            chains = []
            for k in range(n):
                chain = [
                    ["set-concern-overview",
                     "--package", "pkg/foo", "--concern", "shared",
                     "--text", "process-{0}-overview".format(k)],
                    ["set-concern-tree",
                     "--package", "pkg/foo", "--concern", "shared",
                     "--text", "process-{0}-tree".format(k)],
                    ["add-concern-export",
                     "--package", "pkg/foo", "--concern", "shared",
                     "--name", "exp-{0}".format(k),
                     "--kind", "function",
                     "--signature", "exp{0}(): void".format(k),
                     "--description", "export number {0}".format(k),
                     "--language", "typescript",
                     "--code-snippet", "export const x = 1;",
                     "--cite-file", "src/main.ts",
                     "--cite-start", "1",
                     "--cite-end", "1"],
                    ["add-concern-dep",
                     "--package", "pkg/foo", "--concern", "shared",
                     "--name", "dep-{0}".format(k),
                     "--kind", "external",
                     "--version", "1.0",
                     "--purpose", "purpose for dep {0}".format(k)],
                    ["add-concern-hazard",
                     "--package", "pkg/foo", "--concern", "shared",
                     "--category", "naming",
                     "--description", "hazard-from-process-{0}".format(k)],
                ]
                chains.append(chain)
            results = _spawn_parallel_chains(self.devforge_dir, chains)
            for i, (rc, _o, err) in enumerate(results):
                self.assertEqual(
                    rc, 0,
                    "iter {0}, chain {1}: rc={2}; stderr={3!r}".format(
                        iteration, i, rc, err,
                    ),
                )
            state = self._read_state()
            concern = state["packages"]["pkg/foo"]["concerns"]["shared"]

            # Exports: every k must be present. The natural key is
            # (name, cite_file, cite_start) — all 4 chains write
            # distinct names + same cite, so all 4 should survive.
            export_names = sorted(
                e["name"] for e in concern["public_surface"]
            )
            expected_exports = sorted(
                "exp-{0}".format(k) for k in range(n)
            )
            self.assertEqual(
                export_names, expected_exports,
                "iter {0}: export-name mismatch. expected={1}, "
                "got={2}; full state=\n{3}".format(
                    iteration, expected_exports, export_names,
                    json.dumps(state, indent=2),
                ),
            )

            # Dependencies: every k present (natural key = name).
            dep_names = sorted(d["name"] for d in concern["dependencies"])
            expected_deps = sorted("dep-{0}".format(k) for k in range(n))
            self.assertEqual(
                dep_names, expected_deps,
                "iter {0}: dep-name mismatch. expected={1}, "
                "got={2}; full state=\n{3}".format(
                    iteration, expected_deps, dep_names,
                    json.dumps(state, indent=2),
                ),
            )

            # Hazards: every k present (natural key = (category,
            # description, cite_file, cite_start)). All chains use the
            # same category + no cite, but distinct descriptions.
            hazard_descs = sorted(h["description"] for h in concern["hazards"])
            expected_hazards = sorted(
                "hazard-from-process-{0}".format(k) for k in range(n)
            )
            self.assertEqual(
                hazard_descs, expected_hazards,
                "iter {0}: hazard-desc mismatch. expected={1}, "
                "got={2}; full state=\n{3}".format(
                    iteration, expected_hazards, hazard_descs,
                    json.dumps(state, indent=2),
                ),
            )

            # set-* setters are last-writer-wins; any one of the n
            # values is acceptable as long as it's not None.
            self.assertIsNotNone(
                concern["overview"],
                "iter {0}: overview is None — set-* writer never "
                "landed; full state=\n{1}".format(
                    iteration, json.dumps(state, indent=2),
                ),
            )
            self.assertTrue(
                concern["overview"].startswith("process-"),
                "iter {0}: overview {1!r} not a recognized "
                "writer's value".format(iteration, concern["overview"]),
            )
            self.assertIsNotNone(
                concern["directory_tree"],
                "iter {0}: directory_tree is None; full state=\n{1}".format(
                    iteration, json.dumps(state, indent=2),
                ),
            )


if __name__ == "__main__":
    unittest.main()
