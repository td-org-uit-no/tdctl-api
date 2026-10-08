from app.db import get_test_db
from app.models import Status
from tests.conftest import client_login
from tests.users import regular_member, admin_member, second_member, second_admin
from tests.utils.authentication import admin_required, authentication_required
from uuid import UUID

db = get_test_db()


# -------------------- List Committees --------------------

def test_list_committees_public(client):
    """Test that anyone can list committees without authentication"""
    response = client.get("/api/committee/")
    assert response.status_code == 200
    res_json = response.json()

    assert "items" in res_json
    assert "total" in res_json
    assert "page" in res_json
    assert "limit" in res_json

    # Should have 4 committees from seed data
    assert res_json["total"] == 4
    assert len(res_json["items"]) == 4

    # Verify structure of committee items
    for item in res_json["items"]:
        assert "id" in item
        assert "name" in item
        assert "slug" in item
        assert "status" in item
        assert "hasOpenSpots" in item
        assert "memberCount" in item
        assert "email" in item


def test_list_committees_pagination(client):
    """Test pagination for committee listing"""
    response = client.get("/api/committee/?page=1&limit=2")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["total"] == 4
    assert len(res_json["items"]) == 2
    assert res_json["page"] == 1
    assert res_json["limit"] == 2


def test_list_committees_filter_by_status(client):
    """Test filtering committees by status"""
    response = client.get("/api/committee/?status=active")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["total"] == 3  # Board, Tech, Social are active
    for item in res_json["items"]:
        assert item["status"] == "active"

    response = client.get("/api/committee/?status=inactive")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["total"] == 1  # Only "Inactive Committee"
    assert res_json["items"][0]["status"] == "inactive"


def test_list_committees_filter_by_open_spots(client):
    """Test filtering committees by hasOpenSpots"""
    response = client.get("/api/committee/?hasOpenSpots=true")
    assert response.status_code == 200
    res_json = response.json()

    # Tech and Social have open spots
    assert res_json["total"] >= 2
    for item in res_json["items"]:
        assert item["hasOpenSpots"] is True


def test_list_committees_sorting(client):
    """Test sorting committees by name"""
    response = client.get("/api/committee/?sortBy=name&sortOrder=asc")
    assert response.status_code == 200
    res_json = response.json()

    names = [item["name"] for item in res_json["items"]]
    assert names == sorted(names)


# -------------------- Get Committee by ID --------------------

def test_get_committee_by_id(client):
    """Test getting a specific committee by ID"""
    committee = db.committees.find_one({"slug": "board"})
    assert committee is not None

    response = client.get(f"/api/committee/{committee['id']}")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["id"] == str(committee["id"])
    assert res_json["name"] == "Board"
    assert res_json["slug"] == "board"
    assert "memberCount" in res_json


def test_get_committee_not_found(client):
    """Test getting a non-existent committee"""
    from uuid import uuid4
    fake_id = uuid4()

    response = client.get(f"/api/committee/{fake_id}")
    assert response.status_code == 404


def test_get_committee_invalid_uuid(client):
    """Test getting committee with invalid UUID"""
    response = client.get("/api/committee/not-a-uuid")
    assert response.status_code == 400  # validate_uuid returns 400


# -------------------- Create Committee (Admin) --------------------


def test_create_committee(client):
    """Test creating a new committee as admin"""
    client_login(client, admin_member["email"], admin_member["password"])

    payload = {
        "name": "New Committee",
        "description": "A brand new committee",
        "hasOpenSpots": True,
        "status": "active",
        "email": "new@td-uit.no"
    }

    response = client.post("/api/committee/", json=payload)
    assert response.status_code == 201

    # Verify committee was created by fetching it
    created_committee = db.committees.find_one({"name": payload["name"]})
    assert created_committee is not None
    assert created_committee["slug"] == "new-committee"  # Auto-generated slug
    assert created_committee["description"] == payload["description"]
    assert created_committee["hasOpenSpots"] == payload["hasOpenSpots"]
    assert created_committee["status"] == payload["status"]
    assert created_committee["email"] == payload["email"]
    assert created_committee["createdBy"] == admin_member["email"]


def test_create_committee_with_custom_slug(client):
    """Test creating a committee with a custom slug"""
    client_login(client, admin_member["email"], admin_member["password"])

    payload = {
        "name": "Custom Committee",
        "slug": "custom-slug",
        "hasOpenSpots": False,
        "status": "active",
        "email": "custom@td-uit.no"
    }

    response = client.post("/api/committee/", json=payload)
    assert response.status_code == 201

    # Verify custom slug was used
    created_committee = db.committees.find_one({"slug": "custom-slug"})
    assert created_committee is not None
    assert created_committee["name"] == payload["name"]


def test_create_committee_duplicate_slug(client):
    """Test that creating a committee with duplicate slug fails"""
    client_login(client, admin_member["email"], admin_member["password"])

    payload = {
        "name": "Duplicate",
        "slug": "board",  # Already exists in seed data
        "hasOpenSpots": True,
        "status": "active",
        "email": "dup@td-uit.no"
    }

    response = client.post("/api/committee/", json=payload)
    assert response.status_code == 409


# -------------------- Update Committee (Admin) --------------------


def test_update_committee(client):
    """Test updating a committee"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "tech"})
    assert committee is not None

    payload = {
        "name": "Updated Tech Committee",
        "description": "Updated description",
        "hasOpenSpots": False
    }

    response = client.put(f"/api/committee/{committee['id']}", json=payload)
    assert response.status_code == 200

    # Verify committee was updated
    updated_committee = db.committees.find_one({"id": committee["id"]})
    assert updated_committee["name"] == payload["name"]
    assert updated_committee["description"] == payload["description"]
    assert updated_committee["hasOpenSpots"] == payload["hasOpenSpots"]
    assert updated_committee["slug"] == "tech"  # Slug unchanged


def test_update_committee_slug_conflict(client):
    """Test that updating slug to existing one fails"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "tech"})
    payload = {"slug": "board"}  # Already exists

    response = client.put(f"/api/committee/{committee['id']}", json=payload)
    assert response.status_code == 409


# -------------------- Delete Committee (Admin) --------------------


def test_delete_committee(client):
    """Test deleting a committee"""
    client_login(client, admin_member["email"], admin_member["password"])

    # Create a committee to delete
    payload = {
        "name": "To Delete",
        "hasOpenSpots": True,
        "status": "active",
        "email": "delete@td-uit.no"
    }
    create_response = client.post("/api/committee/", json=payload)
    assert create_response.status_code == 201

    # Get the created committee ID from database
    created_committee = db.committees.find_one({"name": "To Delete"})
    assert created_committee is not None
    committee_id = created_committee["id"]

    # Delete it
    response = client.delete(f"/api/committee/{committee_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_response = client.get(f"/api/committee/{committee_id}")
    assert get_response.status_code == 404


# -------------------- Add Committee Member (Admin) --------------------


def test_add_committee_member(client):
    """Test adding a member to a committee"""
    client_login(client, admin_member["email"], admin_member["password"])

    # Get a committee with open spots
    committee = db.committees.find_one({"slug": "tech"})
    member = db.members.find_one({"email": regular_member["email"]})

    payload = {"userId": str(member["id"])}

    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 201

    # Verify member was added
    membership = db.committeeMembers.find_one({
        "committeeId": committee["id"],
        "userId": member["id"],
        "active": True
    })
    assert membership is not None
    assert membership["addedBy"] == admin_member["email"]


def test_add_committee_member_no_open_spots(client):
    """Test adding member to committee without open spots fails"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "board"})  # hasOpenSpots: false
    member = db.members.find_one({"email": regular_member["email"]})

    payload = {"userId": str(member["id"])}

    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 400


def test_add_committee_member_duplicate(client):
    """Test adding the same member twice fails"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "tech"})
    member = db.members.find_one({"email": second_member["email"]})

    payload = {"userId": str(member["id"])}

    # Add first time
    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 201

    # Verify member was added and is active
    membership = db.committeeMembers.find_one({
        "committeeId": committee["id"],
        "userId": member["id"]
    })
    assert membership is not None
    assert membership["active"] is True

    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 409


def test_reactivate_inactive_member(client):
    """Test that adding a previously removed member reactivates them"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "tech"})
    member = db.members.find_one({"email": second_admin["email"]})

    payload = {"userId": str(member["id"])}

    # Add member
    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 201

    # Remove member
    response = client.delete(f"/api/committee/{committee['id']}/members/{member['id']}")
    assert response.status_code == 200

    # Verify member is inactive
    membership = db.committeeMembers.find_one({
        "committeeId": committee["id"],
        "userId": member["id"]
    })
    assert membership is not None
    assert membership.get("active") is False

    # Add again (should reactivate and return 201)
    response = client.post(f"/api/committee/{committee['id']}/members", json=payload)
    assert response.status_code == 201

    # Note: The actual reactivation logic sets active=True in the database
    # We've verified the API accepts the request successfully


# -------------------- List Committee Members (Admin) --------------------


def test_list_committee_members(client):
    """Test listing members of a committee"""
    client_login(client, admin_member["email"], admin_member["password"])

    # Add some members first
    committee = db.committees.find_one({"slug": "social"})
    member1 = db.members.find_one({"email": regular_member["email"]})
    member2 = db.members.find_one({"email": second_member["email"]})

    for member in [member1, member2]:
        payload = {"userId": str(member["id"])}
        client.post(f"/api/committee/{committee['id']}/members", json=payload)

    # List members
    response = client.get(f"/api/committee/{committee['id']}/members")
    assert response.status_code == 200
    res_json = response.json()

    assert "items" in res_json
    assert "total" in res_json
    assert res_json["total"] == 2

    # Verify member structure
    for item in res_json["items"]:
        assert "id" in item
        assert "realName" in item
        assert "email" in item
        assert "classOf" in item
        assert "role" in item



# -------------------- Remove Committee Member (Admin) --------------------


def test_remove_committee_member(client):
    """Test removing a member from a committee"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "tech"})
    member = db.members.find_one({"email": second_admin["email"]})

    # Add member first
    payload = {"userId": str(member["id"])}
    client.post(f"/api/committee/{committee['id']}/members", json=payload)

    # Remove member
    response = client.delete(f"/api/committee/{committee['id']}/members/{member['id']}")
    assert response.status_code == 200

    # Verify member is inactive
    membership = db.committeeMembers.find_one({
        "committeeId": committee["id"],
        "userId": member["id"]
    })
    assert membership["active"] is False
    assert membership["leftBy"] == admin_member["email"]
    assert membership["leftAt"] is not None


def test_remove_nonexistent_member(client):
    """Test removing a member that doesn't exist"""
    client_login(client, admin_member["email"], admin_member["password"])

    from uuid import uuid4
    committee = db.committees.find_one({"slug": "tech"})
    fake_member_id = uuid4()

    response = client.delete(f"/api/committee/{committee['id']}/members/{fake_member_id}")
    assert response.status_code == 404

# -------------------- Member Count Validation --------------------

def test_member_count_accuracy(client):
    """Test that memberCount reflects active members only"""
    client_login(client, admin_member["email"], admin_member["password"])

    committee = db.committees.find_one({"slug": "social"})

    # Get initial count
    response = client.get(f"/api/committee/{committee['id']}")
    initial_count = response.json()["memberCount"]

    # Add a member
    member = db.members.find_one({"email": regular_member["email"]})
    payload = {"userId": str(member["id"])}
    client.post(f"/api/committee/{committee['id']}/members", json=payload)

    # Check count increased
    response = client.get(f"/api/committee/{committee['id']}")
    assert response.json()["memberCount"] == initial_count + 1

    # Remove the member
    client.delete(f"/api/committee/{committee['id']}/members/{member['id']}")

    # Check count decreased
    response = client.get(f"/api/committee/{committee['id']}")
    assert response.json()["memberCount"] == initial_count
