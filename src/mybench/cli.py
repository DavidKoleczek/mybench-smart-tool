"""Command line entry point for MyBench."""

from pathlib import Path
from typing import Annotated

import typer

from mybench import lib
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


def main() -> int:
    try:
        app()
    except MyBenchError as error:
        typer.echo(error, err=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
