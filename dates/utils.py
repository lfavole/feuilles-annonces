import datetime

from django.utils.dateformat import format, time_format
from django.utils.formats import get_format


def format_date(date: datetime.date | datetime.datetime):
    if isinstance(date, datetime.datetime):
        return format(date, "l " + get_format("DATETIME_FORMAT"))
    return format(date, "l " + get_format("DATE_FORMAT"))


def format_date_range(start: datetime.date | datetime.datetime, end: datetime.date | datetime.datetime):
    start_date = format(start, "l " + get_format("DATE_FORMAT"))
    end_date = format(end, "l " + get_format("DATE_FORMAT"))

    if not isinstance(start, datetime.datetime) or not isinstance(end, datetime.datetime):
        if start_date == end_date:
            return start_date
        return f"{start_date} - {end_date}"

    start_time = time_format(start, get_format("TIME_FORMAT"))
    end_time = time_format(end, get_format("TIME_FORMAT"))

    if start_date == end_date:
        return f"{start_date} {start_time} - {end_time}"

    return f"{start_date} {start_time} - {end_date} {end_time}"
