from dataclasses import dataclass
import json
import urllib.error
import urllib.request
from typing import Optional

import jwt
from jwt import PyJWKClient

from app.core.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_JWT_SECRET,
    SUPABASE_JWT_AUDIENCE,
)


@dataclass
class AuthUser:
    """Representa o usuario autenticado via Supabase Auth."""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


_jwks_clients: dict[str, PyJWKClient] = {}

ASYMMETRIC_ALGS = {"ES256", "RS256", "ES384", "RS384", "EdDSA"}


def _get_jwks_client(supabase_url: str) -> PyJWKClient:
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        _jwks_clients[jwks_url] = client
    return client


def _verify_via_supabase_api(
    token: str,
    supabase_url: str,
    supabase_anon_key: str,
    timeout: int = 5,
) -> AuthUser:
    """Fallback para validar o token diretamente no endpoint /auth/v1/user do Supabase."""
    url = f"{supabase_url.rstrip('/')}/auth/v1/user"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": supabase_anon_key,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise jwt.InvalidTokenError("Token rejeitado pelo Supabase Auth.")
            data = json.loads(resp.read().decode("utf-8"))
            user_id = data.get("id")
            if not user_id:
                raise jwt.InvalidTokenError("Resposta do Supabase Auth sem ID de usuario.")
            return AuthUser(
                id=str(user_id),
                email=data.get("email"),
                role=data.get("role", "authenticated"),
            )
    except urllib.error.HTTPError as e:
        raise jwt.InvalidTokenError(f"Token invalido ou expirado (HTTP {e.code}).") from e
    except Exception as e:
        raise jwt.InvalidTokenError(f"Falha ao validar token no Supabase Auth: {e}") from e


def verify_supabase_token(
    token: str,
    supabase_url: Optional[str] = None,
    jwt_secret: Optional[str] = None,
    anon_key: Optional[str] = None,
    audience: Optional[str] = None,
) -> AuthUser:
    """
    Valida um access_token JWT emitido pelo Supabase Auth.
    Suporta:
    1. Chaves assimetricas (ES256/RS256/EdDSA) via JWKS local (padrao moderno do Supabase).
    2. Chave simetrica (HS256) via SUPABASE_JWT_SECRET (projetos legados).
    3. Fallback via endpoint /auth/v1/user caso HS256 seja usado sem SUPABASE_JWT_SECRET.
    """
    url = (supabase_url if supabase_url is not None else SUPABASE_URL).rstrip("/")
    secret = jwt_secret if jwt_secret is not None else SUPABASE_JWT_SECRET
    key = anon_key if anon_key is not None else SUPABASE_ANON_KEY
    aud = audience if audience is not None else SUPABASE_JWT_AUDIENCE

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise jwt.InvalidTokenError("Cabecalho JWT invalido.") from e

    alg = header.get("alg", "")
    payload = None

    if alg in ASYMMETRIC_ALGS and url:
        jwks_client = _get_jwks_client(url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=aud,
            issuer=f"{url}/auth/v1",
            options={"verify_aud": True},
        )
    elif alg == "HS256" and secret:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=aud,
            options={"verify_aud": True},
        )
    elif url and key:
        return _verify_via_supabase_api(token, url, key)
    else:
        raise jwt.InvalidTokenError(
            "Configuracao do Supabase Auth incompleta no servidor (defina SUPABASE_URL e SUPABASE_ANON_KEY)."
        )

    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("Token sem identificador de usuario (sub).")

    return AuthUser(
        id=str(sub),
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )
