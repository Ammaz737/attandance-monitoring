from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import current_user, require
from app.core.helpers import exists
from app.db.database import audit, connection, rows

router = APIRouter(tags=['reviews'])

@router.get('/api/v1/reviews')
def reviews(user=Depends(current_user)):
    return rows('''SELECT r.*,p.name,c.name AS camera_name FROM review_items r
        LEFT JOIN people p ON p.id=r.person_id LEFT JOIN cameras c ON c.id=r.camera_id
        ORDER BY r.created_at DESC LIMIT 100''')


class ReviewResolution(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


@router.post('/api/v1/reviews/{review_id}/resolve')
def resolve_review(review_id: str, data: ReviewResolution, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    exists('review_items', review_id)
    with connection() as db:
        db.execute("UPDATE review_items SET status='resolved' WHERE id=?", (review_id,))
    audit(user['username'], 'review.resolved', review_id, data.reason)
    return {'ok': True}


