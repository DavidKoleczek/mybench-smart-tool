"""Run: the configured models against the tasks on disk, appending to runs/."""

from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from mybench.core import benchmark, execute
from mybench.harness.execution import docker_client, ensure_image
from mybench.schemas import BenchmarkConfig, MyBenchError, Task, TaskResult
from mybench.settings import benchmark_home


class PairOutcome(BaseModel):
    """One pair of task and model in a run: skipped, executed, or failed before recording."""

    task: str
    model: str
    skipped: bool = False
    result: TaskResult | None = None
    error: str | None = None


def run_benchmark(
    models: list[str] | None = None, tasks: list[str] | None = None, rerun: bool = False
) -> list[TaskResult]:
    return [outcome.result for outcome in run_pairs(models, tasks, rerun) if outcome.result is not None]


def run_pairs(
    models: list[str] | None = None, tasks: list[str] | None = None, rerun: bool = False
) -> Iterator[PairOutcome]:
    """Execute the selected matrix pair by pair, yielding each pair's outcome as it lands.

    Prerequisites for every pair, credentials included, are checked before the first
    one runs; a pair failing mid-run is reported in its outcome and the run continues.
    """
    home = benchmark_home()
    config = benchmark.load_config(home)
    chosen_models = _select_models(config, models)
    selected = _select_tasks(home, tasks)
    for model in chosen_models:
        execute.provider_env(model, config)
    for _, task in selected:
        execute.grading_setup(task, config)
    ensure_image(docker_client())
    for task_dir, task in selected:
        for model in chosen_models:
            if not rerun and benchmark.has_success_run(home, task, model):
                yield PairOutcome(task=task.id, model=model, skipped=True)
                continue
            run_dir = benchmark.new_run_dir(home / "runs", task.id, model)
            try:
                result = execute.execute_task(task, task_dir, model, config, run_dir)
            except MyBenchError as error:
                yield PairOutcome(task=task.id, model=model, error=str(error))
                continue
            yield PairOutcome(task=task.id, model=model, result=result)


def _select_models(config: BenchmarkConfig, models: list[str] | None) -> list[str]:
    """The config's models, narrowed by the filter; a filter cannot add what the config does not declare."""
    if not config.models:
        raise MyBenchError("config.yaml declares no models under `models`, so there is nothing to run.")
    if models is None:
        return list(config.models)
    unknown = sorted(set(models) - set(config.models))
    if unknown:
        raise MyBenchError(
            f"Not declared in config.yaml under `models`: {', '.join(unknown)}. Run only executes declared models."
        )
    return [model for model in config.models if model in models]


def _select_tasks(home: Path, tasks: list[str] | None) -> list[tuple[Path, Task]]:
    """The tasks on disk, narrowed by the filter and loaded up front so a bad task fails before anything runs."""
    task_dirs = benchmark.list_tasks(home)
    if tasks is not None:
        known = {path.name for path in task_dirs}
        unknown = sorted(set(tasks) - known)
        if unknown:
            raise MyBenchError(f"No tasks under {home / 'tasks'} named: {', '.join(unknown)}.")
        task_dirs = [path for path in task_dirs if path.name in set(tasks)]
    if not task_dirs:
        raise MyBenchError(f"No tasks under {home / 'tasks'}; add one before running.")
    return [(path, benchmark.load_task(path)) for path in task_dirs]
