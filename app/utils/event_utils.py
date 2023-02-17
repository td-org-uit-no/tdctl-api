from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from datetime import datetime, timedelta

def validate_registartion_opening_time(event_date, opening_date):
    try:
        # registration Opening Time are defined as days hours:minutes before the event starts
        opening_date = datetime.strptime(str(opening_date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format for when registration is opening")
    if opening_date >= event_date:
        raise HTTPException(400, "Registration date must be before event start")
    return opening_date

def validate_event_dates(event):
    print(event.date, event.registrationOpeningDate)
    try:
        event_date = datetime.strptime(str(event.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.now():
        raise HTTPException(400, "Invalid date")

    if event.registrationOpeningDate != None:
        validate_registartion_opening_time(event.date, event.registrationOpeningDate)

# validates if the cancellation time is inside the acceptable time frame
def validate_cancellation_time(start_date):
    cancellation_threshold = 24
    now = datetime.now()
    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        diff = abs(start_date-date)
        print(diff)
        print(diff>=timedelta(hours=cancellation_threshold))
    except ValueError:
        return False
    return diff>=timedelta(hours=cancellation_threshold)

def should_penalize(event, user_id):
    already_penalized = user_id in event["registeredPenalties"]
    if already_penalized:
        return False
    # Only penalize if regestration is late and the user is in a "reserved" spot
    # members in waiting list does not receive a penalty
    if (event["bindingRegistration"] and not validate_cancellation_time(event["date"])):
        maxParticipants = event["maxParticipants"]
        # no penalty when there are no reserved spots i.e no participant cap
        if maxParticipants == None:
            return False

        for member in event["participants"][:maxParticipants]:
            if member["id"] == UUID(user_id):
                return True
    return False

def valid_registration(opening_date):
    # non specified opening date means registration is open
    if opening_date == None:
        return True
    try:
        # validates format
        registration_start = datetime.strptime(str(opening_date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return datetime.now()>registration_start
