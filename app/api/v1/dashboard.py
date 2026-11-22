from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import AuthUser, get_current_user
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter()


@router.get("")
def dashboard(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db, user_id=current_user.id)
