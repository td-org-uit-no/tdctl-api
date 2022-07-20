from fastapi import APIRouter, Response, Request, HTTPException, Depends
from uuid import UUID

def get_event_or_404(db, eid: str):
    eid = UUID(eid).hex
    event = db.events.find_one({'eid': eid})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return event
