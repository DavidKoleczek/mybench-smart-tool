"""Read Results: every completed run under runs/, the tree the dashboard is built on."""

from mybench.core import benchmark
from mybench.schemas import TaskResult
from mybench.settings import benchmark_home


def load_results(models: list[str] | None = None, tasks: list[str] | None = None) -> list[TaskResult]:
    """Load the stored results in task, model, then chronological order.

    A run directory without run.yaml is a crashed run and is skipped. Filters only narrow,
    against what is on disk rather than the config: `tasks` by task id, `models` by the
    exact model string in run.yaml.
    """
    home = benchmark_home()
    runs_dir = home / "runs"
    if not runs_dir.is_dir():
        return []
    # Directory names are lossy slugs, so they only pre-filter; the recorded model string decides.
    slugs = {benchmark.model_slug(model) for model in models} if models else None
    results: list[TaskResult] = []
    for task_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        if tasks and task_dir.name not in tasks:
            continue
        for model_dir in sorted(path for path in task_dir.iterdir() if path.is_dir()):
            if slugs is not None and model_dir.name not in slugs:
                continue
            for run_dir in sorted(path for path in model_dir.iterdir() if path.is_dir()):
                if not (run_dir / "run.yaml").is_file():
                    continue
                result = benchmark.read_task_result(run_dir)
                if models and result.run.model not in models:
                    continue
                results.append(result)
    return results
