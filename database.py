"""
Re-exportacoes para compatibilidade retroativa.
A implementacao centralizada agora reside em app.core.database.
"""
from app.core.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
