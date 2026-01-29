from django import forms
from django.utils.html import conditional_escape


def get_occurrences_form_for(occurrences):
    form = forms.Form()
    for occurrence in occurrences:
        form.fields[f"{occurrence.event.pk}_{occurrence.start_date.strftime('%Y%m%d')}"] = forms.BooleanField(label=conditional_escape(occurrence))
    return form
