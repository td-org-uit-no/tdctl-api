from app.db import get_test_db
from app.models import Role, Status
from tests.conftest import client_login
from tests.users import regular_member, admin_member, second_member
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
    assert new_member["status"] == Status.inactive
    assert new_member["role"] == Role.unconfirmed

@authentication_required('/api/member', 'get')
def test_get_member_associated_with_token(client):
    client_login(client, regular_member['email'], regular_member['password'])
    response = client.get('/api/member/')
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member["email"]
     

@admin_required('api/members', 'get')
def test_get_members(client):
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.get('/api/members/')
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
    client_login(client, regular_member['email'], regular_member['password'])
    response = client.get(f"/api/member/{member['id']}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json['email'] == regular_member['email']


@admin_required('api/member/email/{uuid}', 'get')
def test_get_member_by_email(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member
    non_existing_user = "not_a@user.com"
    invalid_email = "not_a@user"

    client_login(client, admin_member['email'], admin_member['password'])

    response = client.get(f"/api/member/email/{non_existing_user}")
    assert response.status_code == 404

    response = client.get(f"/api/member/email/{invalid_email}")
    assert response.status_code == 422

    # test excpected behavior
    response = client.get(f"/api/member/email/{member['email']}")
    assert response.status_code == 200
    res = response.json()
    assert res["id"] == member["id"].hex

@authentication_required('api/member/', 'put')
def test_update_member(client):
    update_value = {"classof": "2016"}
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.put("/api/member/", json=update_value)
    assert response.status_code == 201
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] == member["classof"]

@authentication_required('api/member/activate', 'post')
def test_member_activation(client):
    # inactive member
    client_login(client, second_member["email"], second_member["password"])
    # set member to inactive as login activates users
    db.members.find_one_and_update({"email": second_member["email"]}, {"$set": {"status": f'{Status.inactive}'}})
    member = db.members.find_one({'email': second_member["email"]})
    assert member and member["status"] == Status.inactive

    response = client.post("/api/member/activate")
    assert response.status_code == 200
    member = db.members.find_one({'email': second_member["email"]})
    assert member and member["status"] == Status.active

    response = client.post("/api/member/activate")
    assert response.status_code == 400
