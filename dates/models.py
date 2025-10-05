import datetime as dt
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.timezone import get_current_timezone
from recurrence.fields import RecurrenceField

from .utils import format_date, format_date_range


class Date(models.Model):
    event: models.ForeignKey["Recurrence"] = models.ForeignKey("Recurrence", on_delete=models.CASCADE, null=True, blank=True)
    _title = models.CharField(db_column="title", max_length=200, blank=True)
    start_date = models.DateField()
    _start_time = models.TimeField(db_column="start_time", null=True, blank=True)
    _end_date = models.DateField(db_column="end_date", null=True, blank=True)
    _end_time = models.TimeField(db_column="end_time", null=True, blank=True)

    @property
    def title(self) -> str:
        return self._title or self.event.title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def start_time(self) -> dt.time | None:
        if self._start_time:
            return self._start_time
        if self.event:
            return self.event.start_time
        return None

    @start_time.setter
    def start_time(self, value: dt.time | None):
        self._start_time = value

    @property
    def end_date(self) -> dt.date:
        if self._end_date:
            return self._end_date
        if self.end_time < self.start_time:
            return self.start_date + dt.timedelta(days=1)
        return self.start_date

    @end_date.setter
    def end_date(self, value):
        self._end_date = value

    @property
    def end_time(self) -> dt.time | None:
        if self._end_time:
            return self._end_time
        if self.event:
            return self.event.end_time
        if self.start_time:
            return self.start_time.replace(hour=(self.start_time.hour + 1) % 24)
        return None

    @end_time.setter
    def end_time(self, value: dt.time | None):
        self._end_time = value

    # def __init__(self, event: "Event", start: date, end: date | None = None):
    #     if not isinstance(start, date) or (not isinstance(end, date) and end is not None):
    #         raise ValidationError({"recurrence": "Start and end must be date objects"})
    #     if end is not None and start >= end:
    #         raise ValidationError({"recurrence": "Start must be before end"})

    #     self.event = event
    #     self.start = start
    #     self.end = end

    @property
    def start(self) -> dt.date:
        if self.start_time is None:
            return self.start_date
        return dt.datetime.combine(self.start_date, self.start_time, get_current_timezone())

    @property
    def end(self) -> dt.date:
        if self.end_time is None:
            return self.end_date
        return dt.datetime.combine(self.end_date, self.end_time, get_current_timezone())

    @property
    def duration(self) -> dt.timedelta:
        """Returns the duration of the occurrence as a timedelta."""
        return self.end - self.start

    def __str__(self):
        return f"{self.title} on {format_date_range(self.start, self.end) if self.end else format_date(self.start)}"


class OccurrencesList(list[dt.date]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ended = True

    @classmethod
    def from_iterable(cls, iterable, limit=20):
        ret = OccurrencesList()
        ret.ended = False
        for _ in range(limit):
            try:
                ret.append(next(iterable))
            except StopIteration:
                ret.ended = True
                break
        if not ret.ended:
            try:
                next(iterable)
            except StopIteration:
                ret.ended = True
        return ret


class Recurrence(models.Model):
    title = models.CharField(max_length=200)
    start_time = models.TimeField(null=True, blank=True)
    _end_time = models.TimeField(db_column="end_time", null=True, blank=True)
    recurrence = RecurrenceField()

    def clean(self):
        self.occurrences = self.get_occurrences()

    @property
    def end_time(self):
        if self._end_time is not None:
            return self._end_time
        if self.start_time is None:
            return None
        return self.start_time.replace(hour=self.start_time.hour + 1)

    def get_occurrences(self, start: dt.date | None = None, end: dt.date | None = None, inc=False, limit=20):
        """Retourne toutes les occurrences d'un événement récurrent."""
        if not start:
            start = dt.datetime.now()
            start -= dt.timedelta(days=start.weekday())

        # self.recurrence.include_dtstart = False
        # end = start + dt.timedelta(weeks=5)
        # start += dt.timedelta(days=5)
        # import code; code.interact(local={**globals(), **locals()})

        if isinstance(start, dt.date) and not isinstance(start, dt.datetime):
            start = dt.datetime.combine(start, dt.time.min)
        if isinstance(end, dt.date) and not isinstance(end, dt.datetime):
            end = dt.datetime.combine(end, dt.time.min)

        # start = start.astimezone(get_current_timezone()).replace(tzinfo=None)
        # if end:
        #     end = end.astimezone(get_current_timezone()).replace(tzinfo=None)
        def get_occurrences():
            occurrences_list = self.recurrence.to_dateutil_rruleset(start)
            for item in (start, end):
                if item and item in occurrences_list._rdate:
                    occurrences_list._rdate.remove(item)
            for occurrence in occurrences_list:
                print(occurrence)
                if start and not (occurrence >= start if inc else occurrence > start):
                    continue
                if end and not (occurrence <= end if inc else occurrence < end):
                    break
                yield occurrence
        # occurrences = iter(self.recurrence.to_dateutil_rruleset(start).xafter(start, inc=inc))
        # occurrences = iter(self.recurrence.between(start, end, inc=inc))
        occurrences = iter(get_occurrences())
        ret = OccurrencesList.from_iterable(occurrences, limit)

        for i, date in enumerate(ret):
            ret[i] = Date(event=self, start_date=date.date())

        return ret

    def __str__(self):
        return self.title
