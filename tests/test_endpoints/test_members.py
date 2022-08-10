from app.db import get_test_db
from tests.conftest import client_login
import json

payload = {
    "realName": "new member",
    "email": "new_member@test.com",
    "password": "Test!234",
    "classof":"2000",
    "graduated": False,
}

regular_member = {
    "email": "test@test.com",
    "password": "Test!234"
}

admin_member = {
    "email": "test_admin@test.com",
    "password": "&AdminTester1"
}

db = get_test_db()

def test_create_member(client):
    unvalid_pwd = {**payload, "password": "unvalid_pwd"}
    response = client.post("/api/member/", json=unvalid_pwd)
    assert response.status_code == 400
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 200
    response = client.post("/api/member/", json=payload)
    assert response.status_code == 409
    db = get_test_db()
    new_member = db.members.find_one({'email': payload["email"]})
    assert new_member != None

def test_get_member_associated_with_token(client):
    response = client.get('/api/member/')
    assert response.status_code == 403
    access_token = client_login(client, regular_member['email'], regular_member['password'])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get('/api/member/', headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member["email"]
     

def test_get_members(client):
    response = client.get("/api/members/")
    assert response.status_code == 403
    access_token = client_login(client, regular_member['email'], regular_member['password'])
    response = client.get('/api/members/', headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    response = client.get('/api/members/', headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    res_json = response.json()

    # number of members in the seeding file
    with open("db/seeds/test_seeds/test_members.json") as seed_file:
        seed_json = json.load(seed_file)

    assert len(res_json) == len(seed_json)

def test_get_member_by_id(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member
    access_token = client_login(client, regular_member['email'], regular_member['password'])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/member/", headers=headers, data=member["id"])
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member['email']

def test_update_member(client):
    update_value = {"classof": "2016"}
    response = client.put("/api/member/", json=update_value)
    assert response.status_code == 403
    access_token = client_login(client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.put("/api/member/", headers=headers, json=update_value)
    assert response.status_code == 201
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] == member["classof"]

def test_member_activation(client):
    response = client.post("/api/member/activate")
    assert response.status_code == 403
    access_token = client_login(client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/member/activate", headers=headers)
    assert response.status_code == 200
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and member["status"] == "active"
