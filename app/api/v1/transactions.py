from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from models import Category, Transaction
from schemas import TransactionCreate, TransactionOut
from auth import AuthUser, get_current_user

router = APIRouter()


def _validate_category_ownership(db: Session, user_id: str, category_id: Optional[int]) -> None:
    if category_id is None:
        return
    exists = (
        db.query(Category.id)
        .filter(Category.id == category_id, Category.user_id == user_id)
        .first()
    )
    if not exists:
        raise HTTPException(status_code=400, detail="Categoria invalida para este usuario.")


@router.get("", response_model=List[TransactionOut])
def list_transactions(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if year:
        q = q.filter(extract("year", Transaction.date) == year)
    if month:
        q = q.filter(extract("month", Transaction.date) == month)
    return q.order_by(Transaction.date.desc()).all()


@router.post("", response_model=TransactionOut)
def create_transaction(
    data: TransactionCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_category_ownership(db, current_user.id, data.category_id)
    t = Transaction(user_id=current_user.id, **data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{tid}", response_model=TransactionOut)
def update_transaction(
    tid: int,
    data: TransactionCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = (
        db.query(Transaction)
        .filter(Transaction.id == tid, Transaction.user_id == current_user.id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")
    _validate_category_ownership(db, current_user.id, data.category_id)
    for k, v in data.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{tid}")
def delete_transaction(
    tid: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = (
        db.query(Transaction)
        .filter(Transaction.id == tid, Transaction.user_id == current_user.id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada")
    db.delete(t)
    db.commit()
    return {"ok": True}
