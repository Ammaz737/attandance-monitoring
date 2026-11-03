import hashlib
import secrets
import sqlite3
import time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from app.core.config import COOKIE_SECURE, TIMEZONE
from app.core.security import current_user, hash_password, require, verify_password
from app.db.database import audit, connection, now, rows, uid

router = APIRouter(tags=['auth'])

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=10, max_length=128)


login_attempts = {}


@router.get('/api/v1/health')
def health():
    from app.vision.engine import engine
    return {'status': 'ok', 'version': '0.1.0', 'timezone': TIMEZONE,
            'face_ready': engine.face is not None, 'detector_ready': engine.detector is not None}


@router.get('/api/v1/auth/status')
def auth_status():
    return {'setup_required': not bool(rows('SELECT id FROM users LIMIT 1'))}


@router.post('/api/v1/auth/setup', status_code=201)
def setup(data: Credentials, request: Request):
    if request.client and request.client.host not in ('127.0.0.1', '::1', 'localhost', 'testclient'):
        raise HTTPException(403, 'Create the initial administrator from this computer.')
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT id FROM users LIMIT 1').fetchone():
            raise HTTPException(409, 'Setup is already complete.')
        db.execute('INSERT INTO users VALUES (?,?,?,?,?)', (uid(), data.username, hash_password(data.password), 'admin', now()))
    return {'message': 'Administrator created. Sign in to continue.'}


@router.post('/api/v1/auth/login')
def login(data: Credentials, request: Request, response: Response):
    ip = request.client.host if request.client else 'unknown'
    recent = [t for t in login_attempts.get(ip, []) if t > time.time() - 300]
    login_attempts[ip] = recent
    if len(recent) >= 10:
        raise HTTPException(429, 'Too many attempts. Try again in five minutes.')
    recent.append(time.time())
    found = rows('SELECT * FROM users WHERE username=?', (data.username,))
    if not found or not verify_password(data.password, found[0]['password']):
        raise HTTPException(401, 'Incorrect username or password.')
    login_attempts.pop(ip, None)
    user = found[0]
    token = secrets.token_urlsafe(40)
    with connection() as db:
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), user['id'], time.time() + 43200))
    response.set_cookie('attendance_session', token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=43200)
    audit(user['username'], 'auth.login')
    return {k: user[k] for k in ('id', 'username', 'role')}


@router.get('/api/v1/auth/me')
def me(user=Depends(current_user)):
    return user


@router.post('/api/v1/auth/logout')
def logout(request: Request, response: Response):
    token = request.cookies.get('attendance_session', '')
    with connection() as db:
        db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie('attendance_session')
    return {'ok': True}


class UserCreate(Credentials):
    role: Literal['admin', 'operator', 'attendance'] = 'operator'


@router.get('/api/v1/users')
def users(user=Depends(current_user)):
    require(user, 'admin')
    return rows('SELECT id,username,role,created_at FROM users ORDER BY created_at')


@router.post('/api/v1/users', status_code=201)
def add_user(data: UserCreate, user=Depends(current_user)):
    require(user, 'admin')
    try:
        with connection() as db:
            db.execute('INSERT INTO users VALUES (?,?,?,?,?)', (uid(), data.username, hash_password(data.password), data.role, now()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Username already exists.')
    audit(user['username'], 'user.created', details=data.username)
    return {'ok': True}


