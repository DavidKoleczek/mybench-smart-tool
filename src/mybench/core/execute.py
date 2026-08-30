"""Try: run one task against one model, or rerun evaluations over an earlier try."""

from datetime import UTC, datetime
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil

from mybench.core import benchmark
from mybench.harness import opencode
from mybench.harness.execution import ExecResult, HarnessSession, docker_client, ensure_image
from mybench.schemas import (
    BenchmarkConfig,
    MyBenchError,
    ScoreRecord,
    ScriptEvaluation,
    Task,
    TaskResult,
    TaskRunRecord,
    TaskRunStatus,
    Usage,
)
from mybench.settings import benchmark_home

# Native harness providers read their key from the conventional variable; custom
# providers name theirs with api_key_env in config.yaml.
NATIVE_PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_GENERATIVE_AI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# Room beyond the in-container GNU timeout for image checks, exports, and evals,
# since the Docker client's timeout bounds every blocking API call.
CLIENT_TIMEOUT_MARGIN_SECONDS = 300


def try_task(task: str | Path, model: str | None = None, reevaluate: Path | None = None) -> TaskResult:
    home = benchmark_home()
    config = benchmark.load_config(home)
    task_dir = benchmark.resolve_task(task, home)
    task_def = benchmark.load_task(task_dir)
    if reevaluate is not None:
        return reevaluate_try(task_def, task_dir, reevaluate.expanduser().resolve())
    chosen = benchmark.resolve_model(config, model)
    run_dir = benchmark.new_run_dir(home / "tries", task_def.id, chosen)
    return execute_task(task_def, task_dir, chosen, config, run_dir)


def execute_task(task: Task, task_dir: Path, model: str, config: BenchmarkConfig, run_dir: Path) -> TaskResult:
    """The single-run engine: container up, setup, model session, transcript, evaluations, record last.

    A failing model session is data (`status` in the record), never an exception; only missing
    prerequisites, checked before anything costly, raise.
    """
    instructions = benchmark.read_instructions(task_dir)
    env = provider_env(model, config)
    client = docker_client(timeout_seconds=task.timeout_seconds + CLIENT_TIMEOUT_MARGIN_SECONDS)
    image = ensure_image(client)
    workspace = run_dir / "workspace"
    input_dir = task_dir / "input"
    if input_dir.is_dir():
        shutil.copytree(input_dir, workspace, dirs_exist_ok=True)
    opencode_config = opencode.render_config(model, config.providers)
    started = _now()
    status: TaskRunStatus = "success"
    session_id = None
    usage = Usage()
    with HarnessSession(client, image, workspace, run_dir / "evals", opencode_config, env) as session:
        provider = config.providers.get(model.partition("/")[0])
        if provider is not None and provider.base_url is not None:
            probe = session.check_endpoint(provider.base_url)
            if probe.error is not None:
                raise MyBenchError(f"{provider.base_url} is not reachable from the container: {probe.error}")
            model_id = model.partition("/")[2]
            if probe.served_models and model_id not in probe.served_models:
                raise MyBenchError(
                    f"{provider.base_url} does not serve '{model_id}'; it serves: {', '.join(probe.served_models)}."
                )
        harness = session.harness_version()
        setup_failure = session.run_setup(task.setup)
        if setup_failure is not None:
            status = "error"
            _write_harness_log(run_dir, setup_failure)
        else:
            result = session.run_model(instructions, model, task.timeout_seconds)
            _write_harness_log(run_dir, result)
            if result.exit_code in opencode.TIMEOUT_EXIT_CODES:
                status = "timeout"
            elif result.exit_code != 0:
                status = "error"
            transcript = session.export_transcript()
            if transcript is not None:
                (run_dir / "transcript.json").write_text(
                    json.dumps(transcript, indent=2), encoding="utf-8", newline="\n"
                )
                summary = opencode.parse_transcript(transcript)
                session_id = summary.session_id or None
                usage = summary.usage
            if status == "success":
                run_evaluations(session, task, task_dir, run_dir)
    record = TaskRunRecord(
        task=task.id,
        task_version=task.version,
        model=model,
        started=started,
        finished=_now(),
        status=status,
        mybench_version=version("mybench"),
        harness=harness,
        session_id=session_id,
        usage=usage,
    )
    benchmark.write_run_record(run_dir, record)
    return benchmark.read_task_result(run_dir)


def reevaluate_try(task: Task, task_dir: Path, try_dir: Path) -> TaskResult:
    """Rerun the task's current evaluations against an earlier try's workspace.

    Only evals/ is replaced; the run record, transcript, and workspace stay the same.
    """
    previous = benchmark.read_task_result(try_dir)
    if previous.run.task != task.id:
        raise MyBenchError(f"{try_dir} is a try of task '{previous.run.task}', not '{task.id}'.")
    workspace = try_dir / "workspace"
    if not workspace.is_dir():
        raise MyBenchError(f"{try_dir} has no workspace to evaluate.")
    client = docker_client(timeout_seconds=task.timeout_seconds + CLIENT_TIMEOUT_MARGIN_SECONDS)
    image = ensure_image(client)
    evals_dir = try_dir / "evals"
    if evals_dir.exists():
        shutil.rmtree(evals_dir)
    evals_dir.mkdir()
    with HarnessSession(client, image, workspace, evals_dir, None, {}) as session:
        run_evaluations(session, task, task_dir, try_dir)
    return benchmark.read_task_result(try_dir)


def run_evaluations(session: HarnessSession, task: Task, task_dir: Path, run_dir: Path) -> None:
    """Stage and run each evaluation in task.yaml order; a failure becomes a null score, never an exception."""
    for evaluation in task.evaluations:
        eval_dir = run_dir / "evals" / evaluation.id
        source = task_dir / "evals" / evaluation.id
        if source.is_dir():
            shutil.copytree(source, eval_dir, dirs_exist_ok=True)
        else:
            eval_dir.mkdir(parents=True, exist_ok=True)
        benchmark.snapshot_evaluation(eval_dir, evaluation)
        if not isinstance(evaluation, ScriptEvaluation):
            continue
        result = session.run_eval(evaluation.command, evaluation.id, task.timeout_seconds)
        _collect_score(eval_dir, result)


def provider_env(model: str, config: BenchmarkConfig) -> dict[str, str]:
    """The credential variables the model's provider needs in the container; empty for keyless endpoints."""
    provider_id = model.partition("/")[0]
    provider = config.providers.get(provider_id)
    key_env = provider.api_key_env if provider is not None else NATIVE_PROVIDER_KEYS.get(provider_id)
    if key_env is None:
        return {}
    value = os.environ.get(key_env)
    if not value:
        raise MyBenchError(f"Model '{model}' needs the environment variable {key_env}, which is not set.")
    return {key_env: value}


def _collect_score(eval_dir: Path, result: ExecResult) -> None:
    """Validate the score the evaluation wrote, or record the failure as a null score with the evidence."""
    score_path = eval_dir / "score.json"
    if result.exit_code != 0:
        _write_error_score(score_path, f"evaluation command exited {result.exit_code}", result)
        return
    if not score_path.is_file():
        _write_error_score(score_path, "evaluation wrote no score.json", result)
        return
    content = score_path.read_text(encoding="utf-8")
    try:
        ScoreRecord.model_validate_json(content)
    except ValueError:
        _write_error_score(score_path, f"evaluation wrote an invalid score.json: {content}", result)


def _write_error_score(score_path: Path, reason: str, result: ExecResult) -> None:
    record = ScoreRecord(
        score=None, graded=_now(), details={"error": reason, "stdout": result.stdout, "stderr": result.stderr}
    )
    score_path.write_text(record.model_dump_json(indent=2, exclude_none=True), encoding="utf-8", newline="\n")


def _write_harness_log(run_dir: Path, result: ExecResult) -> None:
    (run_dir / "harness.log").write_text(
        f"$ {result.command}\nexit code: {result.exit_code}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}\n",
        encoding="utf-8",
        newline="\n",
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)
