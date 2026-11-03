import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.helpers import exists
from app.core.security import current_user, decrypt, require
from app.db.database import rows
from app.modules.enrollment.preview import previews

router = APIRouter(tags=['enrollment-preview'])


@router.get('/api/v1/enrollment/cameras')
async def enrollment_cameras(user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    from app.streaming.devices import discover_webcams
    registered = rows('SELECT id,name,enabled,source FROM cameras ORDER BY enabled DESC,name')
    options = [{'id': 'camera:' + camera['id'], 'name': camera['name'] + (' · running camera' if camera['enabled'] else ' · registered camera')}
               for camera in registered]
    warning = ''
    try:
        devices = await asyncio.to_thread(discover_webcams)
        registered_sources = {decrypt(camera['source']) for camera in registered}
        options += [{'id': 'device:' + device['source'], 'name': device['name']}
                    for device in devices if device['source'] not in registered_sources]
    except Exception:
        warning = 'Local webcam discovery is unavailable. Select a registered camera or use Browser camera.'
    return {'devices': options, 'warning': warning}


class PreviewInput(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)


@router.post('/api/v1/people/{person_id}/enrollment/preview')
async def start_preview(person_id: str, data: PreviewInput, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    person = exists('people', person_id)
    if not person['active'] or not person['consent']:
        raise HTTPException(400, 'Person must be active with recorded enrollment consent.')
    camera = None
    if data.device_id.startswith('camera:'):
        camera = exists('cameras', data.device_id.removeprefix('camera:'))
        source = decrypt(camera['source'])
    elif data.device_id.startswith('device:'):
        from app.streaming.devices import discover_webcams
        devices = await asyncio.to_thread(discover_webcams)
        source = data.device_id.removeprefix('device:')
        if source not in {device['source'] for device in devices}:
            raise HTTPException(400, 'This webcam is no longer connected. Refresh the camera list.')
        candidates = rows('SELECT * FROM cameras WHERE enabled=1')
        for candidate in candidates:
            registered_source = decrypt(candidate['source'])
            if registered_source == source:
                camera = candidate
                break
    else:
        raise HTTPException(400, 'Select a connected webcam or registered camera.')
    # Reuse frames if monitoring already owns this device; never open it twice.
    preview = await asyncio.to_thread(previews.start, user['id'], person_id,
                                      None if camera and camera['enabled'] else source,
                                      camera['id'] if camera and camera['enabled'] else None)
    return {'id': preview.id}


@router.get('/api/v1/people/{person_id}/enrollment/preview/{token}')
def preview_frame(person_id: str, token: str, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    return previews.get(token, user['id'], person_id).read()


@router.delete('/api/v1/people/{person_id}/enrollment/preview/{token}')
def stop_preview(person_id: str, token: str, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    previews.close(token, user['id'], person_id)
    return {'ok': True}
