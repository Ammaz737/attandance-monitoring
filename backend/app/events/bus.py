import asyncio
import threading
from collections import deque
from app.db.database import now, uid


class EventBus:
    def __init__(self):
        self.events = deque(maxlen=300)
        self.lock = threading.Lock()

    def emit(self, event_type, entity_id=None, **data):
        event = {'id': uid(), 'type': event_type, 'entity_id': entity_id, 'at': now(), 'data': data}
        with self.lock:
            self.events.append(event)
        return event

    async def stream(self, request):
        with self.lock:
            cursor = self.events[-1]['id'] if self.events else None
        yield 'event: ready\ndata: {}\n\n'
        while not await request.is_disconnected():
            with self.lock:
                snapshot = list(self.events)
            ids = [event['id'] for event in snapshot]
            if cursor in ids:
                pending = snapshot[ids.index(cursor) + 1:]
            else:
                pending = snapshot
            import json
            for event in pending:
                yield f"data: {json.dumps(event)}\n\n"
                cursor = event['id']
            yield ': heartbeat\n\n'
            await asyncio.sleep(2)


bus = EventBus()
