import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Converte prefixo legado postgres:// para postgresql:// exigido pelo SQLAlchemy 2.0."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL: str = _normalize_database_url(
    os.getenv("DATABASE_URL", "sqlite:///./financas.db")
)

# Supabase Auth
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_ANON_KEY: str = (
    os.getenv("SUPABASE_ANON_KEY", "").strip()
    or os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
)
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "").strip()
SUPABASE_JWT_AUDIENCE: str = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip()

# Vercel / Runtime
IS_VERCEL: bool = bool(os.getenv("VERCEL"))
CRON_SECRET: str = os.getenv("CRON_SECRET", "").strip()
AUTO_CREATE_TABLES: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

# CORS (lista separada por virgula; vazio ou "*" libera todas as origens sem cookies)
_raw_cors = os.getenv("CORS_ORIGINS", "*").strip()
CORS_ORIGINS: list[str] = (
    ["*"]
    if not _raw_cors or _raw_cors == "*"
    else [o.strip() for o in _raw_cors.split(",") if o.strip()]
)
