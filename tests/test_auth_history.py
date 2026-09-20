import pytest
import uuid
from app.core.security import hash_password, verify_password
from app.schemas.auth import SignUpRequest, SignInRequest
from app.schemas.history import ChatHistoryItem


def test_password_hashing():
    password = "secret_password_123"
    hashed, salt = hash_password(password)
    assert hashed != password
    assert len(salt) == 32
    assert verify_password(password, salt, hashed) is True
    assert verify_password("wrong_password", salt, hashed) is False


def test_auth_schemas():
    req = SignUpRequest(email="test@example.com", password="password123")
    assert req.email == "test@example.com"
    assert req.password == "password123"

    signin = SignInRequest(email="test@example.com", password="password123")
    assert signin.email == "test@example.com"


def test_chat_history_schema():
    item = ChatHistoryItem(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        query="What is DevAI?",
        answer="DevAI is a dataset for evaluating agents.",
        citations=[{"page_number": 4, "section": "Dataset", "source_type": "text"}],
        evidence=[{"id": "c1", "content": "Sample content", "score": 0.95, "page_number": 4}],
        created_at="2026-09-20T11:45:00Z",
    )
    assert item.query == "What is DevAI?"
    assert len(item.citations) == 1
    assert len(item.evidence) == 1


def test_jwt_create_and_decode():
    from datetime import timedelta
    from app.core.security import create_access_token, decode_access_token
    token, expires_at = create_access_token({"sub": "user-123", "email": "user@example.com"})
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "user@example.com"

    # test expired token
    expired_token, _ = create_access_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None
