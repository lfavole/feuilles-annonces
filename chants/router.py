from django.db.models import Count
from rest_framework import serializers, viewsets

from .models import Sheet, SheetBlock, Song, SongCategory

class SongCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SongCategory
        fields = '__all__'

class SongSerializer(serializers.ModelSerializer):
    usage_count = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Song
        fields = '__all__'

class SheetBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = SheetBlock
        fields = ['id', 'sheet', 'order', 'block_type', 'title', 'content', 'song', 'selected_verses']

class SheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sheet
        fields = ['id', 'name', 'date', 'header_info']

class SongCategoryViewSet(viewsets.ModelViewSet):
    queryset = SongCategory.objects.all()
    serializer_class = SongCategorySerializer

class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer

    def get_queryset(self):
        # Annotate with usage count for the library view
        return super().get_queryset().annotate(usage_count=Count('sheetblock'))

class SheetViewSet(viewsets.ModelViewSet):
    queryset = Sheet.objects.all()
    serializer_class = SheetSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Handle /api/sheets/?id=X
        sheet_id = self.request.query_params.get('id')
        if sheet_id is not None:
            queryset = queryset.filter(id=sheet_id)
        return queryset

class SheetBlockViewSet(viewsets.ModelViewSet):
    queryset = SheetBlock.objects.all().select_related('song')
    serializer_class = SheetBlockSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Handle /api/blocks/?sheet=X to get blocks for a specific sheet
        sheet_id = self.request.query_params.get('sheet')
        if sheet_id is not None:
            queryset = queryset.filter(sheet__id=sheet_id)
        # Support the 'q' parameter for global search
        query_param = self.request.query_params.get('q')
        if query_param:
            queryset = queryset.filter(
                Q(title__icontains=query_param) |
                Q(chorus__icontains=query_param) |
                Q(verses__icontains=query_param)
            )
        return queryset

def register(router):
    router.register("blocks", SheetBlockViewSet)
    router.register("categories", SongCategoryViewSet)
    router.register("songs", SongViewSet)
    router.register("sheets", SheetViewSet)
