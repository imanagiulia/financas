from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Investment
from schemas import InvestmentCreate, InvestmentUpdate
from auth import AuthUser, get_current_user
from app.services.investment_service import calculate_yield
from app.services.dashboard_service import get_rate_setting

router = APIRouter()


def _get_investment_calc(inv: Investment, db: Session, user_id: str) -> dict:
    cdi_rate = get_rate_setting(db, "cdi_rate", 10.5, user_id=user_id)
    ipca_rate = get_rate_setting(db, "ipca_rate", 4.5, user_id=user_id)
    selic_rate = get_rate_setting(db, "selic_rate", 13.75, user_id=user_id)
    return calculate_yield(
        invested_amount=inv.invested_amount,
        rate=inv.rate,
        rate_type=inv.rate_type,
        start_date=inv.start_date,
        end_date=inv.end_date,
        cdi_rate=cdi_rate,
        ipca_rate=ipca_rate,
        selic_rate=selic_rate,
        inv_type=inv.type,
    )


@router.get("")
def list_investments(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    investments = (
        db.query(Investment)
        .filter(Investment.user_id == current_user.id)
        .order_by(Investment.created_at.desc())
        .all()
    )
    result = []
    for i in investments:
        calc = _get_investment_calc(i, db, current_user.id)
        row = {c.name: getattr(i, c.name) for c in i.__table__.columns}
        row.update(calc)
        result.append(row)
    return result


@router.post("")
def create_investment(
    data: InvestmentCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    i = Investment(user_id=current_user.id, **data.model_dump())
    db.add(i)
    db.commit()
    db.refresh(i)
    calc = _get_investment_calc(i, db, current_user.id)
    return {**{c.name: getattr(i, c.name) for c in i.__table__.columns}, **calc}


@router.put("/{iid}")
def update_investment(
    iid: int,
    data: InvestmentUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    i = (
        db.query(Investment)
        .filter(Investment.id == iid, Investment.user_id == current_user.id)
        .first()
    )
    if not i:
        raise HTTPException(status_code=404, detail="Investimento nao encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(i, k, v)
    db.commit()
    db.refresh(i)
    calc = _get_investment_calc(i, db, current_user.id)
    return {**{c.name: getattr(i, c.name) for c in i.__table__.columns}, **calc}


@router.delete("/{iid}")
def delete_investment(
    iid: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    i = (
        db.query(Investment)
        .filter(Investment.id == iid, Investment.user_id == current_user.id)
        .first()
    )
    if not i:
        raise HTTPException(status_code=404, detail="Investimento nao encontrado")
    db.delete(i)
    db.commit()
    return {"ok": True}
