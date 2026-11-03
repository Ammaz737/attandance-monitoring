from fastapi import HTTPException
from app.db.database import connection, now, uid
from app.events.bus import bus


def mark(person_id, kind, reason, source='manual', camera_id=None, event_key=None, occurred_at=None):
    at = occurred_at or now()
    event_id = uid()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        person = db.execute('SELECT * FROM people WHERE id=?', (person_id,)).fetchone()
        if not person or not person['active']:
            raise HTTPException(400, 'Select an active registered person.')
        if event_key and db.execute('SELECT id FROM attendance_events WHERE event_key=?', (event_key,)).fetchone():
            return {'duplicate': True}
        session = db.execute('SELECT * FROM attendance_sessions WHERE person_id=? AND out_at IS NULL', (person_id,)).fetchone()
        if kind == 'IN' and session:
            raise HTTPException(409, 'This person already has an open attendance session.')
        if kind == 'OUT' and not session:
            raise HTTPException(409, 'No open session exists for this person.')
        if session and at < session['in_at']:
            raise HTTPException(400, 'Exit cannot be earlier than entry.')
        db.execute('INSERT INTO attendance_events VALUES (?,?,?,?,?,?,?,?)',
                   (event_id, person_id, camera_id, kind, source, reason, at, event_key or event_id))
        if kind == 'IN':
            db.execute('INSERT INTO attendance_sessions VALUES (?,?,?,?,?,?)', (uid(), person_id, at, None, event_id, None))
        else:
            db.execute('UPDATE attendance_sessions SET out_at=?,out_event=? WHERE id=?', (at, event_id, session['id']))
    bus.emit('attendance.changed', person_id, kind=kind)
    return {'id': event_id, 'occurred_at': at, 'kind': kind}
