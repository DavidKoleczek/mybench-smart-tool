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

## Key Files

@CONTRIBUTING.md

## References

The `reference/` directory should be used for exemplars, references, documentation, or other notes that we want to pull from as we are working on. 
They should all be clones of only the main branch with no history to save space. They should also always be gitignored and not impact anything else (like pytest discovery, formatters, etc). The repos that we have exemplars are (add to the list as we get more, the one exception to modifying this file):

- https://github.com/microsoft/eval-recipes
- https://github.com/prime-radiant-inc/smevals
- https://github.com/UKGovernmentBEIS/inspect_ai
- https://github.com/harbor-framework/harbor
- https://github.com/anomalyco/opencode
- https://github.com/github/copilot-sdk
- https://github.com/astral-sh/ty
- https://github.com/astral-sh/uv
- https://github.com/astral-sh/ruff

