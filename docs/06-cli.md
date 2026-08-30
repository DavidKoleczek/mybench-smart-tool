# CLI Reference

The CLI is a thin wrapper over the [library](02-library.md). Each command maps to one library capability; this page documents only the command-line surface: flags, defaults, and exit behavior.

## mybench init

```bash
# Scaffold a new benchmark at a path, or register one already there
mybench init <path>

# Clone an existing benchmark: a full git URL or GitHub <org>/<repo> shorthand
mybench init <org>/<repo>
mybench init https://github.com/<org>/<repo> <path>
```

A target that looks like a URL, or like `<org>/<repo>` with nothing at that local path, is cloned, and the remote comes with the clone, so `mybench publish` and `mybench pull` need no `--remote`. 
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

## mybench create

```bash
# Create a new task from an idea, context material, or both
mybench create --idea "<idea>"
mybench create --context "<file, url, or text>"
mybench create --idea "<idea>" --context "<file, url, or text>"
```

Prints the path of the task written to disk.

## mybench run

```bash
# Run every configured model against every task that has no result yet
mybench run

# Filter the matrix for this invocation; repeat either flag
mybench run --model "<model>" --task "<task>"

# Run the selection again even where results already exist
mybench run --rerun
```

`--model` and `--task` only narrow what the [config file](05-configuration.md) and the tasks on disk already declare.

## mybench push

```bash
# Push new tasks and results to the remembered remote
mybench push

# Set the remote; required only if the benchmark was not cloned
mybench push --remote "<git url>"
```

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

## Exit Codes

```bash
0  # success
1  # the command failed and printed the remedy: no benchmark registered, Docker unavailable, missing credentials, an unknown model or task, a harness or evaluation error, a merge conflict on pull
2  # invalid usage: unknown command or flag, no --idea or --context given to create
```
