from django.urls import path

from .pdfs.feuille_annonces import FeuilleAnnonces
from .views import export

urlpatterns = [
    path("export", export),
    path("feuille-annonces/<str:week>", FeuilleAnnonces.as_view()),
    path("feuille-annonces", FeuilleAnnonces.as_view()),
    path(".well-known/caldav", export),
    path("", export),
]
