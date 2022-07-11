from fastapi import APIRouter, Response, Request, HTTPException, Depends
from uuid import UUID

def crud_get_event_by_id(db, eid: UUID):
    event = db.events.find_one({'eid': eid.hex})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return event
