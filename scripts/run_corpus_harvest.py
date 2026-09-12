"""Harvest a Git repository into a shared RepoHarvester corpus."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from gitingest.schemas import IngestionQuery

from repoharvester.corpus import harvest_into_corpus
from repoharvester.receipts import write_extraction_receipt

DEFAULT_IGNORES = {".git", "*.pyc", "__pycache__", "node_modules"}


def _git(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _resolve_revision(repository_url: str, revision: str | None) -> str:
    """Resolve a caller ref, or remote HEAD, to one exact commit SHA."""

    ref = revision or "HEAD"
    output = _git("ls-remote", repository_url, ref)
    matches = [line.split("\t", 1)[0] for line in output.splitlines() if line.strip()]
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise RuntimeError(
            f"could not resolve {ref!r} to one exact revision for {repository_url!r}"
        )
    return unique[0]


def _checkout_exact_revision(repository_url: str, revision: str, destination: Path) -> str:
    _git("init", str(destination))
    _git("remote", "add", "origin", repository_url, cwd=destination)
    _git("fetch", "--depth", "1", "origin", revision, cwd=destination)
    _git("checkout", "--detach", "FETCH_HEAD", cwd=destination)
    actual = _git("rev-parse", "HEAD", cwd=destination)
    if actual != revision:
        raise RuntimeError(f"checked out {actual}, expected {revision}")
    return actual


def _derive_slug(repository_url: str) -> str:
    trimmed = repository_url.rstrip("/")
    name = trimmed.rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    if not slug:
        raise ValueError(f"cannot derive repository slug from {repository_url!r}")
    return slug


def run_corpus_harvest(
    repository_url: str,
    database_path: Path,
    output_dir: Path,
    *,
    revision: str | None = None,
    slug: str | None = None,
) -> dict[str, object]:
    """Resolve, checkout, harvest, persist, receipt, and prove source immutability."""

    output_dir.mkdir(parents=True, exist_ok=True)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_slug = slug or _derive_slug(repository_url)
    resolved_revision = _resolve_revision(repository_url, revision)

    with tempfile.TemporaryDirectory(prefix="repoharvester-corpus-") as temp_dir:
        checkout = Path(temp_dir) / "source"
        checkout.mkdir()
        _checkout_exact_revision(repository_url, resolved_revision, checkout)
        status_before = _git("status", "--porcelain", cwd=checkout)

        query = IngestionQuery(
            local_path=checkout,
            url=repository_url,
            slug=resolved_slug,
            id=uuid4(),
            commit=resolved_revision,
            ignore_patterns=DEFAULT_IGNORES,
        )
        result = harvest_into_corpus(query, database_path)

        write_extraction_receipt(output_dir / "EXTRACTION_RECEIPT.json", result.receipt)

        status_after = _git("status", "--porcelain", cwd=checkout)
        if status_before != status_after or status_after:
            raise RuntimeError("corpus harvest mutated the external source checkout")

        summary = dict(result.summary)
        summary.update(
            {
                "requested_revision": revision,
                "resolved_revision": resolved_revision,
                "slug": resolved_slug,
                "source_worktree_clean": True,
                "output_dir": str(output_dir),
            }
        )
        (output_dir / "HARVEST_SUMMARY.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harvest a repository into a shared RepoHarvester SQLite corpus."
    )
    parser.add_argument("repository_url", help="Git clone URL for the repository to harvest")
    parser.add_argument(
        "--revision",
        help="Exact commit SHA or remote ref. If omitted, remote HEAD is resolved and pinned.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Shared SQLite corpus path; existing repositories are preserved",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Per-harvest directory for the extraction receipt and summary",
    )
    parser.add_argument("--slug", help="Optional repository slug; defaults to the clone URL basename")
    args = parser.parse_args()

    print(
        json.dumps(
            run_corpus_harvest(
                args.repository_url,
                args.database,
                args.output_dir,
                revision=args.revision,
                slug=args.slug,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
