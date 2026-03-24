# /release — Template Release Workflow

> **Scope**: This command runs in the AIDevTeamForge template repo itself, NOT in target projects.

Automates version bump, changelog, and documentation updates after making changes to the template.

## PHASE 1: Analyze Changes

1. Read the current version from `.claude/template-version`
2. Run `git diff --stat` and `git diff` (staged + unstaged) to understand all pending changes
3. Run `git log --oneline` to see recent commits for context
4. Categorize the changes:
   - **Added**: new features, commands, placeholders, config keys
   - **Changed**: modified behavior, updated strategies, template content changes
   - **Fixed**: bug fixes, inconsistencies resolved
   - **Removed**: deleted features or deprecated items

## PHASE 2: Version Bump

Ask the user via AskUserQuestion:

"Current version is X.Y.Z. What type of bump?"
- **Patch** (X.Y.Z+1) — bug fixes, typo corrections, minor tweaks
- **Minor** (X.Y+1.0) — new features, new commands, new config options, behavioral changes
- **Major** (X+1.0.0) — breaking changes to update.sh, manifest format, or wizard flow

Suggest the appropriate level based on the changes detected in Phase 1. Default to **minor** for most feature work.

## PHASE 3: Apply Version Bump

Update the version string in:
1. `.claude/template-version`
2. `.claude/template-manifest.json` (`"version"` field)

## PHASE 4: Update CHANGELOG.md

Insert a new section at the top (after the header), following Keep a Changelog format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- [items from Phase 1 categorization]

### Changed
- [items from Phase 1 categorization]
- Template version: OLD → NEW

### Fixed
- [items from Phase 1 categorization]
```

Omit empty categories. Write concise but specific entries — each should explain WHAT changed and WHY it matters. Include sub-bullets for details when the change has multiple aspects.

Reference the previous changelog entries for style consistency.

## PHASE 5: Update Documentation

### 5.1: DEVELOPMENT-STATUS.md

Update if any of these changed:
- **Commands section**: new command added or command description changed
- **Agent Templates section**: new agents, template structure changes
- **Supporting Templates section**: new templates or template content changes
- **Update System section**: update.sh strategy changes, new config keys
- **Key Design Decisions**: new architectural decisions worth documenting
- **Other sections**: wrapper mode, onboarding, context maintenance, crash recovery

Skip if changes are purely internal (bug fixes, minor tweaks that don't affect the status overview).

### 5.2: README.md

Update if any of these changed:
- **Installation section**: new files installed, new flags
- **Setup wizard section**: new questions, new detection logic
- **Update section**: new strategies, changed table, new subsections
- **Workflow section**: new commands, changed command descriptions
- **Artifact Storage**: new directories or changed structure
- **Hard Gates / Automated Guardrails**: new gates or guardrails
- **Pre-Populated Universal Rules**: changes to defaults
- **Wrapper Mode / Greenfield / Customization**: behavioral changes

Skip if changes don't affect the user-facing documentation.

### 5.3: install.sh

Update if:
- New directories need to be copied during installation (e.g., new top-level folders like `research/`)
- New flags or installation options added

Skip for most releases — install.sh rarely changes.

### 5.4: update.sh

Usually already modified as part of the feature work. Check if the version-related display or changelog excerpt logic needs adjustment. Skip if no update.sh behavioral changes.

## PHASE 6: Summary

Present what was done:

```
## Release X.Y.Z

### Version bumped:
- .claude/template-version: OLD → NEW
- .claude/template-manifest.json: OLD → NEW

### CHANGELOG.md:
- Added X.Y.Z entry with N items

### Documentation updated:
- [list of files updated, or "No documentation changes needed"]

### Not committed — review changes with `git diff` before committing.
```

## IMPORTANT RULES

1. **Read before write** — always read each file before modifying it
2. **Don't invent changes** — only document what actually changed in the git diff
3. **Match existing style** — follow the conventions in each file (changelog format, README structure, dev status sections)
4. **Don't commit** — present the changes for user review, they commit manually
5. **Today's date** — use the current date for the changelog entry
6. **Be concise** — changelog entries should be scannable, not essays
7. **Skip unchanged docs** — don't update README/DEVELOPMENT-STATUS if changes don't affect them