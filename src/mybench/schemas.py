from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

RESULTS_FORMAT_VERSION = 1

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class MyBenchError(Exception):
    """Raised for any failure the library can name and explain how to fix."""


# region: Task Definition


class RubricCriterion(BaseModel):
    points: int = Field(gt=0)
    description: str


class ScriptEvaluation(BaseModel):
    id: str
    kind: Literal["script"] = "script"
    weight: float = Field(default=1.0, ge=0)
    command: str


class JudgeEvaluation(BaseModel):
    id: str
    kind: Literal["judge"] = "judge"
    weight: float = Field(default=1.0, ge=0)
    steps: str
    rubric: dict[str, RubricCriterion] = Field(min_length=1)


class ManualEvaluation(BaseModel):
    id: str
    kind: Literal["manual"] = "manual"
    weight: float = Field(default=1.0, ge=0)
    guidance: str = Field(description="Instructions for the human grader")


type Evaluation = Annotated[ScriptEvaluation | JudgeEvaluation | ManualEvaluation, Field(discriminator="kind")]


class Task(BaseModel):
    """A task definition: `id` is the directory name under tasks/, the rest is task.yaml."""

    id: str = Field(pattern=SLUG_PATTERN)
    name: str
    version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    tags: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(gt=0)
    setup: list[str] = Field(
        default_factory=list,
        description="Shell commands run in order in the container working directory, after input/ is copied and before the model starts. A failure records an error status for the run and the model never starts.",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="Any deliverables that should be highlighted (including as missing). Enumerated as relative paths from where the task's working directory is.",
    )
    evaluations: list[Evaluation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_evaluation_ids(self) -> Self:
        ids = [evaluation.id for evaluation in self.evaluations]
        duplicates = sorted({eval_id for eval_id in ids if ids.count(eval_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate evaluation ids: {duplicates}")
        return self


# endregion


# region: Task Runs and Results


class BenchmarkConfig(BaseModel):
    """config.yaml at the benchmark root; describes the benchmark, never the machine."""

    models: list[str] = Field(default_factory=list)
    grading_model: str | None = None


type TaskRunStatus = Literal["success", "error", "timeout"]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


class TaskRunRecord(BaseModel):
    """One execution of one task by one model: run.yaml, whose presence marks the run directory complete."""

    task: str = Field(pattern=SLUG_PATTERN)
    task_version: str = Field(pattern=SEMVER_PATTERN)
    model: str
    started: datetime
    finished: datetime
    status: TaskRunStatus
    mybench_version: str
    harness: str
    session_id: str | None = None
    usage: Usage = Field(default_factory=Usage)
    format: int = RESULTS_FORMAT_VERSION


class Grader(BaseModel):
    model: str
    implementation: str


class CriterionResult(BaseModel):
    awarded: int = Field(ge=0)
    points: int = Field(gt=0)

    @model_validator(mode="after")
    def _awarded_within_points(self) -> Self:
        if self.awarded > self.points:
            raise ValueError(f"awarded {self.awarded} exceeds points {self.points}")
        return self


class ScoreRecord(BaseModel):
    """score.json written by one evaluation; `score` is None when the evaluation errored.

    `grader`, `criteria`, and `report` are present only for judge evaluations.
    """

    score: float | None = Field(ge=0, le=100)
    graded: datetime
    grader: Grader | None = None
    criteria: dict[str, CriterionResult] | None = None
    report: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """One evals/<eval-id>/ directory in a run: the evaluation.yaml snapshot and its score.json.

    `score` is None until score.json exists, which for a manual evaluation is after the run.
    """

    evaluation: Evaluation
    score: ScoreRecord | None = None


class TaskResult(BaseModel):
    """One run directory: runs/<task-id>/<model-slug>/<timestamp>/."""

    path: Path
    run: TaskRunRecord
    evaluation_results: list[EvaluationResult] = Field(default_factory=list)

    @property
    def score(self) -> float | None:
        """Weighted mean of evaluation scores, 0 to 100, or None while nothing is scored."""
        scored = [
            (result.evaluation.weight, result.score.score)
            for result in self.evaluation_results
            if result.score is not None and result.score.score is not None
        ]
        total_weight = sum(weight for weight, _ in scored)
        if total_weight == 0:
            return None
        return sum(weight * score for weight, score in scored) / total_weight


# endregion
