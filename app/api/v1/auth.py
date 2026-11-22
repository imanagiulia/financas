from fastapi import APIRouter, Depends

from app.core.config import SUPABASE_URL, SUPABASE_ANON_KEY
from auth import AuthUser, get_current_user

router = APIRouter()


@router.get("/config")
def get_auth_config():
    """Retorna a configuracao publica do Supabase Auth para o frontend."""
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
        "configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
    }


@router.get("/me")
def get_me(current_user: AuthUser = Depends(get_current_user)):
    """Retorna os dados basicos do usuario autenticado (e inicializa defaults se necessario)."""
    return {
        "id": current_user.id,
        "email": current_user.email,
    }
