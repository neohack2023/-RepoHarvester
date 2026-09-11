"""Deterministic provenance helpers for harvested source."""

from __future__ import annotations

from pathlib import Path

import git


def resolve_checked_out_revision(local_path: Path) -> str:
    """Return the exact Git HEAD containing ``local_path``.

    RepoHarvester records must point at the revision that is actually checked out,
    rather than trusting a requested branch, tag, or commit string carried by a query.
    """
    worktree_path = local_path.parent if local_path.is_file() else local_path
    try:
        repo = git.Repo(worktree_path, search_parent_directories=True)
        return repo.head.commit.hexsha
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError) as exc:
        msg = f"Cannot create reproducible harvest records without a resolvable Git HEAD: {local_path}"
        raise ValueError(msg) from exc
