import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import get_settings

MAX_FILE_SIZE = 50 * 1024 * 1024


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt, expire


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex(), salt


def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return secrets.compare_digest(key.hex(), hashed_password)


def validate_file(filename: str, file_size: int = 0) -> tuple[bool, str]:
    if not filename:
        return False, "Filename cannot be empty"
    if not filename.lower().endswith(".pdf"):
        return False, "Only PDF files are supported"
    if file_size > MAX_FILE_SIZE:
        return False, f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB"
    return True, ""


def compute_file_hash(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()
