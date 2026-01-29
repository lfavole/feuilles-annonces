from dateutil.rrule import rruleset, rrulestr
from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .utils import serialize_rruleset

class RecurrenceWidget(forms.Textarea):
    def __init__(self, attrs=None, **kwargs):
        defaults = {'class': 'recurrence-widget'}
        if attrs is not None:
            defaults.update(attrs)
        super().__init__(defaults)

    def render(self, *args, **kwargs):
        return mark_safe(
            super().render(*args, **kwargs)
            + render_to_string("admin/dates/recurrence_widget.html")
        )

    class Media:
        css = {"all": ("dates/recurrence-widget.css",)}
        js = (
            "https://cdn.jsdelivr.net/npm/rrule@2/dist/es5/rrule.min.js",
            mark_safe('<script src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js" defer></script>'),
            "dates/recurrence-widget.js",
        )


class RecurrenceField(models.TextField):#OldRecurrenceField):#
    """
    Champ de modèle personnalisé pour stocker la récurrence au format RFC 5545.
    """
    # description = "Chaîne de récurrence compatible RFC 5545"

    def to_python(self, value):
        if value is None or isinstance(value, rruleset):
            return value
        value = super(RecurrenceField, self).to_python(value) or u''
        return value
        return rrulestr(value, forceset=True)

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)

    def get_prep_value(self, value):
        if not isinstance(value, str):
            value = serialize_rruleset(value)
        return value

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))

    # def __init__(self, *args, **kwargs):
    #     kwargs['max_length'] = 1000  # Sécurité pour les règles complexes
    #     super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = RecurrenceWidget
        return super().formfield(**kwargs)
