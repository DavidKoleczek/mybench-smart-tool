"""Top level entry point for the MyBench library."""

from datetime import UTC, datetime
from pathlib import Path

from mybench.core import init
from mybench.schemas import Task, TaskResult, TaskRunRecord


def init_benchmark(target: str, path: Path | None = None) -> None:
    return init.init_benchmark(target, path)


def inspire(guidance: str | None = None) -> list[str]:
    return []


def create_task(idea: str | None = None, context: str | None = None) -> Task:
    return Task(id="example-task", name="Example Task", timeout_seconds=900)


def try_task(
    task: str | Path,
    model: str | None = None,
    reevaluate: Path | None = None,
) -> TaskResult:
    return TaskResult(
        path=Path(),
        run=TaskRunRecord(
            task="example-task",
            task_version="1.0.0",
            model="provider/model",
            started=datetime.now(UTC),
            finished=datetime.now(UTC),
            status="success",
            mybench_version="0.0.0",
            harness="opencode 0.0.0",
        ),
    )


def run_benchmark(
    models: list[str] | None = None,
    tasks: list[str] | None = None,
    rerun: bool = False,
) -> list[TaskResult]:
    return []


def push_results(remote: str | None = None) -> None:
    return None


def pull_results() -> None:
    return None


def load_results(models: list[str] | None = None, tasks: list[str] | None = None) -> list[TaskResult]:
    return []


def serve_dashboard(port: int | None = None, host: str = "127.0.0.1") -> str:
    return ""
