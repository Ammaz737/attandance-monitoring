from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.core.config import STORAGE
from app.core.security import current_user
from app.core.helpers import exists, date_window
from app.db.database import audit, now, rows

router = APIRouter(tags=['recordings'])

@router.get('/api/v1/recordings')
def recordings(camera_id: str = '', person_id: str = '', location_id: str = '', day: date | None = None, user=Depends(current_user)):
    query = '''SELECT r.id,r.camera_id,r.started_at,r.ended_at,r.status,r.bytes,c.name AS camera_name,
        l.name AS location_name FROM recordings r JOIN cameras c ON c.id=r.camera_id
        JOIN locations l ON l.id=c.location_id WHERE 1=1'''
    args = []
    if location_id:
        query += ' AND c.location_id=?'
        args.append(location_id)
    if camera_id:
        query += ' AND r.camera_id=?'
        args.append(camera_id)
    if person_id:
        query += ''' AND EXISTS(SELECT 1 FROM sightings s WHERE s.person_id=? AND s.camera_id=r.camera_id
                    AND s.occurred_at>=r.started_at AND s.occurred_at<=COALESCE(r.ended_at,?))'''
        args.extend([person_id, now()])
    if day:
        start, end = date_window(day)
        query += ' AND r.started_at<? AND COALESCE(r.ended_at,?)>=?'
        args.extend([end, now(), start])
    return rows(query + ' ORDER BY r.started_at DESC LIMIT 500', args)


@router.get('/api/v1/recordings/{recording_id}/file')
def recording_file(recording_id: str, download: bool = False, user=Depends(current_user)):
    from pathlib import Path
    recording = exists('recordings', recording_id)
    path = Path(recording['path']).resolve()
    if not path.is_relative_to((STORAGE / 'recordings').resolve()):
        raise HTTPException(403, 'Invalid recording path.')
    if recording['status'] != 'ready' or not path.is_file():
        raise HTTPException(410, 'This recording is not available or has expired.')
    audit(user['username'], 'recording.download' if download else 'recording.played', recording_id)
    return FileResponse(path, media_type='video/mp4', filename=path.name if download else None)


