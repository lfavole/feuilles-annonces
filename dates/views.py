import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from icalendar import Alarm, Calendar, Event

from .models import Recurrence as StoredEvent, Date, Week
from .pdfs.feuille_annonces import FeuilleAnnonces

# Create your views here.

@login_required
def edit(request):
    return render(request, "dates/edit.html")

@csrf_exempt
@require_http_methods(["GET", "PROPFIND"])
def export(request):
    print(request.headers["User-Agent"])

    if request.method == "PROPFIND":
        return HttpResponse("""\
<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
    <D:response>
        <D:href>/export</D:href>
        <D:propstat>
            <D:prop>
                <D:displayname>Calendrier caté</D:displayname>
                <D:resourcetype><D:collection/></D:resourcetype>
            </D:prop>
            <D:status>HTTP/1.1 200 OK</D:status>
        </D:propstat>
    </D:response>
</D:multistatus>
""", content_type="application/xml")

    events = StoredEvent.objects.all()
    occurrences: list[Date] = []
    for event in events:
        occurrences.extend(event.get_occurrences(Week.get_current()))

    now = datetime.datetime.now()

    cal = Calendar()
    cal.calendar_name = "Calendrier caté"
    cal.description = cal.calendar_name
    cal.add("PRODID", f"-//Secteur paroissial de l'Embrunais et du Savinois//Espace caté {datetime.date.today().year} (https://github.com/lfavole/sitekt)//")  # FIXME
    cal.add("VERSION", "2.0")
    cal.add("X-WR-CALNAME", cal.calendar_name)
    cal.add("X-WR-CALDESC", cal.calendar_name)

    for i, occurrence in enumerate(occurrences, start=1):
        event = Event()
        event.add("summary", occurrence.event.title)
        event.add("DTSTAMP", now)
        event.uid = f"{occurrence.event.pk}_{i}"
        event.start = occurrence.start

        # Default to 1 hour duration, will not trigger on all-day events (1 hour < 1 day)
        event.end = occurrence.end or occurrence.start + datetime.timedelta(hours=1)

        # Add reminders
        # Reminder 1: 1 day before at 5 PM
        alarm1 = Alarm()
        alarm1.add("action", "DISPLAY")
        alarm1.add("description", f'"{occurrence.event.title}" commence demain' + (f" à {occurrence.start.time()}" if isinstance(occurrence.start, datetime.datetime) else ""))
        # 1 day before at 5 PM
        alarm1.TRIGGER = datetime.datetime.combine(occurrence.start, datetime.time(17, 0, 0)) - datetime.timedelta(days=1)
        event.add_component(alarm1)

        # Reminder 2: 15 minutes before (only if not an all-day event)
        if isinstance(occurrence.start, datetime.datetime):
            alarm2 = Alarm()
            alarm2.add("action", "DISPLAY")
            alarm2.add("description", f'"{occurrence.event.title}" commence dans 15 minutes')
            # 15 minutes before
            alarm2.add("trigger", occurrence.start - datetime.timedelta(minutes=15))
            event.add_component(alarm2)

        cal.add_component(event)

    cal.add_missing_timezones()

    return HttpResponse(cal.to_ical(), content_type="text/calendar")
