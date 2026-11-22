import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.core.security import verify_supabase_token, AuthUser
from app.api.v1.cron import verify_cron_secret


class TestSecurity(unittest.TestCase):

    def test_verify_supabase_hs256_token(self):
        secret = "super-secret-supabase-jwt-key-32chars"
        uid = "550e8400-e29b-41d4-a716-446655440000"
        token = jwt.encode(
            {
                "sub": uid,
                "email": "user@example.com",
                "aud": "authenticated",
                "role": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            secret,
            algorithm="HS256",
        )
        user = verify_supabase_token(
            token,
            supabase_url="https://example.supabase.co",
            jwt_secret=secret,
            audience="authenticated",
        )
        self.assertIsInstance(user, AuthUser)
        self.assertEqual(user.id, uid)
        self.assertEqual(user.email, "user@example.com")

    def test_verify_supabase_expired_token_fails(self):
        secret = "super-secret-supabase-jwt-key-32chars"
        token = jwt.encode(
            {
                "sub": "550e8400-e29b-41d4-a716-446655440000",
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
            },
            secret,
            algorithm="HS256",
        )
        with self.assertRaises(jwt.ExpiredSignatureError):
            verify_supabase_token(token, supabase_url="", jwt_secret=secret)

    def test_verify_supabase_es256_jwks_token(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        uid = "11111111-2222-3333-4444-555555555555"
        supabase_url = "https://myproj.supabase.co"

        token = jwt.encode(
            {
                "sub": uid,
                "email": "es256@example.com",
                "aud": "authenticated",
                "iss": f"{supabase_url}/auth/v1",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            private_key,
            algorithm="ES256",
            headers={"kid": "test-kid"},
        )

        mock_client = MagicMock()
        mock_key = MagicMock()
        mock_key.key = public_key
        mock_client.get_signing_key_from_jwt.return_value = mock_key

        with patch("app.core.security._get_jwks_client", return_value=mock_client):
            user = verify_supabase_token(
                token,
                supabase_url=supabase_url,
                jwt_secret="",
                audience="authenticated",
            )
            self.assertEqual(user.id, uid)
            self.assertEqual(user.email, "es256@example.com")

    def test_verify_cron_secret(self):
        with patch("app.api.v1.cron.CRON_SECRET", "my-cron-secret-123456"):
            # Deve aceitar o header Bearer correto
            verify_cron_secret("Bearer my-cron-secret-123456")

            # Deve rejeitar token errado
            with self.assertRaises(HTTPException) as ctx:
                verify_cron_secret("Bearer wrong-secret")
            self.assertEqual(ctx.exception.status_code, 401)

            # Deve rejeitar ausencia de header
            with self.assertRaises(HTTPException) as ctx2:
                verify_cron_secret(None)
            self.assertEqual(ctx2.exception.status_code, 401)

        with patch("app.api.v1.cron.CRON_SECRET", ""):
            with self.assertRaises(HTTPException) as ctx3:
                verify_cron_secret("Bearer anything")
            self.assertEqual(ctx3.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
