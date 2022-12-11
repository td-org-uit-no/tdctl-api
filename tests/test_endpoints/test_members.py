from app.db import get_test_db
from tests.conftest import client_login
from tests.users import regular_member, admin_member
import json

from tests.utils.authentication import admin_required, authentication_required

payload = {
    "realName": "new member",
    "email": "new_member@test.com",
    "password": "Test!234",
    "classof":"2000",
    "graduated": False,
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

@authentication_required('/api/member', 'get')
def test_get_member_associated_with_token(client):
    access_token = client_login(client, regular_member['email'], regular_member['password'])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get('/api/member/', headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member["email"]
     

@admin_required('api/members', 'get')
def test_get_members(client):
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    response = client.get('/api/members/', headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    res_json = response.json()

    # number of members in the seeding file
    with open("db/seeds/test_seeds/test_members.json") as seed_file:
        seed_json = json.load(seed_file)

    assert len(res_json) == len(seed_json)

@authentication_required('api/member/{uuid}', 'get')
def test_get_member_by_id(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member
    access_token = client_login(client, regular_member['email'], regular_member['password'])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"/api/member/{member['id']}", headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member['email']


@admin_required('api/member/email/{uuid}', 'get')
def test_get_member_by_email(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member
    non_existing_user = "not_a@user.com"
    invalid_email = "not_a@user"

    access_token = client_login(client, admin_member['email'], admin_member['password'])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.get(f"/api/member/email/{non_existing_user}", headers=headers)
    assert response.status_code == 404

    response = client.get(f"/api/member/email/{invalid_email}", headers=headers)
    assert response.status_code == 422

    # test excpected behavior
    response = client.get(f"/api/member/email/{member['email']}", headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["id"] == member["id"]

@authentication_required('api/member/', 'put')
def test_update_member(client):
    update_value = {"classof": "2016"}
    access_token = client_login(client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.put("/api/member/", headers=headers, json=update_value)
    assert response.status_code == 201
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] == member["classof"]

@authentication_required('api/member/activate', 'post')
def test_member_activation(client):
    access_token = client_login(client, regular_member["email"], regular_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/member/activate", headers=headers)
    assert response.status_code == 200
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and member["status"] == "active"
