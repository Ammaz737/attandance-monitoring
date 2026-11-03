import hashlib
import hmac
import os
import secrets
import time
from fastapi import HTTPException, Request
from cryptography.fernet import Fernet
from app.core.config import STORAGE
from app.db.database import rows

key_path = STORAGE / 'encryption.key'
if not key_path.exists():
    # The local deployment uses one API process; back this file up with the DB.
    key_path.write_bytes(Fernet.generate_key())
cipher = Fernet(key_path.read_bytes())


def encrypt(value: str):
    return cipher.encrypt(value.encode()).decode()


def decrypt(value: str):
    return cipher.decrypt(value.encode()).decode()


def hash_password(password: str):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()


def verify_password(password, stored):
    salt, expected = stored.split(':')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(actual, expected)


def current_user(request: Request):
    token = request.cookies.get('attendance_session', '')
    result = rows('SELECT u.id,u.username,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',
                  (hashlib.sha256(token.encode()).hexdigest(), time.time()))
    if not result:
        raise HTTPException(401, 'Please sign in to continue.')
    return result[0]


def require(user, *roles):
    if user['role'] not in roles:
        raise HTTPException(403, 'Your role cannot perform this action.')
