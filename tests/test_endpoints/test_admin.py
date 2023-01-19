from uuid import uuid4
from app.db import get_test_db
from app.models import MemberInput
from tests.users import admin_member, second_admin, regular_member, second_member
from tests.conftest import client_login
from tests.utils.authentication import admin_required

payload = {
    "realName": "new member",
    "email": "new_member@test.com",
    "password": "Test!234",
    "classof":"2000",
    "graduated": False,
}

db = get_test_db()

def generate_non_existing_uuid():
    id = uuid4().hex
    while db.members.find_one({'id': id}):
        id = uuid4().hex
    return id

@admin_required("/api/admin/", "POST")
def test_create_admin(client):
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    # tests password requirements
    unvalid_pwd = {**payload, "password": "unvalid_pwd"}
    response = client.post("/api/admin/", json=unvalid_pwd, headers=headers)
    assert response.status_code == 400

    existing_member = db.members.find_one({'email': second_member["email"]})
    assert existing_member
    
    # testing creating a user with existing email
    existing_member = MemberInput.parse_obj(existing_member).dict()
    response = client.post("/api/admin/", json=existing_member, headers=headers)
    assert response.status_code == 409

    #testing excepted behavior
    response = client.post("/api/admin/", json=payload, headers=headers)
    assert response.status_code == 201
    new_admin = db.members.find_one({'email': payload["email"]})
    assert new_admin and new_admin["role"] == "admin"

@admin_required("/api/admin/member/{uuid}", "PUT")
def test_admin_update_member(client):
    update_value = {"classof": "2016"}

    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] != member["classof"]

    # Should be able to update info on a regular member
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(f"/api/admin/member/{member['id'].hex}", headers=headers, json=update_value)
    assert response.status_code == 201

    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] == member["classof"]

    # Checks against updating non existing user
    non_existing_member = generate_non_existing_uuid()
    response = client.put(f"/api/admin/member/{non_existing_member}", headers=headers, json=update_value)
    assert response.status_code == 404

    # Should not be able to update info on another admin
    admin = db.members.find_one({'email': second_admin["email"]})
    assert admin

    response = client.put(f"/api/admin/member/{admin['id'].hex}", headers=headers, json=update_value)
    assert response.status_code == 403

    admin = db.members.find_one({'email': second_admin["email"]})
    assert admin and update_value["classof"] != admin["classof"]

@admin_required("api/admin/member/{uuid}", "delete")
def test_delete_user(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member

    # checks if endpoint is protected against deleting non existing user
    non_existing_id = generate_non_existing_uuid()
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.delete(f"/api/admin/member/{non_existing_id}", headers=headers)
    assert response.status_code == 404

    admin = db.members.find_one({'email': second_admin["email"]})
    assert admin
    
    # checks if cannot delete another admin
    response = client.delete(f"/api/admin/member/{admin['id']}", headers=headers)
    assert response.status_code == 403

    # checks expected behavior
    response = client.delete(f"/api/admin/member/{member['id']}", headers=headers)
    assert response.status_code == 200
    assert db.members.find_one({'id': member["id"]}) == None

@admin_required("api/admin/give-admin-privileges/{uuid}", "post")
def test_give_admin_privileges(client):
    member = db.members.find_one({'email': regular_member["email"]})
    assert member

    admin = db.members.find_one({'email': admin_member["email"]})
    assert admin

    # check response for admin upgrading admin
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = client.post(f"api/admin/give-admin-privileges/{admin['id']}", headers=headers)
    assert response.status_code == 400

    # checks if the endpoint working as expected
    response = client.post(f"api/admin/give-admin-privileges/{member['id']}", headers=headers, content="")
    assert response.status_code == 201
    member = db.members.find_one({'email': member["email"]})
    assert member and member["role"] == "admin"
