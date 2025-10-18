from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS

from .liturgical_calendar import default_translations


def create_movable_feasts(
    app_config: AppConfig,
    verbosity=2,
    using=DEFAULT_DB_ALIAS,
    **_kwargs,
):
    """
    Automatically creates the default movable feasts.
    """
    if app_config.name != "dates":
        return

    MovableFeast = app_config.get_model("MovableFeast")  # type: ignore
    movable_feasts = [
        MovableFeast(slug=key, display_name=value) for key, value in default_translations.items()
    ]
    MovableFeast.objects.bulk_create(movable_feasts, ignore_conflicts=True)
