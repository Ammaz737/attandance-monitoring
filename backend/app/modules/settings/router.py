import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.config import TIMEZONE
from app.core.security import current_user, require
from app.db.database import audit, connection, rows

router = APIRouter(tags=['settings'])

@router.get('/api/v1/settings')
def settings(user=Depends(current_user)):
    from app.vision.engine import engine
    return {'organization': json.loads(rows("SELECT value FROM settings WHERE key='organization'")[0]['value']),
            'timezone': TIMEZONE, 'vision': engine.status(), 'stream_transport': 'MJPEG',
            'database': 'SQLite WAL', 'recording': 'Continuous 60-second MP4 segments', 'version': '0.1.0'}


class SettingsInput(BaseModel):
    organization: str = Field(min_length=2, max_length=100)


@router.patch('/api/v1/settings')
def change_settings(data: SettingsInput, user=Depends(current_user)):
    require(user, 'admin')
    with connection() as db:
        db.execute("UPDATE settings SET value=? WHERE key='organization'", (json.dumps(data.organization),))
    audit(user['username'], 'settings.updated')
    return {'ok': True}


