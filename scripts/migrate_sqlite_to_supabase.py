"""
Script para migrar dados existentes do banco local SQLite (financas.db)
para o PostgreSQL do Supabase, associando todos os registros ao user_id do Supabase Auth.

Uso:
    python scripts/migrate_sqlite_to_supabase.py --email seu-email@exemplo.com --dry-run
    python scripts/migrate_sqlite_to_supabase.py --email seu-email@exemplo.com
    python scripts/migrate_sqlite_to_supabase.py --user-id <UUID-DO-SUPABASE>
"""
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Garante importacao dos modulos da raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import models  # noqa: E402
from app.core.database import Base  # noqa: E402


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    return date.fromisoformat(s[:10])


def _parse_datetime(val) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _resolve_user_id(pg_session, user_id: Optional[str], email: Optional[str]) -> str:
    if user_id:
        return user_id.strip()
    if not email:
        raise SystemExit("Informe --user-id <UUID> ou --email <email-cadastrado-no-supabase>.")
    row = pg_session.execute(
        text("SELECT id::text FROM auth.users WHERE lower(email) = lower(:email) LIMIT 1"),
        {"email": email.strip()},
    ).fetchone()
    if not row:
        raise SystemExit(
            f"Usuario '{email}' nao encontrado em auth.users no Supabase. "
            "Crie a conta primeiro no painel do Supabase ou pela tela de cadastro da aplicacao."
        )
    return row[0]


def _read_sqlite_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not exists:
        return []
    cur.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def migrate(
    sqlite_path: str,
    database_url: str,
    user_id: Optional[str],
    email: Optional[str],
    dry_run: bool = False,
    replace: bool = False,
) -> None:
    if not Path(sqlite_path).is_file():
        raise SystemExit(f"Arquivo SQLite nao encontrado: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    try:
        categories = _read_sqlite_rows(sqlite_conn, "categories")
        transactions = _read_sqlite_rows(sqlite_conn, "transactions")
        fixed_expenses = _read_sqlite_rows(sqlite_conn, "fixed_expenses")
        fixed_payments = _read_sqlite_rows(sqlite_conn, "fixed_expense_payments")
        debts = _read_sqlite_rows(sqlite_conn, "debts")
        debt_payments = _read_sqlite_rows(sqlite_conn, "debt_payments")
        investments = _read_sqlite_rows(sqlite_conn, "investments")
        app_settings = _read_sqlite_rows(sqlite_conn, "app_settings")
    finally:
        sqlite_conn.close()

    print("=== Resumo dos dados encontrados no SQLite ===")
    print(f"  categories:             {len(categories)}")
    print(f"  transactions:           {len(transactions)}")
    print(f"  fixed_expenses:         {len(fixed_expenses)}")
    print(f"  fixed_expense_payments: {len(fixed_payments)}")
    print(f"  debts:                  {len(debts)}")
    print(f"  debt_payments:          {len(debt_payments)}")
    print(f"  investments:            {len(investments)}")
    print(f"  app_settings:           {len(app_settings)}")

    if dry_run:
        print("\n[DRY-RUN] Nenhuma alteracao foi gravada no destino.")
        return

    norm_url = _normalize_url(database_url)
    if norm_url.startswith("sqlite"):
        raise SystemExit(
            "DATABASE_URL aponta para SQLite. Informe a URL PostgreSQL do Supabase via --database-url ou .env."
        )

    connect_args = {}
    if "sslmode=" not in norm_url.lower() and "localhost" not in norm_url.lower():
        connect_args["sslmode"] = "require"

    engine = create_engine(norm_url, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    try:
        target_uid = _resolve_user_id(db, user_id=user_id, email=email)
        print(f"\nMigrando para user_id: {target_uid}")

        if replace:
            print("Limpando dados anteriores deste usuario no destino (--replace)...")
            for model in (
                models.DebtPayment,
                models.Debt,
                models.FixedExpensePayment,
                models.FixedExpense,
                models.Transaction,
                models.Category,
                models.Investment,
                models.AppSettings,
            ):
                db.query(model).filter(model.user_id == target_uid).delete()
            db.flush()

        # 1. Categories (evita duplicatas se ja existirem por nome)
        cat_map: dict[int, int] = {}
        existing_cats = {
            c.name: c.id
            for c in db.query(models.Category)
            .filter(models.Category.user_id == target_uid)
            .all()
        }
        for row in categories:
            name = row["name"]
            if name in existing_cats:
                cat_map[row["id"]] = existing_cats[name]
                continue
            c = models.Category(
                user_id=target_uid,
                name=name,
                type=row["type"],
                color=row.get("color") or "#6366f1",
            )
            db.add(c)
            db.flush()
            cat_map[row["id"]] = c.id
            existing_cats[name] = c.id

        # 2. Transactions
        for row in transactions:
            old_cid = row.get("category_id")
            t = models.Transaction(
                user_id=target_uid,
                description=row["description"],
                amount=float(row["amount"]),
                type=row["type"],
                category_id=cat_map.get(old_cid) if old_cid is not None else None,
                date=_parse_date(row["date"]),
                notes=row.get("notes"),
                created_at=_parse_datetime(row.get("created_at")),
            )
            db.add(t)

        # 3. Fixed Expenses
        fe_map: dict[int, int] = {}
        for row in fixed_expenses:
            fe = models.FixedExpense(
                user_id=target_uid,
                name=row["name"],
                amount=float(row["amount"]),
                due_day=int(row["due_day"]),
                category=row.get("category") or "Outros",
                active=bool(row.get("active", True)),
                created_at=_parse_datetime(row.get("created_at")),
            )
            db.add(fe)
            db.flush()
            fe_map[row["id"]] = fe.id

        # 4. Fixed Expense Payments
        for row in fixed_payments:
            new_fe_id = fe_map.get(row["expense_id"])
            if not new_fe_id:
                continue
            fep = models.FixedExpensePayment(
                user_id=target_uid,
                expense_id=new_fe_id,
                year=int(row["year"]),
                month=int(row["month"]),
                paid=bool(row.get("paid", False)),
                paid_date=_parse_date(row.get("paid_date")),
                paid_amount=float(row["paid_amount"]) if row.get("paid_amount") is not None else None,
            )
            db.add(fep)

        # 5. Debts
        debt_map: dict[int, int] = {}
        for row in debts:
            d = models.Debt(
                user_id=target_uid,
                name=row["name"],
                creditor=row.get("creditor"),
                total_amount=float(row["total_amount"]),
                paid_amount=float(row.get("paid_amount") or 0.0),
                installments=row.get("installments"),
                remaining_installments=row.get("remaining_installments"),
                monthly_payment=float(row["monthly_payment"]) if row.get("monthly_payment") is not None else None,
                interest_rate=float(row["interest_rate"]) if row.get("interest_rate") is not None else None,
                due_day=row.get("due_day"),
                due_date=_parse_date(row.get("due_date")),
                active=bool(row.get("active", True)),
                notes=row.get("notes"),
                display_order=row.get("display_order") or 0,
                created_at=_parse_datetime(row.get("created_at")),
            )
            db.add(d)
            db.flush()
            debt_map[row["id"]] = d.id

        # 6. Debt Payments
        for row in debt_payments:
            new_did = debt_map.get(row["debt_id"])
            if not new_did:
                continue
            dp = models.DebtPayment(
                user_id=target_uid,
                debt_id=new_did,
                amount=float(row["amount"]),
                date=_parse_date(row["date"]),
                notes=row.get("notes"),
            )
            db.add(dp)

        # 7. Investments
        for row in investments:
            inv = models.Investment(
                user_id=target_uid,
                name=row["name"],
                institution=row.get("institution"),
                type=row["type"],
                invested_amount=float(row["invested_amount"]),
                rate=float(row["rate"]),
                rate_type=row["rate_type"],
                start_date=_parse_date(row["start_date"]),
                end_date=_parse_date(row.get("end_date")),
                active=bool(row.get("active", True)),
                notes=row.get("notes"),
                created_at=_parse_datetime(row.get("created_at")),
            )
            db.add(inv)

        # 8. App Settings (upsert por chave)
        for row in app_settings:
            key = row["key"]
            val = row.get("value")
            existing = (
                db.query(models.AppSettings)
                .filter(models.AppSettings.user_id == target_uid, models.AppSettings.key == key)
                .first()
            )
            if existing:
                existing.value = val
            else:
                db.add(models.AppSettings(user_id=target_uid, key=key, value=val))

        db.commit()
        print("\nMigracao concluida com sucesso!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Migra dados do SQLite local (financas.db) para o PostgreSQL do Supabase."
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(ROOT_DIR / "financas.db"),
        help="Caminho para o arquivo financas.db (padrao: ./financas.db)",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="URL PostgreSQL do Supabase (padrao: DATABASE_URL do .env)",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("TARGET_USER_ID", ""),
        help="UUID do usuario no Supabase Auth (alternativa a --email)",
    )
    parser.add_argument(
        "--email",
        default="",
        help="E-mail do usuario cadastrado no Supabase Auth para buscar o UUID automaticamente",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra os registros encontrados sem gravar no Supabase",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Remove registros existentes desse usuario no Supabase antes de importar",
    )
    args = parser.parse_args()

    migrate(
        sqlite_path=args.sqlite_path,
        database_url=args.database_url,
        user_id=args.user_id or None,
        email=args.email or None,
        dry_run=args.dry_run,
        replace=args.replace,
    )


if __name__ == "__main__":
    main()
