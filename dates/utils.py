import datetime as dt
import re
from html import unescape

from django.utils.dateformat import format
from django.utils.timezone import get_current_timezone


def striptags(value: str):
    value = str(value)
    value = re.sub(r"<!--.*?-->", "", value)
    value = re.sub(r"<.*?>", "", value)
    return unescape(value)


def date_to_datetime(date: dt.date):
    if isinstance(date, dt.datetime):
        return date
    return dt.datetime.combine(date, dt.time.min, tzinfo=get_current_timezone())


def _get_parts(date_or_time: dt.date | dt.time | None = None):
    ret = {}
    if isinstance(date_or_time, dt.date):
        ret["date"] = [format(date_or_time, format_string) for format_string in ("l", "j", "F", "Y")]
        if ret["date"][1] == "1":
            ret["date"][1] = "1<sup>er</sup>"
    if isinstance(date_or_time, (dt.time, dt.datetime)):
        ret["time"] = [format(date_or_time, format_string) for format_string in ("H", "i", "s")]
    return ret


def format_date_or_time(start: dt.date | dt.time, end: dt.date | dt.time | None = None, *, weekday=True, year=False, natural=False, natural_time=False):
    parts = [_get_parts(start)]
    if end:
        parts.append(_get_parts(end))
    return _render_parts(parts, weekday=weekday, year=year, natural=natural, natural_time=natural_time)


def _render_date(parts, *, weekday, natural, year):
    if not year:
        # Remove the last item for all the parts
        parts = [part[:-1] for part in parts]
    if not weekday:
        # Remove the first item for all the parts
        parts = [part[1:] for part in parts]
    if len(parts) > 1:
        index = len(parts[0]) - 1
        while all(parts) and all(part[index] == parts[0][index] for part in parts[1:]):
            index -= 1
            # Remove the last item for all the parts except the last one
            parts[:-1] = [part[:-1] for part in parts[:-1]]
        if not any(part for part in parts[:-1]):
            # If all the items of all the parts (except the last one) were removed, keep only the last one
            del parts[:-1]
    chunks = [" ".join(part) for part in parts]
    if natural:
        if len(chunks) == 1:
            return chunks[0]
        return "du " + " au ".join(chunks)
    return " - ".join(chunks)


def _render_time(parts, *, natural, natural_time):
    if all(part == parts[0] for part in parts[1:]):
        del parts[1:]
    # If seconds are 0 for all the parts, remove the last item
    if all(len(part) == 3 and int(part[-1]) == 0 for part in parts):
        parts = [part[:-1] for part in parts]
    if natural_time and all(len(part) == 2 for part in parts):
        # Remove the last item of each part if it's 0 (the minute)
        parts = [(part[:-1] if int(part[-1]) == 0 else part) for part in parts]
        chunks = [part[0] + "h" + (part[1] if len(part) > 1 else "") for part in parts]
    else:
        chunks = [":".join(part) for part in parts]
    if natural:
        if len(chunks) == 1:
            return chunks[0]
        return "de " + " à ".join(chunks)
    return " - ".join(chunks)


def _render_parts(all_parts, *, weekday=True, year=False, natural=False, natural_time=False):
    assert len(all_parts) in (1, 2)

    zipped = {}
    for parts in all_parts:
        for key, value in parts.items():
            if value:
                zipped.setdefault(key, []).append(value)

    # A bit of terminology: (the line has parts)
    # October 6, 2025 10:00 - 11:00
    # ↑ item          \___________/ ← items/part

    rendered = {}
    for type, parts in zipped.items():
        if not parts:
            continue

        if type == "date":
            rendered["date"] = _render_date(parts, weekday=weekday, natural=natural, year=year)
            continue

        if type == "time":
            rendered["time"] = _render_time(parts, natural=natural, natural_time=natural_time)
            continue

        raise RuntimeError(f"Unexpected type: {type}")

    return " ".join([part for part in (rendered.get("date"), rendered.get("time")) if part])
