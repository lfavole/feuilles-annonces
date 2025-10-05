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

from .forms import get_occurrences_form_for
from .models import Recurrence, Date

@admin.register(Recurrence)
class RecurrenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get_occurrences', self.admin_site.admin_view(self.get_occurrences), name='get_occurrences'),
        ]
        return custom_urls + urls

    def get_occurrences(self, request):
        """Retourne les occurrences d'un événement sous forme de JSON."""
        class TestForm(forms.ModelForm):
            class Meta:
                model = self.model
                fields = ["start_time", "_end_time", "recurrence"]

        form = TestForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"invalid": True, "errors": form.errors.get_json_data()}, status=500)
        recurrence: Recurrence = form.instance
        occurrences = recurrence.get_occurrences() if recurrence else []
        return JsonResponse({
            'occurrences': [
                [date.isoformat() if date else date for date in (occurrence.start, occurrence.end)]
                for occurrence in occurrences
            ],
            'ended': getattr(occurrences, "ended", True),
        })

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Affiche les occurrences sur la page de modification de l'événement."""
        event = self.get_object(request, object_id)
        occurrences = event.get_occurrences() if event else []
        extra_context = extra_context or {}
        extra_context['occurrences'] = occurrences
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def render_change_form(self, request, context, **kwargs):
        """Rendre le formulaire de changement avec les occurrences."""
        context['occurrences'] = context.get('occurrences', [])
        return super().render_change_form(request, context, **kwargs)


class WeekFilter(admin.SimpleListFilter):
    title = 'Week'
    parameter_name = 'week'

    def value(self):
        ret = self.used_parameters.get(self.parameter_name, "")
        if ret == "all":
            return None
        return ret

    def current_week(self):
        ret = timezone.now()
        ret -= timedelta(days=ret.weekday())
        return ret

    def week(self):
        if self.value() is None:
            return None
        ret = timezone.now()
        if self.value() != "":
            try:
                ret = timezone.datetime.strptime(self.value(), '%Y-%m-%d')
            except ValueError:
                pass
        ret -= timedelta(days=ret.weekday())
        return ret

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
        current_date = timezone.now().date()
        current_date -= timedelta(days=current_date.weekday())
        weeks = []
        for i in range(-5, 1):
            week_start = current_date + timedelta(weeks=i)
            weeks.append((week_start.strftime('%Y-%m-%d'), f'Week of {week_start.strftime("%Y-%m-%d")}'))
        return weeks

    def queryset(self, request, queryset):
        week_start = self.week()
        if week_start is None:
            return queryset
        week_end = week_start + timedelta(days=6)
        return queryset.filter(start_date__range=(week_start, week_end))


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
        current_week: datetime = cl.filter_specs[0].week() or cl.filter_specs[0].current_week()
        previous_week = current_week - timedelta(days=7)
        next_week = current_week + timedelta(days=7)
        ret.context_data['previous_week'] = previous_week.strftime('%Y-%m-%d')
        ret.context_data['previous_week_link'] = cl.get_query_string({self.list_filter[0].parameter_name: previous_week.strftime('%Y-%m-%d')})
        ret.context_data['current_week'] = current_week.strftime('%Y-%m-%d')
        ret.context_data['current_week_link'] = cl.get_query_string(remove=[self.list_filter[0].parameter_name])
        ret.context_data['next_week'] = next_week.strftime('%Y-%m-%d')
        ret.context_data['next_week_link'] = cl.get_query_string({self.list_filter[0].parameter_name: next_week.strftime('%Y-%m-%d')})

        # Get all events
        events = Recurrence.objects.all()
        occurrences = []
        for event in events:
            occurrences.extend(
                event.get_occurrences(
                    current_week,
                    current_week + timedelta(weeks=1, days=-1),
                    inc=True,
                )
            )
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
