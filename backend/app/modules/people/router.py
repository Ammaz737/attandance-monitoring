import asyncio
import json
import sqlite3
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from app.core.security import current_user, encrypt, require
from app.core.helpers import exists
from app.db.database import audit, connection, now, rows, uid
from app.events.bus import bus

router = APIRouter(tags=['people'])

class PersonInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    employee_id: str = Field(min_length=1, max_length=40)
    contact: str = Field(default='', max_length=80)
    department: str = Field(default='General', min_length=1, max_length=80)
    consent: bool

    @field_validator('name', 'employee_id', 'department')
    @classmethod
    def no_blank(cls, value):
        if not value.strip():
            raise ValueError('This field cannot be blank.')
        return value.strip()


@router.get('/api/v1/people')
def people(user=Depends(current_user)):
    return rows('''SELECT p.*, (SELECT COUNT(*) FROM face_templates f WHERE f.person_id=p.id) AS template_count,
        (SELECT id FROM attendance_sessions a WHERE a.person_id=p.id AND a.out_at IS NULL) AS open_session
        FROM people p ORDER BY p.name''')


@router.post('/api/v1/people', status_code=201)
def add_person(data: PersonInput, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    if not data.consent:
        raise HTTPException(400, 'Enrollment consent is required for this registered-person workflow.')
    person_id = uid()
    try:
        with connection() as db:
            db.execute('INSERT INTO people VALUES (?,?,?,?,?,?,?,?,?)',
                       (person_id, data.employee_id, data.name, data.contact, data.department, 1, 1, now(), now()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Employee ID already exists.')
    audit(user['username'], 'person.created', person_id)
    bus.emit('people.changed', person_id)
    return exists('people', person_id)


@router.patch('/api/v1/people/{person_id}')
def update_person(person_id: str, data: PersonInput, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    exists('people', person_id)
    if not data.consent:
        raise HTTPException(400, 'Use deactivate and delete enrollment to withdraw enrollment.')
    try:
        with connection() as db:
            db.execute('UPDATE people SET name=?,employee_id=?,contact=?,department=? WHERE id=?',
                       (data.name, data.employee_id, data.contact, data.department, person_id))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Employee ID already exists.')
    audit(user['username'], 'person.updated', person_id)
    return exists('people', person_id)


@router.post('/api/v1/people/{person_id}/toggle')
def toggle_person(person_id: str, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    person = exists('people', person_id)
    if person['active'] and rows('SELECT id FROM attendance_sessions WHERE person_id=? AND out_at IS NULL', (person_id,)):
        raise HTTPException(409, 'Close the open attendance session before deactivating this person.')
    with connection() as db:
        db.execute('UPDATE people SET active=? WHERE id=?', (not person['active'], person_id))
    audit(user['username'], 'person.status.changed', person_id)
    return {'ok': True}


@router.post('/api/v1/people/{person_id}/enrollment')
async def enroll(person_id: str, files: list[UploadFile] = File(...), user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    person = exists('people', person_id)
    if not person['active'] or not person['consent']:
        raise HTTPException(400, 'Person must be active with recorded consent.')
    if not 3 <= len(files) <= 8:
        raise HTTPException(400, 'Provide 3 to 8 clear face images.')
    from app.vision.engine import engine
    templates = []
    first_template = None
    for sample_number, file in enumerate(files, start=1):
        content = await file.read(6 * 1024 * 1024 + 1)
        if len(content) > 6 * 1024 * 1024:
            raise HTTPException(413, 'Each image must be smaller than 6 MB.')
        try:
            template = await asyncio.to_thread(engine.enrollment, content)
            duplicate, score = engine.match(template, exclude=person_id)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(422, f'Sample {sample_number}: {exc}')
        if duplicate:
            raise HTTPException(409, 'This face matches an existing enrollment. Review the person records.')
        import numpy as np
        vector = np.asarray(template, dtype=np.float32)
        if first_template is not None:
            consistency = float(np.dot(first_template, vector) / (np.linalg.norm(first_template) * np.linalg.norm(vector) + 1e-8))
            from app.core.config import FACE_THRESHOLD
            if consistency < FACE_THRESHOLD:
                raise HTTPException(422, 'Face samples are inconsistent. Capture the same person with clear lighting.')
        else:
            first_template = vector
        templates.append(encrypt(json.dumps(template)))
    with connection() as db:
        db.execute('DELETE FROM face_templates WHERE person_id=?', (person_id,))
        for template in templates:
            db.execute('INSERT INTO face_templates VALUES (?,?,?,?,?)', (uid(), person_id, template, engine.model_name, now()))
    audit(user['username'], 'enrollment.replaced', person_id, f'{len(templates)} templates')
    return {'templates': len(templates), 'model': engine.model_name}


@router.delete('/api/v1/people/{person_id}/enrollment')
def delete_enrollment(person_id: str, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    exists('people', person_id)
    with connection() as db:
        db.execute('DELETE FROM face_templates WHERE person_id=?', (person_id,))
    audit(user['username'], 'enrollment.deleted', person_id)
    return {'ok': True}


