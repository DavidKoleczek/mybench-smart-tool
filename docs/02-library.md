# Library Reference

Every capability of MyBench is reachable from the `mybench` package. 
All other surfaces, including the CLI, are thin wrappers over the library and add no capability of their own.

The intelligent commands are implemented with the [GitHub Copilot SDK](https://github.com/github/copilot-sdk) behind a thin internal interface, so the intelligence layer can be swapped for something else. 
They require GitHub Copilot authentication (a signed-in Copilot CLI, or a BYOK provider key). Invoked without it, they fail with a message naming exactly what to configure. 
Run and Try require credentials for the model under test, which are passed to the harness. 
Deterministic capabilities run with no credentials configured. 
TBD: how authentication is provided, both for the intelligence layer and for the model under test inside the container.

## Init

Creates a new benchmark, a git repository that holds the tasks, results, and config file, or sets up an existing one. 
`target` is one of:
- A git URL, or a GitHub `<org>/<repo>` shorthand naming nothing on the local disk: the benchmark is cloned, and the remote comes with it, so [Push](#push) and [Pull](#pull) work immediately. 
  - `path` is where the clone goes; default is the repo's name under the current directory.
- A path to an existing benchmark, such as a clone made by hand: registered as is.
- Any other path: a new benchmark is scaffolded there.

Whatever the target, the benchmark's location is recorded in [user settings](05-configuration.md#user-settings), so every other capability finds the benchmark from anywhere. 
Running it again is how MyBench is pointed at a different benchmark, or at one that moved on disk.

```python
def init_benchmark(target: str, path: Path | None = None) -> None
```

## Inspire

Proposes ideas for new tasks, optionally steered by guidance. 
Returned ideas can be passed directly to `create_task`.

```python
def inspire(guidance: str | None = None) -> list[str]
```

## Create

Creates a new task in the benchmark from an idea, context material, or both. At least one must be provided.
Writes the task to disk in the [task format](03-task-format.md) and returns it.

```python
def create_task(idea: str | None = None, context: str | None = None) -> Task
```

## Try

Runs one task against one model without touching the results, for iterating on a task's definition and evaluations during development.
The run executes exactly like [Run](#run), Docker, harness, and evaluations included, but the output goes to a [try directory](04-results-format.md#try-runs), which never leaves the machine and is invisible to [Read Results](#read-results) and Run's skip logic.

```python
def try_task(
    task: str | Path,
    model: str | None = None,
    reevaluate: Path | None = None,
) -> TaskResult
```

- `task`: a task id in the benchmark, or a path to a task directory anywhere on disk, so a task can be tried before it joins `tasks/`. A `Path` is always a path; a `str` is an id when it is shaped like one, a lowercase slug, and a path otherwise. To reach a directory whose name is itself a valid id, write it with a separator, like `./where-was-this-taken`.
- `model`: any model in the harness's naming, not limited to the [config file](05-configuration.md); the config's first model when omitted.
- `reevaluate`: a previous try's directory, the `path` of its returned result. The model run is skipped and the task's current evaluations run against that try's workspace, replacing the try's evaluation results, so evaluations can be iterated on without paying for a model run.

## Run

Runs the benchmark: the models declared in the [config file](05-configuration.md) against the tasks on disk, using each model's provider credentials. 
Each task executes in Docker through the fixed OpenCode harness and is evaluated inside the container.
The config and the tasks on disk define the full matrix of model and task pairs. 
`models` and `tasks` only filter that matrix for one invocation; they cannot add anything the config does not declare. 
Within the selection, pairs that already have a result for the task's current major version are skipped, so a bare `run_benchmark()` executes exactly what is new and a major version bump makes a task new again. 
`rerun=True` executes the selected pairs even if they have results, appending to the run history rather than replacing it. 
Results are written in the [results format](04-results-format.md).

```python
def run_benchmark(
    models: list[str] | None = None,
    tasks: list[str] | None = None,
    rerun: bool = False,
) -> list[TaskResult]
```

- `models`: model names as the [config file](05-configuration.md) declares them.
- `tasks`: task ids. Unlike [Try](#try), a path is never accepted: Run only executes tasks that live in the benchmark.

## Push

Pushes the benchmark repository, tasks and results together, to its git remote.
Creates and pushes the remote if new, otherwise pushes what is new. 
API keys are sanitized before anything leaves the machine. 

```python
def push_results(remote: str | None = None) -> None
```

- `remote`: the git remote URL; remembered once set, and already set when the benchmark was cloned by [Init](#init).

## Pull

Updates the benchmark from its remote: a git fetch and merge that brings down new tasks, results, and config together. 
Runs merge cleanly, because every run is a new directory only one machine has ever written. 
A conflict can only come from editing the same task or config on two machines; pull stops, names the conflicted files, and leaves them to be resolved with ordinary git tools.

```python
def pull_results() -> None
```

## Read Results

Loads benchmark results for analysis. This is what the dashboard is built on.

```python
def load_results(models: list[str] | None = None, tasks: list[str] | None = None) -> list[TaskResult]
```

## Serve Dashboard

Serves the dashboard, a compiled web app whose assets ship with the package, and prints its URL. 
The server binds to `127.0.0.1` by default, so it is not reachable from the local network; set `host` to deliberately expose it. 
The frontend gets its data from a JSON endpoint backed by `load_results`, so the dashboard adds no capability of its own.
Returns a description of how it is hosted (url and if on local network)

```python
def serve_dashboard(port: int | None = None, host: str = "127.0.0.1") -> str
```

- `port`: a free port is chosen when omitted.

## Failure

Failures explain why and what happened so its clear how to investigate and fix it.
- A missing prerequisite, such as Docker not running or no benchmark registered, fails immediately, naming what is absent and the fix, like running [Init](#init).
- A model-backed capability without credentials fails saying exactly what to configure, and never falls back to a deterministic answer.
- Run completes partially by design: each pair of model and task succeeds or fails on its own, a failed pair is recorded with its status in the [task run record](04-results-format.md#task-run-record),
and the returned results say which is which. A failed [Try](#try) is recorded the same way in its [try directory](04-results-format.md#try-runs). Every other capability either completes or fails whole, like Pull stopping on a merge conflict.

`Task` and `TaskResult` mirror the on-disk [task](03-task-format.md) and [results](04-results-format.md) formats. 
`Task` adds `id`, the task's directory name. 
`TaskResult` adds `path`, the run directory on disk, so a consumer can reach the workspace and artifacts.
