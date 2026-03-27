from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.base import init_db

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="AI-powered Indian tax assistant",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "taxsage-ai"}


@app.get("/")
async def root() -> dict:
    return {"message": "TaxSage AI is running"}
