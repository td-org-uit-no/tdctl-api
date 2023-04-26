import os
import json
from uuid import UUID, uuid4
from app.db import get_test_db
from app.utils.event_utils import num_of_confirmed_participants, num_of_deprioritized_participants
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


def test_get_past_events(client):
    # Login
    client_login(client, admin_member["email"], admin_member["password"])

    # Create future event
    response = client.post('/api/event/', json=new_event)
    assert response.status_code == 200

    # Should only get past events
    response = client.get('/api/event/past-events/')
    assert response.status_code == 200
    assert len(response.json()) == len(test_events)


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
    response = client.post(f'/api/event/{test_event_id}/join', json=joinEventPayload)
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
    assert response.json()['transportation'] == joinEventPayload['transportation']
    assert response.json()['food'] == joinEventPayload['food']
    assert response.json()['dietaryRestrictions'] == joinEventPayload['dietaryRestrictions']


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
    response = client.put(f'/api/event/{eid}/update-options', json=updateEventPayload)
    assert response.status_code == 200

    # Fetch updated event options
    response = client.get(f'/api/event/{eid}/options')
    assert response.status_code == 200
    assert response.json()['transportation'] == updateEventPayload['transportation']
    assert response.json()['food'] == updateEventPayload['food']
    assert response.json()['dietaryRestrictions'] == updateEventPayload['dietaryRestrictions']

    # Set event to confirmed
    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 200

    # Should fail to update options
    response = client.put(f'/api/event/{eid}/update-options', json=updateEventPayload)
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
    response = client.post(f'/api/event/{test_event_id}/join', json=joinEventPayload)
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
    response = client.post(f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 403

    # admin should be able to join
    client_login(client, second_admin["email"], second_admin["password"])
    response = client.post(f'/api/event/{test_event_id}/join', json=joinEventPayload)
    assert response.status_code == 200

@authentication_required("/api/event/{uuid}/join", "post")
def test_join_published_event(client):
    client_login(client, admin_member["email"], admin_member["password"])

    # creates event with maxParticipants = 1
    response = client.post("/api/event/", json=new_event)
    new_event_eid = response.json()["eid"]
    assert response.status_code == 200

    # joins the event
    response = client.post(f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # creates new member for joining the event
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    # checks response on full event
    client_login(client, payload["email"], payload["password"])

    response = client.post(f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    # === test join ordering ===
    client_login(client, admin_member["email"], admin_member["password"])
    eid = test_events[0]["eid"]
    
    # setup event
    response = client.put(f"/api/event/{eid}", json={"date": f"{future_time_str}"})
    assert response.status_code == 200

    new_member = db.members.find_one({"email": payload["email"]})
    assert new_member

    client_login(client, payload["email"], payload["password"])

    response = client.post(f'/api/event/{eid}/join', json=joinEventPayload)
    assert response.status_code == 200
    # check that joined non penalized comes in front of penalized member
    updated_event = db.events.find_one({"eid": UUID(eid)})
    assert updated_event
    assert num_of_deprioritized_participants(updated_event["participants"]) != 0
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

    response = client.put(f"/api/event/{eid}", json={"date": f"{future_time_str}"})
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
    response = client.post(f'/api/event/{new_event_eid}/join', json=joinEventPayload)
    assert response.status_code == 200

    penalty_before = member_before_leave["penalty"]

    client_login(client, second_member["email"], second_member["password"])
    # test that users on waiting list does not receive penalty
    response = client.post(f'/api/event/{new_event_eid}/join', json=joinEventPayload)
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

    response = client.post(f'/api/event/{new_event_eid}/join', json=joinEventPayload)
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
    response = client.post(f'/api/event/{eid}/confirm')
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
    resp = client.delete(f'/api/event/{eid}/removeParticipant/{participant_id}')
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


@admin_required("/api/event/{uuid}/confirm", "post")
def test_confirm_event(client):
    eid = test_events[0]["eid"]

    client_login(client, admin_member["email"], admin_member["password"])
    
    # check confirmation is not allowed on finished events
    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 400

    # update to valid date but not public
    response = client.put(
            f"/api/event/{eid}", json={"date": f"{future_time_str}", "maxParticipants": 1, "public": False})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 400

    # setup for confirmation on event who isn't open for registration
    response = client.put(
            f"/api/event/{eid}", json={"public": True, "registrationOpeningDate": f"{future_time_str}"})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 400

    response = client.put(
            f"/api/event/{eid}", json={"registrationOpeningDate": None})
    assert response.status_code == 200

    # check expected behavior
    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 200

    event = db.events.find_one({"eid": UUID(eid)})
    assert event and num_of_confirmed_participants(event["participants"]) == event["maxParticipants"]
    
    response = client.post(f'/api/event/{eid}/confirm')
    # should get 400 when all participants have gotten their confirmation mail
    assert response.status_code == 400

    response = client.put(f"/api/event/{eid}", json={"maxParticipants": None})
    assert response.status_code == 200

    response = client.post(f'/api/event/{eid}/confirm')
    assert response.status_code == 200

    event = db.events.find_one({"eid": UUID(eid)})
    # checks that all participants gets confirmation when there are no limit
    assert event and num_of_confirmed_participants(event["participants"]) == len(event["participants"])


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
    for i,p in enumerate(event["participants"]):
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

    response = client.post(f'/api/event/{eid}/confirm')
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
    
    ## Self update
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
    response = client.put(f'/api/event/{eid}', json={"date": new_future_time_str})
    assert response.status_code == 200

    # Should be able do register less than 1 hour prior
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.put(f'/api/event/{rid}/register', json=payload)
    assert response.status_code == 200


    ## Update others attendance
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
    response = client.post(f'/api/event/{eid}/confirm')
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
    
