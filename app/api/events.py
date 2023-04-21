from datetime import datetime, timedelta
import os
import shutil
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from pydantic import ValidationError
from starlette.responses import FileResponse
from starlette.background import BackgroundTasks
from uuid import uuid4, UUID
from app.utils.event_utils import event_has_started, num_of_confirmed_participants, num_of_deprioritized_participants, should_penalize, valid_registration, validate_event_dates, validate_pos_update
from app.utils.validation import validate_image_file_type, validate_uuid
from ..auth_helpers import authorize, authorize_admin, optional_authentication
from ..db import get_database, get_image_path, get_qr_path, get_export_path
from ..models import Event, EventDB, AccessTokenPayload, EventInput, EventUpdate, EventUserView, JoinEventPayload, Participant, ParticipantPosUpdate, Role, SetAttendencePayload
from .utils import get_event_or_404, penalize
import pandas as pd
from .mail import send_mail
from ..models import MailPayload
import asyncio
import qrcode as qr
from fpdf import FPDF


router = APIRouter()
lock = asyncio.Lock()

@router.post('/')
def create_event(request: Request, newEvent: EventInput, token: AccessTokenPayload = Depends(authorize_admin)):
    # TODO better format handling and date date-time handling
    db = get_database(request)
    # validates event date and registrationOpningDate
    validate_event_dates(newEvent)

    member = db.members.find_one({'id': UUID(token.user_id)})
    if member == None:
        raise HTTPException(500, "Problem caller not found")
    host_email = member["email"]

    eid = uuid4()
    additionalFields = {
        'eid': eid,
        'participants': [],
        'posts': [],
        'registeredPenalties': [],
        'host': host_email
    }
    if newEvent.bindingRegistration:
        additionalFields['confirmed'] = False

    event = newEvent.dict()
    event.update(additionalFields)
    event = db.events.insert_one(event)

    return {'eid': eid.hex}


@router.get('/')
def get_all_event_ids(request: Request, token: AccessTokenPayload = Depends(optional_authentication)):
    '''
    returns all public events and if user is admin all events are returned
    '''
    db = get_database(request)
    search_filter = {"public": {"$eq": True}}
    if token and token.role == Role.admin:
        search_filter = {}
    return [str(event['eid']) for event in db.events.find(search_filter)]


@router.get('/upcoming')
def get_upcoming_events(request: Request, token: AccessTokenPayload = Depends(optional_authentication)):
    '''
    Provides public upcoming events to regular members and return all events to admin
    '''
    db = get_database(request)
    # allows ongoing events to still be visible for users
    now = datetime.now() - timedelta(hours=4)

    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(500, "Problem handling date format")
    # search filter for non admin users
    search_filter = {
        "$and": [{'date': {'$gt': date}}, {"public": {"$eq": True}}]}
    if token and token.role == Role.admin:
        search_filter = {'date': {"$gt": date}}

    upcoming_events = db.events.find(search_filter)

    return [Event.parse_obj(event) for event in upcoming_events]

@router.get('/past-events')
def get_past_events(request: Request, token: AccessTokenPayload = Depends(optional_authentication)):
    """ Get last 10 events that have passed """
    # TODO: Expand endpoint to accept custom amount?
    db = get_database(request)

    # Get todays date
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


    # Apply search filter according to role
    search_filter = {
        "$and": [{'date': {'$lt': date}}, {"public": {"$eq": True}}]}
    if token and token.role == Role.admin:
        search_filter = {'date': {"$lt": date}}

    # Get the last 10 events
    pipeline = [
        {"$match": search_filter},
        {"$sort": {"date": -1}},
        {"$limit": 10}
    ]

    res = db.events.aggregate(pipeline)

    if not res:
        raise HTTPException(404, "No past events found")
    
    return [Event.parse_obj(event) for event in res]


@router.get('/joined-events')
def get_joined_events(request: Request, token: AccessTokenPayload = Depends(authorize)):
    """ Returns all (upcoming) events user has joined """
    db = get_database(request)
    member = db.members.find_one({'id': UUID(token.user_id)})
    if not member:
        raise HTTPException(404, "User could not be found")

    now = datetime.now()

    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(500, "Problem handling date format")
    

    search_filter = {'date': {"$gt": date}}

    # Events to be returned
    pipeline = [
        {"$match": search_filter},
        {"$unwind": "$participants"},
        {"$match": {"participants.id": {"$eq": member["id"]}}}
    ]
    res = db.events.aggregate(pipeline)

    return [EventUserView.parse_obj(e) for e in res]


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

    if not os.path.isdir(image_path):
        os.mkdir(image_path)

    picturePath = f"{image_path}/{UUID(id).hex}.png"

    with open(picturePath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    return Response(status_code=200)


@router.put('/{id}', dependencies=[Depends(validate_uuid)])
def update_event(request: Request, id: str, eventUpdate: EventUpdate, AccessTokenPayload=Depends(authorize_admin)):
    """ To unset an optional field set the value to null """
    db = get_database(request)
    event = get_event_or_404(db, id)

    # exclude_unset allows null to be included allowing for optional fields to be updated to be null i.e not present
    values = eventUpdate.dict(exclude_unset=True)
    if len(values) == 0:
        raise HTTPException(400, "Update values cannot be empty")

    if "date" in values:
        try:
            event_date = datetime.strptime(
                str(eventUpdate.date), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(400, "Invalid date format")

        if event_date < datetime.now():
            raise HTTPException(400, "Invalid date")

    # check if update does not remove required fields i.e a valid update
    try:
        EventDB.parse_obj({**event, **values})
    except ValidationError:
        raise HTTPException(
            400, "Cannot remove field as this is required filed for all events")

    result = db.events.find_one_and_update(
        {'eid': UUID(id)},
        {"$set": values})

    if not result:
        raise HTTPException(500, "Unexpected error when updating event")

    return Response(status_code=200)


@router.delete('/{id}', dependencies=[Depends(validate_uuid)])
def delete_event_by_id(request: Request, id: str, AccessTokenPayload=Depends(authorize_admin)):
    db = get_database(request)
    event = get_event_or_404(db, id)

    res = db.events.find_one_and_delete({'eid': event["eid"]})

    if not res:
        raise HTTPException(500, "Unexpected error when deleting event")

    return Response(status_code=200)


@router.get('/{id}', dependencies=[Depends(validate_uuid)])
def get_event_by_id(request: Request, id: str, token: AccessTokenPayload = Depends(optional_authentication)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    role = None

    if token:
        role = token.role
    if event["public"] == False and role != Role.admin:
        # only allow admin members acces to unpublished events
        raise HTTPException(
            403, "Insufficient privileges to access this resource")

    if role == Role.admin:
        return EventDB.parse_obj(event)

    return EventUserView.parse_obj(event)


@router.get('/{id}/participants', dependencies=[Depends(validate_uuid)])
def get_event_participants(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)

    if token.role == Role.admin:
        return [Participant.parse_obj(p) for p in event['participants']]

    if event["maxParticipants"] != None:
        # only return the list when events are open i.e no cap
        raise HTTPException(
            401, "regular user cannot get participant list for limited events")

    return [{'id': p['id'], 'name': p['realName']} for p in event['participants']]


@router.get('/{id}/options', dependencies=[Depends(validate_uuid)])
def get_event_options(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    """ Get event options for requesting user """
    db = get_database(request)
    event = get_event_or_404(db, id)

    # Get event (if user is joined)
    user_event = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": UUID(token.user_id)}}})
    
    # Check whether user exists in event
    if not user_event or 'participants' not in user_event:
        raise HTTPException(400, "User not joined event!")

    # Get user data and return
    userData = user_event['participants'][0]
    return {'food': userData['food'], 'transportation': userData['transportation'],
            'dietaryRestrictions': userData['dietaryRestrictions']}


@router.put('/{id}/update-options', dependencies=[Depends(validate_uuid)])
def update_event_options(request: Request, id: str, payload: JoinEventPayload, token: AccessTokenPayload = Depends(authorize)):
    """ Update options for given event """
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': UUID(token.user_id)})

    # Get event (if user is joined)
    user_event = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": UUID(token.user_id)}}})
    
    # Check whether user exists in event
    if not user_event or 'participants' not in user_event:
        raise HTTPException(400, "User not joined event!")
    
    # Can validate whether payload entries are
    # actually applicable for event here

    # Cannot update options for confirmed event   
    if event.get('confirmed'):
        raise HTTPException(400, "Cannot update options for confirmed event")

    # Create a dictionary with the payload
    values = payload.dict(exclude_unset=True)
    update_dict = {f"participants.$.{key}": value for key, value in values.items()}
    
    # Update db field
    res = db.events.update_one({"eid": event["eid"], "participants.id": member["id"]}, {"$set": update_dict})

    # Return error if user was not in event
    if not res:
        raise HTTPException(500, "Could not find user in event")
    


@router.post('/{id}/join', dependencies=[Depends(validate_uuid)])
def join_event(request: Request, id: str, payload: JoinEventPayload, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': UUID(token.user_id)})

    if not member:
        raise HTTPException(400, "User could not be found")

    if event_has_started(event):
        raise HTTPException(400, "Cannot join event after it started")

    # admin can join all events
    if member["role"] != Role.admin:
        if not valid_registration(event["registrationOpeningDate"]):
            raise HTTPException(403, "Event registration is not open")

        if event["public"] == False:
            raise HTTPException(403, "Event is not public")

    check_participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": member["id"]}}})

    try:
        check_participant['participants']
        raise HTTPException(400, "User already joined")
    except KeyError:
        pass

    participantData = {
        'food': payload.food,
        'transportation': payload.transportation,
        'dietaryRestrictions': payload.dietaryRestrictions,
        'submitDate': datetime.now(),
        'confirmed': False
    }

    new_fields = {**member, **participantData}
    participant = Participant.parse_obj(new_fields)

    # find pos in query to have the newest list when inserting
    pos = len(event["participants"])
    if member["penalty"] < 2:
        # members below penalty limit gets moved in front of penalized users
        pos -= num_of_deprioritized_participants(event["participants"])

    db.events.update_one(
        {'eid': event['eid']}, 
        {"$push": {
            "participants": { 
                "$each": [participant.dict()], 
                "$position": pos}
            }
        })

    return Response(status_code=200)


@router.post('/{id}/leave', dependencies=[Depends(validate_uuid)])
async def leave_event(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': UUID(token.user_id)})
    penalty = should_penalize(event, token.user_id)

    if not member:
        raise HTTPException(400, "User could not be found")

    if event_has_started(event):
        raise HTTPException(400, "Cannot leave event after it started")

    participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": member["id"]}}})

    if not participant:
        raise HTTPException(400, "User not joined event!")

    try:
        participant['participants']
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    if penalty:
        res = db.events.update_one(
            {'eid': event["eid"]},
            {"$addToSet": {"registeredPenalties": member["id"]}}
        )
        # Only give penalty if addToSet added a new entry
        if res.modified_count != 0:
            await penalize(db, member["id"])

    res = db.events.update_one({'eid': event['eid']}, {
        "$pull": {"participants": {"id": member["id"]}}})

    if res == None:
        raise HTTPException(500, "Unexpected error updating database in leave")

    return Response(status_code=200)


@router.get('/{id}/joined', dependencies=[Depends(validate_uuid)])
def is_joined_event(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    db = get_database(request)
    event = get_event_or_404(db, id)

    # uses event["eid"] instead of casting eid -> UUID
    user = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": UUID(token.user_id)}}})

    if not user:
        return {'joined': False}

    try:
        user['participants'][0]
        return {'joined': True}
    except KeyError:
        return {'joined': False}
    

@router.get('/{id}/confirmed', dependencies=[Depends(validate_uuid)])
def is_confirmed(request: Request, id: str, token: AccessTokenPayload = Depends(authorize)):
    """ Returns whether user is confirmed to event """
    db = get_database(request)
    event = get_event_or_404(db, id)

    # Get event (if user is joined)
    user_event = db.events.find_one({"eid": event['eid']}, {'participants': {
        '$elemMatch': {'id': UUID(token.user_id)}}})
    
    # Check whether user exists in event
    if not user_event or 'participants' not in user_event:
        raise HTTPException(400, "User not joined event!")
    
    userData = user_event['participants'][0]
    # Check whether event has been confirmed
    if not event.get('confirmed'):
        raise HTTPException(400, 'Event has not been confirmed yet')
    
    # Return user data
    return {'confirmed' : userData['confirmed']}


@router.delete('/{id}/removeParticipant/{uid}', dependencies=[Depends(validate_uuid)])
def remove_participant(request: Request, id: str, uid: str, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    event = get_event_or_404(db, id)
    member = db.members.find_one({'id': UUID(uid)})

    if not member:
        raise HTTPException(404, "User could not be found")

    participant = db.events.find_one({"eid": event["eid"]}, {"participants": {
        "$elemMatch": {"id": member["id"]}}})

    if not participant:
        raise HTTPException(400, "User not joined event!")

    try:
        participant['participants']
    except KeyError:
        raise HTTPException(400, "User not joined event!")

    db.events.update_one({'eid': event['eid']}, {
                         "$pull": {"participants": {"id": member["id"]}}})

    return Response(status_code=200)

@router.put('/{id}/updateParticipantsOrder/', dependencies=[Depends(validate_uuid)])
async def reorder_participants(request: Request, id:str, position_update: ParticipantPosUpdate, token: AccessTokenPayload = Depends(authorize_admin)):
    # blocks all request meaning no changes to the event when reordering
    # TODO find a more scaleable solution
    async with lock:
        db = get_database(request)
        event = get_event_or_404(db, id)
        participants = event["participants"]
        num_penalties = num_of_deprioritized_participants(participants)
        # start index of where penalized user should be
        pen_start_pos =  len(participants) - 1 - num_penalties

        if not validate_pos_update(participants, position_update.updateList):
            raise HTTPException(400, "Not valid: got invalid or outdated participant list")

        for participant in position_update.updateList:
            participant = participant.dict()
            for i, p in enumerate(participants):
                if p["id"] == participant["id"]:
                    new_pos = participant["pos"]
                    # Checks if a penalized member is moved in front of a non penalized member
                    if p["penalty"] >= 2 and new_pos <= pen_start_pos:
                        raise HTTPException(400, "User with penalty can't be rearranged")

                    # no need to swap same index
                    if new_pos == i:
                        continue
                    # swaps current pos with new pos
                    participants[i], participants[new_pos] = participants[new_pos], participants[i]
                    break

        if event["maxParticipants"]:
            for i, p in enumerate(participants):
                # ensure fields exist
                p = Participant.parse_obj(p).dict()
                if p["confirmed"] and i >= event["maxParticipants"]:
                   raise HTTPException(400, "Confirmed user cannot be moved to a non confirmed spot") 

        res = db.events.find_one_and_update({'eid': event["eid"]}, {"$set": { "participants": participants}})

        if res == None:
            HTTPException(500, "Unexpected error when updating participants list")

        return Response(status_code=200)

@router.post('/{id}/confirm', dependencies=[Depends(validate_uuid)])
async def confirmation(request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    async with lock:
        db = get_database(request)
        event = get_event_or_404(db, id)
        num_confs = num_of_confirmed_participants(event["participants"])

        if event["bindingRegistration"] == False:
            raise HTTPException(400, "Events without bindingRegistration should not send out confirmations")

        if event_has_started(event):
            raise HTTPException(400, "Cannot send confirmation after event start")

        if event["public"] == False:
            raise HTTPException(400, "Cannot send confirmation to a unpublished event")

        # if users cannot join confirmations cannot be sent out
        if not valid_registration(event["registrationOpeningDate"]):
            raise HTTPException(400, "Cannot send confirmations before registration is opened")

        result = db.events.find_one_and_update(
            {'eid': UUID(id)},
            {"$set": {"confirmed": True}})

        if not result:
            raise HTTPException(500, "Unexpected error when updating event")

        # all users joined gets confirmed if maxParticipants is not set
        # maxIdx-> which array position is 
        maxIdx = len(event["participants"])
        if event["maxParticipants"] != None:
            maxIdx = event["maxParticipants"]

        confirmationPositions = maxIdx - num_confs
        if confirmationPositions == 0:
            raise HTTPException(400, "All participants have received confirmation ")
        # Aggregate all participants emails to send confirmation email
        # doesn't needs to filter out penalty < 2 as these should be at the bottom of the list
        # includeArrayIndex preserves the original position making sure the aggregation always gets returned in correct order
        # meaning $limit excludes penalized participants
        pipeline = [
            {"$match": {"eid": event["eid"]}},
            {"$unwind": {"path": "$participants", "includeArrayIndex": "arrayIndex"}},
            {"$match": {"participants.confirmed": {"$ne": True}}},
            {"$sort": {"arrayIndex": 1}},
            {"$limit": confirmationPositions},
            {"$group": {"_id": "$participants.email"}},
        ]
        confirmedParticipants = db.events.aggregate(pipeline)

        mailingList = [p['_id'] for p in confirmedParticipants]
        # tags participants with confirmed 
        result = db.events.update_many(
                {"eid": event["eid"]}, 
                {"$set": {"participants.$[element].confirmed": True}}, 
                array_filters=[{"element.email": {"$in": mailingList}}],
            )
        if not result:
            raise HTTPException(500, "Unexpected error when updating participants")

        # Send email to all participants
        if request.app.config.ENV == 'production':
            with open("./app/assets/mails/event_confirmation.txt", 'r') as mail_content:
                content = mail_content.read().replace(
                    "$EVENT_NAME$", event['title'])
                content = content.replace(
                    "$DATE$", event['date'].strftime("%d %B, %Y"))
                content = content.replace("$TIME$", event['date'].strftime("%H:%M:%S"))
                content = content.replace("$LOCATION$", event['address'])
                # send mail individual
                for mail in mailingList:
                    confirmation_email = MailPayload(
                        to=[mail],
                        subject=f"Bekreftelse {event['title']}",
                        content=content,
                    )
                    send_mail(confirmation_email)

        return Response(status_code=200)


@router.get('/{id}/export', dependencies=[Depends(validate_uuid)])
async def exportEvent(background_tasks: BackgroundTasks, request: Request, id: str, token: AccessTokenPayload = Depends(authorize_admin)):
    if not os.path.exists(get_export_path(request)):
        os.makedirs(get_export_path(request))

    filename = f"{id}.xlsx"
    export_dir = get_export_path(request)
    path = f"{export_dir}/{filename}"

    db = get_database(request)
    event = get_event_or_404(db, id)

    participants = [Participant(
        **p).copy(exclude={'id'}).dict() for p in event['participants']]

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
    writer.close()
    background_tasks.add_task(os.remove, path)

    headers = {'Content-Disposition': 'attachment; filename="Book.xlsx"'}
    return FileResponse(path, headers=headers)
