from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from app.core.config import TIMEZONE
from app.db.database import rows

def exists(table, entity_id):
    # table names are constants at call sites, never request input.
    result = rows(f'SELECT * FROM {table} WHERE id=?', (entity_id,))
    if not result:
        raise HTTPException(404, 'Record not found.')
    return result[0]


def date_window(day: date):
    local = datetime.combine(day, datetime.min.time(), ZoneInfo(TIMEZONE))
    from datetime import timezone
    return local.astimezone(timezone.utc).isoformat(), (local + timedelta(days=1)).astimezone(timezone.utc).isoformat()


