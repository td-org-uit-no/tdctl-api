import os
import json
from uuid import UUID, uuid4
from app.db import get_test_db
from tests.conftest import client_login
from datetime import datetime, timedelta
from tests.test_endpoints.test_members import payload
from tests.users import regular_member, admin_member

from tests.utils.authentication import admin_required, authentication_required

db = get_test_db()

future_time = datetime.now() + timedelta(hours=1)
future_time_str = future_time.strftime("%Y-%m-%d %H:%M:%S")

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
    "active": False
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
    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    # tests for date being in the past
    invalid_date_event = {**new_event, "date": "2022-01-01T00:00:00"}
    response = client.post(
        "/api/event/", json=invalid_date_event, headers=headers)
    assert response.status_code == 400
    response = client.post("/api/event/", json=new_event, headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    event = db.events.find_one({'eid': res_json["eid"]})
    assert event != None


@admin_required("/api/event/{uuid}", "put")
def test_update_event(client):
    update_field = {"title": "new title"}
    eid = test_events[0]["eid"]
    invalid_date = {"date": "2022-01-01T00:00:00"}

    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.put(
        f"/api/event/{eid}", json=invalid_date, headers=headers)
    assert response.status_code == 400

    non_existing_eid = "1"*32
    response = client.put(
        f"/api/event/{non_existing_eid}", json=update_field, headers=headers)
    assert response.status_code == 404

    response = client.put(
        f"/api/event/{eid}", json=update_field, headers=headers)
    assert response.status_code == 200

    event = db.events.find_one({'eid': eid})
    assert event and event["title"] == update_field["title"]


def test_get_all_event(client):
    response = client.get("/api/event/")
    assert response.status_code == 200
    assert len(response.json()) == len(test_events)


def test_get_upcoming_events(client):
    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/event/", json=new_event, headers=headers)
    assert response.status_code == 200
    response = client.get("/api/upcoming/")
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
    img_path = f'db/seeds/seedImages/{eid}.png'
    file = {
        "image": (f'{eid}.png', open(f'{img_path}', 'rb'), 'image/png'),
    }

    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post(
        f'/api/event/{eid}/image', files=file, headers=headers)
    assert response.status_code == 200

    # tests file type validation
    file_name = 'tmp.txt'
    with open(file_name, 'w') as file:
        file.write("testing")

    file = {
        "image": (f'{file_name}', open(file_name, 'rb'), 'text/plain'),
    }
    response = client.post(
        f'/api/event/{eid}/image', files=file, headers=headers)
    assert response.status_code == 400
    os.remove(file_name)


def test_get_event_by_id(client):
    eid = test_events[0]["eid"]
    response = client.get(f'/api/event/{non_existing_eid}')
    assert response.status_code == 404

    response = client.get(f'/api/event/{eid}')
    assert response.status_code == 200


def test_get_event_participants(client):
    eid = test_events[1]["eid"]
    access_token = client_login(
        client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.get(
        f'/api/event/{non_existing_eid}/participants', headers=headers)
    assert response.status_code == 404

 # Check !admin
    response = client.get(f'/api/event/{eid}/participants', headers=headers)
    res_json = response.json()
    assert response.status_code == 200
    assert len(res_json) == len(test_members)

    assert 'food' not in res_json[0]

    # Check admin
    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.get(f'/api/event/{eid}/participants', headers=headers)
    res_json = response.json()
    assert response.status_code == 200
    assert len(res_json) == len(test_members)
    assert 'food' in res_json[0]


@authentication_required("/api/event/{uuid}/join", "post")
def test_join_event(client):
    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    # creates event with maxParticipants = 1
    response = client.post("/api/event/", json=new_event, headers=headers)
    new_event_eid = response.json()["eid"]
    # creates new member for joining the event
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200
    # joins the event
    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload, headers=headers)
    assert response.status_code == 200

    res = response.json()

    assert res['max'] == False
    # checks response on full event
    access_token = client_login(client, payload["email"], payload["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.post(
        f'/api/event/{new_event_eid}/join', json=joinEventPayload, headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res['max'] == True


@authentication_required("/api/event/{uuid}/leave", "post")
def test_leave_event(client):
    eid = test_events[1]["eid"]

    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    access_token = client_login(client, payload["email"], payload["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post(
        f'/api/event/{non_existing_eid}/leave', headers=headers)
    assert response.status_code == 404

    response = client.post(f'/api/event/{eid}/leave', headers=headers)
    assert response.status_code == 400

    # all seeding members are joined every event
    access_token = client_login(
        client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.post(f'/api/event/{eid}/leave', headers=headers)
    assert response.status_code == 200


@authentication_required("/api/event/{uuid}/joined", "get")
def test_is_joined_event(client):
    eid = test_events[0]["eid"]
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200

    access_token = client_login(client, payload["email"], payload["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(
        f'/api/event/{non_existing_eid}/joined', headers=headers)
    assert response.status_code == 404

    response = client.get(f'/api/event/{eid}/joined', headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["joined"] == False

    access_token = client_login(
        client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f'/api/event/{eid}/joined', headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["joined"] == True


@admin_required("/api/event/{uuid}/removeParticipant/{uuid}", "delete")
def test_remove_participant(client):
    eid = test_events[0]["eid"]

    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    participants_before = client.get(
        f'/api/event/{eid}/participants', headers=headers)

    participants_before = participants_before.json()

    # Remove first participant from event
    participant_id = participants_before[0]['id']
    resp = client.delete(
        f'/api/event/{eid}/removeParticipant/{participant_id}', headers=headers)
    assert resp.status_code == 200

    participants_after = client.get(
        f'/api/event/{eid}/participants', headers=headers)

    participants_after = participants_after.json()
    assert len(participants_after) == len(participants_before) - 1
    assert participants_after[0]['id'] != participants_before[0]['id']


@admin_required("/api/event/{uuid}/export", "get")
def test_export_event(client):
    eid = test_events[0]["eid"]

    access_token = client_login(
        client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.get(f'/api/event/{eid}/export', headers=headers)
    assert response.status_code == 200

    response = client.get(
        f'/api/event/{non_existing_eid}/export', headers=headers)
    assert response.status_code == 404
