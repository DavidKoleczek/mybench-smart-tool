# Vision

MyBench is a [Smart Tool](https://github.com/microsoft/amplifier-smart-tools) for building a personal benchmark, so you know how well a model works for *you*. 
A benchmark consists of tasks which have evaluations that measure a model's capability. 
MyBench measures capability at the model level as much as possible, irrespective of harness. 
The harness is always fixed, so results are comparable across models and over time.

## Goals

- Easy to create tasks and evaluations
  - There is a stable, but flexible schema for everything
- The model should be the only variable
  - Tasks are executed in Docker and evaluated in the container
- It should be easy to define a new model to execute tasks on, without re-running the other models for cost savings.
  - Similarly, when a new task is added - we should just be able to run a new task
  - We can also rerun select results.
  - We should store all the historical runs and include metadata about what versions and dates it was run.
- Default dashboard to be able to visualize results.
- Results should be persisted to a git-enabled directory.
  - We provide an easy command that can publish the repo (if new, or push new results to it). 
  - Also easy to pull down updates from upstream.
  - We make sure to sanitize any API keys
- The tool should work on Windows and Linux seamlessly

## Non-Goals

- Benchmarking agents, harnesses, or scaffolding.
- A general-purpose eval framework or a public leaderboard.
- NOTE: Ideas that might be goals, but we are not targeting yet are in [ROADMAP.md](ROADMAP.md)

## Principles

- The library is the tool. The CLI, dashboard, and any other surface are thin wrappers over it.
- The intelligence is implemented using the GitHub Copilot SDK. However, it should be architected and structured such that it easily to swap in with something else.
- The dashboard should be a Vite+TS+React app so we can benefit from all the UX features of that ecosystem.
- Deterministic paths run with no model provider configured.
- All final evaluation scores for a task should be normalized to 0 to 100.
- Nothing updates the remote repository automatically; push and pull are always explicit.
