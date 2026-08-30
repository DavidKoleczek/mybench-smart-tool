"""The OpenCode harness: a pinned Docker image and one container session per run."""

import hashlib
from importlib.resources import files
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import TracebackType
from typing import Any, Self

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container
from docker.types import Mount
from pydantic import BaseModel

from mybench.harness import opencode
from mybench.schemas import MyBenchError

CONTAINER_WORKSPACE = "/workspace"
CONTAINER_EVALS = "/evals"
CONTAINER_OPENCODE_CONFIG = "/root/.config/opencode"


class ExecResult(BaseModel):
    """One in-container command: what ran, how it exited, and what it printed."""

    command: str
    exit_code: int
    stdout: str
    stderr: str


class EndpointProbe(BaseModel):
    """What probing a custom endpoint from inside the container found."""

    error: str | None = None
    served_models: list[str] = []


def docker_client(timeout_seconds: int = 600) -> docker.DockerClient:
    """A client for the local Docker daemon.

    `timeout_seconds` bounds every API call, so it must exceed the longest in-container
    command; the model session's own limit is enforced by GNU timeout inside the container.
    """
    try:
        client = docker.from_env(timeout=timeout_seconds)
        client.ping()
    except DockerException as error:
        raise MyBenchError(f"Docker is not reachable: {error}. Start Docker and run again.") from error
    return client


def ensure_image(client: docker.DockerClient) -> str:
    """Build the harness image unless it exists for the packaged Dockerfile.

    The tag carries a digest of the Dockerfile itself, so any change to it, a version
    bump or otherwise, yields a fresh build instead of silently reusing a stale image.
    """
    dockerfile = (files("mybench.harness") / "Dockerfile").read_bytes()
    tag = f"mybench-harness:{hashlib.sha256(dockerfile).hexdigest()[:12]}"
    try:
        client.images.get(tag)
    except ImageNotFound:
        try:
            client.images.build(fileobj=io.BytesIO(dockerfile), tag=tag, rm=True)
        except DockerException as error:
            raise MyBenchError(f"Building the harness image {tag} failed: {error}") from error
    return tag


class HarnessSession:
    """One container for one run; entering starts it, exiting restores file ownership and removes it.

    The workspace and evals directories are bind mounted, so everything crossing the container
    boundary is staged host-side; the evals mount starts empty and sits outside the workspace,
    keeping evaluation material invisible to the model.
    """

    def __init__(
        self,
        client: docker.DockerClient,
        image: str,
        workspace: Path,
        evals_dir: Path,
        opencode_config: dict[str, Any] | None,
        env: dict[str, str],
    ) -> None:
        self._client = client
        self._image = image
        self._workspace = workspace
        self._evals_dir = evals_dir
        self._opencode_config = opencode_config
        self._env = env
        self._container: Container | None = None
        self._config_dir: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Self:
        mounts = [
            Mount(CONTAINER_WORKSPACE, str(self._workspace), type="bind"),
            Mount(CONTAINER_EVALS, str(self._evals_dir), type="bind"),
        ]
        if self._opencode_config is not None:
            # Writable because opencode writes housekeeping files (a .gitignore) into its
            # config directory at startup; the mounted directory is scratch and per-run.
            self._config_dir = tempfile.TemporaryDirectory(prefix="mybench-opencode-", ignore_cleanup_errors=True)
            config_path = Path(self._config_dir.name) / "opencode.json"
            config_path.write_text(json.dumps(self._opencode_config, indent=2), encoding="utf-8", newline="\n")
            mounts.append(Mount(CONTAINER_OPENCODE_CONFIG, self._config_dir.name, type="bind"))
        try:
            self._container = self._client.containers.run(
                self._image,
                ["sleep", "infinity"],
                detach=True,
                working_dir=CONTAINER_WORKSPACE,
                mounts=mounts,
                environment=self._env,
            )
        except DockerException as error:
            raise MyBenchError(f"Starting a harness container from {self._image} failed: {error}") from error
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            if self._container is not None:
                self._restore_ownership()
                self._container.remove(force=True)
        finally:
            if self._config_dir is not None:
                self._config_dir.cleanup()

    def harness_version(self) -> str:
        """The `harness:` string for run.yaml, read from inside the container, never from the image tag."""
        result = self._exec(["opencode", "--version"])
        return f"opencode {result.stdout.strip()}"

    def check_endpoint(self, base_url: str) -> EndpointProbe:
        """Probe a custom provider's endpoint from inside the container.

        The served model ids come from the endpoint's /models listing, best effort: an
        endpoint that is reachable but lists nothing parseable yields an empty list.
        """
        result = self._exec(["curl", "-sS", "-m", "20", f"{base_url.rstrip('/')}/models"])
        if result.exit_code != 0:
            return EndpointProbe(error=result.stderr.strip() or f"curl exited {result.exit_code}")
        try:
            listing = json.loads(result.stdout)
            models = [entry["id"] for entry in listing.get("data", []) if isinstance(entry.get("id"), str)]
        except (json.JSONDecodeError, AttributeError):
            models = []
        return EndpointProbe(served_models=models)

    def run_setup(self, commands: list[str]) -> ExecResult | None:
        """Run the task's setup commands in order; the first failure, or None when all succeed."""
        for command in commands:
            result = self._exec(["bash", "-lc", command])
            if result.exit_code != 0:
                return result
        return None

    def run_model(self, instructions: str, model: str, timeout_seconds: int) -> ExecResult:
        """The model session; never raises on model failure, the exit code is the outcome."""
        return self._exec(opencode.run_command(model, instructions, timeout_seconds))

    def export_transcript(self) -> dict[str, Any] | None:
        """The exported session, or None when the run died before creating one.

        A fresh container holds exactly one session, so the newest listed session is the run's,
        and even a timed-out session exports.
        """
        listing = self._exec(opencode.session_list_command())
        try:
            sessions = json.loads(listing.stdout or "[]")
        except json.JSONDecodeError:
            return None
        if not sessions:
            return None
        export = self._exec(opencode.export_command(sessions[0]["id"]))
        if export.exit_code != 0:
            return None
        try:
            return json.loads(export.stdout)
        except json.JSONDecodeError:
            return None

    def run_eval(self, command: str, eval_id: str, timeout_seconds: int) -> ExecResult:
        """One evaluation, run in the workspace with MYBENCH_EVAL_DIR pointing at its staged directory."""
        wrapped = ["timeout", "-k", "15", str(timeout_seconds), "bash", "-lc", command]
        return self._exec(wrapped, env={"MYBENCH_EVAL_DIR": f"{CONTAINER_EVALS}/{eval_id}"})

    def _exec(self, command: list[str], env: dict[str, str] | None = None) -> ExecResult:
        if self._container is None:
            raise MyBenchError("The harness session is not open; use it as a context manager.")
        exit_code, output = self._container.exec_run(command, workdir=CONTAINER_WORKSPACE, environment=env, demux=True)
        stdout, stderr = output or (None, None)
        return ExecResult(
            command=shlex.join(command),
            exit_code=exit_code,
            stdout=(stdout or b"").decode("utf-8", errors="replace"),
            stderr=(stderr or b"").decode("utf-8", errors="replace"),
        )

    def _restore_ownership(self) -> None:
        # Bind-mounted files written by container root land root-owned on native Linux and
        # WSL2; Docker Desktop's mounts arrive user-owned, so Windows needs nothing.
        if sys.platform == "win32":
            return
        paths = [CONTAINER_WORKSPACE, CONTAINER_EVALS]
        if self._config_dir is not None:
            paths.append(CONTAINER_OPENCODE_CONFIG)
        self._exec(["chown", "-R", f"{os.getuid()}:{os.getgid()}", *paths])
