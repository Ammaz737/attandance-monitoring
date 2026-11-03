import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import ORIGINS
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app):
    init_db()
    from app.vision.engine import engine
    await asyncio.to_thread(engine.load)
    from app.workers.manager import manager
    manager.restore()
    yield
    from app.modules.enrollment.preview import previews
    previews.shutdown()
    manager.shutdown()


app = FastAPI(title='Presence API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Content-Type'])


@app.middleware('http')
async def protect_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in ORIGINS:
        return JSONResponse({'detail': 'This frontend address is not allowed. Check FRONTEND_ORIGIN in the backend configuration.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response



from app.modules.auth.router import router as auth_router
app.include_router(auth_router)
from app.modules.people.router import router as people_router
app.include_router(people_router)
from app.modules.enrollment.router import router as enrollment_router
app.include_router(enrollment_router)
from app.modules.locations.router import router as locations_router
app.include_router(locations_router)
from app.modules.cameras.router import router as cameras_router
app.include_router(cameras_router)
from app.modules.attendance.router import router as attendance_router
app.include_router(attendance_router)
from app.modules.sightings.router import router as sightings_router
app.include_router(sightings_router)
from app.modules.recordings.router import router as recordings_router
app.include_router(recordings_router)
from app.modules.reviews.router import router as reviews_router
app.include_router(reviews_router)
from app.modules.dashboard.router import router as dashboard_router
app.include_router(dashboard_router)
from app.modules.reports.router import router as reports_router
app.include_router(reports_router)
from app.modules.settings.router import router as settings_router
app.include_router(settings_router)
from app.modules.audit.router import router as audit_router
app.include_router(audit_router)
from app.events.router import router as events_router
app.include_router(events_router)

# A built frontend can be served by the same local API process.
from pathlib import Path
FRONTEND_DIST = Path(__file__).resolve().parents[2].parent / 'frontend' / 'dist'
if (FRONTEND_DIST / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets'), name='assets')


@app.get('/{path:path}', include_in_schema=False)
def frontend_app(path: str):
    if path.startswith('api/'):
        raise HTTPException(404, 'API endpoint not found.')
    index = FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(404, 'Build the frontend first, or run the Vite development server.')
    return FileResponse(index)
