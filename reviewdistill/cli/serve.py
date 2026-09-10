from __future__ import annotations

import typer
import uvicorn


def build_uvicorn_args(host: str, port: int) -> dict:
    return {"app": "reviewdistill.web.app:app", "host": host, "port": port}


def run_serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    typer.echo(f"ReviewDistill workbench at http://{host}:{port}")
    uvicorn.run(**build_uvicorn_args(host, port))
