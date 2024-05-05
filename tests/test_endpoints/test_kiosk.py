from uuid import uuid4
from app.db import get_test_db
from tests.users import regular_member, admin_member, kiosk_admin
from tests.conftest import client_login
from tests.utils.authentication import admin_required, kiosk_admin_required

db = get_test_db()

# Full name of regular_member
regular_name = "Test"

# NOTE: product name must be capitalized
suggestion = {"product": "Testproduct"}


def test_add_suggestion(client):
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post("/api/kiosk/suggestion", json=suggestion)
    assert response.status_code == 201
    db_suggestion = db.kioskSuggestions.find_one({"product": suggestion["product"]})
    assert db_suggestion is not None


@kiosk_admin_required("/api/kiosk/suggestions", "get")
def test_get_suggestions(client):
    # Post suggestion first
    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post("/api/kiosk/suggestion", json=suggestion)
    assert response.status_code == 201

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.get("/api/kiosk/suggestions")
    assert response.status_code == 200

    suggestions = response.json()
    assert suggestions is not None
    assert len(suggestions) == 1
    assert suggestions[0]["product"] == suggestion["product"]
    assert suggestions[0]["username"] == regular_name

    # Kiosk admin also permitted
    client_login(client, kiosk_admin["email"], kiosk_admin["password"])
    response = client.get("/api/kiosk/suggestions")
    assert response.status_code == 200

    # Should not receive names
    suggestions = response.json()
    assert suggestions[0]["username"] == "-"


@admin_required("/api/kiosk/suggestion/{uuid}", "delete")
def test_delete_suggestion(client):
    # Post suggestion first
    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post("/api/kiosk/suggestion", json=suggestion)
    assert response.status_code == 201

    # Non existing suggestion
    response = client.delete(f"/api/kiosk/suggestion/{uuid4()}")
    assert response.status_code == 404

    # Suggestion we just posted
    response = client.get("/api/kiosk/suggestions")
    assert response.status_code == 200
    posted_suggestion_id = response.json()[0]["id"]

    response = client.delete(f"/api/kiosk/suggestion/{posted_suggestion_id}")
    assert response.status_code == 200

    deleted = db.kioskSuggestions.find_one({"id": posted_suggestion_id})
    assert deleted is None
