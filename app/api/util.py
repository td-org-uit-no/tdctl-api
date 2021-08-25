from fastapi import APIRouter, Response, Request, HTTPException, Depends
from bson.objectid import ObjectId

def crud_get_event_by_id(db, id: str):
    if not ObjectId.is_valid(id):
        "Throw 404 since the interface requires a string while object id requires BSON i.e id not found"
        raise HTTPException(404, "Event could not be found")

    event = db.events.find_one({'_id': ObjectId(id)})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return event
