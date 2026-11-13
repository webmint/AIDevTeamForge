"""Synthetic multi-language fixtures for test_closure_check.py and test_research_lint.py. All code is invented.

Each language has a path builder that calls a normaliser internally: the ledger that omits the normaliser is the
case closure_check.py must catch. `write_project(root)` writes the sources; `LEDGERS[lang]` is a complete ledger and
`MISSING[lang]` the same ledger without the normaliser edge (and its entry).
"""
from __future__ import annotations

import json
import os
import stat
import sys

SOURCES = {
    "src/js/paths.js": "\n".join([
        'const { join } = require("path");',          # 1
        "",                                             # 2
        "function normalizeSegment(seg) {",             # 3
        "  return seg.trim().toLowerCase();",           # 4
        "}",                                            # 5
        "",                                             # 6
        "function buildUserPath(root, userId) {",       # 7
        "  const clean = normalizeSegment(userId);",    # 8
        '  return join(root, "users", clean);',         # 9
        "}",                                            # 10
        "",                                             # 11
        "module.exports = { buildUserPath, normalizeSegment };",  # 12
    ]),
    "src/js/auth.js": "\n".join([
        "function checkAccess(user, id) {",                           # 1
        '  if (user.id !== id) throw new Error("forbidden");',        # 2
        "}",                                                          # 3
        "module.exports = { checkAccess };",                          # 4
    ]),
    "src/js/handler.js": "\n".join([
        'const { buildUserPath } = require("./paths");',             # 1
        'const { checkAccess } = require("./auth");',                # 2
        "",                                                           # 3
        "async function getProfile(req) {",                           # 4
        "  checkAccess(req.user, req.params.id);",                    # 5
        '  return readFile(buildUserPath("/data", req.params.id));',  # 6
        "}",                                                          # 7
    ]),
    "src/py/store.py": "\n".join([
        "import os",                                                  # 1
        "",                                                           # 2
        "",                                                           # 3
        "def normalize_key(key):",                                    # 4
        "    return key.strip().lower()",                             # 5
        "",                                                           # 6
        "",                                                           # 7
        "def object_path(bucket, key):",                              # 8
        '    """Build the storage path for a key."""',                # 9
        "    return os.path.join(bucket, normalize_key(key))  # joined",  # 10
        "",                                                           # 11
        "",                                                           # 12
        "class Store:",                                               # 13
        "    def get(self, bucket, key):",                            # 14
        "        path = object_path(bucket, key)",                    # 15
        "        return open(path).read()",                           # 16
    ]),
    "src/go/paths.go": "\n".join([
        "package paths",                                              # 1
        "",                                                           # 2
        'import "strings"',                                           # 3
        "",                                                           # 4
        "func normalizeID(id string) string {",                       # 5
        "\treturn strings.ToLower(strings.TrimSpace(id))",            # 6
        "}",                                                          # 7
        "",                                                           # 8
        "// UserPath builds the data path for a user.",               # 9
        "func UserPath(root string, id string) string {",             # 10
        '\treturn root + "/users/" + normalizeID(id)',                # 11
        "}",                                                          # 12
        "",                                                           # 13
        "type Loader struct{ Root string }",                          # 14
        "",                                                           # 15
        "func (l *Loader) Load(id string) string {",                  # 16
        "\treturn UserPath(l.Root, id)",                              # 17
        "}",                                                          # 18
    ]),
    "src/java/UserPaths.java": "\n".join([
        "package app;",                                               # 1
        "",                                                           # 2
        "public class UserPaths {",                                   # 3
        "    static String normalize(String id) {",                   # 4
        "        return id.trim().toLowerCase();",                    # 5
        "    }",                                                      # 6
        "",                                                           # 7
        "    public static String userPath(String root, String id) {",  # 8
        '        return root + "/users/" + normalize(id);',           # 9
        "    }",                                                      # 10
        "}",                                                          # 11
    ]),
}

# (name, path, line, kind[, signature]) as Universal Ctags reports them for SOURCES (long kind names; a Python
# method is a `member` with a signature, a Go struct field a `member` without one)
TAGS = [
    ("normalizeSegment", "src/js/paths.js", 3, "function"),
    ("buildUserPath", "src/js/paths.js", 7, "function"),
    ("checkAccess", "src/js/auth.js", 1, "function"),
    ("getProfile", "src/js/handler.js", 4, "function"),
    ("normalize_key", "src/py/store.py", 4, "function"),
    ("object_path", "src/py/store.py", 8, "function"),
    ("Store", "src/py/store.py", 13, "class"),
    ("get", "src/py/store.py", 14, "member", "(self, bucket, key)"),
    ("normalizeID", "src/go/paths.go", 5, "func"),
    ("UserPath", "src/go/paths.go", 10, "func"),
    ("Loader", "src/go/paths.go", 14, "struct"),
    ("Root", "src/go/paths.go", 14, "member"),
    ("Load", "src/go/paths.go", 16, "func"),
    ("UserPaths", "src/java/UserPaths.java", 3, "class"),
    ("normalize", "src/java/UserPaths.java", 4, "method"),
    ("userPath", "src/java/UserPaths.java", 8, "method"),
]

LEDGERS = {
    "js": """# Call ledger

## Seeds
- `getProfile` `src/js/handler.js:4` — pass 1 — top-down

## Read
### `getProfile` `src/js/handler.js:4-7`
- `checkAccess` → `src/js/auth.js:1`
- `buildUserPath` → `src/js/paths.js:7`
- `readFile` → external
### `buildUserPath` `src/js/paths.js:7-10`
- `normalizeSegment` → `src/js/paths.js:3`
- `join` → external
### `checkAccess` `src/js/auth.js:1-3`
""",
    "py": """# Call ledger

## Seeds
- `Store.get` `src/py/store.py:14` — pass 1 — bottom-up

## Read
### `Store.get` `src/py/store.py:14-16`
- `object_path` → `src/py/store.py:8`
- `open` → external
### `object_path` `src/py/store.py:8-10`
- `normalize_key` → `src/py/store.py:4`
- `os.path.join` → external
""",
    "go": """# Call ledger

## Seeds
- `Loader.Load` `src/go/paths.go:16` — pass 1 — top-down

## Read
### `Loader.Load` `src/go/paths.go:16-18`
- `Loader` → `src/go/paths.go:14`
- `UserPath` → `src/go/paths.go:10`
### `UserPath` `src/go/paths.go:10-12`
- `normalizeID` → `src/go/paths.go:5`
### `Loader` `src/go/paths.go:14`
""",
    "java": """# Call ledger

## Seeds
- `UserPaths.userPath` `src/java/UserPaths.java:8` — pass 2 — approach

## Read
### `UserPaths.userPath` `src/java/UserPaths.java:8-10`
- `normalize` → `src/java/UserPaths.java:4`
### `normalize` `src/java/UserPaths.java:4-6`
""",
}

# the callee each MISSING ledger omits, with the body that calls it
OMITTED = {
    "js": ("normalizeSegment", "- `normalizeSegment` → `src/js/paths.js:3`\n"),
    "py": ("normalize_key", "- `normalize_key` → `src/py/store.py:4`\n"),
    "go": ("normalizeID", "- `normalizeID` → `src/go/paths.go:5`\n"),
    "java": ("normalize", "- `normalize` → `src/java/UserPaths.java:4`\n"),
}
MISSING = {lang: LEDGERS[lang].replace(line, "") for lang, (_n, line) in OMITTED.items()}


def write_project(root: str) -> None:
    for rel, text in SOURCES.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")


def write_fake_other_ctags(bin_dir: str, name: str = "ctags") -> str:
    """An executable that is not Universal Ctags (BSD/Xcode style): `--version` fails, any other run prints nothing."""
    os.makedirs(bin_dir, exist_ok=True)
    exe = os.path.join(bin_dir, name)
    with open(exe, "w", encoding="utf-8") as handle:
        handle.write("#!%s\nimport sys\n" % sys.executable)
        handle.write("if '--version' in sys.argv:\n    sys.stderr.write('ctags: illegal option -- -\\n')\n    sys.exit(1)\n")
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


def write_fake_ctags(bin_dir: str, tags=None, name: str = "ctags") -> str:
    """An executable `ctags` (or `name`) that says it is Universal Ctags and prints TAGS as its JSON output."""
    os.makedirs(bin_dir, exist_ok=True)
    data = os.path.join(bin_dir, "tags.jsonl")
    with open(data, "w", encoding="utf-8") as handle:
        for tag in (TAGS if tags is None else tags):
            row = {"_type": "tag", "name": tag[0], "path": tag[1], "line": tag[2], "kind": tag[3]}
            if len(tag) > 4 and tag[4]:
                row["signature"] = tag[4]
            if len(tag) > 5:
                row["end"] = tag[5]
            handle.write(json.dumps(row) + "\n")
    exe = os.path.join(bin_dir, name)
    with open(exe, "w", encoding="utf-8") as handle:
        handle.write("#!%s\nimport sys\n" % sys.executable)
        handle.write("if '--version' in sys.argv:\n    print('Universal Ctags 6.1.0 (fake)')\n    sys.exit(0)\n")
        handle.write("sys.stdout.write(open(%r, encoding='utf-8').read())\n" % data)
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe
