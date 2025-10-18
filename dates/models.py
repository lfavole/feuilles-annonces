import datetime as dt
from functools import total_ordering
from string import Template
from typing import Generator, Union

from django.db import models
from django.utils.timezone import get_current_timezone, now
from recurrence.fields import RecurrenceField
from solo.models import SingletonModel

from .liturgical_calendar import default_translations, get_liturgical_year, get_movable_feasts_for
from .ordinal import ordinal
from .utils import date_to_datetime, format_date_or_time


@total_ordering
class DateRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __add__(self, other):
        if isinstance(other, dt.timedelta):
            return type(self)(self.start + other)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, type(self)):
            return self.start - other.start
        return self + -other

    __rsub__ = __sub__

    def __eq__(self, other):
        return self.start == other.start

    def __lt__(self, other):
        return self.start < other.start

    def __contains__(self, other):
        return self.start <= other <= self.end

    def __str__(self):
        return f"{type(self).__name__}({self.start}, {self.end})"


WeekType = Union["Week", str, dt.date, None]


class Week(DateRange):
    def __init__(self, start: WeekType, allow_error=False):
        if isinstance(start, type(self)):
            start = start.start
        if isinstance(start, str):
            try:
                start = dt.datetime.strptime(start, "%Y-%m-%d")
            except ValueError:
                if not allow_error:
                    raise
                start = None
        if start is None:
            start = now()
        if isinstance(start, dt.datetime):
            start = start.date()
        start -= dt.timedelta(start.weekday())
        super().__init__(start, start + dt.timedelta(weeks=1, days=-1))

    @classmethod
    def get_current(cls):
        return cls(None)

    def __str__(self):
        return self.start.strftime("%Y-%m-%d")


class DateManager(models.Manager):
    def get_for_week(self, week: WeekType, allow_error=False):
        week = Week(week, allow_error)
        return self.filter(start_date__gte=week.start, start_date__lte=week.end)

    def get_for_current_week(self):
        return self.get_for_week(Week.get_current())


class Config(SingletonModel):
    official_name = models.CharField(max_length=100)
    logo = models.ImageField()


class OccurrencesList(list["Date"]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ended = True

    @classmethod
    def from_iterable(cls, iterable, limit=20):
        iterable = iter(iterable)
        ret = cls()
        for _ in range(limit):
            try:
                ret.append(next(iterable))
            except StopIteration:
                return ret
        ret.ended = False
        return ret


class HasOccurrences:
    def get_occurrences(self, start: dt.date | None = None, end: dt.date | None = None, inc=False, limit=20):
        """Retourne toutes les occurrences d'un événement récurrent."""
        if not start:
            start = Week.get_current().start

        if isinstance(start, DateRange):
            week = start
            start = week.start
            end = week.end
            inc = True

        if isinstance(start, dt.date):
            start = date_to_datetime(start)
        if isinstance(end, dt.date):
            end = date_to_datetime(end)

        def real_get_occurrences():
            for occurrence in self._get_occurrences(start, end):
                if occurrence.contains(start, end, inc):
                    yield occurrence

        return OccurrencesList.from_iterable(real_get_occurrences(), limit)

    def _get_occurrences(self, start: dt.datetime, end: dt.datetime | None) -> Generator["Date", None, None]:
        if not hasattr(self, "recurrence"):
            raise NotImplementedError(
                "To be able to use the default implementation of _get_occurrences, there must be "
                + f"a recurrence attribute on the {type(self).__name__} class. "
                + "Please add one or override _get_occurrences."
            )

        occurrences_list = self.recurrence.to_dateutil_rruleset(start)
        for item in (start, end):
            if item and item in occurrences_list._rdate:
                occurrences_list._rdate.remove(item)
        for occurrence in occurrences_list:
            if start and occurrence < start:
                continue
            if end and occurrence > end:
                break
            yield Date(event=self, start_date=occurrence.date())


class Date(HasOccurrences, models.Model):
    objects = DateManager()

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
        if self.start_time and self.end_time and self.end_time < self.start_time:
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
        return None

    @end_time.setter
    def end_time(self, value: dt.time | None):
        self._end_time = value

    @property
    def start(self) -> dt.date:
        if self.start_time is None:
            return self.start_date
        return dt.datetime.combine(self.start_date, self.start_time, get_current_timezone())

    @property
    def end(self) -> dt.date | None:
        if self.end_time is None:
            return self.end_date
        return dt.datetime.combine(self.end_date, self.end_time, get_current_timezone())

    @property
    def duration(self) -> dt.timedelta:
        """Returns the duration of the occurrence as a timedelta."""
        return self.end - self.start

    def __str__(self):
        return f"{self.title} on {format_date_or_time(self.start, self.end, year=getattr(self, '_display_year', False))}"

    def contains(self, start: dt.date | None = None, end: dt.date | None = None, inc=False):
        self_start = date_to_datetime(self.start)
        self_end = date_to_datetime(self.end)
        start = date_to_datetime(start) if start else None
        end = date_to_datetime(end) if end else None
        if start and (self_start < start if inc else self_start <= start):
            return False
        if end and (self_end > end if inc else self_end >= end):
            return False
        return True

    def _get_occurrences(self, *args, **kwargs):
        return [self]


class Recurrence(HasOccurrences, models.Model):
    title = models.CharField(max_length=200)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    recurrence = RecurrenceField()

    def clean(self):
        self.occurrences = self.get_occurrences()

    def __str__(self):
        return self.title


class FixedFeast(HasOccurrences, models.Model):
    name = models.CharField(max_length=200)
    recurrence = RecurrenceField()


class MovableFeast(HasOccurrences, models.Model):
    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=200)

    def _get_occurrences(self, start: dt.datetime, end: dt.datetime | None):
        if self.slug not in default_translations:
            return  # avoid iterating until the end of the date range (year 10000)
        start = start.date()
        end = end.date() if end else None
        liturgical_year = get_liturgical_year(start)
        ended = False
        while not ended:
            for date, (slug, params) in get_movable_feasts_for(liturgical_year).items():
                if date < start:
                    continue
                if end and date > end:
                    ended = True
                    break
                if slug != self.slug:
                    continue
                if "n" in params:
                    params["ord"] = ordinal(params["n"])
                yield Date(
                    _title=Template(self.display_name or default_translations[slug]).substitute(params),
                    start_date=date,
                )
            liturgical_year += 1
