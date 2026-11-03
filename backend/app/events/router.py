from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.core.security import current_user
from app.events.bus import bus

router = APIRouter(tags=['events'])

@router.get('/api/v1/events')
async def events(request: Request, user=Depends(current_user)):
    return StreamingResponse(bus.stream(request), media_type='text/event-stream',
                             headers={'X-Accel-Buffering': 'no'})


