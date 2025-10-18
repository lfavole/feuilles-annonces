from django.contrib.humanize.templatetags.humanize import ordinal as django_ordinal
from django.utils.safestring import mark_safe
from django.utils.translation import get_language


def ordinal(value):
    if get_language().split("-")[0] == "fr":
        try:
            value = int(value)
        except (TypeError, ValueError):
            return value
        if value < 0:
            return str(value)
        return mark_safe(f"{value}<sup>{'er' if value == 1 else 'e'}</sup>")
    return django_ordinal(value)
