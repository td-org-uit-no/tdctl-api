from datetime import datetime
import os
import shutil
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from starlette.responses import FileResponse
from starlette.background import BackgroundTasks
from uuid import uuid4, UUID
from app.utils.validation import validate_image_file_type, validate_uuid
from ..auth_helpers import authorize, authorize_admin
from ..db import get_database, get_image_path, get_export_path
from ..models import Event, EventDB, AccessTokenPayload, EventInput, EventUpdate, JoinEventPayload, Participant
from .utils import get_event_or_404
import pandas as pd

router = APIRouter()


@router.post('/')
def create_event(request: Request, newEvent: EventInput, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    # TODO better format handling and date date-time handling
    try:
        event_date = datetime.strptime(str(newEvent.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.now():
        raise HTTPException(400, "Invalid date")

    eid = uuid4().hex
    additionalFields = {
        'eid': eid,
        'participants': [],
        'posts': [],
    }

    event = newEvent.dict()
    event.update(additionalFields)

    event = db.events.insert_one(event)

    return {'eid': eid}


@router.get('/')
def get_all_event_ids(request: Request):
    db = get_database(request)

    return [str(event['eid']) for event in db.events.find()]


@router.get('/upcoming')
def get_upcoming_events(request: Request):
    db = get_database(request)

    now = datetime.now()
    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(500, "Problem handling date format")

    coming_events = db.events.find({'date': {'$gt': date}})

    return [Event.parse_obj(event) for event in coming_events]

# custom uuid validation as eid: UUID will not allow users to copy eids into swagger as they are not formatted correctly
# id is used over eid as parameter name as validate_uuid and the api function needs the have the same parameter name.


@router.get('/{id}/image', dependencies=[Depends(validate_uuid)])
def get_event_picture(request: Request, id: str):
    image_path = get_image_path(request)
    file_name = f"{image_path}/{UUID(id).hex}.png"
    if not os.path.exists(file_name):
        raise HTTPException(404, "picture not found")
    return FileResponse(file_name)


@router.post('/{id}/image', dependencies=[Depends(validate_uuid)])
def upload_event_picture(request: Request, id: str, image: UploadFile = File(...), token: AccessTokenPayload = Depends(authorize_admin)):
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
def update_event(request: Request, id: str, eventUpdate: EventUpdate, AccessTokenPayload=Depends(authorize_admin)):
    db = get_database(request)

    values = eventUpdate.dict(exclude_none=True)
    if "date" in values:
        try:
            event_date = datetime.strptime(
                str(eventUpdate.date), "%Y-%m-%d %H:%M:%S")
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
def get_event_by_id(request: Request, id: str):
    db = get_database(request)

    event = get_event_or_404(db, id)
    return EventDB.parse_obj(event)


@router.get('/{id}/participants', dependencies=[Depends(validate_uuid)])
def get_event_participants(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    if token.role == "admin":
        return [Participant.parse_obj(p) for p in event['participants']]

    return [{'id': p['id'], 'name': p['realName']} for p in event['participants']]


@router.post('/{id}/join', dependencies=[Depends(validate_uuid)])
def join_event(request: Request, id: str, payload: JoinEventPayload, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    check_participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": token.user_id}}})

    try:
        check_participant['participants']
        raise HTTPException(400, "User already joined")
    except KeyError:
        pass

    participantData = {
        'food': payload.food,
        'transportation': payload.transportation,
        'dietaryRestrictions': payload.dietaryRestrictions,
        'submitDate': datetime.now()
    }

    new_fields = {**member, **participantData}
    participant = Participant.parse_obj(new_fields)
    participant.id = token.user_id  # Necessary cast to get id on correct format

    db.events.update_one({'eid': event['eid']}, {
        "$addToSet": {"participants": participant.dict()}})

    if event['maxParticipants']:
        if len(event['participants']) >= event['maxParticipants']:
            return {'max': True}

    return {'max': False}


@router.post('/{id}/leave', dependencies=[Depends(validate_uuid)])
def leave_event(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': token.user_id})

    if not member:
        raise HTTPException(400, "User could not be found")

    participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": token.user_id}}})

    if not participant:
        raise HTTPException(400, "User not joined event!")
    try:
        participant['participants']
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'eid': event['eid']}, {
        "$pull": {"participants": {"id": token.user_id}}})

    if event['maxParticipants']:
        if len(event['participants']) >= event['maxParticipants']:
            return {'max': True}

    return {'max': False}


@router.get('/{id}/joined', dependencies=[Depends(validate_uuid)])
def is_joined_event(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)

    # uses event["eid"] instead of casting eid -> UUID
    user = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": token.user_id}}})

    if not user:
        return {'joined': False}

    try:
        user['participants'][0]
        return {'joined': True}
    except KeyError:
        return {'joined': False}


@router.delete('/{id}/removeParticipant/{uid}', dependencies=[Depends(validate_uuid)])
def remove_participant(request: Request, id: str, uid: str, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': UUID(uid).hex})

    if not member:
        raise HTTPException(400, "User could not be found")

    participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": UUID(uid).hex}}})

    if not participant:
        raise HTTPException(400, "User not joined event!")

    try:
        participant['participants']
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'eid': event['eid']}, {
                         "$pull": {"participants": {"id": UUID(uid).hex}}})

    return Response(status_code=200)


@router.get('/{id}/export', dependencies=[Depends(validate_uuid)])
async def exportEvent(background_tasks: BackgroundTasks, request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    if not os.path.exists(get_export_path(request)):
        os.makedirs(get_export_path(request))

    filename = f"{id}.xlsx"
    path = get_export_path(request)
    path = path + filename

    db = get_database(request)
    event = get_event_or_404(db, id)

    participants = [Participant(
        **p).copy(exclude={'id'}).dict() for p in event['participants']]
    participants = sorted(participants, key=lambda p: p['submitDate'])

    event_details = [{'Title': event['title'], 'date':event['date'], 'address':event['address'], 'price':event['price'],
                      'maxParticipants':event['maxParticipants'], 'duration':event['duration'], 'transportation':str(event['transportation']), 'food':str(event['food'])}]

    event_header = [{event['title']}]

    event_data = [{'Total participants': len(event['participants']),
                   'Total to eat': len([p for p in event['participants'] if p['food'] == True]),
                   'Total to transportation':  len(
        [p for p in event['participants'] if p['transportation'] == True])}]

    # Create dataframe
    df_title = pd.DataFrame(event_header)
    df_event_data = pd.DataFrame(event_data)
    df_participants = pd.DataFrame(
        data=participants)
    df_event_ditails = pd.DataFrame(data=event_details)

    # Write dataframes to file
    writer = pd.ExcelWriter(path, engine='xlsxwriter')
    df_title.to_excel(writer, sheet_name='Event',
                      startrow=0, startcol=0, index=False, header=False)
    df_event_ditails.to_excel(writer, sheet_name='Event',
                              startrow=3, startcol=0, index=False, header=True)
    df_event_data.to_excel(writer, sheet_name='Event',
                           startrow=8, startcol=0, index=False,)
    df_participants.to_excel(writer, sheet_name='Event',
                             startrow=13, startcol=0, index=False)

    # Set some cascading
    workbook = writer.book
    worksheet = writer.sheets['Event']

    title_format = workbook.add_format({'bold': True, 'font_size': 20})
    table_header_format = workbook.add_format({'bg_color': 'gray'})
    participants_accept_format = workbook.add_format({'bg_color': '#b3dfc1'})
    participants_accept_format2 = workbook.add_format({'bg_color': '#bfe2ca'})
    participants_wait_format = workbook.add_format({'bg_color': '#e6b9b8'})
    participants_wait_format2 = workbook.add_format({'bg_color': '#f2dddc'})

    worksheet.set_row(0, 25, title_format)
    worksheet.set_column(0, 8, 18, None)

    worksheet.set_row(4, 15, table_header_format)
    worksheet.set_row(9, 15, table_header_format)

    if len(participants) <= event['maxParticipants']:
        for col in range(14, 14+len(participants), 2):
            worksheet.set_row(
                col, 15 + 1, cell_format=participants_accept_format)
            worksheet.set_row(
                col+1, 15 + 1, cell_format=participants_accept_format2)
    else:
        for col in range(14, 14+len(participants), 2):
            if(col < 14+event['maxParticipants']):
                worksheet.set_row(
                    col, 15 + 1, cell_format=participants_accept_format)
                worksheet.set_row(
                    col+1, 15 + 1, cell_format=participants_accept_format2)
            else:
                worksheet.set_row(
                    col, 15 + 1, cell_format=participants_wait_format)
                worksheet.set_row(
                    col+1, 15 + 1, cell_format=participants_wait_format2)
    # Cleanup file created after request is done
    #writer.save()
    writer.close()
    background_tasks.add_task(os.remove, path)

    headers = {'Content-Disposition': 'attachment; filename="Book.xlsx"'}
    return FileResponse(path, headers=headers)
