from pathlib import Path

import pytest

from mybench.core.git import run_git
from mybench.lib import init_benchmark
from mybench.settings import load_user_settings


def test_init_benchmark_scaffolds_a_committed_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirect the settings directory on both platform layouts, and give git an identity of its own,
    # so the test neither reads nor writes anything belonging to the machine it runs on.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "config"))
    monkeypatch.setenv("GIT_AUTHOR_NAME", "MyBench Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "MyBench Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
    benchmark = tmp_path / "benchmark"

    init_benchmark(str(benchmark))

    assert (benchmark / "config.yaml").read_text(encoding="utf-8") == "models: []\n"
    assert (benchmark / ".gitignore").read_text(encoding="utf-8") == "tries/\n"
    assert (benchmark / "tasks" / ".gitkeep").is_file()
    assert (benchmark / "runs" / ".gitkeep").is_file()
    assert run_git(["rev-parse", "--is-inside-work-tree"], cwd=benchmark) == "true"
    assert run_git(["status", "--porcelain"], cwd=benchmark) == ""

    settings = load_user_settings()
    assert settings is not None
    assert settings.benchmark_path == benchmark
