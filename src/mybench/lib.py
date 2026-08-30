"""Top level entry point for the MyBench library."""

from pathlib import Path

from mybench.core import execute, init, results, run, sync
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
    """Run the benchmark, writing to the results: the configured models against the tasks on disk.

    Pairs that already have a successful result for the task's current major version are skipped,
    so a bare call executes exactly what is new. Each pair succeeds or fails on its own; the
    returned results carry each recorded run's status.

    Args:
        models: Model names as the config file declares them; filters the matrix for this invocation.
        tasks: Task ids; filters the matrix for this invocation.
        rerun: Execute the selected pairs even where results exist, appending to the run history.
    """
    return run.run_benchmark(models, tasks, rerun)


def push_results(remote: str | None = None) -> None:
    """Push the benchmark repository, tasks and results together, to its git remote.

    Configured API key values are scrubbed from new files before anything is committed.
    When no remote exists and none is given, a private GitHub repository is created through the signed-in GitHub CLI and pushed to.

    Args:
        remote: A git remote URL; remembered once set, and already set when the benchmark was cloned.
    """
    sync.push_results(remote)


def pull_results() -> None:
    """Update the benchmark from its remote: a fetch and merge bringing down new tasks, results, and config.

    A merge conflict stops the pull and names the conflicted files, left to be resolved with ordinary git tools in the benchmark repository.
    """
    sync.pull_results()


def load_results(models: list[str] | None = None, tasks: list[str] | None = None) -> list[TaskResult]:
    """Load the stored results: every completed run under the benchmark's runs/.

    Crashed run directories are ignored and tries never appear.
    Results come back ordered by task, then model, then chronologically.

    Args:
        models: Exact model strings as run.yaml records them; filters the results.
        tasks: Task ids; filters the results.
    """
    return results.load_results(models, tasks)


def serve_dashboard(port: int | None = None, host: str = "127.0.0.1") -> str:
    return ""
