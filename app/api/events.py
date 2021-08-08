import datetime

from fastapi import APIRouter, Response, Request, HTTPException, Depends
from ..db import get_database
from bson.objectid import ObjectId
from ..auth_helpers import authorize
from ..models import EventDB, AccessTokenPayload

router = APIRouter()

@router.post('/')
def create_event(request: Request, newEvent: EventDB, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    # TODO better format handling and date date-time handling
    try :
        event_date = datetime.datetime.strptime(str(newEvent.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.datetime.now():
        raise HTTPException(400, "Invalid date")

    event = db.events.insert_one(newEvent.dict())

    return {'_id' : str(event.inserted_id)}

@router.get('/{id}')
def get_event_by_id(request: Request, id:str):
    db = get_database(request)

    if not ObjectId.is_valid(id):
        "Throw 404 since the interface requires a string while object id requires BSON i.e id not found"
        raise HTTPException(404, "Event could not be found")

    event = db.events.find_one({'_id': ObjectId(id)})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return EventDB.parse_obj(event)
