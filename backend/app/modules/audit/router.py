from fastapi import APIRouter, Depends
from app.core.security import current_user, require
from app.db.database import rows

router = APIRouter(tags=['audit'])

@router.get('/api/v1/audit')
def audit_log(user=Depends(current_user)):
    require(user, 'admin')
    return rows('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100')


