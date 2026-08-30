"""Judge evaluations: an agent grades the whole rubric in one session, in the container."""

from datetime import UTC, datetime
from typing import Any

from liquid import render

from mybench.intelligence.interface import Intelligence
from mybench.intelligence.schemas import AgentRequest, ContainerWorkspace
from mybench.schemas import CriterionResult, Grader, JudgeEvaluation, RubricCriterion, ScoreRecord

GRADING_PROMPT = """\
You are grading work another agent produced in the current working directory. \
You may read anything here and run anything you need to verify it.

The agent was given these instructions:

<instructions>
{{ instructions }}
</instructions>

How to grade:

<steps>
{{ steps }}
</steps>

Reference material for grading, if any, is in {{ eval_dir }}.

Grade every criterion of this rubric:
{% for criterion in criteria %}
- {{ criterion.id }}: {{ criterion.description }}
{%- endfor %}

Score each criterion from 0 (not satisfied at all) to 100 (fully satisfied), judging it on its own \
merits, then submit all your scores and reasoning through the submit tool, exactly once."""


def grade_judge_evaluation(
    intelligence: Intelligence,
    grading_model: str,
    task_instructions: str,
    evaluation: JudgeEvaluation,
    workspace: ContainerWorkspace,
    eval_dir: str,
    timeout_seconds: int,
) -> ScoreRecord:
    """Grade the rubric in one session and fold the criterion scores into one score record.

    Every criterion is scored 0 to 100 and weighted into the evaluation's score; a grader
    that fails to submit makes the record a null score carrying the failure.
    """
    prompt = render(
        GRADING_PROMPT,
        instructions=task_instructions,
        steps=evaluation.steps.strip(),
        eval_dir=eval_dir,
        criteria=[
            {"id": criterion_id, "description": criterion.description}
            for criterion_id, criterion in evaluation.rubric.items()
        ],
    )
    result = intelligence.run(
        AgentRequest(
            prompt=prompt,
            model=grading_model,
            workspace=workspace,
            output_schema=_rubric_schema(evaluation.rubric),
            timeout_seconds=timeout_seconds,
        )
    )
    grader = Grader(model=grading_model, implementation=intelligence.implementation)
    graded = datetime.now(UTC).replace(microsecond=0)
    if result.output is None:
        return ScoreRecord(
            score=None,
            graded=graded,
            grader=grader,
            details={"error": result.error or "the grader produced no submission"},
        )
    criteria = {
        criterion_id: CriterionResult(
            score=float(result.output[criterion_id]["score"]),
            weight=criterion.weight,
            reasoning=str(result.output[criterion_id]["reasoning"]),
        )
        for criterion_id, criterion in evaluation.rubric.items()
    }
    total_weight = sum(criterion.weight for criterion in criteria.values())
    score = (
        sum(criterion.score * criterion.weight for criterion in criteria.values()) / total_weight
        if total_weight
        else None
    )
    report = "\n\n".join(f"## {criterion_id}\n{criterion.reasoning}" for criterion_id, criterion in criteria.items())
    return ScoreRecord(score=score, graded=graded, grader=grader, criteria=criteria, report=report)


def _rubric_schema(rubric: dict[str, RubricCriterion]) -> dict[str, Any]:
    """The submit tool's schema, generated from the rubric so only the declared criteria are accepted."""
    return {
        "type": "object",
        "properties": {
            criterion_id: {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": f"How fully the work satisfies '{criterion_id}', 0 to 100",
                    },
                    "reasoning": {"type": "string", "minLength": 1, "description": "What you observed, citing files"},
                },
                "required": ["score", "reasoning"],
                "additionalProperties": False,
            }
            for criterion_id in rubric
        },
        "required": list(rubric),
        "additionalProperties": False,
    }
