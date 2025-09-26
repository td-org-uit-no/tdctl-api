from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from datetime import datetime, timedelta
from ..api.mail import send_mail
from ..models import MailPayload


def validate_registartion_opening_time(event_date, opening_date):
    try:
        # registration Opening Time are defined as days hours:minutes before the event starts
        opening_date = datetime.strptime(
            str(opening_date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(
            400, "Invalid date format for when registration is opening")
    if opening_date >= event_date:
        raise HTTPException(
            400, "Registration date must be before event start")
    return opening_date


def validate_event_dates(event):
    try:
        event_date = datetime.strptime(str(event.date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    if event_date < datetime.now():
        raise HTTPException(400, "Invalid date")

    if event.registrationOpeningDate != None:
        validate_registartion_opening_time(
            event.date, event.registrationOpeningDate)

    if event.prioritizedRegistrationDate != None:
        validate_registartion_opening_time(
            event.date, event.prioritizedRegistrationDate)

        # Prioritized registration date must be before regular registration date
        if event.registrationOpeningDate != None:
            try:
                prioritized_date = datetime.strptime(
                    str(event.prioritizedRegistrationDate), "%Y-%m-%d %H:%M:%S")
                regular_date = datetime.strptime(
                    str(event.registrationOpeningDate), "%Y-%m-%d %H:%M:%S")

                if prioritized_date >= regular_date:
                    raise HTTPException(
                        400, "Prioritized registration date must be before regular registration date")
            except ValueError:
                raise HTTPException(
                    400, "Invalid date format for prioritized registration date")

def validate_cancellation_time(start_date):
    """ validates if the cancellation time is inside the acceptable time frame """
    cancellation_threshold = 24
    now = datetime.now()
    try:
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        diff = abs(start_date-date)
    except ValueError:
        return False
    return diff >= timedelta(hours=cancellation_threshold)


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


def valid_registration(opening_date, member=None, event=None):
    # Check if member is in prioritized years and prioritized registration is open
    if member and event and event.get("prioritizedYears") and event.get("prioritizedRegistrationDate"):
        try:
            member_year = int(member["classof"])
            if member_year in event["prioritizedYears"]:
                prioritized_start = datetime.strptime(
                    str(event["prioritizedRegistrationDate"]), "%Y-%m-%d %H:%M:%S")
                if datetime.now() > prioritized_start:
                    return True
        except (ValueError, KeyError):
            pass

    # Check regular registration opening date
    # non specified opening date means registration is open
    if opening_date == None:
        return True
    try:
        # validates format
        registration_start = datetime.strptime(
            str(opening_date), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # sets registration open if field is malformed
        return True
    return datetime.now() > registration_start


def validate_pos_update(participants, updateList):
    """
    Validates position reorder input
    - id:
        - all participants in reorder list have already joined the event
    - pos
        - all pos arguments are valid i.e. between 0 and len(participants)
    """
    valid_args = list(range(0, len(participants)))
    joined_ids = [p["id"] for p in participants]
    for p in updateList:
        try:
            valid_args.remove(p.pos)
            joined_ids.remove(p.id)
        except ValueError:
            return False
    return len(valid_args) == 0 and len(joined_ids) == 0


def event_has_started(event):
    try:
        start_date = datetime.strptime(str(event["date"]), "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        return current_time > start_date
    except ValueError:
        return True


def event_starts_in(event, dt):
    """ 
    Return whether event has started, calculated with the given
    time delta (in hours)
    """
    try:
        start_date = datetime.strptime(str(event['date']), "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now() + timedelta(hours=dt)
        return current_time > start_date
    except ValueError:
        return True


def num_of_deprioritized_participants(participants):
    return sum(p["penalty"] > 1 for p in participants)


def num_of_confirmed_participants(participants):
    return sum(p["confirmed"] == True for p in participants)


def get_default_confirmation(event):
    with open("./app/assets/mails/event_confirmation.txt", 'r') as mail_content:
        content = mail_content.read().replace(
            "$EVENT_NAME$", event['title'])
        content = content.replace(
            "$DATE$", event['date'].strftime("%d %B, %Y"))
        content = content.replace("$TIME$", event['date'].strftime("%H:%M"))
        content = content.replace("$LOCATION$", event['address'])

        return content


def send_emails(mailing_list, subject, content):
    """
    Send emails to addresses in mailing list with given subject and content.
    """
    for address in mailing_list:
        email = MailPayload(
            to=[address],
            subject=subject,
            content=content
        )
        send_mail(email)
