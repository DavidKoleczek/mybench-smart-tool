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


def main() -> int:
    try:
        app()
    except MyBenchError as error:
        typer.echo(error, err=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
