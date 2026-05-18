from app.core.security import hash_password, verify_password
import pytest

@pytest.fixture
def hashed():
    return hash_password("mysecretpassword")

def test_hash_password_is_not_plain_text(hashed):
    assert hashed != "mysecretpassword"

def test_verify_password_correct_password_returns_true(hashed):
    assert verify_password("mysecretpassword", hashed) is True

@pytest.mark.parametrize("wrong_password", [
    "wrongpassword",
    "MYSECRETPASSWORD",
    "mysecretpasswor",  
    "",
    "   ",
])
def test_verify_password_wrong_passwords_return_false(hashed, wrong_password):
    assert verify_password(wrong_password, hashed) is False