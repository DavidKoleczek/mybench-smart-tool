import os
from pathlib import Path

from pydantic import BaseModel, ValidationError

from mybench.schemas import MyBenchError


class UserSettings(BaseModel):
    """The contents of settings.json, which stays on this machine and out of the benchmark."""

    benchmark_path: Path


def settings_file() -> Path:
    """The per-user config path for settings.json."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "mybench" / "settings.json"


def load_user_settings() -> UserSettings | None:
    """Read the saved settings, or None when nothing has been saved yet."""
    path = settings_file()
    if not path.is_file():
        return None
    try:
        return UserSettings.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        raise MyBenchError(
            f"{path} is not readable as MyBench settings: {error}. Run `mybench init <path>` to write it again."
        ) from error


def save_user_settings(settings: UserSettings) -> None:
    """Write the settings, creating the config directory if needed."""
    path = settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")


def benchmark_home() -> Path:
    """The benchmark to work on: MYBENCH_HOME when set, otherwise the registered one."""
    override = os.environ.get("MYBENCH_HOME")
    if override:
        return Path(override).expanduser().resolve()
    settings = load_user_settings()
    if settings is None:
        raise MyBenchError(
            "No benchmark is registered. Run `mybench init <path>` to create one, or set MYBENCH_HOME to an existing benchmark."
        )
    return settings.benchmark_path
