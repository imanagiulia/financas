from datetime import date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from models import (
    Transaction,
    FixedExpense,
    FixedExpensePayment,
    Debt,
    Investment,
    AppSettings,
)
from app.services.investment_service import calculate_yield, round_brl


MONTH_ABBR = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def get_fixed_payment(
    db: Session,
    expense_id: int,
    year: int,
    month: int,
    user_id: Optional[str] = None,
) -> Optional[FixedExpensePayment]:
    """Retorna o registro de pagamento de uma despesa fixa para um determinado mes/ano."""
    q = db.query(FixedExpensePayment).filter(
        FixedExpensePayment.expense_id == expense_id,
        FixedExpensePayment.year == year,
        FixedExpensePayment.month == month,
    )
    if user_id is not None:
        q = q.filter(FixedExpensePayment.user_id == user_id)
    return q.first()


def get_rate_setting(db: Session, key: str, fallback: float, user_id: str) -> float:
    """Busca taxa parametrizada nas configuracoes do usuario ou fallback."""
    row = (
        db.query(AppSettings)
        .filter(AppSettings.user_id == user_id, AppSettings.key == key)
        .first()
    )
    if row and row.value:
        try:
            return float(row.value)
        except ValueError:
            pass
    return fallback


def get_dashboard_summary(
    db: Session,
    user_id: str,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Consolida as metricas financeiras do mes atual e patrimonio geral do usuario.
    Regra de agregacao de negocio isolada de controllers HTTP.
    """
    today = reference_date or date.today()
    year, month = today.year, today.month

    # 1. Transacoes do mes
    month_income = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "income",
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
        .scalar()
        or 0.0
    )

    month_expense = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
        .scalar()
        or 0.0
    )

    # 2. Contas fixas do mes
    fixed_expenses = (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == user_id, FixedExpense.active == True)
        .all()
    )
    fixed_total = sum(fe.amount for fe in fixed_expenses)
    fixed_paid = 0.0
    for fe in fixed_expenses:
        p = get_fixed_payment(db, fe.id, year, month, user_id=user_id)
        if p and p.paid:
            fixed_paid += p.paid_amount or fe.amount

    # 3. Dividas do mes e saldo devedor
    debts = (
        db.query(Debt)
        .filter(Debt.user_id == user_id, Debt.active == True)
        .all()
    )
    debt_monthly = sum(d.monthly_payment or 0 for d in debts)
    total_debt_remaining = sum(max(d.total_amount - d.paid_amount, 0) for d in debts)

    # 4. Investimentos e rendimentos
    cdi_rate = get_rate_setting(db, "cdi_rate", 10.5, user_id=user_id)
    ipca_rate = get_rate_setting(db, "ipca_rate", 4.5, user_id=user_id)
    selic_rate = get_rate_setting(db, "selic_rate", 13.75, user_id=user_id)

    investments = (
        db.query(Investment)
        .filter(Investment.user_id == user_id, Investment.active == True)
        .all()
    )
    total_invested = sum(i.invested_amount for i in investments)

    total_current = 0.0
    total_net = 0.0
    total_tax = 0.0
    for inv in investments:
        calc = calculate_yield(
            invested_amount=inv.invested_amount,
            rate=inv.rate,
            rate_type=inv.rate_type,
            start_date=inv.start_date,
            end_date=inv.end_date,
            cdi_rate=cdi_rate,
            ipca_rate=ipca_rate,
            selic_rate=selic_rate,
            reference_date=today,
            inv_type=inv.type,
        )
        total_current += calc["current_value"]
        total_net += calc["net_value"]
        total_tax += calc["total_tax"]

    total_gain = total_current - total_invested
    net_worth = total_net - total_debt_remaining
    total_month_outflow = month_expense + fixed_total + debt_monthly
    month_balance = month_income - total_month_outflow

    # 5. Proximos vencimentos (proximos 7 dias para contas/dividas, 30 dias para investimentos)
    in_7 = today + timedelta(days=7)
    upcoming = []

    for fe in fixed_expenses:
        try:
            due = date(year, month, fe.due_day)
        except ValueError:
            due = date(year, month, 28)
        p = get_fixed_payment(db, fe.id, year, month, user_id=user_id)
        if (not p or not p.paid) and today <= due <= in_7:
            upcoming.append({"type": "fixed", "name": fe.name, "amount": fe.amount, "due": str(due)})

    for d in debts:
        if d.due_day:
            try:
                due = date(year, month, d.due_day)
            except ValueError:
                due = date(year, month, 28)
            if today <= due <= in_7:
                upcoming.append({"type": "debt", "name": d.name, "amount": d.monthly_payment or 0, "due": str(due)})
        elif d.due_date and today <= d.due_date <= in_7:
            upcoming.append({"type": "debt", "name": d.name, "amount": d.total_amount - d.paid_amount, "due": str(d.due_date)})

    for i in investments:
        if i.end_date and today <= i.end_date <= today + timedelta(days=30):
            inv_calc = calculate_yield(
                invested_amount=i.invested_amount,
                rate=i.rate,
                rate_type=i.rate_type,
                start_date=i.start_date,
                end_date=i.end_date,
                cdi_rate=cdi_rate,
                ipca_rate=ipca_rate,
                selic_rate=selic_rate,
                reference_date=today,
                inv_type=i.type,
            )
            upcoming.append({"type": "investment", "name": i.name, "amount": inv_calc["current_value"], "due": str(i.end_date)})

    upcoming.sort(key=lambda x: x["due"])

    # 6. Cash flow ultimos 6 meses
    cashflow = []
    fe_total_active = sum(fe.amount for fe in fixed_expenses)
    for delta in range(5, -1, -1):
        d = today.replace(day=1) - timedelta(days=delta * 30)
        y, m = d.year, d.month
        inc = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == "income",
                extract("year", Transaction.date) == y,
                extract("month", Transaction.date) == m,
            )
            .scalar()
            or 0.0
        )
        exp = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                extract("year", Transaction.date) == y,
                extract("month", Transaction.date) == m,
            )
            .scalar()
            or 0.0
        )
        label = f"{MONTH_ABBR[m-1]}/{y}"
        cashflow.append({"label": label, "income": round_brl(inc), "expense": round_brl(exp + fe_total_active)})

    return {
        "month_income": round_brl(month_income),
        "month_expense_variable": round_brl(month_expense),
        "month_fixed_total": round_brl(fixed_total),
        "month_fixed_paid": round_brl(fixed_paid),
        "month_debt_installments": round_brl(debt_monthly),
        "month_total_outflow": round_brl(total_month_outflow),
        "month_balance": round_brl(month_balance),
        "total_invested": round_brl(total_invested),
        "total_current_value": round_brl(total_current),
        "total_net_value": round_brl(total_net),
        "total_tax": round_brl(total_tax),
        "total_gain": round_brl(total_gain),
        "total_debt_remaining": round_brl(total_debt_remaining),
        "net_worth": round_brl(net_worth),
        "upcoming": upcoming,
        "cashflow": cashflow,
    }


def get_monthly_total_report(db: Session, year: int, month: int, user_id: str) -> Dict[str, Any]:
    """Calcula o fechamento consolidado para um mes especifico do usuario."""
    income = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "income",
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
        .scalar()
        or 0.0
    )

    var_expense = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
        .scalar()
        or 0.0
    )

    fixed = (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == user_id, FixedExpense.active == True)
        .all()
    )
    fixed_total = sum(fe.amount for fe in fixed)
    fixed_paid = 0.0
    for fe in fixed:
        p = get_fixed_payment(db, fe.id, year, month, user_id=user_id)
        if p and p.paid:
            fixed_paid += p.paid_amount or fe.amount

    debts = (
        db.query(Debt)
        .filter(Debt.user_id == user_id, Debt.active == True)
        .all()
    )
    debt_installments = sum(d.monthly_payment or 0 for d in debts)

    total_outflow = var_expense + fixed_total + debt_installments
    balance = income - total_outflow

    return {
        "year": year,
        "month": month,
        "income": round_brl(income),
        "var_expense": round_brl(var_expense),
        "fixed_total": round_brl(fixed_total),
        "fixed_paid": round_brl(fixed_paid),
        "debt_installments": round_brl(debt_installments),
        "total_outflow": round_brl(total_outflow),
        "balance": round_brl(balance),
    }
