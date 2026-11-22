from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FixedExpense, FixedExpensePayment
from schemas import FixedExpenseCreate, FixedExpenseUpdate, MarkPaidRequest
from auth import AuthUser, get_current_user
from app.services.dashboard_service import get_fixed_payment

router = APIRouter()


@router.get("")
def list_fixed_expenses(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    y = year or today.year
    m = month or today.month
    expenses = (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == current_user.id, FixedExpense.active == True)
        .all()
    )
    result = []
    for fe in expenses:
        p = get_fixed_payment(db, fe.id, y, m, user_id=current_user.id)
        result.append({
            "id": fe.id,
            "name": fe.name,
            "amount": fe.amount,
            "due_day": fe.due_day,
            "category": fe.category,
            "active": fe.active,
            "paid": p.paid if p else False,
            "paid_date": str(p.paid_date) if (p and p.paid_date) else None,
            "paid_amount": p.paid_amount if (p and p.paid_amount) else None,
        })
    return result


@router.get("/all")
def list_all_fixed_expenses(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(FixedExpense)
        .filter(FixedExpense.user_id == current_user.id)
        .all()
    )


@router.post("")
def create_fixed_expense(
    data: FixedExpenseCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fe = FixedExpense(user_id=current_user.id, **data.model_dump())
    db.add(fe)
    db.commit()
    db.refresh(fe)
    return fe


@router.put("/{feid}")
def update_fixed_expense(
    feid: int,
    data: FixedExpenseUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fe = (
        db.query(FixedExpense)
        .filter(FixedExpense.id == feid, FixedExpense.user_id == current_user.id)
        .first()
    )
    if not fe:
        raise HTTPException(status_code=404, detail="Conta fixa nao encontrada")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(fe, k, v)
    db.commit()
    db.refresh(fe)
    return fe


@router.delete("/{feid}")
def delete_fixed_expense(
    feid: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fe = (
        db.query(FixedExpense)
        .filter(FixedExpense.id == feid, FixedExpense.user_id == current_user.id)
        .first()
    )
    if not fe:
        raise HTTPException(status_code=404, detail="Conta fixa nao encontrada")
    db.delete(fe)
    db.commit()
    return {"ok": True}


@router.put("/{feid}/payment/{year}/{month}")
def mark_payment(
    feid: int,
    year: int,
    month: int,
    data: MarkPaidRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fe = (
        db.query(FixedExpense)
        .filter(FixedExpense.id == feid, FixedExpense.user_id == current_user.id)
        .first()
    )
    if not fe:
        raise HTTPException(status_code=404, detail="Conta fixa nao encontrada")
    p = get_fixed_payment(db, feid, year, month, user_id=current_user.id)
    if not p:
        p = FixedExpensePayment(
            user_id=current_user.id,
            expense_id=feid,
            year=year,
            month=month,
        )
        db.add(p)
    p.paid = data.paid
    p.paid_date = data.paid_date
    p.paid_amount = data.paid_amount if data.paid_amount else (fe.amount if data.paid else None)
    db.commit()
    return {"ok": True}
