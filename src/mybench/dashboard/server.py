"""Serve Dashboard: the compiled web app shipped with the package and the JSON API it reads."""

from pathlib import Path
import threading
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
import uvicorn

from mybench.core import benchmark, results
from mybench.schemas import MyBenchError, TaskResult
from mybench.settings import benchmark_home

STATIC_DIR = Path(__file__).parent / "static"


def serialize_result(result: TaskResult, home: Path) -> dict[str, Any]:
    """A TaskResult as the API returns it: the run path relative to the benchmark, plus the aggregate score."""
    data = result.model_dump(mode="json")
    data["path"] = result.path.relative_to(home).as_posix()
    data["score"] = result.score
    return data


def create_app() -> FastAPI:
    app = FastAPI(title="MyBench Dashboard")

    @app.exception_handler(MyBenchError)
    async def mybench_error(request: Request, error: MyBenchError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(error)})

    @app.get("/api/results")
    def get_results(
        model: Annotated[list[str] | None, Query()] = None,
        task: Annotated[list[str] | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        home = benchmark_home()
        return [serialize_result(result, home) for result in results.load_results(model, task)]

    @app.get("/api/tasks")
    def get_tasks() -> list[dict[str, Any]]:
        home = benchmark_home()
        return [benchmark.load_task(task_dir).model_dump(mode="json") for task_dir in benchmark.list_tasks(home)]

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        config = benchmark.load_config(benchmark_home())
        return {"models": config.models, "grading_model": config.grading_model}

    @app.get("/api/runs/{task_id}/{model_slug}/{timestamp}/files/{file_path:path}")
    def get_run_file(task_id: str, model_slug: str, timestamp: str, file_path: str) -> FileResponse:
        runs_dir = (benchmark_home() / "runs").resolve()
        run_dir = (runs_dir / task_id / model_slug / timestamp).resolve()
        target = (run_dir / file_path).resolve()
        inside = run_dir.parents[2] == runs_dir and target.is_relative_to(run_dir)
        if not inside or not target.is_file():
            raise HTTPException(status_code=404, detail=f"No file {file_path} in run {task_id}/{model_slug}/{timestamp}.")
        return FileResponse(target)

    @app.get("/{page_path:path}", include_in_schema=False)
    def spa(page_path: str) -> Response:
        index = STATIC_DIR / "index.html"
        if not index.is_file():
            return PlainTextResponse(
                "The dashboard is not compiled. Run `pnpm --dir dashboard build` from the repository root.",
                status_code=503,
            )
        candidate = (STATIC_DIR / page_path).resolve()
        if page_path and candidate.is_relative_to(STATIC_DIR.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    return app


def serve_dashboard(port: int | None = None, host: str = "127.0.0.1") -> str:
    """Serve the dashboard from a background thread and describe how it is hosted.

    The benchmark must be registered; a free port is chosen when none is given. The server
    thread is a daemon, so it lives until the process exits.
    """
    benchmark_home()
    config = uvicorn.Config(create_app(), host=host, port=port or 0, log_level="warning")
    server = uvicorn.Server(config)
    socket = config.bind_socket()
    bound_host, bound_port = socket.getsockname()[:2]
    thread = threading.Thread(target=server.run, kwargs={"sockets": [socket]}, daemon=True)
    thread.start()
    reachable = "only this machine" if host == "127.0.0.1" else f"the local network (bound to {bound_host})"
    display_host = "127.0.0.1" if host in ("127.0.0.1", "0.0.0.0") else host
    return f"Dashboard at http://{display_host}:{bound_port}, reachable from {reachable}."
