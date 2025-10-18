from django.apps import AppConfig
from django.db.models.signals import post_migrate

from .migration_helpers import create_movable_feasts


class DatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dates"

    def ready(self):
        post_migrate.connect(
            create_movable_feasts,
            dispatch_uid="dates.migration_helpers.create_movable_feasts",
        )
