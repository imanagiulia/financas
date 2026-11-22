import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from models import Transaction, FixedExpense, FixedExpensePayment, Debt, Investment
from app.services.dashboard_service import get_dashboard_summary, get_monthly_total_report

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


class TestDashboardService(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_dashboard_summary_and_monthly_report_with_user_isolation(self):
        ref_date = date(2026, 10, 5)

        # Dados do USER_A
        t1 = Transaction(user_id=USER_A, description="Salario", amount=5000.0, type="income", date=date(2026, 10, 1))
        t2 = Transaction(user_id=USER_A, description="Mercado", amount=1200.0, type="expense", date=date(2026, 10, 2))
        # Dados do USER_B (nao devem vazar para USER_A)
        t_other = Transaction(user_id=USER_B, description="Salario Outro", amount=99999.0, type="income", date=date(2026, 10, 1))
        self.db.add_all([t1, t2, t_other])

        # Conta fixa USER_A (R$ 300, paga)
        fe = FixedExpense(user_id=USER_A, name="Internet", amount=300.0, due_day=10, active=True)
        fe_other = FixedExpense(user_id=USER_B, name="Aluguel Outro", amount=4000.0, due_day=10, active=True)
        self.db.add_all([fe, fe_other])
        self.db.flush()

        p = FixedExpensePayment(user_id=USER_A, expense_id=fe.id, year=2026, month=10, paid=True, paid_amount=300.0)
        self.db.add(p)

        # Divida USER_A (R$ 1000 total, R$ 200 pago, parcela R$ 200)
        debt = Debt(
            user_id=USER_A,
            name="Cartao",
            total_amount=1000.0,
            paid_amount=200.0,
            monthly_payment=200.0,
            active=True,
            due_day=8,
        )
        debt_other = Debt(
            user_id=USER_B,
            name="Divida Outro",
            total_amount=50000.0,
            paid_amount=0.0,
            monthly_payment=1500.0,
            active=True,
        )
        self.db.add_all([debt, debt_other])

        # Investimento USER_A (R$ 10000 invested)
        inv = Investment(
            user_id=USER_A,
            name="CDB 100%",
            type="CDB",
            invested_amount=10000.0,
            rate=10.0,
            rate_type="prefixado",
            start_date=date(2026, 10, 5),
            active=True,
        )
        self.db.add(inv)
        self.db.commit()

        # Executa servico de resumo para USER_A
        summary = get_dashboard_summary(self.db, user_id=USER_A, reference_date=ref_date)

        self.assertEqual(summary["month_income"], 5000.0)
        self.assertEqual(summary["month_expense_variable"], 1200.0)
        self.assertEqual(summary["month_fixed_total"], 300.0)
        self.assertEqual(summary["month_fixed_paid"], 300.0)
        self.assertEqual(summary["month_debt_installments"], 200.0)
        self.assertEqual(summary["month_total_outflow"], 1700.0)  # 1200 + 300 + 200
        self.assertEqual(summary["month_balance"], 3300.0)       # 5000 - 1700
        self.assertEqual(summary["total_debt_remaining"], 800.0) # 1000 - 200
        self.assertEqual(summary["total_invested"], 10000.0)
        self.assertEqual(summary["net_worth"], 9200.0)           # 10000 - 800

        # Testa relatorio mensal USER_A
        report = get_monthly_total_report(self.db, year=2026, month=10, user_id=USER_A)
        self.assertEqual(report["income"], 5000.0)
        self.assertEqual(report["total_outflow"], 1700.0)
        self.assertEqual(report["balance"], 3300.0)

        # Testa isolamento para USER_B
        summary_b = get_dashboard_summary(self.db, user_id=USER_B, reference_date=ref_date)
        self.assertEqual(summary_b["month_income"], 99999.0)
        self.assertEqual(summary_b["total_invested"], 0.0)
        self.assertEqual(summary_b["total_debt_remaining"], 50000.0)


if __name__ == "__main__":
    unittest.main()
