import os
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Category, AppSettings

DEFAULT_CATEGORIES = [
    {"name": "Salario", "type": "income", "color": "#10b981"},
    {"name": "Freela / Extra", "type": "income", "color": "#34d399"},
    {"name": "Investimentos", "type": "income", "color": "#3b82f6"},
    {"name": "Moradia", "type": "expense", "color": "#f59e0b"},
    {"name": "Alimentacao", "type": "expense", "color": "#ef4444"},
    {"name": "Transporte", "type": "expense", "color": "#8b5cf6"},
    {"name": "Saude", "type": "expense", "color": "#ec4899"},
    {"name": "Lazer", "type": "expense", "color": "#06b6d4"},
    {"name": "Educacao", "type": "expense", "color": "#6366f1"},
    {"name": "Outros", "type": "expense", "color": "#6b7280"},
]

# Cache em memoria por instancia para evitar consultas repetidas no mesmo usuario
_seeded_users: set[str] = set()


def reset_seeded_cache() -> None:
    """Limpa cache em memoria de usuarios ja inicializados (util em testes)."""
    _seeded_users.clear()


def seed_user_defaults(db: Session, user_id: str) -> None:
    """Insere categorias e configuracoes iniciais para um usuario especifico."""
    has_categories = (
        db.query(Category.id).filter(Category.user_id == user_id).first() is not None
    )
    if not has_categories:
        categories = [Category(user_id=user_id, **cat) for cat in DEFAULT_CATEGORIES]
        db.add_all(categories)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    existing_keys = {
        row[0]
        for row in db.query(AppSettings.key)
        .filter(AppSettings.user_id == user_id)
        .all()
    }
    setting_defaults = {
        "email_host": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
        "email_port": os.getenv("EMAIL_PORT", "587"),
        "email_user": os.getenv("EMAIL_USER", ""),
        "email_password": os.getenv("EMAIL_PASSWORD", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        "cdi_rate": os.getenv("CDI_RATE", "10.5"),
        "ipca_rate": os.getenv("IPCA_RATE", "4.5"),
        "selic_rate": os.getenv("SELIC_RATE", "13.75"),
        "selic_last_update": "",
        "alerts_enabled": "true",
    }
    added = False
    for key, value in setting_defaults.items():
        if key not in existing_keys:
            db.add(AppSettings(user_id=user_id, key=key, value=value))
            added = True
    if added:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()


def ensure_user_seeded(db: Session, user_id: str) -> None:
    """Garante de forma idempotente e rapida que o usuario possui dados iniciais."""
    if user_id in _seeded_users:
        return
    seed_user_defaults(db, user_id)
    _seeded_users.add(user_id)
