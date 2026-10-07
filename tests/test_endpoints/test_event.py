import os
import json
import re
from uuid import UUID, uuid4
import app.api.events as events_module
import app.utils.event_utils as event_utils
from app.db import get_test_db
from app.utils.event_utils import num_of_confirmed_participants, num_of_deprioritized_participants, get_default_waitlist_mail
from tests.conftest import client_login
from datetime import datetime, timedelta
from tests.test_endpoints.test_members import payload
from tests.users import regular_member, admin_member, second_admin, second_member

from tests.utils.authentication import admin_required, authentication_required

db = get_test_db()

future_time = datetime.now() + timedelta(hours=6)
future_time_str = future_time.strftime("%Y-%m-%d %H:%M:%S")
valid_reg_opening_time = datetime.now() + timedelta(hours=3)
valid_reg_opening_time_str = valid_reg_opening_time.strftime(
    "%Y-%m-%d %H:%M:%S")

new_event = {
    "title": "test event",
    "date": f"{future_time_str}",
    "address": "Test street 1",
    "description": "test description",
    "price": 0,
    "duration": 3,
    "maxParticipants": 1,
    "transportation": True,
    "food": False,
    "public": True,
    "bindingRegistration": True,
    "registeredPenalties": []
}

joinEventPayload = {
    "transportation": False,
    "food": True,
    "dietaryRestrictions": "Eggs"
}


with open("db/seeds/test_seeds/test_events.json") as seed_file:
    test_events = json.load(seed_file)
    for test_event in test_events:
        test_event["eid"] = UUID(test_event["eid"]).hex


with open("db/seeds/test_seeds/test_members.json") as seed_file:
    test_members = json.load(seed_file)

# makes sure we test on a uuid not existing
non_existing_eid = ""
while non_existing_eid in open('db/seeds/test_seeds/test_events.json').read():
    non_existing_eid = uuid4().hex
    continue


@admin_required("/api/event/", "post")
def test_create_event(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # tests for date being in the past
    invalid_date_event = {**new_event, "date": "2022-01-01T00:00:00"}
    response = client.post("/api/event/", json=invalid_date_event)
    assert response.status_code == 400
    response = client.post("/api/event/", json=new_event)
    assert response.status_code == 200
    res_json = response.json()
    event = db.events.find_one({'eid': UUID(res_json["eid"])})
    assert event != None


@admin_required("/api/event/{uuid}", "put")
def test_update_event(client):
    update_field = {"title": "new title"}
    eid = test_events[0]["eid"]
    invalid_date = {"date": "2022-01-01T00:00:00"}

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.put(f"/api/event/{eid}", json=invalid_date)
    assert response.status_code == 400

    non_existing_eid = "1"*32
    response = client.put(f"/api/event/{non_existing_eid}", json=update_field)
    assert response.status_code == 404

    response = client.put(f"/api/event/{eid}", json=update_field)
    assert response.status_code == 200

    event = db.events.find_one({'eid': UUID(eid)})
    assert event and event["title"] == update_field["title"]


@admin_required("/api/event/{uuid}", "delete")
def test_delete_event(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # test delete on non existing event
    response = client.delete(f"api/event/{non_existing_eid}")
    assert response.status_code == 404

    # test delete on existing event
    eid = test_events[0]["eid"]
    response = client.delete(f"api/event/{eid}")
    assert response.status_code == 200

    event = db.events.find_one({'eid': eid})
    assert event == None


def test_get_all_event(client):
    response = client.get("/api/event/")
    assert response.status_code == 200
    assert len(response.json()) == len(test_events)


def test_get_upcoming_events(client):
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post("/api/event/", json=new_event)
    assert response.status_code == 200
    response = client.get("/api/upcoming/")
    assert len(response.json()) == 1

def test_get_past_events_count(client):
    # Login as admin
    client_login(client, admin_member["email"], admin_member["password"])

    # Get count of past events
    response = client.get('/api/event/past-events/count')
    assert response.status_code == 200
    count_response = response.json()
    assert "count" in count_response

    # Assert that the count matches the expected number
    expected_past_events_count = 17 
    assert count_response["count"] == expected_past_events_count


def test_get_past_events_with_pagination(client):
    # Login as admin
    client_login(client, admin_member["email"], admin_member["password"])

    # Get total count of past events
    response = client.get('/api/event/past-events/count')
    assert response.status_code == 200
    total_past_events = response.json()["count"]

    # Set pagination parameters
    limit = 10  
    total_pages = (total_past_events + limit - 1) // limit  

    # Iterate through pages
    for page in range(total_pages):
        skip = page * limit
        response = client.get(f'/api/event/past-events?skip={skip}')
        assert response.status_code == 200
        past_events = response.json()

        # Calculate expected number of events on this page
        expected_events = min(limit, total_past_events - skip)
        assert len(past_events) == expected_events


@authentication_required("/api/event/joined-events", "get")
def test_get_joined_events(client):
    # Login
    client_login(client, admin_member["email"], admin_member["password"])

    # Seeded events are past, should return none
    response = client.get("/api/event/joined-events/")
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Make copy to avoid affecting other tests
    event = new_event.copy()
    event["public"] = False

    # Create upcoming, unpublished event
    response = client.post("/api/event/", json=new_event)
    assert response.status_code == 200
    test_event_id = response.json()["eid"]

    # Join
    response = client.post(
        f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Now returns one event
    response = client.get("/api/joined-events/")
    assert len(response.json()) == 1


def test_get_event_picture(client):
    eid = test_events[0]["eid"]

    response = client.get(f'/api/event/{eid}/image')
    assert response.status_code == 200

    response = client.get(f'/api/event/{non_existing_eid}/image')
    assert response.status_code == 404


@admin_required("/api/event/{uuid}/image", "post")
def test_upload_event_picture(client):
    eid = test_events[0]["eid"]
    img_path = f'db/seeds/seed_images/{eid}.png'
    file = {
        "image": (f'{eid}.png', open(f'{img_path}', 'rb'), 'image/png'),
    }

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post(f'/api/event/{eid}/image', files=file)
    assert response.status_code == 200

    # tests file type validation
    file_name = 'tmp.txt'
    with open(file_name, 'w') as file:
        file.write("testing")

    file = {
        "image": (f'{file_name}', open(file_name, 'rb'), 'text/plain'),
    }
    response = client.post(f'/api/event/{eid}/image', files=file)
    assert response.status_code == 400
    os.remove(file_name)


def test_get_event_by_id(client):
    eid = test_events[0]["eid"]

    response = client.get(f'/api/event/{non_existing_eid}')
    assert response.status_code == 404

    response = client.get(f'/api/event/{eid}')
    res = response.json()
    assert response.status_code == 200
    assert ("participants" in res) == False

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.get(f'/api/event/{eid}')
    assert response.status_code == 200


def test_get_event_participants(client):
    eid = test_events[1]["eid"]

    # Test regular member

    client_login(client, regular_member["email"], regular_member["password"])

    response = client.get(f'/api/event/{non_existing_eid}/participants')
    assert response.status_code == 404

    response = client.get(f'/api/event/{eid}/participants')
    res_json = response.json()
    assert response.status_code == 401

    # checks that list is only returned for regular users on open events
    response = client.get(f'/api/event/{eid}/participants')
    res_json = response.json()
    assert response.status_code == 401

    # Test admin

    client_login(client, admin_member["email"], admin_member["password"])

    # Check expected behavior
    response = client.get(f'/api/event/{eid}/participants')
    res_json = response.json()
    assert response.status_code == 200
    assert len(res_json) == len(test_members)

    # remove maxParticipants to check that participants are returned
    update_field = {"maxParticipants": None}
    response = client.put(f"/api/event/{eid}", json=update_field)
    assert response.status_code == 200
    response = client.get(f'/api/event/{eid}/participants')
    res_json = response.json()
    assert response.status_code == 200
    assert len(res_json) == len(test_members)

    response = client.get(f'/api/event/{eid}/participants')
    res_json = response.json()
    assert response.status_code == 200
    assert len(res_json) == len(test_members)
    assert 'food' in res_json[0]


@authentication_required("/api/event/{uuid}/options", "get")
def test_get_event_options(client):
    # Login
    client_login(client, admin_member["email"], admin_member["password"])

    # Add event to insert options
    response = client.post("/api/event/", json=new_event)
    eid = response.json()["eid"]
    assert response.status_code == 200

    # Join with options
    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Fetch event options
    response = client.get(f'/api/event/{eid}/options')
    assert response.status_code == 200
    assert response.json()[
        'transportation'] == joinEventPayload['transportation']
    assert response.json()['food'] == joinEventPayload['food']
    assert response.json()[
        'dietaryRestrictions'] == joinEventPayload['dietaryRestrictions']


@authentication_required("/api/event/{uuid}/options", "get")
def test_update_event_options(client):
    # Login
    client_login(client, admin_member["email"], admin_member["password"])

    # Create event to insert options
    response = client.post("/api/event/", json=new_event)
    eid = response.json()["eid"]
    assert response.status_code == 200

    # Join with options
    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Update options
    updateEventPayload = {
        "transportation": True,
        "food": False,
        "dietaryRestrictions": ""
    }
    response = client.put(
        f'/api/event/{eid}/update-options', json=updateEventPayload)
    assert response.status_code == 200

    # Fetch updated event options
    response = client.get(f'/api/event/{eid}/options')
    assert response.status_code == 200
    assert response.json()[
        'transportation'] == updateEventPayload['transportation']
    assert response.json()['food'] == updateEventPayload['food']
    assert response.json()[
        'dietaryRestrictions'] == updateEventPayload['dietaryRestrictions']

    # Set event to confirmed
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    # Should fail to update options
    response = client.put(
        f'/api/event/{eid}/update-options', json=updateEventPayload)
    assert response.status_code == 400


@authentication_required("/api/event/{uuid}/join", "post")
def test_join_unpublished_event(client):
    # make copy so other test doesn't get affected
    event = new_event.copy()
    event["public"] = False
    # allow for more users to join
    event["maxParticipants"] = 3

    # Login as admin
    client_login(client, admin_member["email"], admin_member["password"])
    # Create unpublished event
    response = client.post("/api/event/", json=event)
    test_event_id = response.json()["eid"]
    assert response.status_code == 200

    # admin should be able to join unpublished events
    response = client.post(
        f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Login as regular member
    client_login(client, regular_member["email"], regular_member["password"])
    # try joining closed event
    response = client.post(
        f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 403

    ########## Set registration opening date ##########

    # Relogin as admin
    client_login(client, admin_member["email"], admin_member["password"])

    # set registration to open in 3 hours
    response = client.put(
        f'/api/event/{test_event_id}/', json={"registrationOpeningDate": valid_reg_opening_time_str, "public": True})
    assert response.status_code == 200

    # user should not be able to join before event registration opens
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post(
        f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 403

    # admin should be able to join
    client_login(client, second_admin["email"], second_admin["password"])
    response = client.post(
        f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 200


@authentication_required("/api/event/{uuid}/join", "post")
def test_join_published_event(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # creates event with maxParticipants = 1
    response = client.post("/api/event/", json=new_event)
    new_event_eid = response.json()["eid"]
    assert response.status_code == 200

    # joins the event
    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # creates new member for joining the event
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    # checks response on full event
    client_login(client, payload["email"], payload["password"])

    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # === test join ordering ===
    client_login(client, admin_member["email"], admin_member["password"])
    eid = test_events[0]["eid"]

    # setup event
    response = client.put(
        f"/api/event/{eid}", json={"date": f"{future_time_str}"})
    assert response.status_code == 200

    new_member = db.members.find_one({"email": payload["email"]})
    assert new_member

    client_login(client, payload["email"], payload["password"])

    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200
    # check that joined non penalized comes in front of penalized member
    updated_event = db.events.find_one({"eid": UUID(eid)})
    assert updated_event
    assert num_of_deprioritized_participants(
        updated_event["participants"]) != 0
    for p in updated_event["participants"]:
        if p["id"] == new_member["id"]:
            break
        # should not be a participants with penalty in front of joined participant
        assert p["penalty"] < 2


@authentication_required("/api/event/{uuid}/leave", "post")
def test_leave_event(client):
    event = new_event.copy()
    # creates an event starting in > 24 hours
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post("/api/event/", json=event)
    new_event_eid = response.json()["eid"]
    assert response.status_code == 200

    event["bindingRegistration"] = False
    response = client.post("/api/event/", json=event)
    # creates new members as all seeding members are joined events
    eid = test_events[1]["eid"]
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    client_login(client, payload["email"], payload["password"])
    # checks for leaving as a user not joined a event
    response = client.post(f'/api/event/{eid}/leave')
    assert response.status_code == 400

    # checks for leaving as non existing user
    response = client.post(f'/api/event/{non_existing_eid}/leave')
    assert response.status_code == 404

    # all seeding members are joined every event
    client_login(client, admin_member["email"], admin_member["password"])

    # should not be able to leave finished event
    response = client.post(f'/api/event/{eid}/leave')
    assert response.status_code == 400

    response = client.put(
        f"/api/event/{eid}", json={"date": f"{future_time_str}"})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/leave')
    assert response.status_code == 200

    # tests penalty assignment for leaving event with binding registration starting in > 24 hours
    member_before_leave = db.members.find_one(
        {'email': regular_member["email"]})
    assert member_before_leave
    second_member_before_leave = db.members.find_one(
        {'email': second_member["email"]})
    assert second_member_before_leave

    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    penalty_before = member_before_leave["penalty"]

    client_login(client, second_member["email"], second_member["password"])
    # test that users on waiting list does not receive penalty
    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    response = client.post(f'/api/event/{new_event_eid}/leave')
    assert response.status_code == 200

    second_member_after = db.members.find_one(
        {'email': second_member["email"]})
    assert second_member_after and second_member_after["penalty"] - \
        second_member_before_leave["penalty"] == 0

    # Relogin again after login in as admin before
    client_login(client, regular_member["email"], regular_member["password"])

    response = client.post(f'/api/event/{new_event_eid}/leave')
    assert response.status_code == 200

    # checks if user gets a penalty as the leave is > 24 hours before event start
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and member["penalty"] - penalty_before == 1

    already_penalized_member = db.members.find_one(
        {'email': regular_member["email"]})
    assert already_penalized_member
    penalty_before = already_penalized_member["penalty"]

    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    response = client.post(f'/api/event/{new_event_eid}/leave')
    assert response.status_code == 200

    # check that user doesn't get another penalty
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and member["penalty"] - penalty_before == 0


@authentication_required("/api/event/{uuid}/joined", "get")
def test_is_joined_event(client):
    eid = test_events[0]["eid"]
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    client_login(client, payload["email"], payload["password"])
    response = client.get(f'/api/event/{non_existing_eid}/joined')
    assert response.status_code == 404

    response = client.get(f'/api/event/{eid}/joined')
    assert response.status_code == 200
    res = response.json()
    assert res["joined"] == False

    client_login(client, regular_member["email"], regular_member["password"])
    response = client.get(f'/api/event/{eid}/joined')
    assert response.status_code == 200
    res = response.json()
    assert res["joined"] == True


@authentication_required("/api/event/{uuid}/joined", "get")
def test_is_confirmed(client):
    # Login
    client_login(client, admin_member["email"], admin_member["password"])

    # Create new event to confirm
    response = client.post("/api/event/", json=new_event)
    eid = response.json()["eid"]
    assert response.status_code == 200

    # Should not be confirmed
    response = client.get(f'/api/event/{eid}/confirmed')
    assert response.status_code == 400

    # Join
    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Should not be confirmed
    response = client.get(f'/api/event/{eid}/confirmed')
    assert response.status_code == 400

    # Set event to confirmed
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    # Should be confirmed
    response = client.get(f'/api/event/{eid}/confirmed')
    assert response.status_code == 200


@admin_required("/api/event/{uuid}/removeParticipant/{uuid}", "delete")
def test_remove_participant(client):
    eid = test_events[0]["eid"]

    client_login(client, admin_member["email"], admin_member["password"])

    participants_before = client.get(f'/api/event/{eid}/participants')

    participants_before = participants_before.json()

    # Remove first participant from event
    participant_id = participants_before[0]['id']
    resp = client.delete(
        f'/api/event/{eid}/removeParticipant/{participant_id}')
    assert resp.status_code == 200

    participants_after = client.get(f'/api/event/{eid}/participants')

    participants_after = participants_after.json()
    assert len(participants_after) == len(participants_before) - 1
    assert participants_after[0]['id'] != participants_before[0]['id']


@admin_required("/api/event/{uuid}/export", "get")
def test_export_event(client):
    eid = test_events[0]["eid"]

    client_login(client, admin_member["email"], admin_member["password"])

    response = client.get(f'/api/event/{eid}/export')
    assert response.status_code == 200

    response = client.get(f'/api/event/{non_existing_eid}/export')
    assert response.status_code == 404


@admin_required("/api/event/{uuid}/confirm-message", "get")
def test_confirm_message(client):
    eid = test_events[0]["eid"]

    client_login(client, admin_member["email"], admin_member["password"])

    response = client.get(f'/api/event/{eid}/confirm-message')
    assert response.status_code == 200
    body = response.json()
    assert body['message'] != None

    response = client.get(f'/api/event/{non_existing_eid}/confirm-message')
    assert response.status_code == 404


@admin_required("/api/event/{uuid}/mail", "post")
def test_send_notification_mail(client):
    eid = test_events[0]["eid"]

    client_login(client, admin_member["email"], admin_member["password"])

    payload = {'subject': 'test subject',
               'msg': 'test msg', 'confirmedOnly': True}

    response = client.post(f'/api/event/{non_existing_eid}/mail', json=payload)
    assert response.status_code == 404

    # Test confirmed only when none are confirmed
    response = client.post(f'/api/event/{eid}/mail', json=payload)
    assert response.status_code == 400

    # Confirm and retry
    response = client.put(
        f'/api/event/{eid}', json={"date": f'{future_time_str}', 'maxParticipants': 1, 'public': True})
    assert response.status_code == 200

    response = client.post(
        f'/api/event/{eid}/confirm', json={'msg': 'test message'})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/mail', json=payload)
    assert response.status_code == 202

    # Test sending to all
    payload["confirmedOnly"] = False
    response = client.post(f'/api/event/{eid}/mail', json=payload)
    assert response.status_code == 202

    # Too long subject
    payload["subject"] = "a" * 51
    response = client.post(f'/api/event/{eid}/mail', json=payload)
    assert response.status_code == 400

    # Too long message
    payload["subject"] = "test"
    payload["msg"] = "a" * 5001
    response = client.post(f'/api/event/{eid}/mail', json=payload)
    assert response.status_code == 400


@admin_required("/api/event/{uuid}/confirm", "post")
def test_confirm_event(client):
    eid = test_events[0]["eid"]
    payload = {"msg": "test message"}

    client_login(client, admin_member["email"], admin_member["password"])

    # check confirmation is not allowed on finished events
    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    assert response.status_code == 400

    # update to valid date but not public
    response = client.put(
        f"/api/event/{eid}", json={"date": f"{future_time_str}", "maxParticipants": 1, "public": False})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    assert response.status_code == 400

    # setup for confirmation on event who isn't open for registration
    response = client.put(
        f"/api/event/{eid}", json={"public": True, "registrationOpeningDate": f"{future_time_str}"})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    assert response.status_code == 400

    response = client.put(
        f"/api/event/{eid}", json={"registrationOpeningDate": None})
    assert response.status_code == 200

    # check expected behavior
    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    assert response.status_code == 200

    event = db.events.find_one({"eid": UUID(eid)})
    assert event and num_of_confirmed_participants(
        event["participants"]) == event["maxParticipants"]

    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    # should get 400 when all participants have gotten their confirmation mail
    assert response.status_code == 400

    response = client.put(
        f"/api/event/{eid}", json={"maxParticipants": (event["maxParticipants"] + 1)})
    assert response.status_code == 200

    # should be able to confirm again when another unconfirmed participant is allowed
    response = client.post(f'/api/event/{eid}/confirm', json=payload)
    assert response.status_code == 200

    response = client.put(f"/api/event/{eid}", json={"maxParticipants": None})
    assert response.status_code == 200

    # should not be required to supply custom email
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})

    event = db.events.find_one({"eid": UUID(eid)})
    # checks that all participants gets confirmation when there are no limit
    assert event and num_of_confirmed_participants(
        event["participants"]) == len(event["participants"])


@admin_required("/api/event/{uuid}/updateParticipantsOrder", "put")
def test_event_reorder(client):
    eid = test_events[0]["eid"]
    event = db.events.find_one({"eid": UUID(eid)})
    assert event
    max_idx = len(event["participants"]) - 1
    penalty_idx = None

    client_login(client, admin_member["email"], admin_member["password"])

    new_order = []
    for i, p in enumerate(event["participants"]):
        if p["penalty"] >= 2:
            penalty_idx = i
        new_order.append({"id": p["id"].hex, "pos": i})

    # test setup not done properly all events should have 1 penalized member
    assert penalty_idx != None

    new_order[0]["pos"] = 1
    new_order[1]["pos"] = 0
    # test expected behavior
    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": new_order})
    assert response.status_code == 200
    event_after = db.events.find_one({"eid": UUID(eid)})
    assert event_after
    diff = False
    participants = event_after["participants"]
    for i, p in enumerate(event["participants"]):
        if p["id"] != participants[i]["id"]:
            diff = True
            break
    assert diff == True

    # checks that order is actually updated
    assert participants[0]["id"] == UUID(new_order[1]["id"])
    assert participants[1]["id"] == UUID(new_order[0]["id"])

    invalid_reorder = new_order
    invalid_reorder[0]["pos"] = penalty_idx
    invalid_reorder[penalty_idx]["pos"] = 0

    # checks that penalized members cannot be moved in front of non penalized member
    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": invalid_reorder})
    assert response.status_code == 400

    invalid_reorder = new_order
    invalid_reorder[0]["pos"] = max_idx + 1

    # checks that reorder only accepts valid pos input
    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": invalid_reorder})
    assert response.status_code == 400

    invalid_reorder[0]["pos"] = -1

    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": invalid_reorder})
    assert response.status_code == 400

    response = client.put(
        f"/api/event/{eid}", json={"maxParticipants": 2, "date": f"{future_time_str}"})
    assert response.status_code == 200

    # tests that a non joined user can be "reorder into the event"
    # creates an non joined member who has not joined the event
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200
    new_member = db.members.find_one({"email": payload["email"]})
    assert new_member

    invalid_id = new_order
    invalid_id[0]["id"] = new_member["id"].hex
    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": invalid_id})
    assert response.status_code == 400

    # tests for reordering with duplicates
    invalid_id = new_order
    invalid_id[1] = new_order[0]

    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": invalid_id})
    assert response.status_code == 400

    # setup for reorder after confirmation is sent
    response = client.put(
        f"/api/event/{eid}", json={"maxParticipants": 1})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    # reorder a confirmed member to a non confirmed spot
    new_order[0]["pos"] = 1
    new_order[1]["pos"] = 0

    response = client.put(
        f'/api/event/{eid}/updateParticipantsOrder', json={"updateList": new_order})
    assert response.status_code == 400


@authentication_required('/api/event/{uuid}/register', 'put')
def test_update_attendance(client):
    eid = test_events[0]['eid']

    # Self update
    client_login(client, admin_member["email"], admin_member["password"])
    payload = {
        'attendance': True
    }

    # Should not register events without registration (and register id)
    response = client.put(f'/api/event/{eid}/register', json=payload)
    assert response.status_code == 404

    # Create registration for event
    response = client.post(f'/api/event/{eid}/qr')
    assert response.status_code == 201

    # Get registration id
    event = db.events.find_one({'eid': UUID(eid)})
    assert 'register_id' in event
    rid = event['register_id']

    # Should be able to register
    response = client.put(f'/api/event/{rid}/register', json=payload)
    assert response.status_code == 200

    # Create future event
    response = client.post('/api/event/', json=new_event)
    assert response.status_code == 200
    eid = response.json()["eid"]

    # Create registration for new event
    response = client.post(f'/api/event/{eid}/qr')
    assert response.status_code == 201

    # Get new register id
    event = db.events.find_one({'eid': UUID(eid)})
    assert 'register_id' in event
    rid = event['register_id']

    # Join event
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # Should not be able to register future event yet
    response = client.put(f'/api/event/{rid}/register', json=payload)
    assert response.status_code == 403

    # Set event to happen soon
    new_future_time = datetime.now() + timedelta(minutes=30)
    new_future_time_str = new_future_time.strftime("%Y-%m-%d %H:%M:%S")
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.put(
        f'/api/event/{eid}', json={"date": new_future_time_str})
    assert response.status_code == 200

    # Should be able do register less than 1 hour prior
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.put(f'/api/event/{rid}/register', json=payload)
    assert response.status_code == 200

    # Update others attendance
    eid = test_events[0]['eid']

    client_login(client, admin_member['email'], admin_member['password'])

    # Get participant list before test
    response = client.get(f'/api/event/{eid}/participants')
    assert response.status_code == 200
    participants_before = response.json()

    # Set first participant as attended
    payload = {
        'member_id': participants_before[0]['id'],
        'attendance': True
    }
    # Regular member should not be authorized
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.put(f'/api/event/{eid}/register', json=payload)
    assert response.status_code == 401

    # Admin should be authorized
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.put(f'/api/event/{eid}/register', json=payload)
    assert response.status_code == 200

    # Assert change has been made
    response = client.get(f'/api/event/{eid}/participants')
    assert response.status_code == 200
    participants_after = response.json()
    assert participants_after[0]['attended'] == payload['attendance']

    # Set as not attended
    payload["attendance"] = False
    response = client.put(f'/api/event/{eid}/register', json=payload)
    assert response.status_code == 200

    # Assert change has been made
    response = client.get(f'/api/event/{eid}/participants')
    assert response.status_code == 200
    participants_after = response.json()
    assert participants_after[0]['attended'] == payload['attendance']


@admin_required('/api/event/{uuid}/register-absence', 'post')
def test_register_absence(client):
    eid = test_events[0]['eid']

    client_login(client, admin_member['email'], admin_member['password'])

    # Should not be able to register absence on unconfirmed event
    response = client.post(f'/api/event/{eid}/register-absence')
    assert response.status_code == 400

    # Set event to future in order to confirm it
    response = client.put(
        f"/api/event/{eid}", json={"date": f"{future_time_str}"})
    assert response.status_code == 200

    # Now confirm event
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    # Should not be able to register absence on future event
    response = client.post(f'/api/event/{eid}/register-absence')
    assert response.status_code == 400

    # Get participant list
    response = client.get(f'/api/event/{eid}/participants')
    assert response.status_code == 200
    participants = response.json()

    # Get first participant before
    p0_before = db.members.find_one({'id': UUID(participants[0]['id'])})
    # Get second participant before
    p1_before = db.members.find_one({'id': UUID(participants[1]['id'])})

    # Set first participant as attended
    payload = {
        'member_id': participants[0]['id'],
        'attendance': True
    }
    response = client.put(f'/api/event/{eid}/register', json=payload)
    assert response.status_code == 200

    # Set event date back to register absence
    time = datetime.now() - timedelta(hours=1)
    time_str = time.strftime("%Y-%m-%d %H:%M:%S")
    res = db.events.find_one_and_update(
        {'eid': UUID(eid)},
        {"$set": {"date": time_str}}
    )
    assert res

    # Register absence for event
    response = client.post(f'/api/event/{eid}/register-absence')
    assert response.status_code == 200

    # First participant should not be penalized
    p0_after = db.members.find_one({'id': UUID(participants[0]['id'])})
    assert p0_after['penalty'] == p0_before['penalty']

    # Second participant should be penalized
    p1_after = db.members.find_one({'id': UUID(participants[1]['id'])})
    assert p1_after['penalty'] > p1_before['penalty']

    # Subsequent run should not penalize again
    response = client.post(f'/api/event/{eid}/register-absence')
    assert response.status_code == 400


@admin_required('/api/event/{uuid}/qr', 'post')
def test_create_qr(client):
    eid = test_events[0]['eid']

    client_login(client, admin_member['email'], admin_member['password'])

    # Should be able to create qr
    response = client.post(f'/api/event/{eid}/qr')
    assert response.status_code == 201

    # Should receive 400 if qr is already created
    response = client.post(f'/api/event/{eid}/qr')
    assert response.status_code == 400


@admin_required('/api/event/{uuid}/qr', 'get')
def test_get_qr(client):
    eid = test_events[0]['eid']

    client_login(client, admin_member['email'], admin_member['password'])

    # Should not be able to get qr if not yet made
    response = client.get(f'/api/event/{eid}/qr')
    assert response.status_code == 400

    # Create qr
    response = client.post(f'/api/event/{eid}/qr')
    assert response.status_code == 201

    # Should now get qr document
    response = client.get(f'/api/event/{eid}/qr')
    assert response.status_code == 200


@admin_required("/api/event/", "post")
def test_create_event_contact_email(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # omitted -> defaults to None and still works (back-compat)
    response = client.post("/api/event/", json=new_event)
    assert response.status_code == 200
    eid = response.json()["eid"]
    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] is None

    # provided -> survives create -> read
    contact = "contact@example.com"
    response = client.post(
        "/api/event/", json={**new_event, "contactEmail": contact})
    assert response.status_code == 200
    eid = response.json()["eid"]

    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact

    event = db.events.find_one({'eid': UUID(eid)})
    assert event and event["contactEmail"] == contact

    # invalid email is rejected by validation
    response = client.post(
        "/api/event/", json={**new_event, "contactEmail": "not-an-email"})
    assert response.status_code == 422


@admin_required("/api/event/{uuid}", "put")
def test_update_event_contact_email(client):
    eid = test_events[0]["eid"]
    client_login(client, admin_member["email"], admin_member["password"])

    contact = "updated-contact@example.com"
    response = client.put(f"/api/event/{eid}", json={"contactEmail": contact})
    assert response.status_code == 200

    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact

    event = db.events.find_one({'eid': UUID(eid)})
    assert event and event["contactEmail"] == contact


@admin_required("/api/event/{uuid}", "put")
def test_update_event_contact_email_can_be_cleared(client):
    eid = test_events[0]["eid"]
    client_login(client, admin_member["email"], admin_member["password"])

    contact = "clear-me@example.com"
    response = client.put(f"/api/event/{eid}", json={"contactEmail": contact})
    assert response.status_code == 200
    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact

    # an explicit null clears the optional field, since model_dump(exclude_unset=True)
    # passes it through to the $set update
    response = client.put(f"/api/event/{eid}", json={"contactEmail": None})
    assert response.status_code == 200
    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] is None
    event = db.events.find_one({'eid': UUID(eid)})
    assert event and event.get("contactEmail") is None

    # omitting the field in a later update leaves the stored value untouched
    response = client.put(f"/api/event/{eid}", json={"contactEmail": contact})
    assert response.status_code == 200
    response = client.put(f"/api/event/{eid}", json={"title": "changed title"})
    assert response.status_code == 200
    response = client.get(f"/api/event/{eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact
    event = db.events.find_one({'eid': UUID(eid)})
    assert event and event["contactEmail"] == contact


# ---------------------------------------------------------------------------
# POST /api/event/{id}/mail recipient selection
# ---------------------------------------------------------------------------


def _capture_emails(monkeypatch, client):
    """Force the production mail code path and capture recipient lists.

    ``send_emails`` is only scheduled when config.ENV == 'production', so we
    swap in a recorder and flip the flag. This asserts on the *computed*
    recipient set without sending anything.
    """
    sent = []

    def fake_send_emails(mailing_list, subject, content):
        sent.append(
            {"to": list(mailing_list), "subject": subject, "content": content})

    monkeypatch.setattr(events_module, "send_emails", fake_send_emails)
    monkeypatch.setattr(client.app.config, "ENV", "production")
    return sent


def _capture_mail_payloads(monkeypatch, client, env="production", fail_for=None):
    """Capture the real MailPayload objects by stubbing only the transport.

    ``send_mail`` is patched one level below ``send_emails`` and
    ``send_waitlist_emails``, so both run for real: this is what verifies
    payload construction, per-address error isolation and delivery-based
    marking. ``fail_for`` simulates a failed send for those addresses; ``env``
    selects the (non-)production code path.

    Returns ``(payloads, attempted)`` - the payloads that would go on the wire
    and every address the transport was called for (including failed ones).
    """
    payloads = []
    attempted = []
    fail_for = set(fail_for or ())

    def fake_send_mail(payload):
        address = payload.to[0]
        attempted.append(address)
        if address in fail_for:
            raise RuntimeError(f"simulated send failure for {address}")
        payloads.append(payload)

    monkeypatch.setattr(event_utils, "send_mail", fake_send_mail)
    monkeypatch.setattr(client.app.config, "ENV", env)
    return payloads, attempted


def _participant_row(email, confirmed):
    return {
        "id": uuid4(), "realName": "Test Person", "email": email,
        "classof": "2023", "phone": None, "role": "member",
        "food": False, "transportation": False, "dietaryRestrictions": "",
        "submitDate": datetime.now(), "penalty": 0,
        "confirmed": confirmed, "attended": None,
    }


def test_send_waitlist_emails_flags_only_the_unconfirmed_row_sharing_an_address(
        client, monkeypatch):
    """members.email has no unique index, so two participant rows can share one.

    Only the unconfirmed row is on the waiting list; the confirmed row must not
    be recorded as notified just because it happens to share the address.
    """
    monkeypatch.setattr(event_utils, "send_mail", lambda payload: None)

    eid = test_events[0]["eid"]
    shared, waiting = "shared@test.com", "waiting@test.com"
    db.events.update_one({'eid': UUID(eid)}, {"$set": {"participants": [
        _participant_row(shared, confirmed=True),
        _participant_row(waiting, confirmed=False),
    ]}})

    event_utils.send_waitlist_emails(
        db, UUID(eid), [shared, waiting], "Emne", "Innhold")

    event = db.events.find_one({'eid': UUID(eid)})
    rows = {}
    for p in event["participants"]:
        rows.setdefault(p["email"], []).append(p)

    assert rows[shared][0]["confirmed"] is True
    assert not rows[shared][0].get("waitListNotified"), (
        "a confirmed participant must not be flagged as notified")
    assert rows[waiting][0].get("waitListNotified") == True


def _prepare_confirmable(client, n, **extra):
    """Make the first seeded event confirmable, without confirming it yet."""
    eid = test_events[0]["eid"]
    body = {"date": f"{future_time_str}", "public": True,
            "registrationOpeningDate": None, "maxParticipants": n}
    body.update(extra)
    response = client.put(f"/api/event/{eid}", json=body)
    assert response.status_code == 200
    return eid


def _confirm_first_n(client, n, **extra):
    """Make the first seeded event confirmable and confirm its first n participants."""
    eid = _prepare_confirmable(client, n, **extra)
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200
    return eid


def _recipient_sets(eid):
    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    confirmed = {p["email"] for p in event["participants"]
                 if p.get("confirmed") == True}
    waiting = {p["email"] for p in event["participants"]
               if p.get("confirmed") != True}
    everyone = {p["email"] for p in event["participants"]}
    return confirmed, waiting, everyone


def test_send_notification_mail_confirmed_only_recipients(client, monkeypatch):
    client_login(client, admin_member["email"], admin_member["password"])
    eid = _confirm_first_n(client, 2)

    confirmed, waiting, everyone = _recipient_sets(eid)
    assert len(confirmed) == 2
    assert len(waiting) == 3
    assert len(everyone) == 5

    sent = _capture_emails(monkeypatch, client)
    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'confirmed only', 'msg': 'msg', 'confirmedOnly': True})
    assert response.status_code == 202
    assert len(sent) == 1
    # the $match must be applied before $group; the buggy version mailed nobody
    assert set(sent[0]["to"]) == confirmed
    assert set(sent[0]["to"]) != waiting


def test_send_notification_mail_waitlist_only_recipients(client, monkeypatch):
    client_login(client, admin_member["email"], admin_member["password"])
    eid = _confirm_first_n(client, 2)

    confirmed, waiting, everyone = _recipient_sets(eid)
    assert len(waiting) == 3

    sent = _capture_emails(monkeypatch, client)
    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'waitlist only', 'msg': 'msg', 'waitListOnly': True})
    assert response.status_code == 202
    assert len(sent) == 1
    assert set(sent[0]["to"]) == waiting
    assert set(sent[0]["to"]) != confirmed


def test_send_notification_mail_without_flags_sends_to_everyone(client, monkeypatch):
    client_login(client, admin_member["email"], admin_member["password"])
    eid = _confirm_first_n(client, 2)

    _, _, everyone = _recipient_sets(eid)

    sent = _capture_emails(monkeypatch, client)
    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'everyone', 'msg': 'msg',
              'confirmedOnly': False, 'waitListOnly': False})
    assert response.status_code == 202
    assert len(sent) == 1
    assert set(sent[0]["to"]) == everyone


def test_send_notification_mail_omitted_flags_back_compat(client, monkeypatch):
    client_login(client, admin_member["email"], admin_member["password"])
    eid = _confirm_first_n(client, 2)

    confirmed, _, everyone = _recipient_sets(eid)
    sent = _capture_emails(monkeypatch, client)

    # both flags entirely omitted (payload only has the pre-existing fields)
    response = client.post(
        f'/api/event/{eid}/mail', json={'subject': 'all', 'msg': 'msg'})
    assert response.status_code == 202
    assert set(sent[0]["to"]) == everyone

    # waitListOnly omitted while confirmedOnly is supplied still works
    sent.clear()
    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'conf', 'msg': 'msg', 'confirmedOnly': True})
    assert response.status_code == 202
    assert set(sent[0]["to"]) == confirmed


def test_send_notification_mail_both_flags_rejected(client):
    client_login(client, admin_member["email"], admin_member["password"])
    eid = _confirm_first_n(client, 2)

    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'both', 'msg': 'msg',
              'confirmedOnly': True, 'waitListOnly': True})
    assert response.status_code == 400
    assert response.json()["detail"] == \
        "Cannot send to confirmed and waiting list at the same time"


def test_send_notification_mail_waitlist_only_without_waitlist(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # maxParticipants None confirms every joined participant -> empty waiting list
    eid = test_events[0]["eid"]
    response = client.put(
        f"/api/event/{eid}",
        json={"date": f"{future_time_str}", "public": True,
              "registrationOpeningDate": None, "maxParticipants": None})
    assert response.status_code == 200
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    confirmed, waiting, everyone = _recipient_sets(eid)
    assert waiting == set()
    assert confirmed == everyone

    response = client.post(
        f'/api/event/{eid}/mail',
        json={'subject': 'waitlist', 'msg': 'msg', 'waitListOnly': True})
    assert response.status_code == 400
    assert response.json()["detail"] == "No participants on the waiting list"


# ---------------------------------------------------------------------------
# POST /api/event/{id}/confirm waiting-list notification
# ---------------------------------------------------------------------------


def test_confirm_event_sends_waitlist_mail(client, monkeypatch):
    """Happy path: real MailPayloads for the confirmations and the waitlist."""
    client_login(client, admin_member["email"], admin_member["password"])
    payloads, attempted = _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2)

    confirmed, waiting, _ = _recipient_sets(eid)
    assert len(confirmed) == 2
    assert len(waiting) == 3

    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    title = event["title"]
    confirmation_mails = [
        p for p in payloads if p.subject == f"Bekreftelse {title}"]
    waitlist_mails = [
        p for p in payloads if p.subject == f"Venteliste {title}"]

    # exactly two confirmation mails and three waitlist mails, no others
    assert len(payloads) == 5
    assert len(confirmation_mails) == 2
    assert len(waitlist_mails) == 3

    # each real payload is addressed to exactly one person
    assert {p.to[0] for p in confirmation_mails} == confirmed
    assert {p.to[0] for p in waitlist_mails} == waiting
    for p in payloads:
        assert len(p.to) == 1
        assert p.content
        assert p.sent_by  # defaulted, never silently missing
        assert p.sent_by == "no-reply@td-uit.no"

    # every participant was actually attempted through the transport
    assert set(attempted) == confirmed | waiting


def test_confirm_waitlist_mail_is_rendered(client, monkeypatch):
    """The waitlist body is a genuinely rendered mail, no placeholder left."""
    client_login(client, admin_member["email"], admin_member["password"])
    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2)

    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    waitlist_mails = [
        p for p in payloads if p.subject.startswith("Venteliste")]
    assert len(waitlist_mails) == 3

    for mail in waitlist_mails:
        # byte-for-byte the rendered template, not a stub's idea of it
        assert mail.content == get_default_waitlist_mail(event)
        assert event["title"] in mail.content
        # no $PLACEHOLDER$ may survive rendering
        assert re.findall(r"\$[A-Z_]+\$", mail.content) == []
        # no contactEmail on this event -> the org fallback address
        assert "post@td-uit.no" in mail.content
        assert "$CONTACT$" not in mail.content


def test_confirm_waitlist_mail_uses_event_contact_email(client, monkeypatch):
    """A configured contactEmail replaces the org fallback in the body."""
    client_login(client, admin_member["email"], admin_member["password"])
    contact = "arrangement-kontakt@example.com"
    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2, contactEmail=contact)

    waitlist_mails = [
        p for p in payloads if p.subject.startswith("Venteliste")]
    assert len(waitlist_mails) == 3
    for mail in waitlist_mails:
        assert contact in mail.content
        assert "post@td-uit.no" not in mail.content
        assert re.findall(r"\$[A-Z_]+\$", mail.content) == []


def test_confirm_marks_waitlist_notified_flag(client, monkeypatch):
    """The waitListNotified flag persists on exactly the people we mailed."""
    client_login(client, admin_member["email"], admin_member["password"])
    _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2)
    confirmed, waiting, everyone = _recipient_sets(eid)
    assert len(confirmed) == 2
    assert len(waiting) == 3

    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    for p in event["participants"]:
        if p["email"] in waiting:
            assert p.get("waitListNotified") == True, (
                f"{p['email']} was mailed the waiting list but is not flagged")
        elif p["email"] in confirmed:
            # confirmed people were never told they are on the waiting list
            assert not p.get("waitListNotified"), (
                f"confirmed participant {p['email']} is wrongly flagged")
        else:
            raise AssertionError(f"unexpected participant {p['email']}")
    # sanity: the sets partition the participant list
    assert confirmed | waiting == everyone


def test_confirm_twice_does_not_remail_waiting_list(client, monkeypatch):
    """A second confirmation round must not re-mail the still-waiting people."""
    client_login(client, admin_member["email"], admin_member["password"])
    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    # round one: 2 spots, 5 joined -> 2 confirmed, 3 waiting
    eid = _confirm_first_n(client, 2)
    confirmed_1, waiting_1, _ = _recipient_sets(eid)
    assert len(confirmed_1) == 2
    assert len(waiting_1) == 3
    assert len(payloads) == 5
    first_round_waitlist = {
        p.to[0] for p in payloads if p.subject.startswith("Venteliste")}
    assert first_round_waitlist == waiting_1

    # make a second round possible by opening one more spot
    response = client.put(f"/api/event/{eid}", json={"maxParticipants": 3})
    assert response.status_code == 200

    payloads.clear()
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    confirmed_2, waiting_2, _ = _recipient_sets(eid)
    assert len(confirmed_2) == 3
    assert len(waiting_2) == 2

    newly_confirmed = confirmed_2 - confirmed_1
    assert len(newly_confirmed) == 1
    # the only round-two mail is the confirmation to the promoted person
    assert len(payloads) == 1
    assert payloads[0].subject.startswith("Bekreftelse")
    assert {payloads[0].to[0]} == newly_confirmed
    assert all(not p.subject.startswith("Venteliste") for p in payloads)

    round_two_recipients = {p.to[0] for p in payloads}
    # nobody still on the waiting list was mailed again
    assert waiting_2.isdisjoint(round_two_recipients)
    # the round-one waitlist people who were not promoted were not touched
    assert (first_round_waitlist - newly_confirmed).isdisjoint(
        round_two_recipients)


def test_confirm_tells_new_joiner_after_first_round(client, monkeypatch):
    """Someone who joins after round one still gets the waiting-list mail."""
    client_login(client, admin_member["email"], admin_member["password"])

    # create the account while still on the test env: member creation sends a
    # real mail under ENV == 'production' (missing SMTP -> 500)
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2)
    confirmed_1, waiting_1, _ = _recipient_sets(eid)
    assert len(confirmed_1) == 2
    assert len(waiting_1) == 3
    told_round_one = {
        p.to[0] for p in payloads if p.subject.startswith("Venteliste")}
    assert told_round_one == waiting_1

    # the brand-new participant joins only after the first confirm round, so it
    # carries no waitListNotified flag
    client_login(client, payload["email"], payload["password"])
    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # open one spot so a second round actually happens
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.put(f"/api/event/{eid}", json={"maxParticipants": 3})
    assert response.status_code == 200

    payloads.clear()
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    confirmed_2, waiting_2, _ = _recipient_sets(eid)
    assert payload["email"] in waiting_2, \
        "new joiner should still be on the waiting list"
    newly_confirmed = confirmed_2 - confirmed_1
    assert len(newly_confirmed) == 1

    waitlist_mails = [
        p for p in payloads if p.subject.startswith("Venteliste")]
    assert len(waitlist_mails) == 1
    # only the newcomer (never told) is mailed; the already-notified are skipped
    assert waitlist_mails[0].to == [payload["email"]]
    # the people still waiting after round two were all told in round one, so
    # none of them may receive anything (the promoted one only gets a
    # confirmation, and the newcomer is the single expected waitlist recipient)
    assert (told_round_one - newly_confirmed).isdisjoint(
        {p.to[0] for p in payloads})


def test_confirm_waitlist_send_failure_is_isolated(client, monkeypatch):
    """One failing waitlist send must not stop the others (the fixed bug)."""
    client_login(client, admin_member["email"], admin_member["password"])

    # prepare without confirming so we can pick a known waitlist member: the
    # first two array positions get the spots, index 2 is on the waitlist
    eid = _prepare_confirmable(client, 2)
    prepared = db.events.find_one({'eid': UUID(eid)})
    assert prepared
    failing = prepared["participants"][2]["email"]

    payloads, attempted = _capture_mail_payloads(
        monkeypatch, client, fail_for={failing})

    # spy on the real send_emails (resolved in event_utils by
    # send_waitlist_emails) so its return value can be asserted directly
    send_returns = []
    real_send_emails = event_utils.send_emails

    def spy_send_emails(mailing_list, subject, content):
        result = real_send_emails(mailing_list, subject, content)
        send_returns.append((list(mailing_list), list(result)))
        return result

    monkeypatch.setattr(event_utils, "send_emails", spy_send_emails)

    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    confirmed, waiting, _ = _recipient_sets(eid)
    assert failing in waiting

    # exactly one send_emails call (the waitlist) and it returned only the
    # addresses actually delivered
    assert len(send_returns) == 1
    mailed_list, delivered = send_returns[0]
    assert set(mailed_list) == waiting
    assert set(delivered) == waiting - {failing}

    title = db.events.find_one({'eid': UUID(eid)})["title"]
    waitlist_sent = {
        p.to[0] for p in payloads if p.subject == f"Venteliste {title}"}

    # the failing address was attempted but delivered nothing
    assert failing in attempted
    assert failing not in waitlist_sent
    # every other address in the batch still got its own payload
    assert waitlist_sent == waiting - {failing}
    assert len(waitlist_sent) == 2
    # the confirmation batch (a different list) was unaffected
    assert {p.to[0] for p in payloads
            if p.subject == f"Bekreftelse {title}"} == confirmed
    assert set(attempted) == confirmed | waiting


def test_confirm_marks_only_delivered_waitlist_recipients(client, monkeypatch):
    """waitListNotified is delivery-based, so a failed send can be retried."""
    client_login(client, admin_member["email"], admin_member["password"])

    eid = _prepare_confirmable(client, 2)
    prepared = db.events.find_one({'eid': UUID(eid)})
    assert prepared
    failing = prepared["participants"][2]["email"]

    _capture_mail_payloads(monkeypatch, client, fail_for={failing})
    response = client.post(f'/api/event/{eid}/confirm', json={"msg": None})
    assert response.status_code == 200

    confirmed, waiting, _ = _recipient_sets(eid)
    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    for p in event["participants"]:
        if p["email"] == failing:
            # the send failed, so the database must not claim it was notified
            assert not p.get("waitListNotified"), (
                "a recipient whose send failed must stay unmarked for retry")
        elif p["email"] in waiting:
            assert p.get("waitListNotified") == True, (
                f"{p['email']} was delivered but is not flagged")
        elif p["email"] in confirmed:
            assert not p.get("waitListNotified")
        else:
            raise AssertionError(f"unexpected participant {p['email']}")
    # exactly the delivered waitlist people are flagged
    delivered = waiting - {failing}
    flagged = {p["email"] for p in event["participants"]
               if p.get("waitListNotified")}
    assert flagged == delivered


def test_confirm_everyone_no_waitlist_mail_or_flags(client, monkeypatch):
    """When everyone gets a spot there is no waitlist mail and no flag."""
    client_login(client, admin_member["email"], admin_member["password"])
    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    # maxParticipants None confirms every joined participant
    eid = _confirm_first_n(client, None)

    _, waiting, everyone = _recipient_sets(eid)
    assert waiting == set()
    assert len(everyone) == 5

    # only the five confirmations, no waitlist mail at all
    assert len(payloads) == 5
    assert all(p.subject.startswith("Bekreftelse") for p in payloads)
    assert {p.to[0] for p in payloads} == everyone

    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    for p in event["participants"]:
        assert not p.get("waitListNotified"), (
            f"{p['email']} must not be flagged when there is no waitlist")


def test_confirm_sends_nothing_outside_production(client, monkeypatch):
    """ENV != 'production' builds no payloads and marks nobody (dev silent)."""
    client_login(client, admin_member["email"], admin_member["password"])
    payloads, attempted = _capture_mail_payloads(
        monkeypatch, client, env="development")

    eid = _confirm_first_n(client, 2)
    confirmed, waiting, _ = _recipient_sets(eid)
    assert len(confirmed) == 2
    assert len(waiting) == 3

    # the production gate short-circuits before any mail is constructed
    assert payloads == []
    assert attempted == []

    event = db.events.find_one({'eid': UUID(eid)})
    assert event
    for p in event["participants"]:
        assert not p.get("waitListNotified"), (
            f"{p['email']} must not be flagged when no mail was sent")


def test_confirm_subject_with_norwegian_characters(client, monkeypatch):
    """Non-ASCII titles survive intact into both subjects and the bodies."""
    client_login(client, admin_member["email"], admin_member["password"])
    title = "Bærekraft og blåbær øl på åpen scene"
    payloads, _ = _capture_mail_payloads(monkeypatch, client)

    eid = _confirm_first_n(client, 2, title=title)

    assert len(payloads) == 5
    for mail in payloads:
        assert title in mail.subject
        assert title in mail.content
    assert {p.subject for p in payloads} == {
        f"Bekreftelse {title}", f"Venteliste {title}"}


# ---------------------------------------------------------------------------
# Public response shape (#326): public endpoints must not leak host-only data
# ---------------------------------------------------------------------------


def test_public_event_response_shape(client):
    host_only_keys = {"host", "registeredPenalties", "register_id"}
    public_keys = {"title", "eid"}

    # create an upcoming event so the unauthenticated checks are not vacuous
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post("/api/event/", json=new_event)
    assert response.status_code == 200

    # --- unauthenticated ---
    client.cookies.clear()

    response = client.get("/api/event/upcoming")
    assert response.status_code == 200
    upcoming = response.json()
    assert len(upcoming) >= 1
    for event in upcoming:
        assert host_only_keys.isdisjoint(event.keys())
        assert public_keys.issubset(event.keys())

    response = client.get("/api/event/past-events")
    assert response.status_code == 200
    past = response.json()
    assert len(past) >= 1
    for event in past:
        assert host_only_keys.isdisjoint(event.keys())
        assert public_keys.issubset(event.keys())

    # --- positive control: admin sees the full event shape ---
    client_login(client, admin_member["email"], admin_member["password"])

    response = client.get("/api/event/upcoming")
    assert response.status_code == 200
    upcoming_admin = response.json()
    assert len(upcoming_admin) >= 1
    for event in upcoming_admin:
        assert host_only_keys.issubset(event.keys())
        assert public_keys.issubset(event.keys())

    response = client.get("/api/event/past-events")
    assert response.status_code == 200
    past_admin = response.json()
    assert len(past_admin) >= 1
    for event in past_admin:
        assert host_only_keys.issubset(event.keys())
        assert public_keys.issubset(event.keys())


# ---------------------------------------------------------------------------
# contactEmail is admin-only: it must never reach a non-admin response
# ---------------------------------------------------------------------------


def test_contact_email_visibility_follows_the_cancellation_window(client):
    """contactEmail may only reach a caller who is both logged in AND inside the
    24h late-cancellation window, because that modal is the only place the UI
    ever shows it.

    Sibling of test_public_event_response_shape, with a real positive control:
    both events below actually store a contactEmail, so the "hidden" assertions
    cannot pass vacuously.
    """
    contact = "arrangement-kontakt@example.com"
    beyond_contact = "senere-kontakt@example.com"
    beyond_time = datetime.now() + timedelta(hours=72)

    # --- set up: one event inside the window, one outside ---
    client_login(client, admin_member["email"], admin_member["password"])

    response = client.post(
        "/api/event/", json={**new_event, "contactEmail": contact})
    assert response.status_code == 200
    inside_eid = response.json()["eid"]

    response = client.post("/api/event/", json={
        **new_event,
        "date": beyond_time.strftime("%Y-%m-%d %H:%M:%S"),
        "contactEmail": beyond_contact,
    })
    assert response.status_code == 200
    outside_eid = response.json()["eid"]

    # sanity: both really are persisted, otherwise the assertions below are vacuous
    assert db.events.find_one({'eid': UUID(inside_eid)})["contactEmail"] == contact
    assert db.events.find_one(
        {'eid': UUID(outside_eid)})["contactEmail"] == beyond_contact

    # --- anonymous: never, on any endpoint ---
    client.cookies.clear()

    for path in ("/api/event/upcoming", "/api/event/past-events"):
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) >= 1
        for event in payload:
            assert "contactEmail" not in event, event

    for path in (f"/api/event/{inside_eid}", f"/api/event/{outside_eid}"):
        response = client.get(path)
        assert response.status_code == 200
        assert "contactEmail" not in response.json(), response.json()

    # --- logged-in member: only inside the window ---
    client_login(client, regular_member["email"], regular_member["password"])

    # #326 is about host/registeredPenalties/register_id too, not just contactEmail:
    # a member must never see them, on any endpoint, whatever the window says.
    host_only = {"host", "registeredPenalties", "register_id"}

    response = client.get(f"/api/event/{inside_eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact
    assert host_only.isdisjoint(response.json()), response.json()

    response = client.get(f"/api/event/{outside_eid}")
    assert response.status_code == 200
    assert "contactEmail" not in response.json(), response.json()
    assert host_only.isdisjoint(response.json()), response.json()

    response = client.get("/api/event/upcoming")
    assert response.status_code == 200
    upcoming = response.json()
    assert len(upcoming) >= 1
    for event in upcoming:
        assert host_only.isdisjoint(event), event

    # a member gets contactEmail for in-window events (that is the rule), but
    # never for events outside it — so the past list must carry none at all
    response = client.get("/api/event/past-events")
    assert response.status_code == 200
    past = response.json()
    assert len(past) >= 1
    for event in past:
        assert "contactEmail" not in event, event
        assert host_only.isdisjoint(event), event

    # --- admin: always, with or without the window ---
    client_login(client, admin_member["email"], admin_member["password"])

    response = client.get(f"/api/event/{inside_eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == contact

    response = client.get(f"/api/event/{outside_eid}")
    assert response.status_code == 200
    assert response.json()["contactEmail"] == beyond_contact
