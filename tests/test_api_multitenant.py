import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.core.database import Base
from app.core.security import AuthUser
from app.services.seed_service import ensure_user_seeded, reset_seeded_cache
from app.api.v1.categories import list_categories, create_category, delete_category
from app.api.v1.transactions import create_transaction, list_transactions, delete_transaction
from app.api.v1.fixed_expenses import create_fixed_expense, list_fixed_expenses, mark_payment
from app.api.v1.investments import create_investment, list_investments
from app.api.v1.settings import get_settings, update_settings
from schemas import (
    CategoryCreate,
    TransactionCreate,
    FixedExpenseCreate,
    MarkPaidRequest,
    InvestmentCreate,
    SettingsUpdate,
)

USER_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


class TestMultiTenantIsolation(unittest.TestCase):

    def setUp(self):
        reset_seeded_cache()
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()
        self.user_a = AuthUser(id=USER_A, email="a@example.com")
        self.user_b = AuthUser(id=USER_B, email="b@example.com")

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        reset_seeded_cache()

    def test_seed_user_defaults_is_isolated_and_idempotent(self):
        ensure_user_seeded(self.db, USER_A)
        ensure_user_seeded(self.db, USER_A)  # idempotente
        ensure_user_seeded(self.db, USER_B)

        cats_a = list_categories(current_user=self.user_a, db=self.db)
        cats_b = list_categories(current_user=self.user_b, db=self.db)
        self.assertEqual(len(cats_a), 10)
        self.assertEqual(len(cats_b), 10)
        self.assertNotEqual({c.id for c in cats_a}, {c.id for c in cats_b})

    def test_cross_user_access_blocked_across_resources(self):
        ensure_user_seeded(self.db, USER_A)
        ensure_user_seeded(self.db, USER_B)

        # Categoria criada por USER_A nao pode ser usada nem apagada por USER_B
        cat_a = create_category(
            CategoryCreate(name="Bonus Exclusivo", type="income", color="#00ff00"),
            current_user=self.user_a,
            db=self.db,
        )
        with self.assertRaises(HTTPException) as ctx:
            delete_category(cat_a.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        with self.assertRaises(HTTPException) as ctx2:
            create_transaction(
                TransactionCreate(
                    description="Tentativa cruzada",
                    amount=100.0,
                    type="income",
                    category_id=cat_a.id,
                    date=date(2026, 11, 1),
                ),
                current_user=self.user_b,
                db=self.db,
            )
        self.assertEqual(ctx2.exception.status_code, 400)

        # Transacao de USER_A invisivel e protegida contra USER_B
        tx_a = create_transaction(
            TransactionCreate(
                description="Freela A",
                amount=500.0,
                type="income",
                category_id=cat_a.id,
                date=date(2026, 11, 2),
            ),
            current_user=self.user_a,
            db=self.db,
        )
        self.assertEqual(len(list_transactions(current_user=self.user_a, db=self.db)), 1)
        self.assertEqual(len(list_transactions(current_user=self.user_b, db=self.db)), 0)
        with self.assertRaises(HTTPException):
            delete_transaction(tx_a.id, current_user=self.user_b, db=self.db)

        # Conta fixa e pagamento isolados
        fe_a = create_fixed_expense(
            FixedExpenseCreate(name="Fibra", amount=120.0, due_day=15),
            current_user=self.user_a,
            db=self.db,
        )
        mark_payment(
            fe_a.id,
            2026,
            11,
            MarkPaidRequest(paid=True, paid_amount=120.0),
            current_user=self.user_a,
            db=self.db,
        )
        self.assertEqual(len(list_fixed_expenses(year=2026, month=11, current_user=self.user_a, db=self.db)), 1)
        self.assertEqual(len(list_fixed_expenses(year=2026, month=11, current_user=self.user_b, db=self.db)), 0)

        # Investimentos isolados
        create_investment(
            InvestmentCreate(
                name="Tesouro Selic",
                type="Tesouro Selic",
                invested_amount=2000.0,
                rate=0.05,
                rate_type="selic",
                start_date=date(2026, 1, 1),
            ),
            current_user=self.user_a,
            db=self.db,
        )
        self.assertEqual(len(list_investments(current_user=self.user_a, db=self.db)), 1)
        self.assertEqual(len(list_investments(current_user=self.user_b, db=self.db)), 0)

        # Configuracoes isoladas por usuario
        update_settings(SettingsUpdate(cdi_rate=11.25), current_user=self.user_a, db=self.db)
        settings_a = get_settings(current_user=self.user_a, db=self.db)
        settings_b = get_settings(current_user=self.user_b, db=self.db)
        self.assertEqual(settings_a["cdi_rate"], "11.25")
        self.assertNotEqual(settings_b["cdi_rate"], "11.25")

    def test_fastapi_app_imports_and_routes_registered(self):
        import main
        paths = {route.path for route in main.app.routes}
        self.assertIn("/", paths)
        self.assertIn("/api/health", paths)
        self.assertIn("/api/auth/config", paths)
        self.assertIn("/api/auth/me", paths)
        self.assertIn("/api/cron/daily-selic", paths)
        self.assertIn("/api/cron/daily-alerts", paths)
        self.assertIn("/api/cron/monthly-summary", paths)


if __name__ == "__main__":
    unittest.main()
