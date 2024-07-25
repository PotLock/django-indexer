from django.db import models
from django.utils.translation import gettext_lazy as _


class BlockHeight(models.Model):
    id = models.IntegerField(
        _("blockheight cache save"),
        primary_key=True,
        help_text=_("saved block height."),
    )
    block_height = models.IntegerField(
        _("blockheight value"),
        help_text=_("the last blockheight saved to db."),
    )
    block_timestamp = models.DateTimeField(
        _("block timestamp"),
        help_text=_("date equivalent of the block height."),
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("block height last update at."),
    )