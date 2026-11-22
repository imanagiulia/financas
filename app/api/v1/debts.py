from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Debt, DebtPayment
from schemas import DebtCreate, DebtUpdate, DebtPaymentCreate, DebtReorder
from auth import AuthUser, get_current_user
from app.services.investment_service import round_brl

router = APIRouter()


@router.get("")
def list_debts(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debts = (
        db.query(Debt)
        .filter(Debt.user_id == current_user.id)
        .order_by(Debt.display_order.asc(), Debt.created_at.desc(), Debt.id.asc())
        .all()
    )
    result = []
    for d in debts:
        pct = (d.paid_amount / d.total_amount * 100) if d.total_amount > 0 else 0
        result.append({
            **{c.name: getattr(d, c.name) for c in d.__table__.columns},
            "progress_pct": round(pct, 1),
        })
    return result


@router.post("")
def create_debt(
    data: DebtCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = Debt(user_id=current_user.id, **data.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.put("/reorder")
@router.post("/reorder")
def reorder_debts(
    data: DebtReorder,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for index, debt_id in enumerate(data.debt_ids):
        (
            db.query(Debt)
            .filter(Debt.id == debt_id, Debt.user_id == current_user.id)
            .update({"display_order": index})
        )
    db.commit()
    return {"ok": True}


@router.put("/{did}")
def update_debt(
    did: int,
    data: DebtUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Debt)
        .filter(Debt.id == did, Debt.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Divida nao encontrada")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    pct = (d.paid_amount / d.total_amount * 100) if d.total_amount > 0 else 0
    return {
        **{c.name: getattr(d, c.name) for c in d.__table__.columns},
        "progress_pct": round(pct, 1),
    }


@router.delete("/{did}")
def delete_debt(
    did: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Debt)
        .filter(Debt.id == did, Debt.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Divida nao encontrada")
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.post("/{did}/payments")
def add_debt_payment(
    did: int,
    data: DebtPaymentCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Debt)
        .filter(Debt.id == did, Debt.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Divida nao encontrada")
    p = DebtPayment(user_id=current_user.id, debt_id=did, **data.model_dump())
    db.add(p)
    d.paid_amount = round_brl(d.paid_amount + data.amount)
    if d.remaining_installments and d.remaining_installments > 0:
        d.remaining_installments -= 1
    if d.paid_amount >= d.total_amount:
        d.active = False
    db.commit()
    return {"ok": True, "new_paid_amount": d.paid_amount}


@router.get("/{did}/payments")
def list_debt_payments(
    did: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Debt.id)
        .filter(Debt.id == did, Debt.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Divida nao encontrada")
    return (
        db.query(DebtPayment)
        .filter(DebtPayment.debt_id == did, DebtPayment.user_id == current_user.id)
        .order_by(DebtPayment.date.desc())
        .all()
    )
