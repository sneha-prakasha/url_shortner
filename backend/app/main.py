"""App entry point. Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import init_db
from .routers import auth, links, redirect


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # create tables (waits for MySQL if needed)
    yield


app = FastAPI(
    title="snip API",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(links.router)
# The redirect router has the catch-all /{code} route, so it must be included LAST
app.include_router(redirect.router)
