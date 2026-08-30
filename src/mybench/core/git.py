"""The git CLI, which carries the user's own credentials and identity."""

from pathlib import Path
import subprocess

from mybench.schemas import MyBenchError


def run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return its stdout."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise MyBenchError("git was not found on PATH. It is a required dependency.") from error
    if result.returncode != 0:
        detail = (result.stderr.strip() or result.stdout.strip()) or f"exit code {result.returncode}"
        raise MyBenchError(f"`git {' '.join(args)}` failed: {detail}")
    return result.stdout.strip()
