import datetime
import pytest
from app.db import get_test_db
from tests.conftest import client_login
from tests.users import regular_member, admin_member
from tests.utils.authentication import admin_required, authentication_required
from datetime import datetime, timedelta

from tests.utils.stats import add_unique_visits

page_payload = {
    'page': '/test_page/1'
}
datetime_format = "%Y-%m-%d %H:%M:%S"

@authentication_required('/api/stats/unique-visit', 'post')
def test_uniquie_visit(client):
    db = get_test_db()
    client_login(client, regular_member['email'], regular_member['password'])
    response = client.post("/api/stats/unique-visit")
    assert response.status_code == 200
    log = db.uniqueVisitLog.find({})
    assert len(list(log)) == 1

    # bloom filter can give false positives however this should always work 
    response = client.post("/api/stats/unique-visit")
    assert response.status_code == 200
    log = db.uniqueVisitLog.find({})
    assert len(list(log)) == 1

def test_add_page_visit(client):
    db = get_test_db()
    response = client.post("api/stats/page-visit", json=page_payload)
    assert response.status_code == 200
    res = db.pageVisitLog.find({"metaData": page_payload["page"]})
    assert res != None
    pages = list(res)
    assert len(pages) == 1
    assert pages[0]["metaData"] == page_payload['page']

@admin_required('/api/stats/unique-visit/', 'get')
def test_get_unique_visits(client):
    db = get_test_db()
    add_unique_visits(db)
    client_login(client, admin_member['email'], admin_member['password'])
    now = datetime.now()
    url = "/api/stats/unique-visit"
    params = {
        "end": now.isoformat(),
    }
    res = client.get(url, params=params)
    # expects 400 on wrong format
    assert res.status_code == 400
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=10)
    start = start.strftime(datetime_format)
    params['start'] = start
    # end of day
    params['end'] = f"{yesterday.year}-{yesterday.month}-{yesterday.day} 23:59:59"
    res = client.get(url, params=params)
    assert res.status_code == 200
    visits = res.json()
    count = 0
    for visit in visits:
        count += visit["count"]
    # 5 visits per day inserted in seed
    assert count == 5

@admin_required('/api/stats/page-visits', 'get')
def test_get_page_visits(client):
    client_login(client, admin_member['email'], admin_member['password'])
    num_visits = 3
    for _ in range(num_visits):
        response = client.post("api/stats/page-visit", json=page_payload)
        if response.status_code != 200:
            pytest.fail(f"Problem setting up page visits, got response {response.status_code}")
    yesterday = datetime.now() - timedelta(days=1)
    yesterday = yesterday.strftime(datetime_format)
    params = {
        "page": page_payload['page'],
    }
    res = client.get('/api/stats/page-visits', params=params)
    assert res.status_code == 200
    res = res.json()
    assert res[0]["count"] == num_visits

@admin_required('/api/stats/most_visited_pages_last_month/', 'get')
def test_most_visited_pages_last_30_days(client):
    client_login(client, admin_member['email'], admin_member['password'])

    # add 6 different pages with descending numbers of visits
    for i in range(6):
        for _ in range(i):
            page_payload['page'] = f"/test_page/{i}"
            response = client.post("api/stats/page-visit", json=page_payload)
            if response.status_code != 200:
                pytest.fail("Failed to setup page visits in setup")
    res = client.get('/api/stats/most_visited_pages_last_month/')
    assert res.status_code == 200
    page_visits = res.json()
    assert len(page_visits) == 5
    # test that the endpoint retrieves the 5 most visited pages
    for page in page_visits:
        # gets the last part of the page name path
        sub_paths = page["path"].split("/")
        num = sub_paths[-1]
        # all paths should have the same amount of visits as their num
        assert int(num) == page["count"]

