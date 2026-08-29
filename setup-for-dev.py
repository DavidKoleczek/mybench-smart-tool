"""
Cross-platform script to set up a development environment for the project.
It assumes that you have installed all the prerequisites listed in CONTRIBUTING.md.
"""

import shlex
import subprocess


def run(command: str) -> None:
    """Run a command, forwarding its output to this process's stdout and stderr."""
    subprocess.run(shlex.split(command), check=True)


def main() -> None:
    run("uv --version")
    run("prek --version")
    run("uv sync --frozen --all-extras --all-groups")
    run("prek install")


if __name__ == "__main__":
    main()
