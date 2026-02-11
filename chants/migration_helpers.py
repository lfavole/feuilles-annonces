def forward_refrain_pos(apps, schema_editor):
    """
    Migrates from refrain_pos (CharField) to chorus_after (BooleanField).
    'after' becomes True, everything else ('before', etc.) becomes False.
    """
    Song = apps.get_model('chants', 'Song')
    for song in Song.objects.all():
        song.chorus_after = (song.refrain_pos == 'after')
        song.save(update_fields=['chorus_after'])

def backward_refrain_pos(apps, schema_editor):
    """
    Migrates back from chorus_after (BooleanField) to refrain_pos (CharField).
    True becomes 'after', False becomes 'before'.
    """
    Song = apps.get_model('chants', 'Song')
    for song in Song.objects.all():
        song.refrain_pos = 'after' if song.chorus_after else 'before'
        song.save(update_fields=['refrain_pos'])
