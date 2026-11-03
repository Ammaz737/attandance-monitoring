"""Isolated UI QA server. Never writes to the real attendance database.

Run from repository root with backend/.venv/Scripts/python.exe backend/tests/manual_preview.py
Test sign-in: qa_operator / local-preview-only-2026
"""
import os
import sys
import tempfile
from pathlib import Path

temporary = tempfile.TemporaryDirectory(prefix='presence-ui-qa-')
os.environ['STORAGE_ROOT'] = temporary.name
os.environ['DATABASE_PATH'] = str(Path(temporary.name) / 'preview.sqlite3')
os.environ['ENABLE_AI'] = 'false'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import init_db, connection, now, uid
from app.core.security import hash_password
from app.main import app

init_db()
with connection() as db:
    db.execute('INSERT INTO users VALUES (?,?,?,?,?)',
               (uid(), 'qa_operator', hash_password('local-preview-only-2026'), 'admin', now()))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
