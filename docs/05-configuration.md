# Configuration

Defines the inputs that apply across capabilities: the config file, user settings, environment variables, and model provider credentials.

## Config File

`config.yaml` at the root of the benchmark repository, committed and published with it. 
It describes the benchmark itself, never the machine, and never contains credentials.

```yaml
models:
  - anthropic/claude-sonnet-5
  - sglang/qwen3.8-27b
grading_model: openai/gpt-5.6-terra
providers:
  sglang:
    base_url: http://192.168.0.20:30000/v1
    api_key_env: SGLANG_API_KEY
    model_params:
      limit: {context: 200000, output: 32768}
```

- `models`: the models under test, as `<provider>/<model>` in the harness's naming. [Run](02-library.md#run) executes these over the tasks on disk, and the exact string is recorded in every [task run record](04-results-format.md#task-run-record).
- `grading_model`: the model `judge` evaluations grade with, separate from the models under test and recorded in the [score record](04-results-format.md#score-records). Optional when no task has a `judge` evaluation.
- `providers`: providers the harness does not know natively, keyed by the provider segment of the model strings that use them. Providers the harness knows, like `anthropic` and `openai`, need no declaration. `npm` names the harness provider SDK package and defaults to the OpenAI-compatible one, so a local or self-hosted endpoint needs only `base_url`. `api_key_env` names the environment variable holding the endpoint's key, and is omitted for keyless endpoints. `options` and `model_params` merge verbatim into the harness's provider and model configuration, so any harness parameter is expressible without a schema change.

## User Settings

Machine-local state, stored outside the benchmark repository and never committed. 
Lives in the platform's per-user config directory: `~/.config/mybench/settings.json` on Linux, `%APPDATA%\mybench\settings.json` on Windows. 
[Init](02-library.md#init) records the benchmark's location here; every command reads it to find the benchmark from any working directory.

## Environment Variables

- `MYBENCH_HOME`: path to the benchmark, overriding user settings for one invocation; for scripts and CI.
- Provider API keys: each native provider's conventional name, such as `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`; a custom provider names its own variable with `api_key_env`.

## Model Providers

[Run](02-library.md#run) needs credentials for each configured model, and [Try](02-library.md#try) for the model it runs, read from the environment and passed to the harness. 
Deterministic capabilities run with no credentials configured. 
Invoking a capability without the credentials it needs fails with a message naming exactly what to configure. 
A declared provider's `base_url` is checked before the model starts: it must be reachable and, when the endpoint lists what it serves, the requested model must be among them. 
Credentials never enter the config file, the user settings, or the [results](04-results-format.md#sanitization).
