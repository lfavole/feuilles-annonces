from django.contrib import admin
from django import forms

from .models import Sheet, SheetBlock, Song, SongCategory
from .widgets import SongEditorWidget

# Register your models here.

class SheetBlockInline(admin.TabularInline):
    """Allows editing blocks directly inside the Sheet admin page."""
    model = SheetBlock
    extra = 1
    fields = ('order', 'block_type', 'title', 'song', 'selected_verses')

@admin.register(Sheet)
class SheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'created_at')
    list_filter = ('date',)
    search_fields = ('name',)
    inlines = [SheetBlockInline]

class SongAdminForm(forms.ModelForm):
    quick_input = forms.CharField(
        label="Contenu",
        widget=SongEditorWidget(),
        required=False,
    )

    class Media:
        css = {
            'all': ('admin/css/hide_song_fields.css',)
        }

    class Meta:
        model = Song
        fields = '__all__'

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    form = SongAdminForm
    list_display = ('title', 'category', 'chorus_after', 'created_at')
    list_filter = ('category', 'chorus_after')
    search_fields = ('title', 'chorus')

    fieldsets = (
        (None, {
            'fields': ('title', 'category', 'verses', 'chorus', 'chorus_after', 'quick_input'),
        }),
    )

@admin.register(SongCategory)
class SongCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
