"""Behavioral boundaries for deterministic path tags."""

import pytest

from repoharvester.tags import baseline_tags, language_for_path


@pytest.mark.parametrize(('path', 'language', 'role'), [
    ('src/app.py', 'Python', 'source'),
    ('tests/test_app.py', 'Python', 'test'),
    ('src/app.test.ts', 'TypeScript', 'test'),
    ('src/app.spec.js', 'JavaScript', 'test'),
    ('docs/example.py', 'Python', 'docs'),
    ('tests/README.md', 'Markdown', 'docs'),
    ('tests/config/helper.py', 'Python', 'test'),
    ('src/config/settings.py', 'Python', 'config'),
    ('.github/workflows/check.yml', 'YAML', 'config'),
    ('pyproject.toml', 'TOML', 'config'),
    ('package.json', 'JSON', 'config'),
    ('fixtures/data.json', 'JSON', 'unknown'),
    ('fixtures/data.yaml', 'YAML', 'unknown'),
    ('contest/latest.txt', None, 'unknown'),
    ('README', None, 'docs'),
    ('Dockerfile', None, 'config'),
    ('SRC/APP.PY', 'Python', 'source'),
    ('unknown.zzz', None, 'unknown'),
])
def test_explicit_role_boundaries(path, language, role):
    """Ambiguous data and misleading substrings do not acquire guessed roles."""
    tags = baseline_tags(path)
    assert language_for_path(path) == language
    assert f'language:{language or "unknown"}' in tags
    assert [tag for tag in tags if tag.startswith('role:')] == [f'role:{role}']


def test_components_and_reproducibility():
    """Only directories become component tags; separators normalize identically."""
    expected = ('language:Python', 'path-component:Pkg', 'path-component:src', 'role:source')
    assert baseline_tags('src/Pkg/src/app.py') == expected
    assert baseline_tags('src\\Pkg\\src\\app.py') == expected
    assert baseline_tags('src/Pkg/src/app.py') == baseline_tags('src/Pkg/src/app.py')


@pytest.mark.parametrize('path', ['', '.', '/src/a.py', '../a.py', 'src/../a.py', 'C:\\src\\a.py'])
def test_invalid_relative_paths(path):
    """Do not classify absolute paths or parent traversal as repo components."""
    with pytest.raises(ValueError, match='relative file path'):
        baseline_tags(path)
