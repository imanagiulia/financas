import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import CRON_SECRET
from database import get_db
from app.services.notification_service import check_and_send_daily_alerts, send_monthly_summary
from app.services.selic_service import sync_selic_rate

router = APIRouter()


def verify_cron_secret(authorization: str | None = Header(default=None)) -> None:
    """Protege endpoints de agendamentos (Vercel Schedules / Cron) usando CRON_SECRET."""
    if not CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET nao configurado no servidor.",
        )
    expected = f"Bearer {CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autorizado.",
        )


@router.post("/daily-selic", dependencies=[Depends(verify_cron_secret)])
@router.get("/daily-selic", dependencies=[Depends(verify_cron_secret)])
def run_daily_selic(db: Session = Depends(get_db)):
    """Atualiza a taxa Selic oficial pelo Banco Central para todos os usuarios."""
    result = sync_selic_rate(db)
    return {"ok": result.get("success", False), "result": result}


@router.post("/daily-alerts", dependencies=[Depends(verify_cron_secret)])
@router.get("/daily-alerts", dependencies=[Depends(verify_cron_secret)])
def run_daily_alerts(db: Session = Depends(get_db)):
    """Dispara alertas diarios de vencimentos para usuarios com alertas habilitados."""
    sent = check_and_send_daily_alerts(db)
    return {"ok": True, "emails_sent": sent}


@router.post("/monthly-summary", dependencies=[Depends(verify_cron_secret)])
@router.get("/monthly-summary", dependencies=[Depends(verify_cron_secret)])
def run_monthly_summary(db: Session = Depends(get_db)):
    """Envia resumo mensal consolidado para usuarios com alertas habilitados."""
    sent = send_monthly_summary(db)
    return {"ok": True, "emails_sent": sent}
