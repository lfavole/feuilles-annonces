from django.urls import path
from .pdfs.feuille_annonces import FeuilleAnnonces
from .views import edit, export

urlpatterns = [
    path("edit", edit),
    path("export", export),
    path("feuille-annonces/<str:week>", FeuilleAnnonces.as_view()),
    path("feuille-annonces", FeuilleAnnonces.as_view()),
    path(".well-known/caldav", export),
]
