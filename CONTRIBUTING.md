# Contributing to MyBench Smart Tool

## Development Setup

### Prerequisites

Install:

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/): Manages Python environments
- [prek](https://github.com/j178/prek): Used for precommit hooks. Recommended to install through PyPI/uv with `uv tool install prek`. Use `uv tool upgrade prek` to update it.
- [Node.js](https://nodejs.org/) 22+ and [pnpm](https://pnpm.io/installation): Used for developing the dashboard
- [Docker](https://docs.docker.com/engine/install)
- [GitHub CLI](https://cli.github.com/) for persisting your benchmark data to GitHub and for intelligence features with GitHub Copilot.
- [GitHub Copilot subscription](https://github.com/github/copilot-cli#prerequisites) for intelligent features.

### Initial Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/DavidKoleczek/mybench-smart-tool.git
   cd mybench-smart-tool
   ```

1. Run the development installation script (sets up uv env and precommit hooks):

   ```bash
   uv run setup-for-dev.py
   ```

### Essential Development Commands

*Commands should be run from the repository root, unless otherwise specified.*

#### Precommit hooks

Setup precommit hooks:

```bash
prek install
```

Run precommit hooks manually:

```bash
prek run --all-files
```

#### Python Library Development

Create uv virtual environment and install dependencies:

```bash
uv sync --frozen --all-extras --all-groups
```

To update dependencies and the lock file:

```bash
uv sync -U --all-extras --all-groups
```

Lint code:

```bash
uv run ruff check --fix --config pyproject.toml
```

Format code (also formats code blocks in .md files):

```bash
uv run ruff format --config pyproject.toml
```

Type check:

```bash
uv run ty check .
```

Run tests:

```bash
uv run pytest
```

#### Dashboard Development

The dashboard is a Vite+TS+React app in `dashboard/`, served by the library from compiled assets in `src/mybench/dashboard/static/`. 
Those assets are committed, because the tool installs from this git repository; the `dashboard build` precommit hook recompiles them whenever frontend source changes.

Install dependencies:

```bash
pnpm --dir dashboard install
```

Run with hot reload against a local benchmark (two terminals):

```bash
MYBENCH_HOME=path/to/benchmark uv run mybench dashboard --port 5199
pnpm --dir dashboard dev
```

The Vite dev server proxies `/api` to port 5199; set `MYBENCH_API_URL` to point it elsewhere.

Lint, format, and type check:

```bash
pnpm --dir dashboard lint
pnpm --dir dashboard format
pnpm --dir dashboard typecheck
```

Compile the assets into the package:

```bash
pnpm --dir dashboard build
```

