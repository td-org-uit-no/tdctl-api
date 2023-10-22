
from datetime import datetime, timedelta

def add_unique_visits(db):
    db.uniqueVisitLog.delete_many({})
    now = datetime.now()

    # generates a year of 5 visits per day
    # one per hour from 12:00
    for i in range(0, 365):
        new_date = now - timedelta(days=i)
        for j in range(0, 5):
            hour = 12 + j
            minute = 0
            ts = new_date.replace(hour=hour, minute=minute)
            db.uniqueVisitLog.insert_one({"timestamp": ts})

