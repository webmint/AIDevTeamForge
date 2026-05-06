# vue-to-ts

Walk a source tree, compile every `.vue` Single File Component to a plain `.ts`/`.js` file using `@vue/compiler-sfc`. The output is intended for downstream graph indexing — TS parsers (ts-morph, tree-sitter-typescript) can read the compiled scripts and extract symbols, imports, and exports that are otherwise invisible inside SFCs.

## Why

Most code-graph tools treat `.vue` files as opaque single nodes because tree-sitter does not recurse into embedded languages inside SFC `<script>` blocks. This tool extracts the script (handles both Options API and `<script setup>` macros via `compileScript`) so a downstream indexer sees real TypeScript: imports, defineProps, defineEmits, composables, exported members.

## Install

```bash
cd tools/vue-to-ts
npm install
```

## Usage

```bash
# Sidecar mode (default): writes <name>.vue.ts next to each .vue file
node index.mjs /path/to/repo

# Mirror mode: writes to a parallel tree, source untouched
node index.mjs /path/to/repo --mode mirror --out /tmp/vue-extracted

# Dry run: parse + compile, no writes
node index.mjs /path/to/repo --dry-run

# Quiet, with extra excludes
node index.mjs /path/to/repo -q --exclude "**/__fixtures__/**,**/storybook/**"
```

## What gets emitted

By default, only the compiled `<script>` content is emitted. Macros (`defineProps`, `defineEmits`, `defineExpose`) are expanded; TypeScript is preserved when `<script lang="ts">` is detected.

Optional flags add the template:

- `--include-template` — appends the compiled render function. Useful when the indexer should see template-referenced identifiers as JS expressions.
- `--raw-template-comment` — appends the raw template as a `//` comment block. Useful for human review without affecting symbol extraction.

`<style>` blocks are dropped — irrelevant for symbol extraction.

## Output language

- `<script lang="ts">` or `<script setup lang="ts">` → `.ts`
- otherwise → `.js`

In sidecar mode the file extension is appended: `App.vue` → `App.vue.ts`. Add `*.vue.ts` and `*.vue.js` to `.gitignore` if you do not want to commit the artifacts.

## Default ignore patterns

`node_modules`, `dist`, `build`, `coverage`, `.git`, `.cache`, `.nuxt`, `.output`, `.turbo`. Override with `--exclude`.

## Empty SFC handling

Files with no content, or files with no `<script>` and no `<template>`, get a stub `export default {}` instead of failing the batch.

## Exit codes

- `0` — all files compiled
- `1` — one or more files failed (errors printed to stderr)
- `2` — invalid arguments

## Limitations

- The compiled render function is verbose and not human-readable. Treat it as machine input.
- Source maps are not emitted.
- Custom Vue compiler plugins (e.g., `@vitejs/plugin-vue` transforms beyond core SFC compilation) are not applied.
- The tool does not type-check — it produces compilable script output, not validated TS.
