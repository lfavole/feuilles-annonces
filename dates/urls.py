import datetime as dt
import re

from django.urls import include, path
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.response import Response

from .models import Celebrant, Date, Recurrence, Week
from .pdfs.feuille_annonces import FeuilleAnnonces
from .views import edit, export

class CelebrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Celebrant
        fields = ["id", "name", "abbreviation"]

class CelebrantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.DjangoModelPermissions]
    queryset = Celebrant.objects.all()
    serializer_class = CelebrantSerializer

class RecurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurrence
        fields = ["id", "title", "start_time", "end_time", "recurrence"]

class PublicDateSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour le grand public."""
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if re.match(r"^(Messe|Célébration|Confession)s?\b", representation["title"]):
            representation["celebrant"] = instance.celebrant.name if instance.celebrant else None

        return representation

    class Meta:
        model = Date
        fields = ["id", "title", "start_date", "start_time", "end_date", "end_time", "note", "cancelled"]

class DateSerializer(serializers.ModelSerializer):
    # Lecture : renvoie les détails de la récurrence parente
    event_details = RecurrenceSerializer(source="event", read_only=True)

    # Écriture : permet de lier une Date à une Recurrence via son ID
    event = serializers.PrimaryKeyRelatedField(
        queryset=Recurrence.objects.all(),
        required=False,
        allow_null=True
    )

    title = serializers.CharField(source="_title", allow_blank=True)
    start_time = serializers.TimeField(source="_start_time", required=False, allow_null=True)
    end_date = serializers.DateField(source="_end_date", required=False, allow_null=True)
    end_time = serializers.TimeField(source="_end_time", required=False, allow_null=True)

    class Meta:
        model = Date
        fields = ["id", "ignored", "event", "event_details", "title", "start_date", "start_time", "end_date", "end_time", "celebrant", "note", "cancelled"]

class DateViewSet(viewsets.ModelViewSet):
    queryset = Date._base_manager.all()
    serializer_class = DateSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().select_related("celebrant")

    def get_serializer_class(self):
        # Si l'utilisateur est membre du staff, on donne accès au Serializer complet
        if self.request.user and self.request.user.is_staff:
            return DateSerializer

        # Sinon (anonyme ou utilisateur classique), on renvoie la version publique
        return PublicDateSerializer

    def list(self, request, *args, **kwargs):
        # 1. Récupération des paramètres de filtrage (ISO format: YYYY-MM-DD)
        try:
            start = dt.datetime.fromisoformat(request.query_params.get("start", ""))
            end = dt.datetime.fromisoformat(request.query_params.get("end", ""))
        except ValueError:
            start = Week.get_current()
            end = None

        # 2. Appel à votre manager personnalisé qui gère HasOccurrences
        # La fonction get_occurrences renvoie un mélange d'objets en DB
        # et d'objets Date instanciés à la volée pour les récurrences.
        events = Recurrence.objects.all()
        result_list = [*self.get_queryset()]
        occurrences = [*result_list]
        for event in events:
            for occurrence in event.get_occurrences(start, end):
                if any(
                    item.event == occurrence.event and item.start_date == occurrence.start_date
                    for item in result_list
                ):
                    continue
                occurrences.append(occurrence)

        # 3. Sérialisation de la liste d'objets (réels + virtuels)
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(occurrences, many=True, context={'request': request})

        return Response(serializer.data)

class RecurrenceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.DjangoModelPermissions]
    queryset = Recurrence.objects.all()
    serializer_class = RecurrenceSerializer

router = routers.DefaultRouter()
router.register("celebrants", CelebrantViewSet)
router.register("dates", DateViewSet)
router.register("recurrences", RecurrenceViewSet)

urlpatterns = [
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/", include(router.urls)),
    path("edit", edit),
    path("export", export),
    path("feuille-annonces/<str:week>", FeuilleAnnonces.as_view()),
    path("feuille-annonces", FeuilleAnnonces.as_view()),
    path(".well-known/caldav", export),
]
