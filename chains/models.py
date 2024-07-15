from django.db import models
from django_extensions.db.fields import AutoSlugField


class Chain(models.Model):
    ############################
    # BLOCKCHAIN MODEL FIELDS
    ############################

    # GENERAL
    name = models.CharField(
        max_length=32, unique=True, blank=False, null=False, db_index=True
    )
    name_slug = AutoSlugField(
        populate_from=("name",),
        max_length=32,
        unique=True,
        blank=False,
        null=False,
        db_index=True,
    )

    # URLS
    rpc_url = models.URLField()
    explorer_url = models.URLField()

    # EVM
    evm_compat = models.BooleanField(null=False, blank=False)
    evm_chain_id = models.IntegerField(null=True, blank=True, db_index=True)

    ############################
    # META
    ############################
    class Meta:
        # default record ordering
        ordering = ("name",)

        constraints = [
            # if an evm then the evm_chain_id id must be set otherwise should be null
            models.CheckConstraint(
                name="evm_chain_id_check",
                check=models.Q(evm_compat=True, evm_chain_id__isnull=False)
                | models.Q(evm_compat=False, evm_chain_id__isnull=True),
            ),
        ]

    def __str__(self):
        return self.name
