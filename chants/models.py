from django.db import models

# Create your models here.

class SongCategory(models.Model):
    """Specific table for song categories."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Song(models.Model):
    """Represents a song in the library."""
    title = models.CharField(max_length=255)
    category = models.ForeignKey(SongCategory, on_delete=models.PROTECT, related_name='songs')
    chorus = models.TextField(blank=True)
    verses = models.JSONField(default=list)
    chorus_after = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Sheet(models.Model):
    """Represents a liturgy sheet (Mass)."""
    name = models.CharField(max_length=255)
    date = models.DateField()
    header_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.date})"

class SheetBlock(models.Model):
    """Represents a block within a sheet."""
    BLOCK_TYPES = [('text', 'Text'), ('song', 'Song')]
    sheet = models.ForeignKey(Sheet, related_name='blocks', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPES)
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    song = models.ForeignKey(Song, null=True, blank=True, on_delete=models.SET_NULL)
    selected_verses = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order']
