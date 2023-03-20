from fastapi import HTTPException
from uuid import UUID

from app.models import EventDB

def get_event_or_404(db, eid: str):
    event = db.events.find_one({'eid': UUID(eid)})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return EventDB.parse_obj(event).dict()
