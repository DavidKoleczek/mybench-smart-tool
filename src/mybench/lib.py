"""Top level entry point for the MyBench library."""

from pathlib import Path

from mybench.core import execute, init
from mybench.schemas import Task, TaskResult


def init_benchmark(target: str, path: Path | None = None) -> None:
    """Point MyBench at a benchmark, recording where it lives so every other capability finds it.

    Args:
        target: What to point at.
            A git URL or GitHub `<org>/<repo>` is cloned, a path to an existing benchmark is used as is, and any other path gets a new benchmark.
        path: Where to put a clone. Defaults to the repository's name in the current directory. Only used when cloning.
    """
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
    """Run one task against one model, writing to a try directory.

    Args:
        task: A task id, resolved under the benchmark's `tasks/`, or a path to a task directory anywhere on disk.
            A `Path` is always a path; a `str` is an id, and is read as a path only when it is not a valid id.
        model: Any valid model in the harness's naming
        reevaluate: A previous try's directory.
            The model run is skipped and the task's current evaluations run against that try's workspace.
    """
    return execute.try_task(task, model, reevaluate)


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
