"""Command line entry point for MyBench."""

import contextlib
from pathlib import Path
import threading
from typing import Annotated

import typer

from mybench import lib
from mybench.core import run as run_module
from mybench.core import sync
from mybench.schemas import MyBenchError
from mybench.settings import load_user_settings

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.callback()
def cli() -> None:
    """A personal benchmark for language models."""


@app.command()
def init(
    target: Annotated[str, typer.Argument(help="A path to a benchmark, or a git URL or <org>/<repo> to clone")],
    path: Annotated[Path | None, typer.Argument(help="Where a clone goes; defaults to the repository name")] = None,
) -> None:
    """Create, register, or clone a benchmark."""
    lib.init_benchmark(target, path)
    settings = load_user_settings()
    if settings is not None:
        typer.echo(f"Benchmark at {settings.benchmark_path}")


@app.command(name="inspire-me")
def inspire_me(
    guidance: Annotated[str | None, typer.Option(help="Steer what the ideas are about")] = None,
) -> None:
    """Propose ideas for new tasks."""
    for idea in lib.inspire(guidance):
        typer.echo(f"- {idea}")


@app.command()
def create(
    idea: Annotated[str | None, typer.Option(help="What the task should be")] = None,
    context: Annotated[str | None, typer.Option(help="Material to build from: a file path, URL, or text")] = None,
) -> None:
    """Create a new task in the benchmark from an idea, context material, or both."""
    if idea is None and context is None:
        raise typer.BadParameter("Give --idea, --context, or both.")
    created = lib.create_task(idea, context)
    typer.echo(f"Task at {created.path}")
    if created.message:
        typer.echo(created.message)


@app.command(name="try")
def try_(
    task: Annotated[str, typer.Argument(help="A task id in the benchmark, or a path to a task directory")],
    model: Annotated[
        str | None, typer.Option(help="Any model in the harness's naming; the config's first model when omitted")
    ] = None,
    reevaluate: Annotated[
        Path | None, typer.Option(help="A previous try's directory; reruns the evaluations against its workspace")
    ] = None,
) -> None:
    """Run one task against one model without touching the results."""
    result = lib.try_task(task, model, reevaluate)
    typer.echo(f"Try directory: {result.path}")
    typer.echo(f"Status: {result.run.status}")
    if result.score is not None:
        typer.echo(f"Score: {result.score:g}")


@app.command()
def run(
    model: Annotated[
        list[str] | None, typer.Option(help="Only these config-declared models; repeat to give several")
    ] = None,
    task: Annotated[list[str] | None, typer.Option(help="Only these task ids; repeat to give several")] = None,
    rerun: Annotated[bool, typer.Option(help="Execute the selection even where results already exist")] = False,
) -> None:
    """Run the configured models against the tasks on disk, appending to the results."""
    skipped = 0
    failed = 0
    for outcome in run_module.run_pairs(model, task, rerun):
        if outcome.skipped:
            skipped += 1
        elif outcome.error is not None:
            failed += 1
            typer.echo(f"{outcome.task} / {outcome.model}: {outcome.error}", err=True)
        elif outcome.result is not None:
            score = f", score {outcome.result.score:g}" if outcome.result.score is not None else ""
            typer.echo(f"{outcome.task} / {outcome.model}: {outcome.result.run.status}{score}")
            if outcome.result.run.status != "success":
                failed += 1
    if skipped:
        typer.echo(f"Skipped {skipped} pairs that already have results.")
    if failed:
        raise typer.Exit(1)


@app.command()
def push(
    remote: Annotated[str | None, typer.Option(help="A git remote URL; overrides where the benchmark pushes")] = None,
) -> None:
    """Push new tasks and results to the remote, creating a private GitHub repository when there is none."""
    outcome = sync.push_results(remote)
    if outcome.scrubbed:
        typer.echo(f"Scrubbed credentials from {outcome.scrubbed} files.")
    typer.echo(f"Pushed to {outcome.remote}")


@app.command()
def dashboard(
    port: Annotated[int | None, typer.Option(help="The port to bind; a free one is chosen when omitted")] = None,
    host: Annotated[str, typer.Option(help="The interface to bind; 0.0.0.0 exposes the server")] = "127.0.0.1",
) -> None:
    """Serve the dashboard and print its URL; Ctrl+C stops it."""
    typer.echo(lib.serve_dashboard(port, host))
    with contextlib.suppress(KeyboardInterrupt):
        threading.Event().wait()


@app.command()
def pull() -> None:
    """Update the benchmark from its remote: new tasks, results, and config."""
    summary = sync.pull_results()
    typer.echo(summary or "Updated.")


def main() -> int:
    try:
        app()
    except MyBenchError as error:
        typer.echo(error, err=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
