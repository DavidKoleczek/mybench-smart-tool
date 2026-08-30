"""Init: create, register, or clone a benchmark, and record where it lives."""

from pathlib import Path
import re

import yaml

from mybench.core.git import run_git
from mybench.schemas import BenchmarkConfig, MyBenchError
from mybench.settings import UserSettings, save_user_settings

CONFIG_FILENAME = "config.yaml"

GIT_URL_PREFIXES = ("https://", "http://", "ssh://", "git://", "file://", "git@")
GITHUB_SHORTHAND = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def init_benchmark(target: str, path: Path | None = None) -> None:
    """Point MyBench at a benchmark, cloning or scaffolding one when needed."""
    url = git_url(target)
    if url is None:
        if path is not None:
            raise MyBenchError(f"'{target}' is a local path, so it is the destination already; drop the path argument.")
        benchmark = register(Path(target).expanduser().resolve())
    else:
        benchmark = clone(url, path)
    save_user_settings(UserSettings(benchmark_path=benchmark))


def git_url(target: str) -> str | None:
    """The URL to clone `target` from, or None when it names a local path."""
    if target.startswith(GIT_URL_PREFIXES) or target.endswith(".git"):
        return target
    if GITHUB_SHORTHAND.match(target) and not Path(target).exists():
        return f"https://github.com/{target}"
    return None


def clone(url: str, path: Path | None) -> Path:
    """Clone a benchmark and return where it landed."""
    destination = (path or Path.cwd() / repo_name(url)).expanduser().resolve()
    require_empty(destination, "Choose a destination that is empty or does not exist yet.")
    run_git(["clone", url, str(destination)])
    if not (destination / CONFIG_FILENAME).is_file():
        raise MyBenchError(
            f"{url} is not a benchmark: the clone at {destination} has no {CONFIG_FILENAME}. Delete it and clone the repository holding your benchmark."
        )
    return destination


def repo_name(url: str) -> str:
    """The repository name a clone of `url` would be given."""
    tail = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    return tail.removesuffix(".git")


def register(path: Path) -> Path:
    """Register the benchmark at `path`, scaffolding a new one when none is there."""
    if (path / CONFIG_FILENAME).is_file():
        return path
    scaffold(path)
    return path


def scaffold(path: Path) -> Path:
    """Write a new benchmark at `path` and commit it."""
    require_empty(
        path, f"Choose an empty or new directory, or point at a benchmark that already has {CONFIG_FILENAME}."
    )
    (path / "tasks").mkdir(parents=True, exist_ok=True)
    (path / "runs").mkdir(parents=True, exist_ok=True)
    (path / "tasks" / ".gitkeep").touch()
    (path / "runs" / ".gitkeep").touch()
    config = yaml.safe_dump(BenchmarkConfig().model_dump(exclude_none=True), sort_keys=False)
    (path / CONFIG_FILENAME).write_text(config, encoding="utf-8", newline="\n")
    (path / ".gitignore").write_text("tries/\n", encoding="utf-8", newline="\n")
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["add", "-A"], cwd=path)
    run_git(["commit", "-m", "Create benchmark"], cwd=path)
    return path


def require_empty(path: Path, fix: str) -> None:
    """Refuse a destination that already holds something, so nothing unrelated is swept in."""
    if not path.exists():
        return
    if not path.is_dir():
        raise MyBenchError(f"{path} is a file. {fix}")
    if any(path.iterdir()):
        raise MyBenchError(f"{path} is not empty. {fix}")
