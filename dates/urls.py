from django.urls import path
from .views import export

urlpatterns = [
    path("export", export),
    path(".well-known/caldav", export),
    path("", export),
]
