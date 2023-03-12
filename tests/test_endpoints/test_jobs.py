from app.db import get_test_db
from tests.conftest import client_login
from tests.users import regular_member, admin_member
from app.db import get_test_db
from uuid import UUID
from tests.utils.authentication import admin_required

db = get_test_db()

new_job = {
    "company": "TD",
    "title": "Vil du være TD's nye nettside ansvarlig?",
    "type": "Charity",
    "img": "",
    "tags": ["TypeScript", "React", "Docker", "MongoDB"],
    "description_preview": "Vi trenger noen til å ta over tds nye nettsider!",
    "description": "Vi trenger noen til å ta over TDs nettsider og videreutvikle produktet.",
    "start_date": "2023-01-01T00:00:00.000Z",
    "published_date": "2023-01-01T00:00:00.000Z",
    "location": "Tromsø",
    "link": "td-uit.no",
    "due_date": "2023-01-01T00:00:00.000Z",
}


@admin_required("/api/jobs/", "post")
def test_create_job(client):

    client_login(client, regular_member["email"], regular_member["password"])
    response = client.post("/api/jobs/", json=new_job)
    assert response.status_code == 403

    client_login(client, admin_member["email"], admin_member["password"])
    response = client.post("/api/jobs/", json=new_job)

    assert response.status_code == 200
    retval = response.json()
    job = db.jobs.find_one({"id": UUID(retval["id"])})
    assert job != None


def test_get_job(client):
    client_login(client, admin_member["email"], admin_member["password"])
    # insert new Job
    response = client.post("/api/jobs/", json=new_job)
    assert response.status_code == 200

    client_login(client, regular_member["email"], regular_member["password"])

    # Validate the new job can be accessed
    response = response.json()
    job = client.get("/api/jobs/"+response["id"])
    assert job.status_code == 200
    assert UUID(job.json()["id"]) == UUID(response['id'])


@admin_required("/api/jobs/{uuid}/", "delete")
def test_delete_job(client):
    client_login(client, admin_member["email"], admin_member["password"])

    response = client.post("/api/jobs/", json=new_job)
    assert response.status_code == 200
    response = response.json()

    delResponse = client.delete("/api/jobs/"+response["id"])
    assert delResponse.status_code == 200

    val_delete = client.delete("/api/jobs/"+response["id"])
    assert val_delete.status_code == 400


@admin_required("/api/jobs/{uuid}", "put")
def test_update_job(client):
    client_login(client, admin_member["email"], admin_member["password"])

    response = client.post("/api/jobs/", json=new_job)
    assert response.status_code == 200
    response = response.json()

    new_job_update = new_job.copy()
    new_job_update["title"] = "New Title"

    update_response = client.put(
        "/api/jobs/"+response["id"], json=new_job_update)
    assert update_response.status_code == 200

    _test = client.get("/api/jobs/"+response["id"])

    assert _test.json()["title"] == new_job_update["title"]
