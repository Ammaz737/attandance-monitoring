from datetime import date
from fastapi import APIRouter, Depends
from app.core.security import current_user
from app.core.helpers import date_window
from app.db.database import rows

router = APIRouter(tags=['sightings'])

@router.get('/api/v1/sightings')
def sightings(person_id: str = '', day: date | None = None, user=Depends(current_user)):
    query = '''SELECT s.*,p.name,p.employee_id,c.name AS camera_name,l.name AS location_name
        FROM sightings s JOIN people p ON p.id=s.person_id JOIN cameras c ON c.id=s.camera_id
        JOIN locations l ON l.id=c.location_id WHERE 1=1'''
    args = []
    if person_id:
        query += ' AND s.person_id=?'
        args.append(person_id)
    if day:
        start, end = date_window(day)
        query += ' AND s.occurred_at>=? AND s.occurred_at<?'
        args.extend([start, end])
    return rows(query + ' ORDER BY s.occurred_at DESC LIMIT 500', args)


