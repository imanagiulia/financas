import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import FixedExpense, FixedExpensePayment, Debt, Investment, AppSettings, Transaction


def get_setting(db: Session, key: str, user_id: str, fallback: str = "") -> str:
    """Busca chave de configuracao do usuario no banco com fallback para variavel de ambiente."""
    row = (
        db.query(AppSettings)
        .filter(AppSettings.user_id == user_id, AppSettings.key == key)
        .first()
    )
    if row and row.value is not None:
        return row.value
    return os.getenv(key.upper(), fallback)


def send_email(db: Session, subject: str, html_body: str, user_id: str) -> bool:
    """Dispara email via SMTP configurado pelo usuario."""
    host = get_setting(db, "email_host", user_id, "smtp.gmail.com")
    port = int(get_setting(db, "email_port", user_id, "587"))
    user = get_setting(db, "email_user", user_id, "")
    password = get_setting(db, "email_password", user_id, "")
    to = get_setting(db, "email_to", user_id, "")

    if not user or not password or not to:
        print(f"[EMAIL] Configuracoes de e-mail incompletas para usuario {user_id}.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Financas] {subject}"
        msg["From"] = user
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to], msg.as_string())
        print(f"[EMAIL] Enviado para {to}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Erro ao enviar: {e}")
        return False


def _card(title: str, value: str, color: str = "#10b981") -> str:
    return f"""
    <div style="background:{color};color:white;border-radius:8px;padding:16px;margin:8px;display:inline-block;min-width:160px;">
        <div style="font-size:12px;opacity:.85;">{title}</div>
        <div style="font-size:22px;font-weight:bold;">{value}</div>
    </div>"""


def _fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _list_target_users(db: Session, user_id: Optional[str]) -> list[str]:
    if user_id:
        return [user_id]
    return [str(r[0]) for r in db.query(AppSettings.user_id).distinct().all()]


def _check_and_send_daily_alerts_for_user(db: Session, user_id: str) -> bool:
    alerts_enabled = get_setting(db, "alerts_enabled", user_id, "true")
    if alerts_enabled.lower() == "false":
        return False

    today = date.today()
    in_7 = today + timedelta(days=7)
    in_30 = today + timedelta(days=30)
    year, month = today.year, today.month

    sections = []

    # 1. Contas fixas pendentes com vencimento nos proximos 7 dias
    fixed_expenses = (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == user_id, FixedExpense.active == True)
        .all()
    )
    pending_fixed = []
    for fe in fixed_expenses:
        due = date(year, month, min(fe.due_day, 28))
        payment = (
            db.query(FixedExpensePayment)
            .filter(
                FixedExpensePayment.user_id == user_id,
                FixedExpensePayment.expense_id == fe.id,
                FixedExpensePayment.year == year,
                FixedExpensePayment.month == month,
            )
            .first()
        )
        if (not payment or not payment.paid) and today <= due <= in_7:
            pending_fixed.append((fe.name, fe.amount, due))

    if pending_fixed:
        rows = "".join(
            f"<tr><td style='padding:6px 12px'>{n}</td><td style='padding:6px 12px'>{_fmt(a)}</td><td style='padding:6px 12px'>{d.strftime('%d/%m/%Y')}</td></tr>"
            for n, a, d in pending_fixed
        )
        sections.append(f"""
        <h3 style="color:#f59e0b">Contas Fixas Pendentes (proximos 7 dias)</h3>
        <table border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead><tr style="background:#f3f4f6"><th style="padding:6px 12px;text-align:left">Conta</th><th style="padding:6px 12px;text-align:left">Valor</th><th style="padding:6px 12px;text-align:left">Vencimento</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>""")

    # 2. Dividas com vencimento proximo
    debts = (
        db.query(Debt)
        .filter(Debt.user_id == user_id, Debt.active == True)
        .all()
    )
    pending_debts = []
    for d in debts:
        if d.due_day:
            due = date(year, month, min(d.due_day, 28))
            if today <= due <= in_7:
                pending_debts.append((d.name, d.monthly_payment or 0, due))
        elif d.due_date and today <= d.due_date <= in_7:
            pending_debts.append((d.name, d.total_amount - d.paid_amount, d.due_date))

    if pending_debts:
        rows = "".join(
            f"<tr><td style='padding:6px 12px'>{n}</td><td style='padding:6px 12px'>{_fmt(a)}</td><td style='padding:6px 12px'>{d.strftime('%d/%m/%Y')}</td></tr>"
            for n, a, d in pending_debts
        )
        sections.append(f"""
        <h3 style="color:#ef4444">Dividas com Vencimento Proximo</h3>
        <table border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead><tr style="background:#f3f4f6"><th style="padding:6px 12px;text-align:left">Divida</th><th style="padding:6px 12px;text-align:left">Parcela</th><th style="padding:6px 12px;text-align:left">Vencimento</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>""")

    # 3. Investimentos vencendo em 30 dias
    investments = (
        db.query(Investment)
        .filter(
            Investment.user_id == user_id,
            Investment.active == True,
            Investment.end_date != None,
        )
        .all()
    )
    expiring_inv = [
        (i.name, i.invested_amount, i.end_date)
        for i in investments
        if i.end_date and today <= i.end_date <= in_30
    ]
    if expiring_inv:
        rows = "".join(
            f"<tr><td style='padding:6px 12px'>{n}</td><td style='padding:6px 12px'>{_fmt(a)}</td><td style='padding:6px 12px'>{d.strftime('%d/%m/%Y')}</td></tr>"
            for n, a, d in expiring_inv
        )
        sections.append(f"""
        <h3 style="color:#3b82f6">Investimentos Vencendo em 30 Dias</h3>
        <table border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead><tr style="background:#f3f4f6"><th style="padding:6px 12px;text-align:left">Investimento</th><th style="padding:6px 12px;text-align:left">Valor</th><th style="padding:6px 12px;text-align:left">Vencimento</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>""")

    if sections:
        body = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px">
          <h2 style="color:#10b981">Financas Pessoais - Alertas do Dia {today.strftime('%d/%m/%Y')}</h2>
          {"".join(sections)}
          <hr style="margin-top:30px;border-color:#e5e7eb">
          <p style="color:#9ca3af;font-size:12px">Este e-mail foi enviado automaticamente pelo seu sistema de Financas Pessoais.</p>
        </body></html>"""
        return send_email(db, f"Alertas do dia {today.strftime('%d/%m/%Y')}", body, user_id=user_id)
    return False


def check_and_send_daily_alerts(db: Session, user_id: Optional[str] = None) -> int:
    """Verifica e dispara alertas diarios para um usuario ou todos os usuarios."""
    sent = 0
    for uid in _list_target_users(db, user_id):
        if _check_and_send_daily_alerts_for_user(db, uid):
            sent += 1
    return sent


def _send_monthly_summary_for_user(db: Session, user_id: str) -> bool:
    alerts_enabled = get_setting(db, "alerts_enabled", user_id, "true")
    if alerts_enabled.lower() == "false":
        return False

    today = date.today()
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1

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

    expense = (
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

    fixed_expenses = (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == user_id, FixedExpense.active == True)
        .all()
    )
    fixed_total = sum(fe.amount for fe in fixed_expenses)

    total_invested = (
        db.query(func.sum(Investment.invested_amount))
        .filter(Investment.user_id == user_id, Investment.active == True)
        .scalar()
        or 0.0
    )
    total_debt = (
        db.query(func.sum(Debt.total_amount - Debt.paid_amount))
        .filter(Debt.user_id == user_id, Debt.active == True)
        .scalar()
        or 0.0
    )

    balance = income - expense - fixed_total
    month_name = [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ][month - 1]

    body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px">
      <h2 style="color:#10b981">Resumo Mensal - {month_name}/{year}</h2>
      <div style="margin:20px 0">
        {_card("Total de Entradas", _fmt(income), "#10b981")}
        {_card("Gastos Variaveis", _fmt(expense), "#ef4444")}
        {_card("Contas Fixas", _fmt(fixed_total), "#f59e0b")}
        {_card("Saldo do Mes", _fmt(balance), "#6366f1")}
      </div>
      <hr style="border-color:#e5e7eb">
      <div style="margin:20px 0">
        {_card("Total Investido", _fmt(total_invested), "#3b82f6")}
        {_card("Total em Dividas", _fmt(total_debt), "#ef4444")}
        {_card("Patrimonio Liquido", _fmt(total_invested - total_debt), "#10b981")}
      </div>
      <hr style="margin-top:30px;border-color:#e5e7eb">
      <p style="color:#9ca3af;font-size:12px">Este e-mail foi enviado automaticamente pelo seu sistema de Financas Pessoais.</p>
    </body></html>"""
    return send_email(db, f"Resumo de {month_name}/{year}", body, user_id=user_id)


def send_monthly_summary(db: Session, user_id: Optional[str] = None) -> int:
    """Envia resumo financeiro mensal para um usuario ou todos os usuarios."""
    sent = 0
    for uid in _list_target_users(db, user_id):
        if _send_monthly_summary_for_user(db, uid):
            sent += 1
    return sent
