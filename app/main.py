"""Aplikasi utama FastAPI SUKU-Monitor."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.models.database import init_db
from app.routers import web

# Pastikan NO_PROXY bersih dari [::1] agar httpx tidak crash
for env_key in ("NO_PROXY", "no_proxy"):
    if env_key in os.environ and "[::1]" in os.environ[env_key]:
        os.environ[env_key] = os.environ[env_key].replace("[::1]", "").strip(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inisialisasi database saat startup
    init_db()
    print("[INFO] Database SUKU-Monitor siap.")
    yield


app = FastAPI(
    title="SUKU-Monitor",
    description="Sistem Monitoring Publikasi & Opini Media Independen UIN Sunan Kudus",
    version="1.0.0",
    lifespan=lifespan,
)

# Router
app.include_router(web.router)
