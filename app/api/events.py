from datetime import datetime
import os
import shutil
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from starlette.responses import FileResponse
from uuid import uuid4, UUID

from app.utils.validation import get_file_type, validate_image_file_type
from ..db import get_database
from bson.objectid import ObjectId
from ..auth_helpers import authorize, role_required
from ..models import Event, EventDB, AccessTokenPayload, EventInput, EventUpdate, Member
from .utils import crud_get_event_by_id

router = APIRouter()

@router.post('/')
def create_event(request: Request, newEvent: EventInput, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    # TODO better format handling and date date-time handling
    try :
        event_date = datetime.strptime(str(newEvent.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.now():
        raise HTTPException(400, "Invalid date")

    eid = uuid4().hex
    additionalFields = {
        'eid' : eid,
        'participants' : [],
        'posts' : [],
    }
    
    event = newEvent.dict()
    event.update(additionalFields)

    event = db.events.insert_one(event)

    return {'eid' : eid}

@router.get('/')
def get_all_event_ids(request: Request):
    db = get_database(request) 

    return [ str(event['eid']) for event in db.events.find() ]

@router.get('/upcoming-events')
def get_upcoming_events(request: Request):
    events = []
    db = get_database(request)

    now = datetime.now()
    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    coming_events = db.events.find({ 'date': {'$gt': date} })

    return [ Event.parse_obj(event) for event in coming_events ]

@router.get('/{eid}/image')
def get_event_picture(request: Request, eid:str):
    file_name = f"db/eventImages/{UUID(eid).hex}.png"
    if not os.path.exists(file_name):
        raise HTTPException(404, "picture not found")
    return FileResponse(file_name)

@router.post('/{eid}/image')
def upload_event_picture(request: Request, eid: str , image: UploadFile = File(...)):
    if not validate_image_file_type(image.content_type):
        raise HTTPException(400, "Unsupported file type")

    db = get_database(request)

    baseDir = "db/eventImages"
    if not os.path.isdir(baseDir):
        os.mkdir(baseDir)
    
    file_type = get_file_type(image.content_type)
    picturePath = f"{baseDir}/{eid}.png"

    with open(picturePath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    db.events.find_one_and_update({'eid': UUID(eid).hex}, {"$set": {"imagePath": picturePath}})

    return Response(status_code=200)

@router.put('/{eid}')
def update_event(request: Request, eid:str, eventUpdate: EventUpdate, AccessTokenPayload = Depends(authorize)):
    role_required(AccessTokenPayload, "admin")
    db = get_database(request)

    values = eventUpdate.dict(exclude_none=True)

    if "date" in values:
        try :
            event_date = datetime.strptime(str(eventUpdate.date), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(400, "Invalid date format")

        if event_date < datetime.now():
            raise HTTPException(400, "Invalid date")

    db.events.find_one_and_update(
        {'eid': UUID(eid).hex},
        {"$set": values})

    return Response(status_code=200)

@router.get('/{eid}')
def get_event_by_id(request: Request, eid:str):
    db = get_database(request)

    event = crud_get_event_by_id(db, eid)
    return EventDB.parse_obj(event)

@router.get('/{eid}/participants')
def get_event_participants(request: Request, eid:str):
    db = get_database(request)

    event = crud_get_event_by_id(db, eid)

    return [{'id' : p['id'], 'name': p['realName']} for p in event['participants']]

# 400 if already joined?
@router.post('/{eid}/join')
def join_event(request: Request, eid:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    
    event = crud_get_event_by_id(db, eid)

    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    if event['maxParticipants']:
        if len(event['participants']) >= event['maxParticipants']:
            raise HTTPException(423, "Event full")

    db.events.update({'eid' : event['eid']}, { "$addToSet": { "participants": member } })

    return Response(status_code=200)

@router.post('/{eid}/leave')
def leave_event(request: Request, eid:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = crud_get_event_by_id(db, eid)
    
    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    user = db.events.find_one({"eid" : UUID(eid).hex}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})

    try : 
        user['participants'][0]
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'eid' : event['eid']}, { "$pull": { "participants": member } })

    return Response(status_code=200)

@router.get('/{eid}/joined')
def is_joined_event(request: Request, eid:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = crud_get_event_by_id(db, eid)
    
    user = db.events.find_one({"eid" : UUID(eid).hex}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})

    try : 
        isJoined = user['participants'][0]
        return {'joined' : True}
    except KeyError:
        return {'joined' : False}
