import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, Response
from app.core.security import current_user, require
from app.db.database import audit
from app.modules.attendance.router import attendance

router = APIRouter(tags=['reports'])

@router.get('/api/v1/reports/attendance.csv')
def export_attendance(day: date, user=Depends(current_user)):
    require(user, 'admin', 'attendance')
    data = attendance(day, user)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['Employee ID', 'Name', 'Department', 'IN (UTC)', 'OUT (UTC)', 'Status'])
    def safe(value):
        value = str(value or '')
        return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
    for record in data:
        writer.writerow([safe(record[k]) for k in ('employee_id', 'name', 'department', 'in_at', 'out_at')] +
                        ['Open' if not record['out_at'] else 'Closed'])
    audit(user['username'], 'report.exported', details=str(day))
    return Response(stream.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="attendance-{day}.csv"'})


