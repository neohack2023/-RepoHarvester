"""Tests to verify that the query parser is Git host agnostic.

These tests confirm that ``parse_remote_repo`` correctly identifies user/repo pairs and canonical URLs for GitHub,
GitLab, Bitbucket, Gitea, and Codeberg without depending on live provider reachability.
"""

from __future__ import annotations

import pytest

import gitingest.utils.query_parser_utils as query_parser_utils
from gitingest.config import MAX_FILE_SIZE
from gitingest.query_parser import parse_remote_repo
from gitingest.utils.query_parser_utils import KNOWN_GIT_HOSTS, _is_valid_git_commit_hash

_FAKE_COMMIT = "a" * 40

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


# Generate cartesian product of repository tuples with URL variants.
@pytest.mark.parametrize(("host", "user", "repo"), _REPOS, ids=[f"{h}:{u}/{r}" for h, u, r in _REPOS])
@pytest.mark.parametrize("variant", ["full", "noscheme", "slug"])
@pytest.mark.asyncio
async def test_parse_query_without_host(
    host: str,
    user: str,
    repo: str,
    variant: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify URL normalization and host discovery without live network probes."""
    expected_url = f"https://{host}/{user}/{repo}"
    existence_probes: list[tuple[str, str | None]] = []
    resolved_refs: list[tuple[str, str, str | None]] = []

    async def fake_check_repo_exists(url: str, token: str | None = None) -> bool:
        existence_probes.append((url, token))
        return host in KNOWN_GIT_HOSTS and url == expected_url

    async def fake_resolve_ref_to_sha(url: str, pattern: str, token: str | None = None) -> str:
        resolved_refs.append((url, pattern, token))
        return _FAKE_COMMIT

    monkeypatch.setattr(query_parser_utils, "check_repo_exists", fake_check_repo_exists)
    monkeypatch.setattr(query_parser_utils, "_resolve_ref_to_sha", fake_resolve_ref_to_sha)

    if variant == "full":
        url = expected_url
    elif variant == "noscheme":
        url = f"{host}/{user}/{repo}"
    else:  # "slug"
        url = f"{user}/{repo}"

    # For slug form with a custom host (not in KNOWN_GIT_HOSTS) we expect a failure,
    # because the parser cannot guess which domain to use.
    if variant == "slug" and host not in KNOWN_GIT_HOSTS:
        with pytest.raises(ValueError, match="Could not find a valid repository host"):
            await parse_remote_repo(url)

        expected_probes = [f"https://{domain}/{user}/{repo}" for domain in KNOWN_GIT_HOSTS]
        assert [probe_url for probe_url, _token in existence_probes] == expected_probes
        assert resolved_refs == []
        return

    query = await parse_remote_repo(url)

    # Compare against the canonical dict while ignoring unpredictable fields.
    actual = query.model_dump(exclude={"id", "local_path", "ignore_patterns", "s3_url"})

    assert actual["commit"] == _FAKE_COMMIT
    assert _is_valid_git_commit_hash(actual["commit"])
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
    assert resolved_refs == [(expected_url, "HEAD", None)]

    if variant == "slug":
        selected_index = KNOWN_GIT_HOSTS.index(host)
        expected_probes = [
            f"https://{domain}/{user}/{repo}" for domain in KNOWN_GIT_HOSTS[: selected_index + 1]
        ]
        assert [probe_url for probe_url, _token in existence_probes] == expected_probes
    else:
        assert existence_probes == []
