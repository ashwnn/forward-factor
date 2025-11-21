"""Tests for authentication utilities and endpoints."""
import pytest
from datetime import timedelta
from app.core.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = hash_password(password)
    
    # Hash should not equal plain password
    assert hashed != password
    
    # Verification should succeed with correct password
    assert verify_password(password, hashed) is True
    
    # Verification should fail with incorrect password
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_token_creation_and_decoding():
    """Test JWT token creation and decoding."""
    data = {"sub": "test-user-id", "email": "test@example.com"}
    
    # Create token
    token = create_access_token(data, expires_delta=timedelta(minutes=30))
    
    assert token is not None
    assert isinstance(token, str)
    
    # Decode token
    decoded = decode_access_token(token)
    
    assert decoded["sub"] == "test-user-id"
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded


def test_jwt_token_with_custom_expiration():
    """Test JWT token with custom expiration."""
    data = {"sub": "test-user-id"}
    expires_delta = timedelta(hours=1)
    
    token = create_access_token(data, expires_delta=expires_delta)
    decoded = decode_access_token(token)
    
    assert "exp" in decoded
    assert decoded["sub"] == "test-user-id"


# Note: Integration tests for API endpoints would require a test database
# and async test client. These can be added later with pytest-asyncio.
