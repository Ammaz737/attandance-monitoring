import os
import sys
import tempfile
from pathlib import Path

# Isolate all runtime data from the real workspace database.
TEMP = tempfile.TemporaryDirectory(prefix='presence-tests-')
os.environ['STORAGE_ROOT'] = TEMP.name
os.environ['DATABASE_PATH'] = str(Path(TEMP.name) / 'test.sqlite3')
os.environ['ENABLE_AI'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.modules.auth.router import login_attempts
from app.db.database import connection, init_db


@pytest.fixture
def client():
    init_db()
    with connection() as db:
        for table in ('sightings', 'review_items', 'recordings', 'attendance_sessions', 'attendance_events',
                      'face_templates', 'cameras', 'locations', 'people', 'audit_logs', 'sessions', 'users'):
            db.execute(f'DELETE FROM {table}')
    login_attempts.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin(client):
    credentials = {'username': 'admin', 'password': 'test-password-123'}
    assert client.post('/api/v1/auth/setup', json=credentials).status_code == 201
    assert client.post('/api/v1/auth/login', json=credentials).status_code == 200
    return client


@pytest.fixture
def person(admin):
    response = admin.post('/api/v1/people', json={'name': 'Ali Ahmed', 'employee_id': 'EMP-001',
                                               'contact': '03001234567', 'department': 'Operations', 'consent': True})
    assert response.status_code == 201, response.text
    return response.json()
