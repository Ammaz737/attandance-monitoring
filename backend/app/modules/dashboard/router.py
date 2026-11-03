from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from app.core.config import TIMEZONE
from app.core.security import current_user
from app.core.helpers import date_window
from app.db.database import rows

router = APIRouter(tags=['dashboard'])

@router.get('/api/v1/dashboard')
def dashboard(user=Depends(current_user)):
    day = datetime.now(ZoneInfo(TIMEZONE)).date()
    start, end = date_window(day)
    counts = rows('''SELECT
        (SELECT COUNT(*) FROM people WHERE active=1) AS people,
        (SELECT COUNT(*) FROM attendance_sessions WHERE out_at IS NULL) AS present,
        (SELECT COUNT(*) FROM attendance_events WHERE kind='IN' AND occurred_at>=? AND occurred_at<?) AS entries,
        (SELECT COUNT(*) FROM attendance_events WHERE kind='OUT' AND occurred_at>=? AND occurred_at<?) AS exits,
        (SELECT COUNT(*) FROM review_items WHERE status='open') AS reviews''', (start, end, start, end))[0]
    events = rows('''SELECT e.*,p.name,c.name AS camera_name FROM attendance_events e JOIN people p ON p.id=e.person_id
                     LEFT JOIN cameras c ON c.id=e.camera_id ORDER BY e.occurred_at DESC LIMIT 12''')
    return {'counts': counts, 'events': events, 'date': str(day), 'timezone': TIMEZONE}


