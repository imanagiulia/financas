import os
from dotenv import load_dotenv

load_dotenv()


def _clean_env(name: str, default: str = "") -> str:
    val = os.getenv(name, default).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1].strip()
    return val


def _normalize_database_url(url: str) -> str:
    """Converte prefixo legado postgres:// para postgresql:// exigido pelo SQLAlchemy 2.0."""
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL: str = _normalize_database_url(
    _clean_env("DATABASE_URL", "sqlite:///./financas.db")
)

# Supabase Auth
SUPABASE_URL: str = _clean_env("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY: str = (
    _clean_env("SUPABASE_ANON_KEY", "")
    or _clean_env("SUPABASE_PUBLISHABLE_KEY", "")
)
SUPABASE_JWT_SECRET: str = _clean_env("SUPABASE_JWT_SECRET", "")
SUPABASE_JWT_AUDIENCE: str = _clean_env("SUPABASE_JWT_AUDIENCE", "authenticated")

# Vercel / Runtime
IS_VERCEL: bool = bool(os.getenv("VERCEL"))
CRON_SECRET: str = _clean_env("CRON_SECRET", "")
AUTO_CREATE_TABLES: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

# CORS (lista separada por virgula; vazio ou "*" libera todas as origens sem cookies)
_raw_cors = os.getenv("CORS_ORIGINS", "*").strip()
CORS_ORIGINS: list[str] = (
    ["*"]
    if not _raw_cors or _raw_cors == "*"
    else [o.strip() for o in _raw_cors.split(",") if o.strip()]
)
