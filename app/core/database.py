from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import DATABASE_URL, IS_VERCEL


def _build_engine():
    is_sqlite = DATABASE_URL.startswith("sqlite")
    if is_sqlite:
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL (Supabase)
    connect_args = {}
    parsed = urlparse(DATABASE_URL)
    hostname = (parsed.hostname or "").lower()
    is_local = hostname in ("localhost", "127.0.0.1", "::1")
    if not is_local and "sslmode=" not in (parsed.query or "").lower():
        connect_args["sslmode"] = "require"

    engine_kwargs = {
        "connect_args": connect_args,
    }

    if IS_VERCEL:
        # Serverless + Supabase PgBouncer Transaction Pooler: evita conexoes ociosas presas
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300

    return create_engine(DATABASE_URL, **engine_kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
