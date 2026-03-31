from datetime import UTC, datetime, timedelta
import base64
import hashlib
import hmac
import os

from jose import jwt
from .config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = hashed_password.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False

        derived = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            base64.b64decode(salt_b64.encode('utf-8')),
            int(iterations),
        )
        return hmac.compare_digest(base64.b64encode(derived).decode('utf-8'), digest_b64)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    iterations = 310000
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{base64.b64encode(salt).decode('utf-8')}$"
        f"{base64.b64encode(derived).decode('utf-8')}"
    )


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {'sub': subject, 'exp': expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
