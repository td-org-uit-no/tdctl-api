from app.db import get_test_db
from tests.users import regular_member, admin_member
from tests.conftest import client_login
from tests.utils.authentication import admin_required

db = get_test_db()

suggestion = {"product": "testproduct"}


def test_add_suggestion(client):
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post("/api/kiosk/suggestion", json=suggestion)
    assert response.status_code == 201
    db_suggestion = db.kioskSuggestions.find_one({"product": suggestion["product"]})
    assert db_suggestion is not None


@admin_required("/api/kiosk/suggestions", "get")
def test_get_suggestions(client):
    # Post suggestion first
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post("/api/kiosk/suggestion", json=suggestion)
    assert response.status_code == 201

    # Non-admin refused
    response = client.get("/api/kiosk/suggestions")
    assert response.status_code == 403

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.get("/api/kiosk/suggestions")
    assert response.status_code == 200

    suggestions = response.json()
    assert suggestions is not None
    assert len(suggestions) == 1
