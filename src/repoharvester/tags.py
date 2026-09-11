"""Versioned baseline classification using only lexical file paths."""

from __future__ import annotations

from pathlib import PurePosixPath

BASELINE_TAG_RULESET = "path-baseline-v1"

_LANGUAGE_BY_SUFFIX = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".h": "C",
    ".hpp": "C++",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".ps1": "PowerShell",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}


_TEST_DIRS = frozenset({"test", "tests", "__tests__"})
_DOC_DIRS = frozenset({"doc", "docs", "documentation"})
_CONFIG_DIRS = frozenset({"config", "configs", ".github"})
_SOURCE_DIRS = frozenset({"src", "source", "lib"})
_DOC_SUFFIXES = frozenset({".md", ".rst", ".adoc"})
_CONFIG_NAMES = frozenset({
    "pyproject.toml", "package.json", "tsconfig.json", "setup.cfg", "tox.ini",
    "pytest.ini", ".gitignore", ".gitattributes", ".editorconfig", ".env",
    "dockerfile", "makefile", "compose.yml", "compose.yaml",
})
_SOURCE_LANGUAGES = frozenset(_LANGUAGE_BY_SUFFIX.values()) - {"JSON", "YAML", "TOML", "Markdown"}


def language_for_path(path: str) -> str | None:
    """Return a suffix-table label, not a content-verified language assertion."""
    return _LANGUAGE_BY_SUFFIX.get(PurePosixPath(path.replace("\\", "/")).suffix.lower())


def baseline_tags(path: str) -> tuple[str, ...]:
    """Return sorted unique tags; role precedence is docs, test, config, source, unknown.

    Directory components are literal, case-preserving labels. Matching for roles
    is case-insensitive and only considers whole components, names, and suffixes.
    No source contents, environment, model, or filesystem access is consulted.
    """
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if not parts or parts[0] == "/" or ".." in parts or (len(parts[0]) == 2 and parts[0][1] == ":"):
        msg = "Baseline tags require a relative file path without parent traversal"
        raise ValueError(msg)
    name = parts[-1].lower()
    directories = {part.lower() for part in parts[:-1]}
    suffix = PurePosixPath(name).suffix
    language = language_for_path(path)
    if directories & _DOC_DIRS or suffix in _DOC_SUFFIXES or name in {"readme", "license", "changelog"}:
        role = "docs"
    elif directories & _TEST_DIRS or name.startswith("test_") or name.endswith("_test.py") or any(
        marker in name for marker in (".test.", ".spec.")
    ):
        role = "test"
    elif directories & _CONFIG_DIRS or name in _CONFIG_NAMES or suffix in {".toml", ".ini", ".cfg"}:
        role = "config"
    elif directories & _SOURCE_DIRS or language in _SOURCE_LANGUAGES:
        role = "source"
    else:
        role = "unknown"
    tags = {f"language:{language or 'unknown'}", f"role:{role}"}
    tags.update(f"path-component:{part}" for part in parts[:-1])
    return tuple(sorted(tags))
