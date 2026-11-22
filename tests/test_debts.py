import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.security import AuthUser
from models import Debt
from app.api.v1.debts import list_debts, reorder_debts
from schemas import DebtReorder

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


class TestDebtsReorder(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()
        self.user_a = AuthUser(id=USER_A, email="a@example.com")
        self.user_b = AuthUser(id=USER_B, email="b@example.com")

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_debt_ordering_reorder_and_isolation(self):
        d1 = Debt(id=1, user_id=USER_A, name="Divida 1", total_amount=100.0, paid_amount=0.0, display_order=0)
        d2 = Debt(id=2, user_id=USER_A, name="Divida 2", total_amount=200.0, paid_amount=0.0, display_order=1)
        d3 = Debt(id=3, user_id=USER_A, name="Divida 3", total_amount=300.0, paid_amount=0.0, display_order=2)
        d4 = Debt(id=4, user_id=USER_B, name="Divida Outro", total_amount=400.0, paid_amount=0.0, display_order=0)
        self.db.add_all([d1, d2, d3, d4])
        self.db.commit()

        # Listagem isolada por usuario
        debts_a = list_debts(current_user=self.user_a, db=self.db)
        self.assertEqual([d["id"] for d in debts_a], [1, 2, 3])

        debts_b = list_debts(current_user=self.user_b, db=self.db)
        self.assertEqual([d["id"] for d in debts_b], [4])

        # Reorder de USER_A nao afeta USER_B (mesmo se tentar incluir id 4)
        reorder_debts(data=DebtReorder(debt_ids=[3, 1, 2, 4]), current_user=self.user_a, db=self.db)

        debts_after = list_debts(current_user=self.user_a, db=self.db)
        self.assertEqual([d["id"] for d in debts_after], [3, 1, 2])
        self.assertEqual(debts_after[0]["display_order"], 0)
        self.assertEqual(debts_after[1]["display_order"], 1)
        self.assertEqual(debts_after[2]["display_order"], 2)

        # Divida de USER_B manteve display_order=0
        debts_b_after = list_debts(current_user=self.user_b, db=self.db)
        self.assertEqual(debts_b_after[0]["display_order"], 0)


if __name__ == "__main__":
    unittest.main()
