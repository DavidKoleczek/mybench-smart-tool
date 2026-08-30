"""Inspire and Create: task ideas from a model, and new tasks authored straight into the benchmark."""

import contextlib
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
from typing import Any

from liquid import render
import yaml

from mybench.core import benchmark
from mybench.intelligence.interface import Intelligence, default_intelligence
from mybench.intelligence.schemas import AgentRequest, HostWorkspace
from mybench.schemas import CreatedTask, MyBenchError
from mybench.settings import benchmark_home

INSPIRE_TIMEOUT_SECONDS = 300
CREATE_TIMEOUT_SECONDS = 1200
TASK_FORMAT_SOURCE = "DavidKoleczek/mybench-smart-tool/contents/docs/03-task-format.md"

INSPIRE_PROMPT = """\
You are proposing ideas for a personal LLM benchmark: tasks its owner runs against new models to \
learn how well each one works for them. Each idea is one or two sentences describing the task, \
ending with how it is evaluated. Make every idea self-contained enough to be handed to task \
creation verbatim.

What makes a task worth having:

<principles>
- A good task discriminates. The interesting result is models partially succeeding in ways that \
separate them; a task every model aces measures nothing.
- Grade passable versus good, not broken versus not. Modern models rarely fail outright; they \
produce competent-looking slop, and the evaluation must have something to say about it.
- Prefer a deterministic script evaluation wherever one is possible. Reserve an LLM judge for what \
genuinely resists string or structural checks, and a manual evaluation for what only a human can \
experience, like playing a game.
- Criteria must be observable and pointable. When a known answer exists, check against a tolerance \
band instead of asking for an opinion.
- Grade the artifact the model produced, not the path it took.
- Instructions describe what done looks like, never how it is checked. Answer keys stay where the \
model cannot see them.
- Resist memorization. Prefer answers determined by the task's own inputs and environment over \
anything that can be looked up.
- A task should feel like a real moment of the owner's actual work or interests, phrased the \
concise way a real person would ask.
- A few high-signal tasks beat many weak ones.
</principles>

Example ideas at the right level of detail:

<examples>
- Create an SVG of a college football player playing in a bowl game.
- Given a photo of a location, figure out where it was taken and write the answer to a JSON file. \
A script parses and checks the file, which also tests instruction following.
- Recreate a real application's UX from a screenshot. No evaluation; the artifact is for viewing.
- Given a set of documents, pick out which one is LLM generated. Evaluated deterministically \
against labels.
- Write a blog post on a given topic. A judge grades it against reference posts in the eval directory.
- Scaffold a FastAPI plus uv Python service. Evaluated by diffing against a reference scaffold.
- Make a playable top-down wave-survival arena game in Godot, with the built game output to a \
specific location. Evaluated manually by playing the build.
</examples>
{% if guidance %}
Steer the ideas by this guidance:

<guidance>
{{ guidance }}
</guidance>
{% endif %}
Propose about five ideas, then submit them through the submit tool, exactly once."""

CREATE_PROMPT = """\
Create exactly one benchmark task in the current working directory, following this task format:

<task-format>
{{ task_format }}
</task-format>
{% if idea %}
The task to build:

<idea>
{{ idea }}
</idea>
{% endif %}{% if context_text %}
Material to build the task from; a URL here can be fetched with curl:

<context>
{{ context_text }}
</context>
{% endif %}{% if context_file %}
Material to build the task from is at {{ context_file }}; move it under the task's input/ or \
evals/ if the task needs it.
{% endif %}
Rules:
- Create one directory here, named as the task's id: a new lowercase slug{% if existing_ids %} \
that is none of {{ existing_ids | join: ", " }}{% endif %}.
- Inside it, write task.yaml (without an id field; the directory name is the id) and \
instructions.md, plus input/ and evals/<eval-id>/ directories when the task calls for them.
- Give the task at least one evaluation suited to it, preferring script over judge over manual.
- Write nothing outside the current working directory.

End with a short message summarizing the task and how it is evaluated, without revealing any answer or hidden label."""

_IDEAS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
                "minLength": 1,
                "description": "One task idea, ending with how it is evaluated",
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def inspire(guidance: str | None = None) -> list[str]:
    """Propose ideas for new tasks, each ready to hand to `create_task`."""
    intelligence, model, _ = _authoring_setup()
    result = intelligence.run(
        AgentRequest(
            prompt=render(INSPIRE_PROMPT, guidance=guidance),
            model=model,
            output_schema=_IDEAS_SCHEMA,
            timeout_seconds=INSPIRE_TIMEOUT_SECONDS,
        )
    )
    if result.output is None:
        raise MyBenchError(f"Inspire produced no ideas: {result.error or 'the model submitted nothing'}")
    return [str(idea) for idea in result.output["ideas"]]


def create_task(idea: str | None = None, context: str | None = None) -> CreatedTask:
    """Author one task into the benchmark's tasks/ from an idea, context material, or both.

    The agent writes into a staging directory under tries/, and only a directory that passes
    the task format's validation is moved into tasks/, so a failed attempt never becomes a task.
    """
    if idea is None and context is None:
        raise MyBenchError("Give an idea, context material, or both.")
    intelligence, model, home = _authoring_setup()
    task_format = _task_format()
    staging = _staging_dir(home)
    context_text, context_file = _stage_context(staging, context)
    prompt = render(
        CREATE_PROMPT,
        task_format=task_format,
        idea=idea,
        context_text=context_text,
        context_file=context_file,
        existing_ids=[path.name for path in benchmark.list_tasks(home)],
    )
    result = intelligence.run(
        AgentRequest(
            prompt=prompt,
            model=model,
            workspace=HostWorkspace(path=staging),
            writable=True,
            timeout_seconds=CREATE_TIMEOUT_SECONDS,
        )
    )
    if result.error is not None:
        raise _rejected(f"Creating the task failed: {result.error}", staging, result.text)
    task_dir = _accept_task(home, staging, result.text)
    destination = home / "tasks" / task_dir.name
    destination.parent.mkdir(exist_ok=True)
    shutil.move(task_dir, destination)
    shutil.rmtree(staging)
    with contextlib.suppress(OSError):
        staging.parent.rmdir()
    return CreatedTask(task=benchmark.load_task(destination), path=destination, message=result.text)


def _authoring_setup() -> tuple[Intelligence, str, Path]:
    """The intelligence, model, and benchmark for authoring, checked before anything costly runs."""
    home = benchmark_home()
    config = benchmark.load_config(home)
    intelligence = default_intelligence()
    intelligence.preflight()
    return intelligence, config.smart_model, home


def _task_format() -> str:
    """The task format documentation, fetched through the GitHub CLI so the prompt always carries the current format."""
    fetched = subprocess.run(
        ["gh", "api", f"repos/{TASK_FORMAT_SOURCE}", "-H", "Accept: application/vnd.github.raw"],
        capture_output=True,
        check=False,
    )
    if fetched.returncode != 0:
        detail = fetched.stderr.decode(errors="replace").strip() or f"exit code {fetched.returncode}"
        raise MyBenchError(
            f"Fetching the task format documentation ({TASK_FORMAT_SOURCE}) failed: {detail}. "
            "Creating a task needs the signed-in GitHub CLI and network access."
        )
    return fetched.stdout.decode("utf-8")


def _staging_dir(home: Path) -> Path:
    """A fresh directory under tries/ for the agent to work in; a failed attempt stays for inspection."""
    parent = home / "tries" / "create"
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    staging = parent / timestamp
    suffix = 2
    while staging.exists():
        staging = parent / f"{timestamp}-{suffix}"
        suffix += 1
    staging.mkdir(parents=True)
    return staging


def _stage_context(staging: Path, context: str | None) -> tuple[str | None, str | None]:
    """The context split into what to inline and what to stage: a local file is copied beside the agent."""
    if context is None:
        return None, None
    path = Path(context).expanduser()
    try:
        is_file = path.is_file()
    except OSError:  # a long pasted context is not a path, but the probe can fail before deciding that
        is_file = False
    if not is_file:
        return context, None
    destination = staging / "context" / path.name
    destination.parent.mkdir()
    shutil.copy2(path, destination)
    return None, f"context/{path.name}"


def _accept_task(home: Path, staging: Path, message: str) -> Path:
    """The one valid task directory the agent created; anything else is a rejection naming why."""
    candidates = [path for path in staging.iterdir() if path.is_dir() and (path / "task.yaml").is_file()]
    if len(candidates) != 1:
        problem = (
            "The model created no task directory."
            if not candidates
            else f"The model created {len(candidates)} task directories where exactly one belongs."
        )
        raise _rejected(problem, staging, message)
    candidate = candidates[0]
    try:
        benchmark.load_task(candidate)
        benchmark.read_instructions(candidate)
    except MyBenchError as error:
        raise _rejected(str(error), staging, message) from error
    data = yaml.safe_load((candidate / "task.yaml").read_text(encoding="utf-8"))
    if isinstance(data, dict) and "id" in data:
        raise _rejected(
            f"{candidate.name}/task.yaml sets an id, which would override the directory name.", staging, message
        )
    if (home / "tasks" / candidate.name).exists():
        raise _rejected(f"The task id '{candidate.name}' is already taken.", staging, message)
    return candidate


def _rejected(problem: str, staging: Path, message: str) -> MyBenchError:
    """A creation failure: what went wrong, where the attempt is left, and what the model said."""
    said = f"\nThe model said: {message}" if message else ""
    return MyBenchError(f"{problem} The attempt is left at {staging}.{said}")
