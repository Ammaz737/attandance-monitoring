from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import current_user, require
from app.core.helpers import exists
from app.db.database import audit, connection, now, rows, uid

router = APIRouter(tags=['locations'])

class LocationInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    building: str = Field(default='Main building', min_length=1, max_length=100)
    floor: str = Field(default='Ground floor', min_length=1, max_length=100)


@router.get('/api/v1/locations')
def locations(user=Depends(current_user)):
    return rows('SELECT * FROM locations ORDER BY building,floor,name')


@router.post('/api/v1/locations', status_code=201)
def add_location(data: LocationInput, user=Depends(current_user)):
    require(user, 'admin')
    location_id = uid()
    with connection() as db:
        db.execute('INSERT INTO locations VALUES (?,?,?,?,?)', (location_id, data.name, data.building, data.floor, now()))
    audit(user['username'], 'location.created', location_id)
    return exists('locations', location_id)


