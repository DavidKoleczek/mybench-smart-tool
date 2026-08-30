# Task Format

The definition of a task. 
Written by [Create](02-library.md#create), read by [Run](02-library.md#run).

## Location

The benchmark is one git repository, created by [Init](02-library.md#init):

```
<benchmark>/
├── config.yaml
├── tasks/
│   └── <task-id>/
└── runs/
```

`config.yaml` is the [config file](05-configuration.md) and `runs/` holds the [results](04-results-format.md). 
Tasks live under `tasks/`, one directory per task. 
The directory name is the task id: a lowercase slug, stable for the life of the task.

## Task Layout

```
tasks/<task-id>/
├── task.yaml
├── instructions.md
├── input/
└── evals/
    └── <eval-id>/
```

`instructions.md` is the prompt, given to the model verbatim. 
`input/` is optional material copied into the container working directory before the model starts, such as a photo, a screenshot, or a document set. 
`evals/<eval-id>/` holds what one evaluation needs: check scripts, answer keys, reference outputs. 
Its content is absent from the container until the model's session ends so the model can never see an answer key.

## task.yaml

```yaml
name: Where Was This Taken
version: 1.2.0
tags: [vision, instruction-following]
timeout_seconds: 900
setup:
  - unzip -q photos.zip
artifacts:
  - answer.json
evaluations:
  - id: check-answer
    kind: script
    command: uv run "$MYBENCH_EVAL_DIR/check.py"
```

- `name`: display name.
- `version`: semantic version; see [Versioning](#versioning).
- `tags`: optional labels for filtering and the dashboard.
- `timeout_seconds`: hard limit on the model's run; hitting it records a timeout in the [task run record](04-results-format.md#task-run-record), not a score.
- `setup`: optional shell commands, run in order in the working directory after `input/` is copied in and before the model starts. A failing command records an `error` in the [task run record](04-results-format.md#task-run-record) and the model never starts.
- `artifacts`: working directory paths that are the deliverables, like a built game or a finished SVG. The whole working directory is captured either way; these tell the dashboard what to surface.
- `evaluations`: zero or more. A task with none is still run and captured, for work you only want to look at.

## Evaluations

Evaluations run inside the same container as the task, after the model's session has ended. 
Nothing is pulled out of the container to be evaluated: an evaluation sees the exact filesystem state the model left behind, so it can parse, diff, build, or execute the work in place. 
For each evaluation, MyBench stages the task's `evals/<eval-id>/` directory into the container, absent until now so the model could not see it, and sets the environment variable `MYBENCH_EVAL_DIR` to its path. 
The evaluation runs with the model's working directory as cwd and writes `score.json`, a [score record](04-results-format.md#score-records), into `MYBENCH_EVAL_DIR`. 
That directory is bind mounted from the host, so the score and anything else the evaluation writes land directly in the [run directory](04-results-format.md#run-directory-layout). 
Because the staging target is the run directory, the evaluation's input material is captured next to its score, so a stored result stays interpretable even after the task's evaluations change.

Scores are floats from 0 to 100. 
A task's score is the weighted mean of its evaluation scores; `weight` defaults to 1.

Every evaluation has an `id` unique within the task, a `kind`, and an optional `weight`. 
The remaining fields depend on the kind.

### script

`command` is the evaluation: a shell command run in the container under the sequence above. 
A nonzero exit records an evaluation error instead of a score.

```yaml
- id: detector
  kind: script
  command: uv run "$MYBENCH_EVAL_DIR/detect.py"
```

The container provides `uv` and a pre-installed Python interpreter, so Python check scripts are invoked with `uv run`, declare any dependencies inline, and need no network to start.

Use it for anything checkable without a model: parsing a structured answer the instructions told the model to write to a file, checking against labels in the eval directory, or diffing a scaffolded project against a reference one.

### judge

LLM as judge. 
The grader is an agent that follows `steps`, inspects the working directory and the eval directory, and fills in the `rubric`: named criteria, each with integer points and a description.

```yaml
- id: blog-quality
  kind: judge
  steps: |
    Read the post the model wrote in the working directory.
    Compare it against the reference posts in the eval directory.
  rubric:
    voice: {points: 10, description: Reads like the reference posts, not like a press release}
    structure: {points: 5, description: Has a point and gets to it}
```

The grader is held to the rubric by deterministic code. 
MyBench computes the score as points awarded over points possible, normalized to 0 to 100, so the points do not need to sum to 100.
It submits its scores through a tool whose schema is generated from the rubric, so only the declared criteria are accepted and each award must be an integer between zero and that criterion's points; an invalid submission is sent back for the grader to take another turn to retry.

The grading model is declared in the [config file](05-configuration.md), separate from the models under test, and recorded in the [score record](04-results-format.md#score-records). 
The grader runs in the container through the same swappable intelligence interface as the rest of the [library](02-library.md), currently the GitHub Copilot SDK. 
Only the score record is part of the format, so the grader implementation can change, or become more agentic, without invalidating any stored result.

### manual

Scored by a human. 
The run captures everything; the score is entered from the dashboard afterwards, guided by `guidance`.

```yaml
- id: playtest
  kind: manual
  guidance: |
    Play the build from artifacts. Knockback should feel like a fighting game.
```

## Versioning

Every task carries a semantic version, starting at `1.0.0`. 
The component bumped tells a consumer of existing results what they are still worth:

- Major: the work itself changed (instructions, input material, environment). Existing results are not comparable; [Run](02-library.md#run) treats the task as new.
  - `1.4.2 -> 2.0.0`: clarified an ambiguous instruction, or replaced the input file the task operates on.
- Minor: only the evaluations changed. Existing model outputs still stand, but their scores are stale.
  - `1.4.2 -> 1.5.0`: fixed an overly strict evaluation, or added a new evaluation.
- Patch: metadata only. Existing results remain valid.
  - `1.4.2 -> 1.4.3`: reworded the task description, or fixed a typo that changes nothing the model or the evaluations see.
