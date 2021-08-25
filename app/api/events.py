import datetime

from fastapi import APIRouter, Response, Request, HTTPException, Depends
from ..db import get_database
from bson.objectid import ObjectId
from ..auth_helpers import authorize
from ..models import Event, EventDB, AccessTokenPayload, Member
from .util import crud_get_event_by_id

router = APIRouter()

@router.post('/')
def create_event(request: Request, newEvent: Event, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    # TODO better format handling and date date-time handling
    try :
        event_date = datetime.datetime.strptime(str(newEvent.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.datetime.now():
        raise HTTPException(400, "Invalid date")

    additionalFields = {
        'participants' : [],
        'posts' : []
    }
    event = newEvent.dict()
    event.update(additionalFields)

    event = db.events.insert_one(event)

    return {'_id' : str(event.inserted_id)}

@router.get('/{id}')
def get_event_by_id(request: Request, id:str):
    db = get_database(request)

    event = crud_get_event_by_id(db, id)

    return EventDB.parse_obj(event)

@router.post('/{id}/join')
def join_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    
    event = crud_get_event_by_id(db, id)

    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    db.events.update({'_id' : event['_id']}, { "$addToSet": { "participants": member } })

    return Response(status_code=200)

@router.post('/{id}/leave')
def leave_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = crud_get_event_by_id(db, id)
    
    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    user = db.events.find_one({"_id" : ObjectId(id)}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})

    try : 
        user['participants'][0]
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'_id' : event['_id']}, { "$pull": { "participants": member } })

    return Response(status_code=200)

@router.get('/{id}/joined')
def is_joined_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = crud_get_event_by_id(db, id)
    
    user = db.events.find_one({"_id" : ObjectId(id)}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})

    try : 
        isJoined = user['participants'][0]
        return {'joined' : True}
    except KeyError:
        return {'joined' : False}
