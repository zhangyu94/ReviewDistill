from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from reviewdistill.web.api import router as api_router
from reviewdistill.web.static_assets import resolve_serve_static_dir

_CLIENT_MISSING = (
    'Client UI not built. Run pip install -e ".[dev]" '
    "(Node ≥ 22 and pnpm) or python client_build.py"
)


def create_app(*, static_dir: Path | None = None) -> FastAPI:
    """JSON under ``/api``; everything else is the Vue SPA (``client/dist`` or packaged static)."""
    app = FastAPI(title="ReviewDistill")
    app.include_router(api_router, prefix="/api")

    resolved = resolve_serve_static_dir(explicit=static_dir)
    app.state.static_dir = resolved

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if (
            full_path == "api"
            or full_path.startswith("api/")
            or full_path in {"docs", "redoc", "openapi.json"}
            or full_path.startswith(("docs/", "redoc/"))
        ):
            raise HTTPException(status_code=404, detail="Not found")
        static_root = app.state.static_dir
        if static_root is None:
            raise HTTPException(status_code=503, detail=_CLIENT_MISSING)
        index = static_root / "index.html"
        candidate = (static_root / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(static_root):
            return FileResponse(candidate)
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=503, detail=_CLIENT_MISSING)

    return app


app = create_app()
