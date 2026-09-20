from fastapi import APIRouter, HTTPException, Header
from app.db.database import get_session_factory
from app.db.repositories import UserRepository
from app.schemas.auth import SignUpRequest, SignInRequest, AuthResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    email = request.email.lower().strip()
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    factory = get_session_factory()
    async with factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email)
        if existing:
            raise HTTPException(status_code=400, detail="An account with this email already exists")

        hashed_pw, salt = hash_password(request.password)
        user = await repo.create(email=email, hashed_password=hashed_pw, salt=salt)
        logger.info("user_registered", email=email, user_id=str(user.id))

        token, expires_at = create_access_token({"sub": str(user.id), "email": user.email})
        return AuthResponse(
            user=UserResponse(id=str(user.id), email=user.email),
            token=token,
            expires_at=expires_at,
        )


@router.post("/signin", response_model=AuthResponse)
async def signin(request: SignInRequest):
    email = request.email.lower().strip()
    factory = get_session_factory()
    async with factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email(email)
        if not user or not verify_password(request.password, user.salt, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        logger.info("user_signed_in", email=email, user_id=str(user.id))
        token, expires_at = create_access_token({"sub": str(user.id), "email": user.email})
        return AuthResponse(
            user=UserResponse(id=str(user.id), email=user.email),
            token=token,
            expires_at=expires_at,
        )


@router.get("/me", response_model=UserResponse)
async def get_me(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication header")

    token = authorization.split("Bearer ")[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token has expired or is invalid")

    return UserResponse(id=payload["sub"], email=payload.get("email", ""))
