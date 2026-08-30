"""Reading and writing the benchmark repository: config, tasks, and run directories."""

from datetime import UTC, datetime
from pathlib import Path
import re

from pydantic import TypeAdapter, ValidationError
import yaml

from mybench.core.init import CONFIG_FILENAME
from mybench.schemas import (
    SLUG_PATTERN,
    BenchmarkConfig,
    Evaluation,
    EvaluationResult,
    MyBenchError,
    ScoreRecord,
    Task,
    TaskResult,
    TaskRunRecord,
)

EVALUATION_ADAPTER: TypeAdapter[Evaluation] = TypeAdapter(Evaluation)


def load_config(benchmark: Path) -> BenchmarkConfig:
    path = benchmark / CONFIG_FILENAME
    if not path.is_file():
        raise MyBenchError(
            f"{benchmark} is not a benchmark: it has no {CONFIG_FILENAME}. Run `mybench init <path>` to point MyBench at one."
        )
    try:
        return BenchmarkConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except (yaml.YAMLError, ValidationError) as error:
        raise MyBenchError(f"{path} is not a valid benchmark config: {error}") from error


def resolve_model(config: BenchmarkConfig, model: str | None) -> str:
    """The model to run: the argument when given, otherwise the config's first."""
    chosen = model if model is not None else next(iter(config.models), None)
    if chosen is None:
        raise MyBenchError("No model to run: pass one explicitly, or add one to config.yaml under `models`.")
    if "/" not in chosen:
        raise MyBenchError(f"'{chosen}' is not a model name; the harness expects `<provider>/<model>`.")
    return chosen


def resolve_task(task: str | Path, benchmark: Path) -> Path:
    """The task's directory: a `Path` is always a path, a `str` is an id when it is a lowercase slug."""
    if isinstance(task, str) and re.match(SLUG_PATTERN, task):
        task_dir = benchmark / "tasks" / task
        if not task_dir.is_dir():
            raise MyBenchError(
                f"No task '{task}' under {benchmark / 'tasks'}. To try a directory named like an id, write it with a separator, like ./{task}."
            )
        return task_dir
    task_dir = Path(task).expanduser().resolve()
    if not task_dir.is_dir():
        raise MyBenchError(f"{task_dir} is not a directory.")
    return task_dir


def load_task(task_dir: Path) -> Task:
    """task.yaml with the directory name as the id."""
    path = task_dir / "task.yaml"
    if not path.is_file():
        raise MyBenchError(f"{task_dir} is not a task: it has no task.yaml.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return Task.model_validate({"id": task_dir.name, **data})
    except (yaml.YAMLError, ValidationError) as error:
        raise MyBenchError(f"{path} is not a valid task definition: {error}") from error


def list_tasks(benchmark: Path) -> list[Path]:
    """The benchmark's task directories, sorted by id; only directories holding a task.yaml count."""
    tasks_dir = benchmark / "tasks"
    if not tasks_dir.is_dir():
        return []
    return sorted(path for path in tasks_dir.iterdir() if (path / "task.yaml").is_file())


def has_success_run(benchmark: Path, task: Task, model: str) -> bool:
    """Whether runs/ holds a successful run of this task's current major version by this model.

    Only success counts (a failed run never blocks a retry), and crashed or unreadable
    run directories are passed over rather than trusted.
    """
    parent = benchmark / "runs" / task.id / model_slug(model)
    if not parent.is_dir():
        return False
    major = task.version.partition(".")[0]
    for run_dir in parent.iterdir():
        record_path = run_dir / "run.yaml"
        if not record_path.is_file():
            continue
        try:
            record = TaskRunRecord.model_validate(yaml.safe_load(record_path.read_text(encoding="utf-8")))
        except (yaml.YAMLError, ValidationError):
            continue
        if record.model == model and record.status == "success" and record.task_version.partition(".")[0] == major:
            return True
    return False


def read_instructions(task_dir: Path) -> str:
    path = task_dir / "instructions.md"
    if not path.is_file():
        raise MyBenchError(f"{task_dir} has no instructions.md, so there is nothing to give the model.")
    return path.read_text(encoding="utf-8").strip()


def model_slug(model: str) -> str:
    """The model name made filesystem safe; the exact string lives in run.yaml."""
    return re.sub(r"[^a-z0-9._-]+", "-", model.lower())


def new_run_dir(base: Path, task_id: str, model: str) -> Path:
    """Create `<base>/<task-id>/<model-slug>/<timestamp>/` with workspace/ and evals/ inside.

    Same-second collisions get a `-2`, `-3` suffix, so every run keeps its own directory.
    """
    parent = base / task_id / model_slug(model)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = parent / timestamp
    suffix = 2
    while run_dir.exists():
        run_dir = parent / f"{timestamp}-{suffix}"
        suffix += 1
    (run_dir / "workspace").mkdir(parents=True)
    (run_dir / "evals").mkdir()
    return run_dir


def write_run_record(run_dir: Path, record: TaskRunRecord) -> None:
    """run.yaml is the engine's last write: its presence marks the run directory complete."""
    data = record.model_dump(mode="json", exclude_none=True)
    (run_dir / "run.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")


def snapshot_evaluation(eval_dir: Path, evaluation: Evaluation) -> None:
    """evaluation.yaml: the definition that produced the score, so a stale grade is detectable."""
    data = evaluation.model_dump(mode="json", exclude_none=True)
    (eval_dir / "evaluation.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")


def read_task_result(run_dir: Path) -> TaskResult:
    """Load a completed run directory; a directory without run.yaml is a crashed run."""
    record_path = run_dir / "run.yaml"
    if not record_path.is_file():
        raise MyBenchError(f"{run_dir} is not a completed run: it has no run.yaml.")
    try:
        record = TaskRunRecord.model_validate(yaml.safe_load(record_path.read_text(encoding="utf-8")))
    except (yaml.YAMLError, ValidationError) as error:
        raise MyBenchError(f"{record_path} is not a valid run record: {error}") from error
    results = []
    evals_dir = run_dir / "evals"
    if evals_dir.is_dir():
        for eval_dir in sorted(path for path in evals_dir.iterdir() if path.is_dir()):
            definition_path = eval_dir / "evaluation.yaml"
            if not definition_path.is_file():
                continue
            evaluation = EVALUATION_ADAPTER.validate_python(yaml.safe_load(definition_path.read_text(encoding="utf-8")))
            score = None
            score_path = eval_dir / "score.json"
            if score_path.is_file():
                score = ScoreRecord.model_validate_json(score_path.read_text(encoding="utf-8"))
            results.append(EvaluationResult(evaluation=evaluation, score=score))
    return TaskResult(path=run_dir, run=record, evaluation_results=results)
