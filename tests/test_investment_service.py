import unittest
from datetime import date, timedelta
from app.services.investment_service import calculate_yield, round_brl


class TestInvestmentService(unittest.TestCase):

    def test_round_brl(self):
        self.assertEqual(round_brl(10.556), 10.56)
        self.assertEqual(round_brl(10.554), 10.55)
        self.assertEqual(round_brl(10), 10.0)

    def test_calculate_yield_prefixado_exact_one_year(self):
        start = date(2025, 1, 1)
        ref = date(2026, 1, 1)  # 365 days
        result = calculate_yield(
            invested_amount=1000.0,
            rate=10.0,  # 10% a.a.
            rate_type="prefixado",
            start_date=start,
            reference_date=ref,
        )
        self.assertEqual(result["days_elapsed"], 365)
        self.assertAlmostEqual(result["current_value"], 1100.0, places=2)
        self.assertAlmostEqual(result["gain"], 100.0, places=2)
        self.assertAlmostEqual(result["gain_pct"], 10.0, places=2)

    def test_calculate_yield_cdi_100_pct(self):
        start = date(2025, 1, 1)
        ref = date(2026, 1, 1)  # 365 days
        # 100% do CDI, onde CDI = 12% a.a.
        result = calculate_yield(
            invested_amount=1000.0,
            rate=100.0,
            rate_type="cdi",
            start_date=start,
            cdi_rate=12.0,
            reference_date=ref,
        )
        self.assertAlmostEqual(result["current_value"], 1120.0, places=2)
        self.assertAlmostEqual(result["gain"], 120.0, places=2)

    def test_calculate_yield_cdi_120_pct(self):
        start = date(2025, 1, 1)
        ref = date(2026, 1, 1)  # 365 days
        # 120% do CDI (10% a.a.) -> taxa efetiva = 12% a.a.
        result = calculate_yield(
            invested_amount=1000.0,
            rate=120.0,
            rate_type="cdi",
            start_date=start,
            cdi_rate=10.0,
            reference_date=ref,
        )
        self.assertAlmostEqual(result["current_value"], 1120.0, places=2)
        self.assertAlmostEqual(result["gain"], 120.0, places=2)

    def test_calculate_yield_ipca_plus_spread(self):
        start = date(2025, 1, 1)
        ref = date(2026, 1, 1)  # 365 days
        # IPCA = 5% a.a., taxa adicional = 6% a.a.
        # (1 + 0.05)*(1 + 0.06) - 1 = 1.113 - 1 = 11.3%
        result = calculate_yield(
            invested_amount=1000.0,
            rate=6.0,
            rate_type="ipca",
            start_date=start,
            ipca_rate=5.0,
            reference_date=ref,
        )
        self.assertAlmostEqual(result["current_value"], 1113.0, places=2)
        self.assertAlmostEqual(result["gain"], 113.0, places=2)

    def test_calculation_freezes_after_end_date(self):
        start = date(2025, 1, 1)
        end = date(2025, 7, 2)  # ~182 days
        ref = date(2026, 1, 1)  # End date passed
        result = calculate_yield(
            invested_amount=1000.0,
            rate=10.0,
            rate_type="prefixado",
            start_date=start,
            end_date=end,
            reference_date=ref,
        )
        # Deve calcular apenas ate o end_date
        self.assertEqual(result["days_elapsed"], (end - start).days)

    def test_zero_invested_amount(self):
        start = date(2025, 1, 1)
        result = calculate_yield(
            invested_amount=0.0,
            rate=10.0,
            rate_type="prefixado",
            start_date=start,
            reference_date=start,
        )
        self.assertEqual(result["current_value"], 0.0)
        self.assertEqual(result["gain"], 0.0)
        self.assertEqual(result["gain_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
