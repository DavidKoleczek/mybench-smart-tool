This is a Smart Tool that must conform to Microsoft's Amplifier Smart Tool Spec. The spec is currently a submodule in this repo.

## Writing Style

- Be concise. The user will not read walls of text.
- When adding to existing documents, add only what's needed.
- Do not restructure or rewrite existing content unless asked.
- Always prefer code blocks and other formatting over tables.
- Match the tone and density of what's already in the file.
- Never write em dashes

## Code, Markdown Files, etc. Are Not Conversation

Every file you write is read later by someone with no memory of this session, and often by a machine. 
Write for that reader, not for me. This applies to all durable output, not just markdown: help text, docstrings, code comments, error messages.

- Never record the state of our work in an artifact. No "Status", "scaffolding", "not implemented yet", "for now", "coming soon", "TODO: remove this later". If a sentence becomes false after the next commit, it does not belong in the file. Tell me in chat instead.
- Never describe the format inside an instance of the format. A manifest does not explain what a manifest is. A test does not explain what testing is.
- When working from a spec, sample, fixture, or reference implementation, copy the structure, never the prose. Their explanatory sentences are written to teach the format to a spec reader. Our users are not that reader.
- Write every artifact as the finished version up to that point, even if it is a scaffold. Incompleteness is tracked in chat and in plan files, never in the artifact itself.

## Instructions

- Never modify this file unless explictly told.
- Never commit or do any other git operations unless explictly told.
- When developing, you must always follow the instructions and patterns described in CONTRIBUTING.md
- When told to look at a GitHub repo or the task requires it, don't do so through web search and web fetch (unless it is a reference). Instead, clone the repo to a temporary directory like in /tmp and then explore it directly.
  - For example if you need to look at the `uv` docs, clone https://github.com/astral-sh/uv into reference/ and then look at its docs/ dir. Things that might be just minor needs, clone them into tmp/.
- If you run into permission issues, STOP and tell the user about the problem. DO NOT create forks or push to other repos that are different from the submodule.
- When you are unusure, prefer to ask me questions.
- For spikes, implementing features, exploring, running/polling for test results, you should use a sub-agent so the main thread does not get polluted with too much context. Be careful about churning for too long however.
- When making PRs, commit messages, or anything that will be public. NEVER mention files, plans, designs, transcripts, that are NOT being made public unless asked.
- Always stay true first and foremost to `docs/00-vision.md`, then the `README.md`/`CONTRIBUTING.md`, then the rest of the docs. 
- When we work on something, and it will impact the docs, at the end propose to make changes to the docs to keep them up to date. Also call out if any contradictions exist.
- Prefer to ask the user more questions to clarify their needs.
- When a question is asked that means answer the question - do not start making changes, refactoring, etc. in the actual project. You *can* take separate spikes, research, etc. But you should answer the question instead of diving into changes!
- When looking for something specific that might take a while, use a sub-agent to find it. Tell the sub-agent return the location (paths) of what is found so it can be referenced easily later.
- For libraries that are new or change frequently, you must refer to their official documentation or source code, using the clones from `reference/` when its a GitHub repo.
- To figure out how `uv` works, start by using `uv --help`.

## Python Development Instructions

- This is a production-grade Python project using `uv` as the package and project manager. You must *always* follow best Python practices.
- Make sure any comments in code are necessary. A necessary comment captures intent that cannot be encoded in names, types, or structure. Comments should be reserved for the "why", only used to record rationale, trade-offs, links to specs/papers, or non-obvious domain insights. They should add signal that code cannot.
- The current code in the package should be treated as an example of high quality code. Make sure to follow its style and tackle issues in similar ways where appropriate.
- Don't generate characters that a user could not type on a standard keyboard like fancy arrows (layout trees are fine)
- Anything is possible. Do not blame external factors after something doesn't work on the first try. Instead, investigate and test assumptions through debugging through first principles.
- `ty` by Astral is used for type checking. Always add appropriate type hints such that the code would pass ty's type check.
- Follow the Google Python Style Guide.
- NEVER add imports to __init__.py files. Leave them empty unless absolutely necessary.
- Always prefer pathlib for dealing with files. Use `Path.open` instead of `open`.
- When using pathlib, **always** Use `.parents[i]` syntax to go up directories instead of using `.parent` multiple times.
- When writing tests, use pytest and pytest-asyncio.
- Prefer using loguru for logging instead of the built-in logging module. Do not add logging unless requested.
- NEVER use `# type: ignore`. It is better to leave the issue and have the user work with you to fix it.
- Don't put types in quotes unless it is absolutely necessary to avoid circular imports and forward references.
- When adding new dependencies, you **must** use `uv add <package>`. AFTER that, update the `pyproject.toml` to follow the convention for versions like the other dependencies.
- When constructing long strings like prompts for LLMs, use `python-liquid`'s `render` function:
```python
from liquid import render

print(render("Hello, {{ you }}!", you="World"))
# Hello, World!
```
- To learn about how packages work, you should read from the relevant source code. This is especially important when determining which types to use.
- Make sure to run the checks when you are done with code changes with `prek run --all-files`
- NEVER add a bare `*,` keyword-only marker to a function signature. Write plain positional-or-keyword parameters and call them by keyword.


## Key Files

@CONTRIBUTING.md
@docs/00-vision.md

## References

The `reference/` directory should be used for exemplars, references, documentation, or other notes that we want to pull from as we are working on. 
They should all be clones of only the main branch with no history to save space. 
They should also always be gitignored and not impact anything else (like pytest discovery, formatters, etc). 
The repos that we have exemplars are (add to the list as we get more, the one exception to modifying this file):

- https://github.com/microsoft/eval-recipes
- https://github.com/microsoft/amplifier-bundle-evaluation
- https://github.com/prime-radiant-inc/smevals
- https://github.com/UKGovernmentBEIS/inspect_ai
- https://github.com/harbor-framework/harbor
- https://github.com/anomalyco/opencode
- https://github.com/github/copilot-sdk
- https://github.com/astral-sh/ty
- https://github.com/astral-sh/uv
- https://github.com/astral-sh/ruff
- https://github.com/fastapi/typer
- https://github.com/prettier/prettier
- https://github.com/prettier/prettier-vscode
- https://github.com/prettier/eslint-config-prettier
- https://github.com/tailwindlabs/prettier-plugin-tailwindcss

