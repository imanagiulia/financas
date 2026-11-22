from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date


# ─── Category ─────────────────────────────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str
    type: str  # income | expense
    color: Optional[str] = "#6366f1"

class CategoryOut(CategoryCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─── Transaction ──────────────────────────────────────────────────────────────
class TransactionCreate(BaseModel):
    description: str
    amount: float
    type: str  # income | expense
    category_id: Optional[int] = None
    date: date
    notes: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    description: str
    amount: float
    type: str
    category_id: Optional[int]
    category: Optional[CategoryOut]
    date: date
    notes: Optional[str]
    class Config:
        from_attributes = True


# ─── Fixed Expense ────────────────────────────────────────────────────────────
class FixedExpenseCreate(BaseModel):
    name: str
    amount: float
    due_day: int
    category: Optional[str] = "Outros"

class FixedExpenseUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_day: Optional[int] = None
    category: Optional[str] = None
    active: Optional[bool] = None

class FixedExpenseOut(BaseModel):
    id: int
    name: str
    amount: float
    due_day: int
    category: str
    active: bool
    paid: Optional[bool] = False
    paid_date: Optional[date] = None
    paid_amount: Optional[float] = None
    class Config:
        from_attributes = True

class MarkPaidRequest(BaseModel):
    paid: bool
    paid_date: Optional[date] = None
    paid_amount: Optional[float] = None


# ─── Debt ─────────────────────────────────────────────────────────────────────
class DebtCreate(BaseModel):
    name: str
    creditor: Optional[str] = None
    total_amount: float
    paid_amount: Optional[float] = 0.0
    installments: Optional[int] = None
    remaining_installments: Optional[int] = None
    monthly_payment: Optional[float] = None
    interest_rate: Optional[float] = None
    due_day: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    display_order: Optional[int] = 0

class DebtUpdate(DebtCreate):
    name: Optional[str] = None
    total_amount: Optional[float] = None
    active: Optional[bool] = None
    display_order: Optional[int] = None

class DebtReorder(BaseModel):
    debt_ids: List[int]

class DebtOut(BaseModel):
    id: int
    name: str
    creditor: Optional[str]
    total_amount: float
    paid_amount: float
    installments: Optional[int]
    remaining_installments: Optional[int]
    monthly_payment: Optional[float]
    interest_rate: Optional[float]
    due_day: Optional[int]
    due_date: Optional[date]
    active: bool
    notes: Optional[str]
    display_order: Optional[int] = 0
    progress_pct: Optional[float] = 0.0
    class Config:
        from_attributes = True

class DebtPaymentCreate(BaseModel):
    amount: float
    date: date
    notes: Optional[str] = None

class DebtPaymentOut(BaseModel):
    id: int
    debt_id: int
    amount: float
    date: date
    notes: Optional[str]
    class Config:
        from_attributes = True


# ─── Investment ───────────────────────────────────────────────────────────────
class InvestmentCreate(BaseModel):
    name: str
    institution: Optional[str] = None
    type: str
    invested_amount: float
    rate: float
    rate_type: str  # prefixado | cdi | ipca | selic
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None

class InvestmentUpdate(InvestmentCreate):
    name: Optional[str] = None
    type: Optional[str] = None
    invested_amount: Optional[float] = None
    rate: Optional[float] = None
    rate_type: Optional[str] = None
    start_date: Optional[date] = None
    active: Optional[bool] = None

class InvestmentOut(BaseModel):
    id: int
    name: str
    institution: Optional[str]
    type: str
    invested_amount: float
    rate: float
    rate_type: str
    start_date: date
    end_date: Optional[date]
    active: bool
    notes: Optional[str]
    current_value: Optional[float] = None
    gain: Optional[float] = None
    gain_pct: Optional[float] = None
    days_elapsed: Optional[int] = None
    is_exempt: Optional[bool] = False
    iof_rate: Optional[float] = None
    iof_amount: Optional[float] = None
    ir_rate: Optional[float] = None
    ir_amount: Optional[float] = None
    total_tax: Optional[float] = None
    net_gain: Optional[float] = None
    net_value: Optional[float] = None
    net_gain_pct: Optional[float] = None
    class Config:
        from_attributes = True


# ─── Settings ─────────────────────────────────────────────────────────────────
class SettingsUpdate(BaseModel):
    email_host: Optional[str] = None
    email_port: Optional[int] = None
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_to: Optional[str] = None
    cdi_rate: Optional[float] = None
    ipca_rate: Optional[float] = None
    selic_rate: Optional[float] = None
    alerts_enabled: Optional[bool] = None
