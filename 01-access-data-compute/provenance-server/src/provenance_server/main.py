"""FastAPI application entry point for the GA4GH Provenance Server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from provenance_server import __version__
from provenance_server.config import Settings, get_settings
from provenance_server.database import init_db
from provenance_server.routes import federated, query, records, workflows

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialised")
    yield


app = FastAPI(
    title="GA4GH Provenance Server",
    description=(
        "A Beacon-style API for querying workflow provenance across GA4GH federated sites. "
        "Each data element can be linked to the workflow (registered via Dockstore / TRS) "
        "that produced it, enabling cross-site provenance queries."
    ),
    version=__version__,
    lifespan=lifespan,
    contact={
        "name": "GA4GH Federated ML Hackathon",
        "url": "https://github.com/kellrott/ga4gh-fedml-hackathon-connect2026",
    },
    license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
)

app.include_router(records.router)
app.include_router(query.router)
app.include_router(workflows.router)
app.include_router(federated.router)


@app.get("/provenance/info", tags=["service-info"], summary="GA4GH service-info compatible endpoint")
async def service_info(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {
        "id": settings.service_id,
        "name": settings.service_name,
        "description": settings.service_description,
        "version": settings.service_version,
        "site": settings.site,
        "type": {
            "group": "org.ga4gh",
            "artifact": "provenance-server",
            "version": __version__,
        },
        "organization": {"name": "GA4GH", "url": "https://www.ga4gh.org"},
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "environment": "dev",
        "contactUrl": "mailto:info@ga4gh.org",
    }


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"message": "GA4GH Provenance Server — see /docs for the API"})


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "provenance_server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
