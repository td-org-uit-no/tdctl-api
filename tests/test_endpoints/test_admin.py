from app.db import get_test_db
from tests.conftest import client_login

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

second_admin = {
    "email": "second_admin@test.com",
}

admin_member = {
    "email": "test_admin@test.com",
    "password": "&AdminTester1"
}

db = get_test_db()

def test_admin_update_member(client):
    update_value = {"classof": "2016"}
    member = db.members.find_one({'email': regular_member["email"]})
    assert member

    # Should not be able to update info without authenticating
    response = client.put(f"/api/admin/member/{member['id']}", json=update_value)
    assert response.status_code == 403

    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] != member["classof"]

    # Should be able to update info on a regular member
    access_token = client_login(client, admin_member["email"], admin_member["password"])
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(f"/api/admin/member/{member['id']}", headers=headers, json=update_value)
    assert response.status_code == 201

    member = db.members.find_one({'email': regular_member["email"]})
    assert member and update_value["classof"] == member["classof"]

    # Should not be able to update info on another admin
    admin = db.members.find_one({'email': second_admin["email"]})
    assert admin

    response = client.put(f"/api/admin/member/{admin['id']}", headers=headers, json=update_value)
    assert response.status_code == 404

    admin = db.members.find_one({'email': second_admin["email"]})
    assert admin and update_value["classof"] != admin["classof"]
