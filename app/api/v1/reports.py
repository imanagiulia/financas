from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import AuthUser, get_current_user
from app.services.dashboard_service import get_monthly_total_report

router = APIRouter()


@router.get("/monthly-total")
def monthly_total(
    year: int,
    month: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_monthly_total_report(db, year=year, month=month, user_id=current_user.id)
