"""Push and Pull: the benchmark travels by git, scrubbed of credentials before anything leaves."""

import os
from pathlib import Path
import shutil
import subprocess

from pydantic import BaseModel

from mybench.core import benchmark
from mybench.core.execute import NATIVE_PROVIDER_KEYS
from mybench.core.git import run_git
from mybench.schemas import BenchmarkConfig, MyBenchError
from mybench.settings import benchmark_home

REDACTION = b"[REDACTED]"


class PushOutcome(BaseModel):
    """What one push did: where it landed, and what was scrubbed and committed on the way."""

    remote: str
    scrubbed: int
    committed: bool


def push_results(remote: str | None = None) -> PushOutcome:
    """Commit everything new and push it to origin, creating a private GitHub repository when there is none.

    Configured API key values are scrubbed from not-yet-committed files first, so no credential
    ever enters the history.
    """
    home = benchmark_home()
    config = benchmark.load_config(home)
    if not (home / ".git").exists():
        run_git(["init", "-b", "main"], cwd=home)
    scrubbed = _scrub_secrets(home, _secret_values(config))
    run_git(["add", "-A"], cwd=home)
    committed = bool(run_git(["status", "--porcelain"], cwd=home))
    if committed:
        run_git(["commit", "-m", "mybench push"], cwd=home)
    if remote is not None:
        _set_origin(home, remote)
    url = _origin_url(home)
    if url is None:
        _create_remote(home)
        return PushOutcome(remote=_origin_url(home) or home.name, scrubbed=scrubbed, committed=committed)
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=home)
    run_git(["push", "-u", "origin", branch], cwd=home)
    return PushOutcome(remote=url, scrubbed=scrubbed, committed=committed)


def pull_results() -> str:
    """Fetch and merge from origin, returning git's summary; a merge conflict stops the pull."""
    home = benchmark_home()
    if not (home / ".git").exists():
        raise MyBenchError(f"{home} is not a git repository. `mybench push` publishes it first.")
    if _origin_url(home) is None:
        raise MyBenchError("The benchmark has no remote to pull from. `mybench push` publishes it first.")
    try:
        # Merge, never rebase: rewriting pushed history would strand the other machines.
        return run_git(["pull", "--no-rebase"], cwd=home)
    except MyBenchError as error:
        conflicted = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=home)
        if conflicted:
            files = ", ".join(conflicted.splitlines())
            raise MyBenchError(
                f"Pull stopped on a merge conflict in: {files}. Resolve with git in {home}, then pull again."
            ) from error
        raise


def _secret_values(config: BenchmarkConfig) -> list[bytes]:
    """The values of every credential variable the config can name, native providers included."""
    names = set(NATIVE_PROVIDER_KEYS.values())
    names.update(provider.api_key_env for provider in config.providers.values() if provider.api_key_env)
    return [value.encode("utf-8") for name in sorted(names) if (value := os.environ.get(name))]


def _scrub_secrets(home: Path, secrets: list[bytes]) -> int:
    """Redact every secret occurrence in the not-yet-committed files; returns how many files changed."""
    if not secrets:
        return 0
    scrubbed = 0
    for path in _uncommitted_files(home):
        content = path.read_bytes()
        cleaned = content
        for secret in secrets:
            cleaned = cleaned.replace(secret, REDACTION)
        if cleaned != content:
            path.write_bytes(cleaned)
            scrubbed += 1
    return scrubbed


def _uncommitted_files(home: Path) -> list[Path]:
    output = run_git(["ls-files", "--others", "--modified", "--exclude-standard", "-z"], cwd=home)
    paths = (home / name for name in output.split("\0") if name)
    return [path for path in paths if path.is_file()]


def _origin_url(home: Path) -> str | None:
    try:
        return run_git(["remote", "get-url", "origin"], cwd=home)
    except MyBenchError:
        return None


def _set_origin(home: Path, url: str) -> None:
    if _origin_url(home) is None:
        run_git(["remote", "add", "origin", url], cwd=home)
    else:
        run_git(["remote", "set-url", "origin", url], cwd=home)


def _create_remote(home: Path) -> None:
    """Publish a new private GitHub repository named after the benchmark directory; gh sets origin and pushes."""
    if shutil.which("gh") is None:
        raise MyBenchError(
            "Publishing a new benchmark needs the GitHub CLI. Install gh and sign in with"
            " `gh auth login`, or pass a remote URL that already exists."
        )
    result = subprocess.run(
        ["gh", "repo", "create", home.name, "--private", "--source", str(home), "--push"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr.strip() or result.stdout.strip()) or f"exit code {result.returncode}"
        raise MyBenchError(f"Creating the private GitHub repository failed: {detail}")
