from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import AUTO_CREATE_TABLES, CORS_ORIGINS
from app.core.database import engine, Base
from app.api.router import api_router, describe_db_error
import models  # noqa: F401 - garante registro de todos os modelos no Base

logger = logging.getLogger("financas")

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


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Erro SQLAlchemy em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": describe_db_error(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro nao tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno ({type(exc).__name__}). Verifique os logs da Vercel ou /api/health."},
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
