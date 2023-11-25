import math
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from app.api.utils import find_object_title_from_path
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response
from app.auth_helpers import authorize, authorize_admin
from app.db import get_database
import pickle as pkl
from app.utils.date import Interval, add_continous_datapoints_to_log, format_date
from pybloom_live import ScalableBloomFilter

from app.models import AccessTokenPayload, PageVisit


router = APIRouter()

# groups all timestamps to their day, but can be extended to group to an arbitrary time
@router.get('/unique-visit')
def get_number_of_unique_visitors(request: Request, start: Optional[str] = None, end:Optional[str] = None, token: AccessTokenPayload = Depends(authorize_admin)):
    ''' Get unique visitors with an optional interval \n
        start: if start date is not provided it uses the first recorded timestamp as start date \n
        end: if end date is not provided it uses the current date
    '''
    db = get_database(request)
    datetime_format = "%Y-%m-%d %H:%M:%S"
    interval = Interval.day
    if end == None:
        end_date = datetime.now()
    else :
        end_date = format_date(end, datetime_format)

    match_query = {"timestamp": {"$lte": end_date}}
    # format on the aggregate query i.e the interval visits are grouped in 
    query_format = "%Y-%m-%d"
    start_date = None
    if start:
        start_date = format_date(start, datetime_format)
        start_query = {"timestamp": {"$gte": start_date}}
        # redefine match_query to contain start
        match_query = {"$and": [start_query, match_query]}

        if start_date >= end_date:
            raise HTTPException(400, "Start date cannot be larger then end date")
        date_range = math.ceil((end_date-start_date).total_seconds()/3600)
        # checks for interval less than one day to group the dates in more detailed groups
        if  date_range <= 48:
            interval = Interval.hour
            query_format = f"{query_format}T%H"

    pipeline = [
        {"$match": match_query},
        {"$group": {
            # could only use $dateToString in _id field
            "_id": {"$dateToString": {"format": query_format, "date": "$timestamp"}},
            "count" :  {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "date": "$_id",
            "count": 1,
            "_id": 0,
        }}
    ]

    res = db.uniqueVisitLog.aggregate(pipeline)
    visits = list(res)
    if not len(visits):
        return visits

    if not start_date:
        # if start date is not provided the first timestamp is used as start date
        start_date = format_date(visits[0]["date"], query_format)
    return add_continous_datapoints_to_log(visits, start_date, end_date, interval)

def register_new_visit(db, user_id):
    member = db.members.find_one({'id': UUID(user_id)})
    if not member:
        logging.error(f"404 - User with {user_id} could not be found")
        return
    today = datetime.today().strftime('%Y-%m-%d')
    stats = db.uniqueFilter.find_one({'entry_date': today})
    update_dict = {}
    # checks if bloomfilter is added for the day
    if not stats:
        update_dict = {
            "createdAt": datetime.utcnow(),
            "entry_date": today,
        }
        # adds a fresh bloomfilter
        bf = ScalableBloomFilter(initial_capacity=1000, error_rate=0.001, mode=ScalableBloomFilter.SMALL_SET_GROWTH)
    else:
        # load the existing filter into memory
        bf = pkl.loads(stats["bloom_filter"])

    # add returns True if key exists in filter and false on successful insert(for some reason)
    exists = bf.add(user_id)
    if exists:
        return

    # stores time object instead of string representation since we don't need to format
    # 26 bytes per entry timestamp and _id
    ts = datetime.now()
    res = db.uniqueVisitLog.insert_one({"timestamp": ts})
    if not res:
        logging.error(f"could not insert timestamp: {ts}")
        return

    update_dict.update({"bloom_filter": pkl.dumps(bf)})

    # upsert=True to create the document if non is found for this date
    res = db.uniqueFilter.update_one({'entry_date': today}, {"$set": update_dict}, upsert=True)
    if not res:
        logging.error(f"could not update bloom_filter with: {today}, {update_dict}")

@router.post('/unique-visit')
async def add_unique_member_visit(request: Request, background_task: BackgroundTasks, token: AccessTokenPayload = Depends(authorize)):
    ''' endpoint to track unique visitors per day. Uses background_tasks as we want to return 200 ok at once.
        The reason is that this endpoint should have minimal effect on the user and errors should only be logged.
    '''
    db = get_database(request)
    background_task.add_task(register_new_visit, db, token.user_id)
    return Response(status_code=200)

def register_page_visit(db, page):
    ts = datetime.now()

    # don't track admin page visits
    if "admin" in page:
    # remove admin logs
        return
    res = db.pageVisitLog.insert_one({"timestamp": ts, "metaData": page})
    if not res:
        logging.error(f"could not insert visit on page: {page}")

# builds on top of the react-router-dom location.pathname for identifying the page
@router.post('/page-visit')
async def add_page_visit(request: Request, payload: PageVisit, background_task: BackgroundTasks):
    db = get_database(request)
    background_task.add_task(register_page_visit, db, payload.page)
    return Response(status_code=200)

# gets the numbers of visit for a page between start and end
# if end is not specified its set to datetime.now()
@router.get('/page-visits')
def get_page_visits(request: Request, page: str, start: Optional[str] = None, end: Optional[str] = None, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    datetime_format = "%Y-%m-%dT%H:%M:%S"
    search_consitions = []

    if end == None:
        end_date = datetime.now()
    else :
        end_date = format_date(end, datetime_format)

    end_query = {"timestamp": {"$lte": end_date}}
    search_consitions.append(end_query)
    start_date = None

    if start:
        start_date = format_date(start, datetime_format)
        start_query = {"timestamp": {"$gte": start_date}}
        # redefine match_query to contain start
        search_consitions.append(start_query)

        if start_date >= end_date:
            raise HTTPException(400, "Start date cannot be larger then end date")
    search_consitions.append({"metaData": page})
    pipeline = [
        {"$match": {"$and": search_consitions}},
        {"$group": {
            # could only use $dateToString in _id field
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count" :  {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "date": "$_id",
            "count": 1,
            "_id": 0,
        }}
    ]

    res = db.pageVisitLog.aggregate(pipeline)
    visits = list(res)

    if not len(visits):
        return visits

    if not start_date:
        # if start date is not provided the first timestamp is used as start date
        start_date = format_date(visits[0]["date"], "%Y-%m-%d")

    return add_continous_datapoints_to_log(visits, start_date, end_date, Interval.day)

@router.get('/most_visited_pages_last_month')
def get_most_visited_page(request: Request, token: AccessTokenPayload = Depends(authorize_admin)):
    db = get_database(request)
    now = datetime.now()
    start_date = now - timedelta(weeks=4) 
    pipeline = [
        {"$match": {"$and": [{"timestamp": {"$lte": now}}, {"timestamp": {"$gte": start_date}}]}},
        {"$group": {
            # could only use $dateToString in _id field
            "_id": "$metaData",
            "count" :  {"$sum": 1},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 5},
        {"$project":{
            "_id": 0,
            "path": "$_id",
            "count": "$count"
        }}
    ]
    res = db.pageVisitLog.aggregate(pipeline)
    pages = list(res)
    
    for page in pages:
        path = page["path"]
        title = find_object_title_from_path(path, db)
        if not title:
            title = path
        page.update({"title": title})
    return pages
