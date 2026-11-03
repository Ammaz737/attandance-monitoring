import asyncio
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from app.core.security import current_user, decrypt, encrypt, require
from app.core.helpers import exists
from app.db.database import audit, connection, now, rows, uid
from app.events.bus import bus

router = APIRouter(tags=['cameras'])

class CameraInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location_id: str
    source: str = Field(default='', max_length=2048)
    role: Literal['entry', 'exit', 'both', 'monitoring'] = 'monitoring'
    recording: bool = False
    line_x: float = Field(default=0.5, ge=0.05, le=0.95)
    entry_direction: Literal['right', 'left'] = 'right'
    retention_days: int = Field(default=7, ge=1, le=90)

    @field_validator('source')
    @classmethod
    def source_format(cls, value):
        if value and not (value.isdigit() or value.startswith(('rtsp://', 'rtsps://', 'http://', 'https://'))):
            raise ValueError('Use a webcam index (0), RTSP URL or HTTP camera stream.')
        return value


def camera_view(camera):
    from app.workers.manager import manager
    result = {k: v for k, v in camera.items() if k != 'source'}
    result.update(manager.status(camera['id']))
    result['source_configured'] = bool(camera['source'])
    source = decrypt(camera['source'])
    result['source_type'] = 'webcam' if source.isdigit() else 'network'
    result['webcam_source'] = source if source.isdigit() else None
    return result


@router.get('/api/v1/cameras/webcams')
async def webcams(user=Depends(current_user)):
    require(user, 'admin')
    from app.streaming.devices import discover_webcams
    try:
        devices = await asyncio.to_thread(discover_webcams)
    except ImportError:
        raise HTTPException(503, 'Webcam discovery is unavailable. Install the backend requirements and restart.')
    except Exception:
        raise HTTPException(503, 'Webcams could not be listed. Check connected devices and system camera permissions, then rescan.')
    return {'devices': devices}


@router.get('/api/v1/cameras')
def cameras(user=Depends(current_user)):
    result = rows('''SELECT c.*,l.name AS location_name,l.building,l.floor FROM cameras c
                     JOIN locations l ON l.id=c.location_id ORDER BY c.name''')
    return [camera_view(camera) for camera in result]


@router.post('/api/v1/cameras', status_code=201)
def add_camera(data: CameraInput, user=Depends(current_user)):
    require(user, 'admin')
    exists('locations', data.location_id)
    if not data.source:
        raise HTTPException(400, 'A camera source is required.')
    camera_id = uid()
    with connection() as db:
        db.execute('INSERT INTO cameras VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   (camera_id, data.name, data.location_id, encrypt(data.source), data.role, 0, int(data.recording),
                    data.line_x, data.entry_direction, data.retention_days, now()))
    audit(user['username'], 'camera.created', camera_id)
    return camera_view(exists('cameras', camera_id))


@router.patch('/api/v1/cameras/{camera_id}')
def edit_camera(camera_id: str, data: CameraInput, user=Depends(current_user)):
    require(user, 'admin')
    camera = exists('cameras', camera_id)
    exists('locations', data.location_id)
    if camera['enabled']:
        raise HTTPException(409, 'Stop the camera before changing its configuration.')
    with connection() as db:
        db.execute('''UPDATE cameras SET name=?,location_id=?,source=?,role=?,recording=?,line_x=?,
                      entry_direction=?,retention_days=? WHERE id=?''',
                   (data.name, data.location_id, encrypt(data.source) if data.source else camera['source'],
                    data.role, int(data.recording), data.line_x, data.entry_direction, data.retention_days, camera_id))
    audit(user['username'], 'camera.updated', camera_id)
    return camera_view(exists('cameras', camera_id))


@router.post('/api/v1/cameras/test')
async def test_camera(data: CameraInput, user=Depends(current_user)):
    require(user, 'admin')
    if not data.source:
        raise HTTPException(400, 'Enter a source to test.')
    from app.workers.manager import probe
    result = await asyncio.to_thread(probe, data.source)
    if not result['ok']:
        raise HTTPException(422, 'Camera did not deliver a frame. Check the URL, credentials and network.')
    return result


@router.post('/api/v1/cameras/{camera_id}/toggle')
def toggle_camera(camera_id: str, user=Depends(current_user)):
    require(user, 'admin')
    camera = exists('cameras', camera_id)
    from app.workers.manager import manager
    if camera['enabled']:
        manager.stop(camera_id)
    else:
        manager.start(camera)
    with connection() as db:
        db.execute('UPDATE cameras SET enabled=? WHERE id=?', (not camera['enabled'], camera_id))
    audit(user['username'], 'camera.stopped' if camera['enabled'] else 'camera.started', camera_id)
    bus.emit('camera.health.changed', camera_id)
    return {'enabled': not camera['enabled']}


@router.get('/api/v1/cameras/{camera_id}/stream')
async def camera_stream(camera_id: str, request: Request, analysis: bool = False, user=Depends(current_user)):
    exists('cameras', camera_id)
    from app.workers.manager import manager
    async def frames():
        previous = None
        while not await request.is_disconnected():
            frame, stamp = manager.frame(camera_id, analysis=analysis)
            if frame and stamp != previous:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
                previous = stamp
            await asyncio.sleep(0.1)
    return StreamingResponse(frames(), media_type='multipart/x-mixed-replace; boundary=frame')


