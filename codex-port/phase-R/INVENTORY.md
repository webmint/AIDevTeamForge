# Phase R.1 — Reshape Inventory

Status: R.1 (mapping only, no file moves yet).
Acceptance of the reshape (Phase R): install.sh produces byte-identical target output before vs after.

---

## 1. Files that MOVE (template repo paths → new template repo paths)

### 1.1 Commands — 23 of 24 move

From `.claude/commands/` → `src/commands/`:

```
_agent-assignment.md          _multi-task-continuation.md    finalize.md         review.md
_context-maintenance.md       _recovery.md                    fix.md              security.md
_tech-writer-onboarding.md    audit.md                        onboard.md          setup-wizard.md
breakdown.md                  constitute.md                   plan.md             specify.md
execute-task.md               refactor.md                     refresh-docs.md     summarize.md
report-bug.md                 research.md                     verify.md
```

### 1.2 Agent templates — 16 files

From `.claude/templates/agents/` → `src/agents/`:

```
ac-verifier.template.md        devops-engineer.template.md      performance-analyst.template.md
api-designer.template.md       frontend-engineer.template.md    qa-engineer.template.md
architect.template.md          migration-engineer.template.md   runtime-debugger.template.md
backend-engineer.template.md   mobile-engineer.template.md      security-reviewer.template.md
code-reviewer.template.md      tech-writer.template.md
db-engineer.template.md        design-auditor.template.md
```

### 1.3 File templates — 5 files

From `.claude/templates/` → `src/files/`:

```
CLAUDE.template.md
constitution.template.md
memory.template.md
settings.template.json
storage-rules.md
```

### 1.4 Manifest

From `.claude/template-manifest.json` → `src/manifest.json`.

### 1.5 Version file (decision needed)

`.claude/template-version` — small file containing version string (`1.28.0` currently).

Options:
- Move to `src/version` (or `src/VERSION`) — cleaner, but install.sh currently writes `target/.claude/template-version` so target path needs decoupling from source path.
- Keep at `.claude/template-version` — breaks "only maintainer stuff in .claude/" rule for one file.
- Move to repo root as `VERSION` — conventional, easy.

**Recommendation**: move to repo root as `VERSION`. Simple, conventional, matches how most npm/Rust/Go projects version.

---

## 2. Files that STAY

### 2.1 `.claude/` — maintainer's own Claude config

```
.claude/commands/release.md        ← maintainer-only (per manifest templateRepoOnly)
.claude/settings.local.json        ← this repo's Claude settings
.claude/memory/                    ← this repo's Claude memory
.claude/template-manifest.json     ← deleted; moves to src/manifest.json (see 1.4)
.claude/template-version           ← deleted; moves to VERSION (see 1.5)
```

### 2.2 Repo root — unchanged

```
install.sh, update.sh              ← rewritten to read from src/, behavior unchanged
scripts/chrome-devtools-mcp.sh     ← shippable script, stays here
specs/, bugs/, research/           ← shipped unchanged to target
.mcp.json                          ← shipped unchanged to target
.github/, .gitignore, .git/        ← normal
README.md, LICENSE, CLAUDE.md      ← unchanged
AI-ISSUES-AUDIT.md, COMPETITIVE-ANALYSIS.md, PUBLIC-RELEASE-PLAN.md,
  PENDING-CHANGES.md, FUTURE-ORCHESTRATOR.md, STRENGTHS-WEAKNESSES.md ← maintainer docs, stay
codex-port/                        ← this branch's planning docs (will be rebased)
```

---

## 3. Code that needs updating

### 3.1 install.sh — currently a simple copier

Current behavior (from reading install.sh):
- Line 63: `cp -r "$TEMPLATE_DIR/.claude" "$TARGET_DIR/"` — copies ALL of `.claude/` wholesale
- Line 64: deletes `target/.claude/settings.local.json` (maintainer's, not for target)
- Line 65: deletes `target/.claude/commands/release.md` (maintainer-only command)
- Line 66–67: wipes/recreates `target/.claude/memory/` (don't carry maintainer's memory)
- Line 71: `cp -r "$TEMPLATE_DIR/scripts" "$TARGET_DIR/"` — stays as is
- Line 75–76: reads `$TEMPLATE_DIR/.claude/template-version`, writes `$TARGET_DIR/.claude/template-version`

Post-reshape rewrite:
- Build target `.claude/` synthetically from `src/`:
  - `src/commands/*.md` → `target/.claude/commands/`
  - `src/agents/*.template.md` → `target/.claude/templates/agents/`
  - `src/files/*` → `target/.claude/templates/`
  - `src/manifest.json` → `target/.claude/template-manifest.json`
- Create `target/.claude/memory/` (empty)
- Lines that previously stripped `settings.local.json` and `release.md` become obsolete (those files don't exist in `src/`, so nothing to strip).
- Version: read `VERSION` at repo root, write to `target/.claude/template-version`.

**Install.sh scope after reshape**: grows from ~30 lines of logic to maybe ~60. Manageable.

### 3.2 update.sh — references to update

Grep results for `.claude/` in update.sh (24 matches):

| Line | Current | Post-reshape |
|---|---|---|
| 64 | `err "Missing .claude/ directory in: $TARGET_DIR"` | Unchanged (target still has `.claude/`) |
| 82 | `MANIFEST="$TEMPLATE_DIR/.claude/template-manifest.json"` | `MANIFEST="$TEMPLATE_DIR/src/manifest.json"` |
| 89 | `TARGET_VERSION_FILE="$TARGET_DIR/.claude/template-version"` | Unchanged (target path) |
| 129, 154, 158, 332, 340, 345 | `$TARGET_DIR/.claude/project-config.json` | Unchanged (target path) |
| 216, 229, 230, 239, 246, 253 | `$TARGET_DIR/.claude/agents/...` | Unchanged (target path) |
| 382 | `# e.g. ".claude/templates/**" → find .claude/templates -type f` | Update comment; logic may work either way depending on manifest format |
| 516, 592 | `$TARGET_DIR/.claude/.baseline` | Unchanged (target path) |
| 534 | echoed message `"WRITE  .claude/template-version → ..."` | Unchanged (target path) |

**Most references are TARGET paths** (what the installed target project looks like). These stay. Only lines referencing the **template repo's own layout** need updating — mainly the manifest path (line 82).

### 3.3 src/manifest.json — content restructuring

Current manifest uses paths like `".claude/commands/breakdown.md"` which today mean BOTH source (template repo) AND target (installed project), because today they're the same path. After reshape, source ≠ target.

Options for manifest format post-reshape:
- **A. Keep manifest listing TARGET paths.** update.sh knows the mapping rule: for templateOwned pattern `"{{target_path}}"`, source lives at `src/{{leaf}}`. Less explicit but compact.
- **B. Pair source + target explicitly.** Every entry becomes `{ source: "src/commands/breakdown.md", target: ".claude/commands/breakdown.md" }`. More verbose, more flexible — enables multi-runtime fan-out in Phase A.

**Recommendation**: **B**, because Phase A will need source → multiple targets anyway (`src/commands/fix.md` → `target/.claude/commands/fix.md` AND `target/.codex/prompts/fix.md`). Starting with A and reformatting later doubles work.

### 3.4 .claude/settings.local.json — contents

Currently this repo has `.claude/settings.local.json` at 75 bytes. Content probably harmless but worth checking it doesn't reference moved paths.

---

## 4. Potential surprises / edge cases

1. **Symlinks or hardlinks?** None observed. Safe to plain-copy.
2. **Hidden files under `.claude/templates/`?** `ls -la` already surveyed; none found.
3. **Other scripts or config referencing the old paths?** Ran broad greps; only `install.sh`/`update.sh`/manifest/wizard reference them. Wizard prose mentions `.claude/templates/` — that's the TARGET path (what's present in the installed project), so it does NOT need changing.
4. **Git history.** Files moved with `git mv` preserve blame cleanly. No concern.
5. **CLAUDE.md at repo root.** This repo has its own CLAUDE.md. Should be inspected to confirm it doesn't reference `.claude/commands/` or `.claude/templates/` in a way that breaks post-reshape. (Low risk; the file is project-about, not tooling-about.)

---

## 5. Acceptance verification plan (for R.3)

1. Pick a disposable test target directory (fresh scaffold, or throwaway clone of a simple project).
2. Run `./install.sh <target>` from `main` branch checkout. Snapshot result: `tar czf pre-reshape.tgz <target>`.
3. `git checkout refactor/src-layout`. Reset the test target (remove and recreate). Run `./install.sh <target>` from reshape branch. Snapshot: `tar czf post-reshape.tgz <target>`.
4. `diff -r` the two snapshots. **Empty diff = Phase R passes.**
5. Also run `./update.sh <target>` on an already-installed target from both branches; diff those too.

---

## 6. Decisions needed before R.2 (execute move)

1. **Version file location**: `VERSION` at repo root (recommended), `src/VERSION`, or keep at `.claude/template-version`?
2. **Manifest format**: pair-based `{ source, target }` (recommended, Phase-A-ready) or target-only with mapping rule?
3. **Branch name**: `refactor/src-layout` (plan default), or something else?
4. **Test target for R.3**: existing throwaway directory you have, or should I create one under `codex-port/phase-R/test-target/`?

---

## 7. Proposed order for R.2 (execute)

Small commits, each independently verifiable:

1. Create `src/` dir skeleton (empty).
2. `git mv .claude/commands/*.md src/commands/` (except release.md).
3. `git mv .claude/templates/agents/*.md src/agents/`.
4. `git mv .claude/templates/*.md src/files/` + `git mv .claude/templates/settings.template.json src/files/`.
5. `git mv .claude/template-manifest.json src/manifest.json`.
6. Move version file per decision #1.
7. Rewrite `install.sh` to build target from `src/`.
8. Update manifest content per decision #2.
9. Update `update.sh` manifest path reference.
10. Run R.3 verification.
