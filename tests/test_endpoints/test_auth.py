from app.db import get_test_db
from app.models import Status
from starlette.testclient import TestClient
from tests.conftest import client_login
from tests.utils.authentication import authentication_required
from app.auth_helpers import decode_token
from app.config import config
from tests.users import regular_member

db = get_test_db()

def test_login(client: TestClient):
    unregister_user = {
        "email": "not@registered.com",
        "password": "ValidPassword!"
    }
    response = client.post("/api/auth/login", json=unregister_user)
    assert response.status_code == 401
    response = client.post("/api/auth/login", json=regular_member)
    assert response.status_code == 200
    member = db.members.find_one({'email': regular_member["email"]})
    assert member and member["status"] == Status.active
    assert response.cookies.get("access_token") != None

def test_refresh_token(client):
    # Should not be able to refresh a token when not logged in
    response = client.post("api/auth/renew")
    assert response.status_code == 401

    response = client.post("/api/auth/login", json=regular_member)
    response = client.post("api/auth/renew")
    assert response.status_code == 200

    renew_access_token = response.cookies.get("access_token")
    token_payload = decode_token(renew_access_token, config["test"])
    assert token_payload["access_token"] == True

@authentication_required('/api/auth/password', "post")
def test_change_password(client):
    change_password_payload = {
        "password": regular_member["password"],
        "newPassword": "NewPassword!2"
    }
    client_login(client, regular_member['email'], regular_member['password'])

    unvalid_password = {**change_password_payload, "password": "WrongPassword!2"}
    response = client.post("/api/auth/password", json=unvalid_password)
    assert response.status_code == 403

    unvalid_new_password = {**change_password_payload, "newPassword": "notValid"}
    response = client.post("/api/auth/password", json=unvalid_new_password)
    assert response.status_code == 400

    response = client.post("/api/auth/password", json=change_password_payload)
    assert response.status_code == 200

    response = client.post("/api/auth/login", json={"email": regular_member["email"], "password": change_password_payload["newPassword"]})
    assert response.status_code == 200
