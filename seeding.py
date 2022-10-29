from datetime import datetime
from uuid import UUID, uuid4
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from app import config
import json
import os
import shutil

# TODO fix imports so that the file can be added into the db folder
base_dir = "db/seeds"

def seed_random_member(db, number):
    ''' seed a numbr of random users '''
    id = 0
    i = 0
    while i < number:
        name = 'name'
        email = f'{name}{id}@mail.com'
        db_member = db.members.find_one({'email': email})
        if db_member:
            id += 1
            continue
        uid = uuid4().hex
        pwd = generate_password_hash(f'{name}%{id}')
        user = {
            'id': uid,
            'realName': name,
            'email': email,
            'password': pwd,
            'role': 'member',
            'status': 'inactive',
            'classof': '2022',
            'graduated': False,
        }
        db.members.insert_one(user)
        i += 1

def seed_members(db, seed_path):
    ''' seed based on seed file '''
    new_members = []
    with open(seed_path, "r") as f:
        members = json.load(f)
    for member in members:
        db_member = db.members.find_one({'email': member['email'].lower()})
        if db_member:
            continue
        new_members.append(member)
        member["id"] = uuid4().hex
    if len(new_members):
        db["members"].insert_many(new_members)

def seed_events(db, seed_path):

    with open(seed_path, "r") as f:
        events = json.load(f)

    for event in events:
        event["eid"] = UUID(event["eid"]).hex
        db_event = db.events.find_one({'eid': event["eid"]})
        if db_event:
            continue
        event["participants"] = []
        for p in db["members"].find({}):
            event["participants"].append(p)

        img_dst = "db/eventImages/"
        if db.name == 'test':
            img_dst = "db/testEventImages"

        try :
            shutil.copy(f'{base_dir}/seedImages/{event["eid"]}.png', img_dst)
        except FileNotFoundError:
            pass

        event["date"] = datetime.strptime(event['date'], "%Y-%m-%d %H:%M:%S")
        db["events"].insert_one(event)

def get_db():
    env = os.getenv('FLASK_APP_ENV', 'default')
    conf = config[env]
    return MongoClient(conf.MONGO_URI)[conf.MONGO_DBNAME]

if __name__ == "__main__":
    db = get_db()
    seed_random_member(db, 5)
    seed_members(db, f"{base_dir}/members.json")
    seed_events(db, f"{base_dir}/events.json")
