# Results Format

What a benchmark run (including the tasks and evals that run) outputs and stores. 
Results live in the [benchmark repository](03-task-format.md#location), so they are [pushed and pulled](02-library.md#push) across machines together with the tasks that produced them.

All historical runs are kept: rerunning a pair of model and task appends a new result and never overwrites an old one.

## Storage Location

Runs live in the benchmark repository under `runs/`, one directory per execution of one task by one model:

```
runs/<task-id>/<model-slug>/<timestamp>/
```

`<model-slug>` is the model name made filesystem safe; the exact model string is in `run.yaml`.
`<timestamp>` is UTC, like `2026-08-29T14-03-12Z`, with a `-2`, `-3` suffix when runs land in the same second.

Plain files are the whole format: [Read Results](02-library.md#read-results) and the dashboard read this tree directly, and pushing, pulling, diffing, and hand inspection need nothing but git.

## Run Directory Layout

```
runs/<task-id>/<model-slug>/<timestamp>/
├── run.yaml
├── transcript.json
├── harness.log
├── workspace/
└── evals/
    └── <eval-id>/
        ├── evaluation.yaml
        ├── score.json
        └── ...
```

Everything the run produces is kept.
`workspace/` is the model's entire working directory, so any output can be viewed later, not only the declared artifacts.
`transcript.json` is the harness session exported with `opencode export`: every message, tool call, and part.
`harness.log` is the harness's own stdout and stderr.
The `evals/<eval-id>/` directories keep whatever else an evaluation wrote alongside its score.
These paths are bind mounted from the host while the container runs, so output survives even a container that dies badly. 
Before the container is removed, file ownership of the mounts is returned to the invoking user, since files the container writes would otherwise land root-owned on Linux.

`run.yaml` is written last and marks the run complete. 
A directory without it is a crashed run and is ignored by [Read Results](02-library.md#read-results).

## Task Run Record

```yaml
task: where-was-this-taken
task_version: 1.2.0
model: anthropic/claude-sonnet-5
started: 2026-08-29T14:03:12Z
finished: 2026-08-29T14:09:47Z
status: success
mybench_version: 0.3.0
harness: opencode 1.18.25
session_id: ses_abc123
usage:
  input_tokens: 48210
  output_tokens: 9114
  reasoning_tokens: 1204
  cache_read_tokens: 31804
  cache_write_tokens: 2210
  cost_usd: 0.41
format: 1
```

Every run records when it ran and what produced it: the start and finish times, the MyBench version, the harness version, and the version of the task at the time it ran. 
Results for a task are comparable only within the same major version of that task; see [task versioning](03-task-format.md#versioning). 
Usage and cost come from the harness session. 
Cache token counts and `cost_usd` depend on the provider: a local or custom endpoint reports 0 for both unless its configuration declares per-token pricing. 
`session_id` is omitted when the run failed before the harness produced a session. 
`status` is `success`, `error`, or `timeout`. 
Anything but `success` is a harness or environment failure, not a model score: the run is kept for inspection, is never scored, and does not stop [Run](02-library.md#run) from trying the pair again. 
A `timeout` or `error` run still keeps whatever the harness produced: the transcript exports even for a killed session, and the workspace may hold finished work, so the status means unscored, not empty.

## Score Records

One evaluation writes one `score.json`:

```json
{
  "score": 73.3,
  "graded": "2026-08-29T14:11:02Z",
  "details": {}
}
```

- `score`: 0 to 100, or null when the evaluation errored.
- `graded`: when it was scored, which for a `manual` evaluation is later than the run.
- `details`: anything the evaluation wants to keep; ignored by aggregation.

A `judge` evaluation adds its per-criterion results and written report:

```json
{
  "score": 73.3,
  "graded": "2026-08-29T14:11:02Z",
  "grader": {
    "model": "openai/gpt-5",
    "implementation": "copilot-sdk 0.2.1"
  },
  "criteria": {
    "voice": {"score": 80, "weight": 2, "reasoning": "Conversational like the references, but the close drifts formal."},
    "structure": {"score": 60, "weight": 1, "reasoning": "The point arrives late; the middle section wanders."}
  },
  "report": "The post opens strongly but...",
  "details": {}
}
```

`grader` records which model graded and through which implementation, so a grade is traceable when either changes. 
This schema is the whole contract between graders and stored results: any grader implementation, present or future, that writes it is interchangeable.

`evaluation.yaml` is a byte for byte snapshot of the evaluation definition that produced the score, so a grade from an older definition of the evaluation is detectable. 
Regrading replaces the evaluation's directory; the task run record, transcript, and workspace are never touched. 
A `manual` evaluation's `score.json` appears when the score is entered from the dashboard.

## Try Runs

[Try](02-library.md#try) writes the same run directory layout under `tries/` instead of `runs/`:

```
tries/<task-id>/<model-slug>/<timestamp>/
```

`tries/` is gitignored, so tries never leave the machine, and [Read Results](02-library.md#read-results) never reads them.
Re-evaluating a try replaces its `evals/` directory; the run record, transcript, and workspace are never touched.

## Sanitization

API keys and other credentials are never written to the benchmark repository. 
Credentials reach the harness only through environment variables, and every configured secret value is scrubbed from the transcript, logs, and workspace before anything is pushed.

## Versioning

`run.yaml` carries `format`, the version of this format, which governs the whole run directory. 
Readers accept older formats and migrate on read; a format newer than the reader knows is an error, not a guess.
