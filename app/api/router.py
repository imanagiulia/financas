from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import DATABASE_URL, IS_VERCEL, SUPABASE_URL, SUPABASE_ANON_KEY
from app.core.database import get_db
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.categories import router as categories_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.fixed_expenses import router as fixed_expenses_router
from app.api.v1.debts import router as debts_router
from app.api.v1.investments import router as investments_router
from app.api.v1.settings import router as settings_router
from app.api.v1.reports import router as reports_router
from app.api.v1.cron import router as cron_router

api_router = APIRouter(prefix="/api")


def describe_db_error(exc: Exception) -> str:
    """Traduz erros comuns de conexao/schema do banco em mensagens claras sem vazar credenciais."""
    msg = str(exc).lower()
    if "readonly database" in msg or ("sqlite" in msg and IS_VERCEL):
        return (
            "DATABASE_URL nao esta configurada para PostgreSQL na Vercel "
            "(SQLite e somente leitura em serverless). Configure DATABASE_URL com o Transaction Pooler do Supabase."
        )
    if "network is unreachable" in msg or "cannot assign requested address" in msg:
        return (
            "Nao foi possivel conectar ao PostgreSQL via IPv6 na Vercel. "
            "Use a URI do Transaction Pooler (porta 6543, host *.pooler.supabase.com) em DATABASE_URL."
        )
    if "password authentication failed" in msg or "tenant or user not found" in msg:
        return (
            "Falha de autenticacao no banco Supabase. Verifique usuario/senha em DATABASE_URL "
            "(caracteres especiais na senha precisam de URL-encode, ex.: @ -> %40, # -> %23)."
        )
    if "does not exist" in msg and ("relation" in msg or "table" in msg):
        return (
            "Tabelas ainda nao criadas no Supabase. Execute o arquivo supabase/schema.sql no SQL Editor do Supabase."
        )
    if "could not translate host name" in msg or "name or service not known" in msg:
        return "Host de DATABASE_URL invalido ou inacessivel. Verifique a string de conexao do Supabase."
    if "timeout" in msg:
        return "Tempo esgotado ao conectar no banco Supabase. Verifique se o projeto Supabase esta ativo e usando Transaction Pooler (porta 6543)."
    return f"Erro de banco de dados ({type(exc).__name__}). Verifique DATABASE_URL e os logs da Vercel."


@api_router.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)):
    driver = "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql"
    db_ok = False
    tables_ok = False
    db_hint = None

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        db.execute(text("SELECT COUNT(*) FROM categories"))
        tables_ok = True
    except Exception as exc:
        db_hint = describe_db_error(exc)

    return {
        "status": "ok" if (db_ok and tables_ok) else "degraded",
        "database_driver": driver,
        "database_ok": db_ok,
        "tables_ok": tables_ok,
        "database_hint": db_hint,
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        "is_vercel": IS_VERCEL,
    }


api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
api_router.include_router(fixed_expenses_router, prefix="/fixed-expenses", tags=["fixed-expenses"])
api_router.include_router(debts_router, prefix="/debts", tags=["debts"])
api_router.include_router(investments_router, prefix="/investments", tags=["investments"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(cron_router, prefix="/cron", tags=["cron"])
