from datetime import datetime
from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    expires_at: datetime
