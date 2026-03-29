"""Tests for security utilities."""

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_password_hash_creates_different_hashes(self):
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        assert hash1 != password

    def test_verify_password_correct(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False


class TestJWTToken:
    def test_create_access_token(self):
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)

    def test_decode_access_token_valid(self):
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["user_id"] == 1

    def test_decode_access_token_invalid(self):
        invalid_token = "invalid.token.here"
        decoded = decode_access_token(invalid_token)
        assert decoded is None

    def test_decode_access_token_empty(self):
        decoded = decode_access_token("")
        assert decoded is None

    def test_token_contains_expiry(self):
        data = {"sub": "testuser"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert "exp" in decoded
