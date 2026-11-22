from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "income" | "expense"
    color = Column(String, default="#6366f1")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # "income" | "expense"
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    category = relationship("Category", back_populates="transactions")


class FixedExpense(Base):
    __tablename__ = "fixed_expenses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    due_day = Column(Integer, nullable=False)  # dia do mes
    category = Column(String, default="Outros")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    payments = relationship(
        "FixedExpensePayment",
        back_populates="expense",
        cascade="all, delete-orphan",
    )


class FixedExpensePayment(Base):
    __tablename__ = "fixed_expense_payments"
    __table_args__ = (
        UniqueConstraint("expense_id", "year", "month", name="uq_fixed_payment_period"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    expense_id = Column(Integer, ForeignKey("fixed_expenses.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    paid = Column(Boolean, default=False)
    paid_date = Column(Date, nullable=True)
    paid_amount = Column(Float, nullable=True)
    expense = relationship("FixedExpense", back_populates="payments")


class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    name = Column(String, nullable=False)
    creditor = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    installments = Column(Integer, nullable=True)       # total de parcelas
    remaining_installments = Column(Integer, nullable=True)
    monthly_payment = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)        # % ao mes
    due_day = Column(Integer, nullable=True)            # dia do mes do vencimento
    due_date = Column(Date, nullable=True)              # para dividas nao parceladas
    active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    payments = relationship(
        "DebtPayment",
        back_populates="debt",
        cascade="all, delete-orphan",
    )


class DebtPayment(Base):
    __tablename__ = "debt_payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    debt = relationship("Debt", back_populates="payments")


class Investment(Base):
    __tablename__ = "investments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    name = Column(String, nullable=False)
    institution = Column(String, nullable=True)
    type = Column(String, nullable=False)   # Tesouro Selic, Tesouro IPCA, CDB, LCI, LCA, Poupanca, etc.
    invested_amount = Column(Float, nullable=False)
    rate = Column(Float, nullable=False)    # percentual
    rate_type = Column(String, nullable=False)  # "prefixado" | "cdi" | "ipca" | "selic"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_app_settings_user_key"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Uuid(as_uuid=False), nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(Text)
