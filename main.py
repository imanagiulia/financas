from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import AUTO_CREATE_TABLES, CORS_ORIGINS
from app.core.database import engine, Base
from app.api.router import api_router
import models  # noqa: F401 - garante registro de todos os modelos no Base

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if AUTO_CREATE_TABLES:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[STARTUP] Aviso ao inicializar tabelas: {e}")

    yield


app = FastAPI(
    title="Financas Pessoais",
    version="3.0.0",
    lifespan=lifespan,
)

allow_credentials = "*" not in CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# Registra todos os modulos de rotas da aplicacao
app.include_router(api_router)
