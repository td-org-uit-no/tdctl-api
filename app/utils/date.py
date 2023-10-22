from datetime import datetime, date, timedelta
from enum import Enum
from fastapi import HTTPException
import math

# returns formatted date, does not validate user input 
def format_date(input_date: str, format: str):
    try:
        formated = datetime.strptime(input_date, format)
    except ValueError as e:
        raise HTTPException(400, "Invalid date format")
    return formated

class Interval(Enum):
    hour = 0,
    day = 1,

def add_continous_datapoints_to_log(log_dict, start:datetime, end:datetime, interval: Interval):
    if (interval == Interval.day):
        return add_continous_datapoints_in_days(log_dict, start, end)
    if (interval == Interval.hour):
        return add_continous_datapoints_in_hours(log_dict, start, end)
    return []

# fill gaps in logging result, with {"count": o, "date": missing_date} 
# to get continuous data points
def add_continous_datapoints_in_days(log_dict, start:datetime, end:datetime):
    date_range = (end - start).days
    ts_format = "%Y-%m-%d"
    # fill dates not captured in aggregate with 0 visits
    for i in range(0, date_range):
        insert = True
        search_date = start.date() + timedelta(days=i)
        for log in log_dict:
            visit_date = format_date(log["date"], ts_format)
            if visit_date.date() == search_date:
                insert = False
                break
        if insert:
            new_entry = {"count": 0, "date": search_date.strftime(ts_format)}
            log_dict.insert(i, new_entry)
    return log_dict

# same as add_continous_datapoints_in_days just for hour
def add_continous_datapoints_in_hours(log_dict, start:datetime, end:datetime):
    date_range = (end - start).total_seconds()
    # convert to hours
    date_range = math.ceil(date_range/3600)
    ts_format: str = "%Y-%m-%dT%H"
    start = start.replace(minute=0, second=0)
    # fill dates not captured in aggregate with 0 visits
    for i in range(0, date_range):
        insert = True
        search_date = start + timedelta(hours=i)
        group_datatpoints(log_dict, search_date, insert,i, ts_format)
    return log_dict

def group_datatpoints(log_dict, search_date, insert, idx, ts_format):
    for log in log_dict:
        visit_date = format_date(log["date"], ts_format)
        if visit_date == search_date:
            insert = False
            break
    if insert:
        new_entry = {"count": 0, "date": search_date.strftime(ts_format)}
        log_dict.insert(idx, new_entry)
