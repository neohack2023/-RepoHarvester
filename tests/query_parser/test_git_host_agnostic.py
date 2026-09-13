"""Tests to verify that the query parser is Git host agnostic.

These tests confirm that ``parse_remote_repo`` correctly identifies user/repo pairs and canonical URLs for GitHub, GitLab,
Bitbucket, Gitea, and Codeberg without depending on third-party host availability.
Live host reachability belongs in the separate External Acceptance workflow.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest

from gitingest.config import MAX_FILE_SIZE
from gitingest.query_parser import parse_remote_repo
from gitingest.utils.query_parser_utils import KNOWN_GIT_HOSTS, _is_valid_git_commit_hash

# Repository matrix: (host, user, repo)
_REPOS: list[tuple[str, str, str]] = [
    ("github.com", "fastapi", "fastapi"),
    ("gitlab.com", "gitlab-org", "gitlab-runner"),
    ("bitbucket.org", "na-dna", "llm-knowledge-share"),
    ("gitea.com", "xorm", "xorm"),
    ("codeberg.org", "forgejo", "forgejo"),
    ("git.rwth-aachen.de", "medialab", "19squared"),
    ("gitlab.alpinelinux.org", "alpine", "apk-tools"),
]

_TEST_COMMIT = "0123456789abcdef0123456789abcdef01234567"


# Generate cartesian product of repository tuples with URL variants.
@pytest.mark.parametrize(
    ("host", "user", "repo"),
    _REPOS,
    ids=[f"{h}:{u}/{r}" for h, u, r in _REPOS],
)
@pytest.mark.parametrize("variant", ["full", "noscheme", "slug"])
@pytest.mark.asyncio
async def test_parse_query_without_host(
    host: str,
    user: str,
    repo: str,
    variant: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify URL/slug parsing without coupling deterministic CI to live Git hosts."""

    async def fake_check_repo_exists(candidate: str, token: str | None = None) -> bool:  # noqa: ARG001
        parsed = urlparse(candidate)
        return parsed.netloc == host and parsed.path.strip("/") == f"{user}/{repo}"

    async def fake_resolve_ref_to_sha(
        url: str,  # noqa: ARG001
        pattern: str,  # noqa: ARG001
        token: str | None = None,  # noqa: ARG001
    ) -> str:
        return _TEST_COMMIT

    monkeypatch.setattr("gitingest.utils.query_parser_utils.check_repo_exists", fake_check_repo_exists)
    monkeypatch.setattr("gitingest.utils.query_parser_utils._resolve_ref_to_sha", fake_resolve_ref_to_sha)

    if variant == "full":
        url = f"https://{host}/{user}/{repo}"
    elif variant == "noscheme":
        url = f"{host}/{user}/{repo}"
    else:  # "slug"
        url = f"{user}/{repo}"

    expected_url = f"https://{host}/{user}/{repo}"

    # Slugs can only resolve through the explicit known-host search set. A self-hosted
    # domain supplied in the matrix is intentionally not guessed from a bare slug.
    if variant == "slug" and host not in KNOWN_GIT_HOSTS:
        with pytest.raises(ValueError, match="Could not find a valid repository host"):
            await parse_remote_repo(url)
        return

    query = await parse_remote_repo(url)

    actual = query.model_dump(exclude={"id", "local_path", "ignore_patterns", "s3_url"})

    assert "commit" in actual
    assert _is_valid_git_commit_hash(actual["commit"])
    assert actual["commit"] == _TEST_COMMIT
    del actual["commit"]

    expected = {
        "host": host,
        "user_name": user,
        "repo_name": repo,
        "url": expected_url,
        "slug": f"{user}-{repo}",
        "subpath": "/",
        "type": None,
        "branch": None,
        "tag": None,
        "max_file_size": MAX_FILE_SIZE,
        "include_patterns": None,
        "include_submodules": False,
    }

    assert actual == expected
