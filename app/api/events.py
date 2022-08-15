from datetime import datetime
import os
import shutil
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from starlette.responses import FileResponse
from uuid import uuid4, UUID

from app.utils.validation import validate_image_file_type, validate_uuid
from ..db import get_database, get_image_path
from ..auth_helpers import authorize, role_required
from ..models import Event, EventDB, AccessTokenPayload, EventInput, EventUpdate
from .utils import get_event_or_404

router = APIRouter()

@router.post('/')
def create_event(request: Request, newEvent: EventInput, token: AccessTokenPayload = Depends(authorize)):
    role_required(token, "admin")
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

@router.get('/upcoming')
def get_upcoming_events(request: Request):
    db = get_database(request)

    now = datetime.now()
    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(500, "Problem handling date format")

    coming_events = db.events.find({ 'date': {'$gt': date} })

    return [ Event.parse_obj(event) for event in coming_events ]

# custom uuid validation as eid: UUID will not allow users to copy eids into swagger as they are not formatted correctly
# id is used over eid as parameter name as validate_uuid and the api function needs the have the same parameter name.
@router.get('/{id}/image', dependencies=[Depends(validate_uuid)])
def get_event_picture(request: Request, id:str):
    image_path = get_image_path(request)
    file_name = f"{image_path}/{UUID(id).hex}.png"
    if not os.path.exists(file_name):
        raise HTTPException(404, "picture not found")
    return FileResponse(file_name)

@router.post('/{id}/image', dependencies=[Depends(validate_uuid)])
def upload_event_picture(request: Request, id:str, image: UploadFile = File(...), token: AccessTokenPayload = Depends(authorize)):
    role_required(token, "admin")
    if not validate_image_file_type(image.content_type):
        raise HTTPException(400, "Unsupported file type")

    image_path = get_image_path(request)

    # baseDir = "db/eventImages"
    if not os.path.isdir(image_path):
        os.mkdir(image_path)

    picturePath = f"{image_path}/{UUID(id).hex}.png"

    with open(picturePath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    return Response(status_code=200)

@router.put('/{id}', dependencies=[Depends(validate_uuid)])
def update_event(request: Request, id:str, eventUpdate: EventUpdate, AccessTokenPayload = Depends(authorize)):
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

    result = db.events.find_one_and_update(
        {'eid': UUID(id).hex},
        {"$set": values})

    if result == None:
        raise HTTPException(404, "No such event with this eid")

    return Response(status_code=200)

@router.get('/{id}', dependencies=[Depends(validate_uuid)])
def get_event_by_id(request: Request, id:str):
    db = get_database(request)

    event = get_event_or_404(db, id)
    return EventDB.parse_obj(event)

@router.get('/{id}/participants', dependencies=[Depends(validate_uuid)])
def get_event_participants(request: Request, id:str):
    db = get_database(request)

    event = get_event_or_404(db, id)

    return [{'id' : p['id'], 'name': p['realName']} for p in event['participants']]

# 400 if already joined?
@router.post('/{id}/join', dependencies=[Depends(validate_uuid)])
def join_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    
    event = get_event_or_404(db, id)

    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    if event['maxParticipants']:
        if len(event['participants']) >= event['maxParticipants']:
            raise HTTPException(423, "Event full")

    db.events.update_one({'eid' : event['eid']}, { "$addToSet": { "participants": member } })

    return Response(status_code=200)

@router.post('/{id}/leave', dependencies=[Depends(validate_uuid)])
def leave_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = get_event_or_404(db, id)
    
    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    user = db.events.find_one({"eid" : event["eid"]}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})
    if not user:
        raise HTTPException(400, "User not joined event!")

    try : 
        user['participants'][0]
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'eid' : event['eid']}, { "$pull": { "participants": member } })

    return Response(status_code=200)

@router.get('/{id}/joined', dependencies=[Depends(validate_uuid)])
def is_joined_event(request: Request, id:str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)

    event = get_event_or_404(db, id)
    # uses event["eid"] instead of casting eid -> UUID 
    user = db.events.find_one({"eid" : event["eid"]}, {"participants" : {"$elemMatch" : {"id": token.user_id}}})

    if not user:
        return {'joined' : False}

    try : 
        user['participants'][0]
        return {'joined' : True}
    except KeyError:
        return {'joined' : False}
