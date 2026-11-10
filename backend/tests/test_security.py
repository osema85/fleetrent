import uuid

import jwt
import pytest

from app.core import security
from app.core.config import settings


def test_password_hash_roundtrip():
    hashed = security.hash_password("Correct-Horse-9!")
    assert hashed.startswith("$argon2id$")
    assert security.verify_password("Correct-Horse-9!", hashed)
    assert not security.verify_password("wrong", hashed)
    assert not security.verify_password("x", "not-a-hash")


@pytest.mark.parametrize("pw", ["short1!A", "alllowercase123!", "ALLUPPERCASE123!", "NoDigitsHere!!", "NoSymbols12345"])
def test_weak_passwords_rejected(pw):
    with pytest.raises(ValueError):
        security.validate_password_strength(pw)


def test_password_must_not_contain_email_name():
    with pytest.raises(ValueError):
        security.validate_password_strength("Johnny-Secret-42", "johnny@example.com")


def test_access_token_roundtrip():
    uid = uuid.uuid4()
    token, expires = security.create_access_token(uid, "agent")
    payload = security.decode_access_token(token)
    assert payload["sub"] == str(uid) and payload["role"] == "agent"
    assert expires == settings.access_token_expire_minutes * 60


def test_token_with_other_key_or_alg_none_is_rejected():
    forged = jwt.encode({"sub": "x", "type": "access"}, "another-key-another-key-another-key", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(forged)
    unsigned = jwt.encode({"sub": "x", "type": "access"}, None, algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(unsigned)


def test_refresh_tokens_are_hashed():
    raw = security.generate_refresh_token()
    assert len(raw) >= 60
    assert security.hash_token(raw) != raw and len(security.hash_token(raw)) == 64
