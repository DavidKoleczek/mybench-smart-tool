"""OpenCode specifics that need no Docker: config rendering, command lines, transcript parsing."""

from typing import Any

from pydantic import BaseModel

from mybench.schemas import ProviderConfig, Usage

TIMEOUT_EXIT_CODES = (124, 137)


class TranscriptSummary(BaseModel):
    """What run.yaml needs from an `opencode export` payload."""

    session_id: str
    harness_version: str
    usage: Usage


def render_config(model: str, providers: dict[str, ProviderConfig]) -> dict[str, Any]:
    """The opencode.json for one run: autoupdate and sharing off, plus the model's provider when custom.

    A custom provider's API key enters as an `{env:VAR}` reference, never a literal value,
    so the rendered config is safe to place in the container.
    """
    config: dict[str, Any] = {"autoupdate": False, "share": "disabled"}
    provider_id, _, model_id = model.partition("/")
    provider = providers.get(provider_id)
    if provider is None:
        return config
    options: dict[str, Any] = dict(provider.options)
    if provider.base_url is not None:
        options.setdefault("baseURL", provider.base_url)
    if provider.api_key_env:
        options["apiKey"] = f"{{env:{provider.api_key_env}}}"
    config["provider"] = {
        provider_id: {
            "npm": provider.npm,
            "name": provider_id,
            "options": options,
            "models": {model_id: {"name": model_id, **provider.model_params}},
        }
    }
    return config


def parse_transcript(data: dict[str, Any]) -> TranscriptSummary:
    """Session id, harness version, and usage from an export; the session `info.tokens` is the run aggregate."""
    info = data.get("info", {})
    tokens = info.get("tokens", {})
    cache = tokens.get("cache", {})
    usage = Usage(
        input_tokens=tokens.get("input", 0),
        output_tokens=tokens.get("output", 0),
        reasoning_tokens=tokens.get("reasoning", 0),
        cache_read_tokens=cache.get("read", 0),
        cache_write_tokens=cache.get("write", 0),
        cost_usd=info.get("cost", 0) or 0.0,
    )
    return TranscriptSummary(session_id=info.get("id", ""), harness_version=info.get("version", ""), usage=usage)


def run_command(model: str, instructions: str, timeout_seconds: int) -> list[str]:
    """The model session command; GNU timeout enforces the limit, exiting 124 or 137 on expiry."""
    return ["timeout", "-k", "15", str(timeout_seconds), "opencode", "run", "--model", model, "--auto", instructions]


def session_list_command() -> list[str]:
    """The newest session's row; export needs an explicit id to stay non-interactive."""
    return ["opencode", "session", "list", "--format", "json", "-n", "1"]


def export_command(session_id: str) -> list[str]:
    return ["opencode", "export", session_id]
