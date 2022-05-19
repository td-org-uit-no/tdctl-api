from datetime import datetime
from uuid import uuid4
from bson.objectid import ObjectId
from pymongo import MongoClient
from app import config
import json
import os
import shutil

# TODO fix imports so that the file can be added into the db folder
base_dir = "db/seeds"
def seed_members(db):
    member_seed = f"{base_dir}/members.json"

    with open(member_seed, "r") as f:
        members = json.load(f)
    for member in members:
        db_member = db.members.find_one({'email': member['email'].lower()})
        if db_member:
            continue
        member["id"] = uuid4().hex
    db["members"].insert_many(members)

def seed_events(db):
    event_seed = f"{base_dir}/events.json"
    event_images = f"{base_dir}/seedImages/"

    with open(event_seed, "r") as f:
        events = json.load(f)

    for event in events:
        db_event = db.events.find_one({'eid': event['eid']})
        if db_event:
            continue
        event["participants"] = []
        for p in db["members"].find({}):
            event["participants"].append(p)

        shutil.copy(f'{event_images}/{event["eid"]}.png', f'db/eventImages/')
        event["date"] = datetime.strptime(event['date'], "%Y-%m-%d %H:%M:%S")
        db["events"].insert_one(event)

def get_db():
    env = os.getenv('FLASK_APP_ENV', 'default')
    conf = config[env]
    return MongoClient(conf.MONGO_URI)[conf.MONGO_DBNAME]

if __name__ == "__main__":
    db = get_db()
    seed_members(db)
    seed_events(db)