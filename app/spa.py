"""Single-page-app serving (React-only).

Replaces the retired Jinja/HTMX page layer. FastAPI serves the built React
bundle from FRONTEND_DIST: hashed assets under /assets, and index.html for any
non-API route so client-side routes (e.g. /resident/hostels/:id) resolve on a
hard refresh. Until the bundle is built, a placeholder is served instead.
"""
import os

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import config

_PLACEHOLDER = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<title>HostelLo</title></head><body style='font-family:system-ui;padding:2rem'>"
    "<h1>HostelLo API is running</h1>"
    "<p>The React bundle has not been built yet. Build the frontend into "
    "<code>{dist}/</code> (e.g. <code>vite build</code>) and reload.</p>"
    "</body></html>"
)


def mount_spa(app: FastAPI) -> None:
    """Wire static-bundle serving + a catch-all index.html route onto the app.

    Must be called after all /api routers are registered so the catch-all only
    receives genuinely non-API paths.
    """
    dist = config.FRONTEND_DIST
    assets_dir = os.path.join(dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    index_path = os.path.join(dist, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Unmatched API/static paths are owned by their routers — never answer
        # them with the SPA shell (that would mask 404s as HTML 200s).
        if full_path == "api" or full_path.startswith(("api/", "static/")):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return HTMLResponse(_PLACEHOLDER.format(dist=dist))
