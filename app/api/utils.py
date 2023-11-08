from typing import Dict
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

from pymongo import UpdateOne
from pymongo.collection import Collection

from app.models import EventDB

import asyncio

lock = asyncio.Lock()

def get_event_or_404(db, eid: str):
    event = db.events.find_one({'eid': UUID(eid)})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return EventDB.model_validate(event).model_dump()


async def penalize(db, uid: UUID):
    """ Apply penalty to member. Applies to member db and all joined event participant lists """

    async with lock:
        member = db.members.find_one({'id': uid})

        if not member:
            raise HTTPException(404, "Member not found")
        
        
        should_deprioritize = bool(member['penalty'] >= 1)

        # Apply penalty to member db
        res = db.members.update_one({"id": uid}, {"$inc": {"penalty": 1}})

        if not res:
            raise HTTPException(500)
        
        # Apply penalty to all joined events
        now = datetime.now()

        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

        pipeline = [
            {"$match": {"date": {"$gt": date}}},
            {"$unwind": "$participants"},
            {"$match": {"participants.id": {"$eq": uid}}}
        ]
        joined = db.events.aggregate(pipeline)


        if not joined:
            raise HTTPException(500)
        
        updates = []
        updated = False
        for event in joined:
            # Update penalty on event
            res = db.events.update_one({"eid": event["eid"], "participants.id": uid}, {
                "$inc": {"participants.$.penalty": 1}
            })


            if not res:
                raise HTTPException(500)

            # Deprioritize for this event
            if should_deprioritize and not event["confirmed"]:
                # Pull member from event
                updates.append(UpdateOne({"eid": event["eid"]}, {
                    "$pull": {"participants": {"id": uid}}
                }))
                
                participant = event["participants"]

                # Add penalty
                if not updated:
                    participant["penalty"] += 1
                    updated = True

                if not participant:
                    raise HTTPException(500)
                
                updates.append(UpdateOne({"eid": event["eid"]}, {
                    "$push": {"participants": participant}
                }))


        if len(updates) == 0:
            return

        res = db.events.bulk_write(updates)

        if not res:
            raise HTTPException(500)

def get_uuid(id: str):
    try:
        return UUID(id)
    except ValueError:
        return None

# get event title from path, can be extended to retrieve other fields
def get_event_title_from_path(db, path):
    id = get_uuid(path)
    if not id:
        return None
    event = db.events.find_one({ 'eid': id })
    if not event:
        return "Et slettet arrangement"
    return event["title"]

# get job title from path, can be extended to retrieve other fields
def get_job_title_from_path(db, path):
    id = get_uuid(path)
    if not id:
        return None
    job = db.jobs.find_one({ 'id': id })
    if not job:
        return "En slettet stillingsultlysning"
    return job["title"]

# function for finding objects for the paths containing uuid
# such as events and jobs 
def find_object_title_from_path(path: str, db: Collection):
    path_to_db = {
        "event": get_event_title_from_path,
        "jobs": get_job_title_from_path,
    }
    sub_paths = path.split("/")
    for i, sub_path in enumerate(sub_paths):
        if sub_path not in path_to_db:
            continue
        if i == len(sub_path) - 1:
            return None
        return path_to_db[sub_path](db, sub_paths[i+1])
    return None
