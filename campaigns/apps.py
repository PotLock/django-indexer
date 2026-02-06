from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campaigns"
    verbose_name = "Campaigns"

    def ready(self):
        # Import signal handlers if any
        pass
