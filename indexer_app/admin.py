from django.contrib import admin
from .models import BlockHeight

@admin.register(BlockHeight)
class BlockHeightAdmin(admin.ModelAdmin):
    list_display = ('id', 'block_height', 'updated_at')
    ordering = ('-updated_at',)
