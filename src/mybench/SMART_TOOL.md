---
smart_tool_format: 1
name: mybench
version: 0.1.0
description: >
  Builds and runs a personal benchmark: your own tasks with evaluations, executed in a
  fixed harness so the model is the only variable. Use when you want to know how well a
  model works for you, not how it places on a public leaderboard.
use_cases:
  - Check how well a new model handles the tasks you actually care about
  - Turn an idea or reference material into a benchmark task with evaluations
  - Track model results over time in a git repository, visualized on a dashboard
platforms:
  - linux
requires:
  - name: git
    purpose: A benchmark is a git repository; creating, cloning, pushing, and pulling all drive git.
    install: https://git-scm.com/downloads
  - name: docker
    purpose: Executes tasks in containers so the model is the only variable. Without it, tasks cannot run.
    optional: true
    install: https://docs.docker.com/engine/install/
  - name: gh
    purpose: >
      Publishes benchmarks to GitHub and generates the token that signs in to GitHub
      Copilot. Without it, results stay local and the model-backed capabilities cannot
      authenticate.
    optional: true
    install: https://cli.github.com/
  - name: github-copilot-subscription
    purpose: >
      A Copilot subscription on the account signed in to gh powers task authoring and
      judge grading. Without it, only the deterministic capabilities run.
    optional: true
    install: https://github.com/github/copilot-cli#prerequisites
---

# MyBench

A personal benchmark for language models. Tasks and their evaluations live in a git
repository; runs execute in Docker through a fixed harness so results are comparable
across models and over time. Every task score is normalized to 0 to 100.

## When to reach for it

- You want evidence of how a model performs on your own work.
- A new model came out and you want to run it against your existing tasks without re-running the others.
- You changed an evaluation and want old runs re-scored without re-running the models.

Not for benchmarking agents, harnesses, or scaffolding, and not a general-purpose eval
framework or public leaderboard.

## Straight and smart paths

`inspire`, `create_task`, `try_task`, and `run_benchmark` invoke models, so they consume
tokens and can answer differently on a second call. Authoring and judge grading go through
GitHub Copilot; the benchmarked models run under whatever providers the benchmark's
`config.yaml` declares. Everything else is deterministic and runs with no provider
configured.

## Worked invocations

```bash
mybench init my-bench                       # scaffold a new benchmark and point the tool at it
mybench create --idea "summarize a 10-K"    # author a task with evaluations
mybench try summarize-a-10-k                # run one task against one model, outside the results
mybench run                                 # run the configured models against all tasks
mybench dashboard                           # serve the results dashboard and print its URL
mybench push                                # push tasks and results to the benchmark's remote
```

## Sharp edges

- Everything operates on the benchmark that `mybench init` registered most recently, or the one `MYBENCH_HOME` points at.
- `run` skips model and task pairs that already have a result for the task's current major version; pass `--rerun` to force them.
- Nothing touches the remote repository automatically; `push` and `pull` are always explicit.

The task and results formats, configuration, and the full library surface are documented
in the repository's `docs/` directory.
