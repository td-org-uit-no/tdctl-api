from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

from pymongo import UpdateOne

from app.models import EventDB

import asyncio

lock = asyncio.Lock()

def get_event_or_404(db, eid: str):
    event = db.events.find_one({'eid': UUID(eid)})

    if not event:
        raise HTTPException(404, "Event could not be found")

    return EventDB.parse_obj(event).dict()


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
