from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AppSettings
from schemas import SettingsUpdate
from auth import AuthUser, get_current_user
from app.services.notification_service import send_email
from app.services.selic_service import sync_selic_rate

router = APIRouter()


@router.get("")
def get_settings(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AppSettings)
        .filter(AppSettings.user_id == current_user.id)
        .all()
    )
    result = {r.key: r.value for r in rows}
    if "email_password" in result and result["email_password"]:
        result["email_password"] = "••••••••"
    return result


@router.put("")
def update_settings(
    data: SettingsUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = data.model_dump(exclude_none=True)
    for k, v in updates.items():
        if k == "email_password" and "•" in str(v):
            continue
        val_str = str(v).lower() if isinstance(v, bool) else str(v)
        row = (
            db.query(AppSettings)
            .filter(AppSettings.user_id == current_user.id, AppSettings.key == k)
            .first()
        )
        if row:
            row.value = val_str
        else:
            db.add(AppSettings(user_id=current_user.id, key=k, value=val_str))
    db.commit()
    return {"ok": True}


@router.post("/test-email")
def test_email(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = send_email(
        db,
        "Teste de E-mail",
        "<h2>Funcionou!</h2><p>Seu sistema de financas esta configurado corretamente.</p>",
        user_id=current_user.id,
    )
    if ok:
        return {"ok": True, "message": "E-mail de teste enviado com sucesso!"}
    raise HTTPException(
        status_code=500,
        detail="Falha ao enviar e-mail. Verifique as configuracoes.",
    )


@router.post("/sync-selic")
def sync_selic(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = sync_selic_rate(db, user_id=current_user.id)
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("message", "Falha ao sincronizar com o Banco Central."),
        )
    return result
