from datetime import datetime, timedelta

from django.contrib import admin
from django import forms
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.formats import get_format
from django.utils.translation import gettext_lazy as _
from solo.admin import SingletonModelAdmin

from .forms import get_occurrences_form_for
from .models import Config, Date, FixedFeast, MovableFeast, Recurrence, Week


class OccurrencesMixin:
    def get_urls(self):
        return [
            path("get_occurrences", self.admin_site.admin_view(self._get_occurrences)),
        ] + super().get_urls()

    def _get_occurrences(self, request):
        """Retourne les occurrences d'un événement sous forme de JSON."""
        Form = self.get_form(request, change=True)
        Form.validate_unique = lambda *_, **__: None
        form = Form(request.POST)
        if not form.is_valid():
            return JsonResponse({"invalid": True, "errors": form.errors.get_json_data()}, status=400)
        obj = form.instance
        try:
            occurrences = obj.get_occurrences(Week.get_current().start) if obj else []
        except (KeyError, ValueError) as err:
            if str(err) == "year 10000 is out of range":
                raise
            return JsonResponse({"invalid": True, "errors": f"{type(err).__name__}: {err}"}, status=400)
        if occurrences and occurrences[0].start.year != occurrences[-1].end.year:
            for occurrence in occurrences:
                occurrence._display_year = True
        return JsonResponse({
            "occurrences": [str(occurrence) for occurrence in occurrences],
            "ended": getattr(occurrences, "ended", True),
        })


@admin.register(Recurrence)
class RecurrenceAdmin(OccurrencesMixin, admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Affiche les occurrences sur la page de modification de l'événement."""
        event = self.get_object(request, object_id)
        occurrences = event.get_occurrences() if event else []
        extra_context = extra_context or {}
        extra_context['occurrences'] = occurrences
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


class WeekFilter(admin.SimpleListFilter):
    title = 'Week'
    parameter_name = 'week'

    def value(self):
        ret = self.used_parameters.get(self.parameter_name, "")
        if ret == "all":
            return None
        return ret

    def week(self):
        if self.value() is None:
            return None
        return Week(self.value(), True)

    def choices(self, changelist):
        first = True
        for choice in super().choices(changelist):
            if first:
                choice["query_string"] = changelist.get_query_string({self.parameter_name: "all"})
            yield choice
            if first:
                yield {
                    "selected": self.value() == "",
                    "query_string": changelist.get_query_string(remove=[self.parameter_name]),
                    "display": _("Current week"),
                }
            first = False

    def lookups(self, request, model_admin):
        current_week = Week.get_current()
        weeks = []
        for i in range(-5, 1):
            week = current_week + timedelta(weeks=i)
            weeks.append((week.start.strftime('%Y-%m-%d'), f'Week of {week.start.strftime("%Y-%m-%d")}'))
        return weeks

    def queryset(self, request, queryset):
        week = self.week()
        if week is None:
            return queryset
        return queryset.filter(start_date__range=(week.start, week.end))


@admin.register(Date)
class DateAdmin(admin.ModelAdmin):
    list_filter = (WeekFilter,)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add_dates', self.admin_site.admin_view(self.add_dates), name='add_dates'),
        ]
        return custom_urls + urls

    def add_dates(self, request):
        dates: list[Date] = []
        for date_to_add in request.POST:
            recurrence_id, sep, date_str = date_to_add.partition("_")
            if not sep:
                continue

            try:
                date_obj = timezone.datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                raise Http404

            recurrence = get_object_or_404(Recurrence, pk=recurrence_id)

            try:
                date = next(iter(recurrence.get_occurrences(date_obj, inc=True)))
            except StopIteration:
                raise Http404

            dates.append(date)


        Date.objects.bulk_create(dates)

        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"success": True})

        return redirect("admin:dates_date_changelist")

    def changelist_view(self, *args, **kwargs):
        ret = super().changelist_view(*args, **kwargs)

        # If we're not on the objects list (e.g. the delete page), stop here
        if "cl" not in getattr(ret, "context_data", {}):
            return ret

        ret.context_data['input_format'] = get_format("DATE_INPUT_FORMATS")[0]
        cl = ret.context_data["cl"]
        current_week: datetime = cl.filter_specs[0].week() or Week.get_current()
        previous_week = current_week - timedelta(days=7)
        next_week = current_week + timedelta(days=7)
        ret.context_data['previous_week'] = str(previous_week)
        ret.context_data['previous_week_link'] = cl.get_query_string({self.list_filter[0].parameter_name: str(previous_week)})
        ret.context_data['current_week'] = str(current_week)
        ret.context_data['current_week_link'] = cl.get_query_string(remove=[self.list_filter[0].parameter_name])
        ret.context_data['next_week'] = str(next_week)
        ret.context_data['next_week_link'] = cl.get_query_string({self.list_filter[0].parameter_name: str(next_week)})

        # Get all events
        events = Recurrence.objects.all()
        occurrences = []
        for event in events:
            occurrences.extend(event.get_occurrences(current_week))
        result_list = ret.context_data["cl"].result_list

        occurrences = [
            occurrence
            for occurrence in occurrences
            if not any(
                result.event == occurrence.event and result.start_date == occurrence.start_date
                for result in result_list
            )
        ]
        occurrences.sort(key=lambda occurrence: (occurrence.start_date, occurrence.start_time))
        ret.context_data["occurrences_form"] = get_occurrences_form_for(occurrences)

        # Add the occurrences to the context
        ret.context_data['occurrences'] = occurrences

        # Call the parent changelist_view method with the updated context
        return ret


@admin.register(Config)
class ConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(FixedFeast)
class FixedFeastAdmin(OccurrencesMixin, admin.ModelAdmin):
    pass


@admin.register(MovableFeast)
class MovableFeastAdmin(OccurrencesMixin, admin.ModelAdmin):
    pass
