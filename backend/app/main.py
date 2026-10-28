from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import adaptation, analytics, auth, relay, research, sessions
from app.api.routes import router
from app.core.config import settings
from app.database.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
for r in (router, auth.router, sessions.router, adaptation.router, analytics.router, research.router, relay.router):
    app.include_router(r)
