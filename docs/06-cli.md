# CLI Reference

The CLI is a thin wrapper over the [library](02-library.md). Each command maps to one library capability; this page documents only the command-line surface: flags, defaults, and exit behavior. 
`-h` and `--help` print the same help, on the tool and on every command.

## mybench init

```bash
# Scaffold a new benchmark at a path, or register one already there
mybench init <path>

# Clone an existing benchmark: a full git URL or GitHub <org>/<repo> shorthand
mybench init <org>/<repo>
mybench init https://github.com/<org>/<repo> <path>
```

A target that looks like a URL, or like `<org>/<repo>` with nothing at that local path, is cloned, and the remote comes with the clone, so `mybench push` and `mybench pull` need no `--remote`. 
The clone lands under the repo's name in the current directory unless a path follows the target. 
Any other target is a path: registered as is when it is already a benchmark, scaffolded fresh when it is not. 
To scaffold at a path shaped like the shorthand, write it as `./<org>/<repo>`.

## mybench inspire-me

```bash
# Propose ideas for new tasks
mybench inspire-me

# Steer the ideas
mybench inspire-me --guidance "tasks about reading long legal documents"
```

Prints the ideas, one per line; any of them can be passed to `mybench create --idea` as is.

## mybench create

```bash
# Create a new task from an idea, context material, or both
mybench create --idea "<idea>"
mybench create --context "<file, url, or text>"
mybench create --idea "<idea>" --context "<file, url, or text>"
```

`--context` takes a path to a local file, a URL, or literal text. 
Prints the path of the task written to disk, then the model's closing message.

## mybench try

```bash
# Run one task by id against the first configured model
mybench try <task-id>

# Try a task directory that is not in the benchmark yet, and pick the model
mybench try ./drafts/where-was-this-taken --model "<model>"

# Rerun the evaluations against an earlier try's workspace
mybench try <task-id> --reevaluate <try dir>
```

A target shaped like a task id is looked up under `tasks/`; anything else is a path to a task directory. 
To try a directory whose name is itself a valid id, write it with a separator, as `./<task-id>`. 
Prints the try directory, which stays on this machine and never reaches the results.

## mybench run

```bash
# Run every configured model against every task that has no result yet
mybench run

# Filter the matrix for this invocation; repeat either flag
mybench run --model "<model>" --task "<task-id>"

# Run the selection again even where results already exist
mybench run --rerun
```

`--model` takes a model name as the [config file](05-configuration.md) declares it and `--task` a task id; both only narrow what the config and the tasks on disk already declare.

## mybench push

```bash
# Push new tasks and results to the remembered remote
mybench push

# Point the benchmark at an existing remote instead
mybench push --remote "<git url>"
```

Without a remote and without `--remote`, push creates a private GitHub repository through the signed-in GitHub CLI, so `--remote` is only for an existing or non-GitHub remote. 
Pushing never happens on its own; `mybench run` only writes locally.

## mybench pull

```bash
# Update the benchmark from its remote: new tasks, results, and config
mybench pull
```

Merge conflicts stop the pull and are resolved with ordinary git tools in the benchmark repository.

## mybench dashboard

```bash
# Serve the dashboard on 127.0.0.1 and a free port, then print its URL
mybench dashboard

# Choose the port, or deliberately expose the server
mybench dashboard --port 8080
mybench dashboard --host 0.0.0.0
```

## mybench manifest

```bash
# Print the tool's manifest as JSON
mybench manifest
```

Prints the [manifest](02-library.md#manifest) on stdout. 
Needs no benchmark, credentials, or prerequisites, so it doubles as a smoke test of the installation.

## Exit Codes

```bash
0  # success
1  # the command failed and printed the remedy: no benchmark registered, Docker unavailable, missing credentials, an unknown model or task, a harness or evaluation error, a merge conflict on pull
2  # invalid usage: unknown command or flag, no --idea or --context given to create
```
