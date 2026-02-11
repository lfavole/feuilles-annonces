from django import forms
from django.utils.safestring import mark_safe

class SongEditorWidget(forms.Widget):
    template_name = "admin/widgets/song_editor_widget.html"

    class Media:
        css = {"all": ("chants/song-editor.css",)}
        js = (
            "chants/song-editor.js",
            mark_safe('<script src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js" defer></script>'),
        )
