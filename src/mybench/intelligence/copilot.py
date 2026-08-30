"""GitHub Copilot SDK implementation of the intelligence interface."""

import asyncio
import contextlib
from importlib.metadata import version
import shutil
import subprocess
import time
from typing import Any

from copilot import CopilotClient, PermissionHandler, RuntimeConnection, Tool, ToolInvocation, ToolResult
import jsonschema

from mybench.intelligence.schemas import AgentRequest, AgentResult, ContainerWorkspace, HostWorkspace, Workspace
from mybench.schemas import MyBenchError

SUBMIT_TOOL = "submit"
MAX_INVALID_SUBMISSIONS = 2

# The token is minted from the GitHub CLI per run and reaches an in-container runtime only
# through `docker exec -e`, which propagates it from the host-side docker process's
# environment: it never appears on a command line or in the container's own environment.
TOKEN_ENV = "COPILOT_GITHUB_TOKEN"


class CopilotIntelligence:
    """Runs agents through a Copilot CLI runtime, on this machine or inside a container."""

    def __init__(self) -> None:
        self.implementation = f"copilot-sdk {version('github-copilot-sdk')}"
        self._token: str | None = None

    def preflight(self) -> None:
        self._github_token()

    def run(self, request: AgentRequest) -> AgentResult:
        client = self._client(request.workspace)
        return asyncio.run(self._run(client, request))

    def _github_token(self) -> str:
        if self._token is not None:
            return self._token
        if shutil.which("gh") is None:
            raise MyBenchError(
                "Model-backed capabilities need the GitHub CLI. Install gh and sign in with `gh auth login`."
            )
        minted = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if minted.returncode != 0:
            raise MyBenchError(
                f"The GitHub CLI is not signed in: {minted.stderr.strip()} "
                "Run `gh auth login` with an account that has Copilot access."
            )
        self._token = minted.stdout.strip()
        return self._token

    def _client(self, workspace: Workspace | None) -> CopilotClient:
        env = {TOKEN_ENV: self._github_token()}
        if isinstance(workspace, ContainerWorkspace):
            if shutil.which("docker") is None:
                raise MyBenchError("Running an agent inside the container needs the docker CLI on PATH.")
            connection = RuntimeConnection.for_stdio(
                path="docker", args=["exec", "-i", "-e", TOKEN_ENV, workspace.container_id, "copilot"]
            )
            return CopilotClient(connection=connection, env=env)
        if isinstance(workspace, HostWorkspace):
            return CopilotClient(working_directory=str(workspace.path), env=env)
        return CopilotClient(env=env)

    async def _run(self, client: CopilotClient, request: AgentRequest) -> AgentResult:
        submitted: dict[str, Any] | None = None

        def capture(invocation: ToolInvocation) -> ToolResult:
            nonlocal submitted
            submitted = invocation.arguments
            return ToolResult(text_result_for_llm="Submission received.")

        session_options: dict[str, Any] = {
            "model": request.model,
            "reasoning_effort": request.reasoning_effort,
            "on_permission_request": PermissionHandler.approve_all,
            "skip_custom_instructions": True,
            "available_tools": [],
        }
        if request.workspace is not None:
            session_options["working_directory"] = str(request.workspace.path)
            session_options["available_tools"] = ["view", "grep", "bash"]
            if request.writable:
                # bash in a HostWorkspace is not sandboxed to it; the caller's prompt bounds
                # the agent and the caller validates before anything the agent wrote is kept.
                session_options["available_tools"] = [*session_options["available_tools"], "edit", "write"]
        if request.output_schema is not None:
            session_options["tools"] = [
                Tool(
                    name=SUBMIT_TOOL,
                    description="Submit your final answer. Call it exactly once, when you are done.",
                    parameters=request.output_schema,
                    handler=capture,
                    skip_permission=True,
                    is_terminal=True,
                )
            ]
            session_options["available_tools"] = [*session_options["available_tools"], SUBMIT_TOOL]
        deadline = time.monotonic() + request.timeout_seconds
        try:
            await client.start()
            session = await client.create_session(**session_options)
            prompt = request.prompt
            invalid = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                try:
                    event = await session.send_and_wait(prompt, timeout=remaining)
                except TimeoutError:
                    await session.abort()
                    return AgentResult(error=f"The agent did not finish within {request.timeout_seconds} seconds.")
                text = str(getattr(event.data, "content", "") or "") if event is not None else ""
                if request.output_schema is None:
                    return AgentResult(text=text)
                problem = _submission_problem(submitted, request.output_schema)
                if problem is None:
                    return AgentResult(output=submitted, text=text)
                if invalid >= MAX_INVALID_SUBMISSIONS:
                    return AgentResult(text=text, error=f"No valid submission after {invalid} retries: {problem}")
                invalid += 1
                submitted = None
                prompt = (
                    f"Your answer was not accepted: {problem}. "
                    f"Call the {SUBMIT_TOOL} tool now with an answer matching its schema."
                )
        except TimeoutError:
            return AgentResult(error=f"The agent did not finish within {request.timeout_seconds} seconds.")
        except Exception as error:  # an SDK or runtime failure is the caller's data, not a crash
            return AgentResult(error=f"{type(error).__name__}: {error}")
        finally:
            with contextlib.suppress(Exception):
                await client.stop()


def _submission_problem(submitted: dict[str, Any] | None, schema: dict[str, Any]) -> str | None:
    if submitted is None:
        return f"the {SUBMIT_TOOL} tool was never called"
    try:
        jsonschema.validate(submitted, schema)
    except jsonschema.ValidationError as error:
        return f"the submission does not match the schema ({error.message})"
    return None
