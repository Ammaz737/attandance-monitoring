import json
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.config import TIMEZONE
from app.core.security import current_user, require
from app.core.helpers import exists, date_window
from app.db.database import audit, connection, now, rows, uid
from app.events.bus import bus
from app.modules.attendance.service import mark

router = APIRouter(tags=['attendance'])

class AttendanceInput(BaseModel):
    person_id: str
    kind: Literal['IN', 'OUT']
    reason: str = Field(min_length=5, max_length=500)


class SessionCorrection(BaseModel):
    in_at: datetime
    out_at: datetime | None = None
    reason: str = Field(min_length=5, max_length=500)


@router.patch('/api/v1/attendance/{session_id}')
def correct_session(session_id: str, data: SessionCorrection, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    from datetime import timezone
    session = exists('attendance_sessions', session_id)
    if data.in_at.tzinfo is None or data.out_at and data.out_at.tzinfo is None:
        raise HTTPException(400, 'Correction times must include a timezone.')
    entry = data.in_at.astimezone(timezone.utc)
    exit_time = data.out_at.astimezone(timezone.utc) if data.out_at else None
    if entry > datetime.now(timezone.utc) or exit_time and (exit_time < entry or exit_time > datetime.now(timezone.utc)):
        raise HTTPException(400, 'Times cannot be in the future, and exit must follow entry.')
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        other = db.execute('''SELECT id FROM attendance_sessions WHERE person_id=? AND id<>?
                           AND in_at<COALESCE(?, '9999') AND COALESCE(out_at,'9999')>?''',
                           (session['person_id'], session_id, exit_time.isoformat() if exit_time else None, entry.isoformat())).fetchone()
        if other:
            raise HTTPException(409, 'The corrected session would overlap another session.')
        db.execute('UPDATE attendance_sessions SET in_at=?,out_at=? WHERE id=?',
                   (entry.isoformat(), exit_time.isoformat() if exit_time else None, session_id))
        db.execute('INSERT INTO audit_logs VALUES (?,?,?,?,?,?)',
                   (uid(), user['username'], 'attendance.corrected', session_id,
                    json.dumps({'reason': data.reason, 'before': {'in_at': session['in_at'], 'out_at': session['out_at']},
                                'after': {'in_at': entry.isoformat(), 'out_at': exit_time.isoformat() if exit_time else None}}), now()))
    bus.emit('attendance.changed', session['person_id'])
    return {'ok': True}


@router.post('/api/v1/attendance')
def manual_attendance(data: AttendanceInput, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    result = mark(data.person_id, data.kind, data.reason)
    audit(user['username'], 'attendance.manual', result['id'], data.reason)
    return result


@router.get('/api/v1/attendance')
def attendance(day: date | None = None, user=Depends(current_user)):
    day = day or datetime.now(ZoneInfo(TIMEZONE)).date()
    start, end = date_window(day)
    return rows('''SELECT a.*,p.name,p.employee_id,p.department FROM attendance_sessions a
        JOIN people p ON p.id=a.person_id WHERE a.in_at<? AND (a.out_at IS NULL OR a.out_at>=?)
        ORDER BY a.in_at DESC''', (end, start))


