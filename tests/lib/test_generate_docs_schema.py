"""Tests for src/devforge/lib/generate_docs_schema.py.

Exercises every dataclass for happy path + at least one error path,
plus the two `__post_init__` helpers (`_require_nonempty`,
`_require_in_enum`) and Literal-enum membership checks.

Schema-level validation only — file existence, snippet-vs-source
verbatim matching, the `architecture_shape` closed enum, and other
cross-record / filesystem invariants belong to `generate_docs_helper.py`
and are tested there.

Stdlib only.
"""

import sys
import unittest
from pathlib import Path

# Add helper dir to sys.path so the schema module can be imported by
# bare module name. Mirrors `test_init_helper.py`'s convention.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import generate_docs_schema as gds  # noqa: E402


# ---------------------------------------------------------------------------
# Common factories — keep tests terse + DRY.
# ---------------------------------------------------------------------------


def _cite(file="src/foo.py", start=1, end=10):
    return gds.SourceCite(file=file, start=start, end=end)


def _code(language="python", snippet="def f(): pass", cite=None):
    return gds.CodeBlock(
        language=language,
        snippet=snippet,
        cite=cite if cite is not None else _cite(),
    )


def _export(name="foo", kind="function", description="Does foo.", code=None):
    return gds.Export(
        name=name,
        kind=kind,
        signature="def foo() -> None",
        description=description,
        code=code if code is not None else _code(),
    )


def _dep(name="requests", kind="external", purpose="HTTP client"):
    return gds.Dependency(
        name=name,
        kind=kind,
        version="2.31.0",
        purpose=purpose,
    )


def _hazard(category="naming", description="Inconsistent verb prefix"):
    return gds.Hazard(category=category, description=description, cite=None)


# ---------------------------------------------------------------------------
# Helper-function tests.
# ---------------------------------------------------------------------------


class RequireNonemptyTests(unittest.TestCase):

    def test_accepts_non_empty_string(self):
        gds._require_nonempty("hello", "x")  # no exception

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            gds._require_nonempty("", "x")
        self.assertIn("x", str(ctx.exception))

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValueError) as ctx:
            gds._require_nonempty("   \t\n", "x")
        self.assertIn("x", str(ctx.exception))

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError) as ctx:
            gds._require_nonempty(123, "x")
        self.assertIn("x", str(ctx.exception))


class RequireInEnumTests(unittest.TestCase):

    def test_accepts_member(self):
        gds._require_in_enum("function", gds.EXPORT_KINDS, "kind")

    def test_rejects_non_member_lists_options(self):
        with self.assertRaises(ValueError) as ctx:
            gds._require_in_enum("widget", gds.EXPORT_KINDS, "kind")
        msg = str(ctx.exception)
        self.assertIn("kind", msg)
        self.assertIn("function", msg)  # at least one allowed value listed


# ---------------------------------------------------------------------------
# SourceCite.
# ---------------------------------------------------------------------------


class SourceCiteTests(unittest.TestCase):

    def test_happy_path(self):
        c = gds.SourceCite(file="src/x.py", start=1, end=10)
        self.assertEqual(c.file, "src/x.py")
        self.assertEqual((c.start, c.end), (1, 10))

    def test_single_line_cite_allowed(self):
        gds.SourceCite(file="src/x.py", start=5, end=5)

    def test_empty_file_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="", start=1, end=1)

    def test_whitespace_only_file_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="   ", start=1, end=1)

    def test_start_zero_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=0, end=5)

    def test_start_negative_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=-1, end=5)

    def test_end_before_start_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=10, end=5)

    def test_non_int_start_rejected(self):
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start="1", end=5)

    def test_bool_start_rejected(self):
        # bool is a subclass of int in Python; explicitly reject.
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=True, end=5)

    def test_bool_end_rejected(self):
        """SourceCite.end must reject bool inputs (bool is a subclass of int)."""
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=1, end=True)

    def test_non_int_end_rejected(self):
        """SourceCite.end must reject non-int inputs (e.g., string)."""
        with self.assertRaises(ValueError):
            gds.SourceCite(file="src/x.py", start=1, end="10")


# ---------------------------------------------------------------------------
# CodeBlock.
# ---------------------------------------------------------------------------


class CodeBlockTests(unittest.TestCase):

    def test_happy_path(self):
        cb = gds.CodeBlock(
            language="python", snippet="x = 1", cite=_cite()
        )
        self.assertEqual(cb.language, "python")

    def test_empty_language_rejected(self):
        with self.assertRaises(ValueError):
            gds.CodeBlock(language="", snippet="x", cite=_cite())

    def test_empty_snippet_rejected(self):
        with self.assertRaises(ValueError):
            gds.CodeBlock(language="python", snippet="", cite=_cite())

    def test_invalid_cite_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.CodeBlock(
                language="python",
                snippet="x",
                cite={"file": "x", "start": 1, "end": 2},
            )

    def test_nested_invalid_cite_propagates(self):
        # Constructing the inner cite first surfaces its own ValueError;
        # this confirms inner validation runs before the outer ctor.
        with self.assertRaises(ValueError):
            gds.CodeBlock(
                language="python",
                snippet="x",
                cite=gds.SourceCite(file="x.py", start=10, end=1),
            )


# ---------------------------------------------------------------------------
# Export.
# ---------------------------------------------------------------------------


class ExportTests(unittest.TestCase):

    def test_happy_path(self):
        e = _export()
        self.assertEqual(e.name, "foo")
        self.assertEqual(e.kind, "function")

    def test_optional_signature_none_allowed(self):
        e = gds.Export(
            name="foo",
            kind="function",
            signature=None,
            description="d",
            code=_code(),
        )
        self.assertIsNone(e.signature)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            _export(name="")

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _export(kind="widget")
        self.assertIn("Export.kind", str(ctx.exception))

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            _export(description="   ")

    def test_invalid_code_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Export(
                name="foo",
                kind="function",
                signature=None,
                description="d",
                code="not a CodeBlock",
            )

    def test_signature_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Export(
                name="foo",
                kind="function",
                signature=123,
                description="d",
                code=_code(),
            )

    def test_all_export_kinds_accepted(self):
        for k in gds.EXPORT_KINDS:
            _export(kind=k)


# ---------------------------------------------------------------------------
# Dependency.
# ---------------------------------------------------------------------------


class DependencyTests(unittest.TestCase):

    def test_happy_path(self):
        d = _dep()
        self.assertEqual(d.consumer_locations, [])  # default factory

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            _dep(name="")

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError):
            _dep(kind="vendor")

    def test_empty_purpose_rejected(self):
        with self.assertRaises(ValueError):
            _dep(purpose="")

    def test_consumer_locations_default_is_empty_list(self):
        d = gds.Dependency(
            name="x", kind="internal", version=None, purpose="p"
        )
        self.assertEqual(d.consumer_locations, [])
        self.assertIsInstance(d.consumer_locations, list)

    def test_consumer_locations_explicit(self):
        d = gds.Dependency(
            name="x",
            kind="internal",
            version=None,
            purpose="p",
            consumer_locations=["a/b", "c/d"],
        )
        self.assertEqual(d.consumer_locations, ["a/b", "c/d"])

    def test_consumer_locations_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Dependency(
                name="x",
                kind="internal",
                version=None,
                purpose="p",
                consumer_locations="a/b",
            )

    def test_version_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Dependency(name="x", kind="internal", version=42, purpose="p")


# ---------------------------------------------------------------------------
# Hazard.
# ---------------------------------------------------------------------------


class HazardTests(unittest.TestCase):

    def test_happy_path(self):
        h = _hazard()
        self.assertIsNone(h.cite)

    def test_with_cite(self):
        h = gds.Hazard(
            category="performance",
            description="N+1 query",
            cite=_cite(),
        )
        self.assertEqual(h.cite.start, 1)

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError):
            _hazard(category="bogus")

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            _hazard(description="")

    def test_all_hazard_categories_accepted(self):
        for c in gds.HAZARD_CATEGORIES:
            _hazard(category=c)

    def test_invalid_cite_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Hazard(category="naming", description="d", cite="not a cite")


# ---------------------------------------------------------------------------
# PackageDoc.
# ---------------------------------------------------------------------------


def _package_doc(**overrides):
    base = dict(
        name="api",
        path="packages/api",
        overview="The API package.",
        directory_tree="packages/api/\n  src/",
        primary_language="python",
        framework=None,
        build_tool=None,
    )
    base.update(overrides)
    return gds.PackageDoc(**base)


class PackageDocTests(unittest.TestCase):

    def test_happy_path_minimal(self):
        p = _package_doc()
        self.assertEqual(p.name, "api")
        self.assertEqual(p.scripts, {})
        self.assertEqual(p.exports, [])
        self.assertEqual(p.dependencies, [])
        self.assertEqual(p.hazards, [])
        self.assertIsNone(p.usage_example)
        self.assertIsNone(p.consumer_pattern)

    def test_happy_path_with_lists(self):
        p = _package_doc(
            scripts={"build": "make build", "test": "pytest"},
            exports=[_export(), _export(name="bar")],
            dependencies=[_dep()],
            hazards=[_hazard()],
        )
        self.assertEqual(len(p.exports), 2)
        self.assertEqual(p.scripts["build"], "make build")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(name="")

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(path="")

    def test_empty_overview_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(overview="")

    def test_empty_directory_tree_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(directory_tree="")

    def test_empty_primary_language_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(primary_language="")

    def test_optional_framework_string(self):
        p = _package_doc(framework="fastapi")
        self.assertEqual(p.framework, "fastapi")

    def test_framework_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(framework=42)

    def test_build_tool_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(build_tool=42)

    def test_scripts_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(scripts=["build"])

    def test_exports_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(exports="not a list")

    def test_invalid_nested_export_propagates(self):
        # Per-Export validation runs at Export construction, not in
        # PackageDoc.__post_init__. Confirm by attempting to build the
        # bad Export.
        with self.assertRaises(ValueError):
            _export(name="")

    def test_usage_example_codeblock(self):
        p = _package_doc(usage_example=_code())
        self.assertIsInstance(p.usage_example, gds.CodeBlock)

    def test_usage_example_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(usage_example="not a code block")

    def test_consumer_pattern_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _package_doc(consumer_pattern={"snippet": "x"})


# ---------------------------------------------------------------------------
# ConcernDoc.
# ---------------------------------------------------------------------------


def _concern_doc(**overrides):
    base = dict(
        package_path="packages/api",
        concern_name="auth",
        overview="Auth concern.",
        directory_tree="auth/\n  jwt.py",
    )
    base.update(overrides)
    return gds.ConcernDoc(**base)


class ConcernDocTests(unittest.TestCase):

    def test_happy_path_minimal(self):
        c = _concern_doc()
        self.assertEqual(c.public_surface, [])
        self.assertEqual(c.types, [])
        self.assertIsNone(c.usage_example)

    def test_happy_path_with_lists(self):
        c = _concern_doc(
            public_surface=[_export()],
            types=[_code()],
            dependencies=[_dep()],
            hazards=[_hazard()],
        )
        self.assertEqual(len(c.public_surface), 1)

    def test_empty_package_path_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(package_path="")

    def test_empty_concern_name_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(concern_name="")

    def test_empty_overview_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(overview="")

    def test_empty_directory_tree_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(directory_tree="")

    def test_public_surface_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(public_surface="not a list")

    def test_usage_example_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            _concern_doc(usage_example="x")


# ---------------------------------------------------------------------------
# Pattern / Layer / DepEdge / Decision / ArchitectureDoc.
# ---------------------------------------------------------------------------


class PatternTests(unittest.TestCase):

    def test_happy_path(self):
        p = gds.Pattern(name="repo-pattern", description="Repository abstraction.")
        self.assertEqual(p.applies_in, [])
        self.assertEqual(p.evidence, [])

    def test_with_evidence(self):
        p = gds.Pattern(
            name="repo-pattern",
            description="Repository abstraction.",
            applies_in=["packages/api"],
            evidence=[_cite()],
        )
        self.assertEqual(len(p.evidence), 1)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            gds.Pattern(name="", description="d")

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            gds.Pattern(name="n", description="")

    def test_evidence_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Pattern(name="n", description="d", evidence="x")


class LayerTests(unittest.TestCase):

    def test_happy_path(self):
        l_ = gds.Layer(name="api", description="HTTP layer")
        self.assertEqual(l_.sample_packages, [])

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            gds.Layer(name="", description="d")

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            gds.Layer(name="n", description="")

    def test_sample_packages_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Layer(name="n", description="d", sample_packages="x")


class DepEdgeTests(unittest.TestCase):

    def test_happy_path(self):
        e = gds.DepEdge(from_pkg="api", to_pkg="core", reason="domain model")
        self.assertEqual(e.from_pkg, "api")

    def test_empty_from_rejected(self):
        with self.assertRaises(ValueError):
            gds.DepEdge(from_pkg="", to_pkg="core", reason="r")

    def test_empty_to_rejected(self):
        with self.assertRaises(ValueError):
            gds.DepEdge(from_pkg="api", to_pkg="", reason="r")

    def test_empty_reason_rejected(self):
        with self.assertRaises(ValueError):
            gds.DepEdge(from_pkg="api", to_pkg="core", reason="")


class DecisionTests(unittest.TestCase):

    def test_happy_path(self):
        d = gds.Decision(title="Use X", rationale="Because Y")
        self.assertEqual(d.evidence, [])

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            gds.Decision(title="", rationale="r")

    def test_empty_rationale_rejected(self):
        with self.assertRaises(ValueError):
            gds.Decision(title="t", rationale="")

    def test_evidence_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.Decision(title="t", rationale="r", evidence="x")


class ArchitectureDocTests(unittest.TestCase):

    def test_happy_path_minimal(self):
        a = gds.ArchitectureDoc(
            project_name="acme", architecture_shape="monorepo"
        )
        self.assertEqual(a.patterns, [])
        self.assertEqual(a.layers, [])
        self.assertEqual(a.cross_package_deps, [])
        self.assertEqual(a.decisions, [])

    def test_happy_path_full(self):
        a = gds.ArchitectureDoc(
            project_name="acme",
            architecture_shape="monorepo",
            patterns=[gds.Pattern(name="p", description="d")],
            layers=[gds.Layer(name="api", description="d")],
            cross_package_deps=[
                gds.DepEdge(from_pkg="a", to_pkg="b", reason="r")
            ],
            decisions=[gds.Decision(title="t", rationale="r")],
        )
        self.assertEqual(len(a.patterns), 1)

    def test_empty_project_name_rejected(self):
        with self.assertRaises(ValueError):
            gds.ArchitectureDoc(project_name="", architecture_shape="monorepo")

    def test_empty_architecture_shape_rejected(self):
        with self.assertRaises(ValueError):
            gds.ArchitectureDoc(project_name="acme", architecture_shape="")

    def test_arbitrary_architecture_shape_string_accepted(self):
        # Schema-level only checks non-empty; closed-enum check lives
        # in the helper validator. This documents the boundary.
        gds.ArchitectureDoc(
            project_name="acme",
            architecture_shape="not-a-real-shape-but-non-empty",
        )

    def test_patterns_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.ArchitectureDoc(
                project_name="acme",
                architecture_shape="monorepo",
                patterns="x",
            )


# ---------------------------------------------------------------------------
# MemoryFinding.
# ---------------------------------------------------------------------------


class MemoryFindingTests(unittest.TestCase):

    def test_happy_path_no_cite(self):
        m = gds.MemoryFinding(
            category="naming",
            unit="packages/api",
            observation="Inconsistent verb prefix in handlers.",
        )
        self.assertIsNone(m.cite)

    def test_happy_path_with_cite(self):
        m = gds.MemoryFinding(
            category="performance",
            unit="workspace",
            observation="N+1 across services.",
            cite=_cite(),
        )
        self.assertEqual(m.unit, "workspace")

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError):
            gds.MemoryFinding(
                category="bogus", unit="workspace", observation="x"
            )

    def test_empty_unit_rejected(self):
        with self.assertRaises(ValueError):
            gds.MemoryFinding(
                category="naming", unit="", observation="x"
            )

    def test_empty_observation_rejected(self):
        with self.assertRaises(ValueError):
            gds.MemoryFinding(
                category="naming", unit="workspace", observation=""
            )

    def test_invalid_cite_type_rejected(self):
        with self.assertRaises(ValueError):
            gds.MemoryFinding(
                category="naming",
                unit="workspace",
                observation="x",
                cite="not a cite",
            )


if __name__ == "__main__":
    unittest.main()
