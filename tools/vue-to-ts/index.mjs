#!/usr/bin/env node
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import fg from 'fast-glob'
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises'
import { dirname, join, relative, resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { createHash } from 'node:crypto'

const HELP = `Usage: vue-to-ts <root> [options]

Walks <root> recursively, compiles every .vue file to .ts (or .js) using
@vue/compiler-sfc, and writes the result for downstream graph indexing.

Options:
  --mode <sidecar|mirror>   sidecar: write next to source as <name>.vue.ts
                            mirror:  write under --out preserving tree
                            (default: sidecar)
  -o, --out <dir>           Required when --mode mirror
  --include <glob>          Extra include glob (repeatable, comma-separated)
  --exclude <glob>          Extra exclude glob (repeatable, comma-separated)
  --include-template        Append compiled render fn (default: script only)
  --raw-template-comment    Append raw template as a trailing comment
  --no-header               Omit the auto-generated provenance header
  --dry-run                 Parse + compile but do not write files
  -q, --quiet               Suppress per-file logs
  -h, --help                Show this message

Defaults
  - Skips: node_modules, dist, build, coverage, .git, .cache, .nuxt, .output, .turbo
  - Output language: .ts if <script lang="ts"> detected, else .js
  - Style blocks are dropped (irrelevant for symbol extraction)

Exit codes
  0  all files compiled
  1  one or more files failed
  2  invalid arguments
`

const args = (() => {
  try {
    return parseArgs({
      options: {
        mode: { type: 'string', default: 'sidecar' },
        out: { type: 'string', short: 'o' },
        include: { type: 'string', multiple: true },
        exclude: { type: 'string', multiple: true },
        'include-template': { type: 'boolean', default: false },
        'raw-template-comment': { type: 'boolean', default: false },
        'no-header': { type: 'boolean', default: false },
        'dry-run': { type: 'boolean', default: false },
        quiet: { type: 'boolean', short: 'q', default: false },
        help: { type: 'boolean', short: 'h', default: false },
      },
      allowPositionals: true,
    })
  } catch (err) {
    console.error(`Argument error: ${err.message}`)
    console.error(HELP)
    process.exit(2)
  }
})()

if (args.values.help || args.positionals.length === 0) {
  console.log(HELP)
  process.exit(args.values.help ? 0 : 2)
}

const root = resolve(args.positionals[0])
const mode = args.values.mode
if (mode !== 'sidecar' && mode !== 'mirror') {
  console.error(`--mode must be 'sidecar' or 'mirror' (got '${mode}')`)
  process.exit(2)
}
const outDir = args.values.out ? resolve(args.values.out) : null
if (mode === 'mirror' && !outDir) {
  console.error('--mode mirror requires --out <dir>')
  process.exit(2)
}

try {
  const s = await stat(root)
  if (!s.isDirectory()) {
    console.error(`<root> is not a directory: ${root}`)
    process.exit(2)
  }
} catch {
  console.error(`<root> does not exist: ${root}`)
  process.exit(2)
}

const DEFAULT_IGNORE = [
  '**/node_modules/**',
  '**/dist/**',
  '**/build/**',
  '**/coverage/**',
  '**/.git/**',
  '**/.cache/**',
  '**/.nuxt/**',
  '**/.output/**',
  '**/.turbo/**',
]

const includes = ['**/*.vue', ...flatten(args.values.include)]
const ignores = [...DEFAULT_IGNORE, ...flatten(args.values.exclude)]

function flatten(arr) {
  if (!arr) return []
  return arr.flatMap((s) => s.split(',').map((x) => x.trim()).filter(Boolean))
}

const files = await fg(includes, {
  cwd: root,
  absolute: true,
  ignore: ignores,
  onlyFiles: true,
  followSymbolicLinks: false,
})

if (files.length === 0) {
  console.error(`No .vue files found under ${root}`)
  process.exit(0)
}

if (!args.values.quiet) {
  console.error(`Found ${files.length} .vue file(s) under ${relative(process.cwd(), root) || '.'}`)
}

const results = { ok: 0, failed: 0, errors: [] }
const t0 = Date.now()

for (const absPath of files) {
  const rel = relative(root, absPath)
  try {
    const out = await processFile(absPath, rel)
    results.ok++
    if (!args.values.quiet) {
      console.log(`  ok  ${rel} -> ${out.outRel}`)
    }
  } catch (err) {
    results.failed++
    results.errors.push({ file: rel, error: err.message })
    console.error(`  err ${rel}: ${err.message}`)
  }
}

const dt = ((Date.now() - t0) / 1000).toFixed(2)
console.error(`\n${results.ok} ok, ${results.failed} failed, ${dt}s`)
process.exit(results.failed > 0 ? 1 : 0)

async function processFile(absPath, rel) {
  const source = await readFile(absPath, 'utf8')
  const id = hashId(rel)

  if (source.trim().length === 0) {
    return writeStub(absPath, rel, 'js', 'empty source file')
  }

  const { descriptor, errors: parseErrors } = parse(source, { filename: absPath })

  const isEmptySfc =
    !descriptor.script && !descriptor.scriptSetup && !descriptor.template
  if (isEmptySfc) {
    return writeStub(absPath, rel, 'js', 'no <script> or <template> blocks')
  }

  if (parseErrors.length) {
    throw new Error(`parse: ${parseErrors.map((e) => e.message).join('; ')}`)
  }

  const hasScriptSetup = !!descriptor.scriptSetup
  const hasScript = !!descriptor.script
  const lang = descriptor.scriptSetup?.lang || descriptor.script?.lang || 'js'
  const isTs = lang === 'ts' || lang === 'tsx'
  const ext = isTs ? '.ts' : '.js'

  let compiledScript = null
  if (hasScript || hasScriptSetup) {
    try {
      compiledScript = compileScript(descriptor, {
        id,
        sourceMap: false,
        inlineTemplate: false,
        babelParserPlugins: isTs ? ['typescript'] : [],
      })
    } catch (err) {
      throw new Error(`compileScript: ${err.message}`)
    }
  }

  let templateBlock = ''
  if (args.values['include-template'] && descriptor.template) {
    try {
      const tpl = compileTemplate({
        id,
        filename: absPath,
        source: descriptor.template.content,
        scoped: false,
        slotted: false,
        compilerOptions: {
          bindingMetadata: compiledScript?.bindings,
          mode: 'module',
        },
      })
      const tplErrors = (tpl.errors || []).map((e) => (typeof e === 'string' ? e : e.message))
      if (tplErrors.length) {
        templateBlock = `\n// --- template (compile errors) ---\n// ${tplErrors.join('\n// ')}\n`
      } else {
        templateBlock = `\n// --- template (compiled render) ---\n${tpl.code}\n`
      }
    } catch (err) {
      templateBlock = `\n// --- template (compile threw) ---\n// ${err.message}\n`
    }
  }

  let rawTemplateComment = ''
  if (args.values['raw-template-comment'] && descriptor.template) {
    const lines = descriptor.template.content.split('\n').map((l) => `// ${l}`).join('\n')
    rawTemplateComment = `\n// --- template (raw) ---\n${lines}\n`
  }

  const header = args.values['no-header']
    ? ''
    : buildHeader(rel, hasScriptSetup ? '<script setup>' : hasScript ? '<script>' : '(no script)', lang)

  const scriptContent = compiledScript ? compiledScript.content : 'export default {}\n'
  const output = header + scriptContent + templateBlock + rawTemplateComment

  let outAbs
  let outRel
  if (mode === 'sidecar') {
    outAbs = absPath + ext
    outRel = relative(process.cwd(), outAbs)
  } else {
    outAbs = join(outDir, rel) + ext
    outRel = relative(process.cwd(), outAbs)
  }

  if (!args.values['dry-run']) {
    await mkdir(dirname(outAbs), { recursive: true })
    await writeFile(outAbs, output, 'utf8')
  }

  return { outAbs, outRel }
}

async function writeStub(absPath, rel, lang, reason) {
  const isTs = lang === 'ts' || lang === 'tsx'
  const ext = isTs ? '.ts' : '.js'
  const header = args.values['no-header']
    ? ''
    : [
        '// ============================================================',
        `// auto-generated by vue-to-ts from ${rel}`,
        `// stub: ${reason}`,
        '// ============================================================',
        '',
        '',
      ].join('\n')
  const output = header + 'export default {}\n'

  let outAbs
  let outRel
  if (mode === 'sidecar') {
    outAbs = absPath + ext
    outRel = relative(process.cwd(), outAbs)
  } else {
    outAbs = join(outDir, rel) + ext
    outRel = relative(process.cwd(), outAbs)
  }
  if (!args.values['dry-run']) {
    await mkdir(dirname(outAbs), { recursive: true })
    await writeFile(outAbs, output, 'utf8')
  }
  return { outAbs, outRel }
}

function buildHeader(rel, blockKind, lang) {
  return [
    '// ============================================================',
    `// auto-generated by vue-to-ts from ${rel}`,
    `// source kind: ${blockKind}, lang: ${lang}`,
    '// edits will be overwritten on next run',
    '// ============================================================',
    '',
    '',
  ].join('\n')
}

function hashId(input) {
  return createHash('sha256').update(input).digest('hex').slice(0, 8)
}
