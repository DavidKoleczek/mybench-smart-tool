# Configuration

Defines the inputs that apply across capabilities: the config file, user settings, environment variables, and model provider credentials.

## Config File

`config.yaml` at the root of the benchmark repository, committed and published with it. 
It describes the benchmark itself, never the machine, and never contains credentials.

```yaml
models:
  - anthropic/claude-sonnet-5
  - openai/gpt-5.6-terra
grading_model: openai/gpt-5.6-terra
```

- `models`: the models under test, as `<provider>/<model>` in the harness's naming. [Run](02-library.md#run) executes these over the tasks on disk, and the exact string is recorded in every [task run record](04-results-format.md#task-run-record).
- `grading_model`: the model `judge` evaluations grade with, separate from the models under test and recorded in the [score record](04-results-format.md#score-records). Optional when no task has a `judge` evaluation.

## User Settings

Machine-local state, stored outside the benchmark repository and never committed. 
Lives in the platform's per-user config directory: `~/.config/mybench/settings.json` on Linux, `%APPDATA%\mybench\settings.json` on Windows. 
[Init](02-library.md#init) records the benchmark's location here; every command reads it to find the benchmark from any working directory.

## Environment Variables

- `MYBENCH_HOME`: path to the benchmark, overriding user settings for one invocation; for scripts and CI.
- Provider API keys, under each provider's conventional name, such as `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

## Model Providers

[Run](02-library.md#run) needs credentials for each configured model, and [Try](02-library.md#try) for the model it runs, read from the environment and passed to the harness. 
Deterministic capabilities run with no credentials configured. 
Invoking a capability without the credentials it needs fails with a message naming exactly what to configure. 
Credentials never enter the config file, the user settings, or the [results](04-results-format.md#sanitization).
