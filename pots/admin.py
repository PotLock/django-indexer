from django import forms
from django.contrib import admin

from accounts.models import Account

from .models import (
    Pot,
    PotApplication,
    PotApplicationReview,
    PotFactory,
    PotPayout,
    PotPayoutChallenge,
    PotPayoutChallengeAdminResponse,
)


class PotFactoryForm(forms.ModelForm):
    class Meta:
        model = PotFactory
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(PotFactoryForm, self).__init__(*args, **kwargs)
        # Ensure self.instance is available before accessing it
        if self.instance.pk:
            # Set the queryset for the admins field to only include relevant accounts
            self.fields["admins"].queryset = self.instance.admins.all()
            # Set the queryset for the whitelisted_deployers field to only include relevant accounts
            self.fields["whitelisted_deployers"].queryset = (
                self.instance.whitelisted_deployers.all()
            )


@admin.register(PotFactory)
class PotFactoryAdmin(admin.ModelAdmin):
    form = PotFactoryForm
    list_display = ("id", "owner", "deployed_at")
    search_fields = ("id", "owner__id")

    def get_form(self, request, obj=None, **kwargs):
        form = super(PotFactoryAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            form.base_fields["admins"].queryset = obj.admins.all()
            form.base_fields["whitelisted_deployers"].queryset = (
                obj.whitelisted_deployers.all()
            )
        return form


class PotForm(forms.ModelForm):
    class Meta:
        model = Pot
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(PotForm, self).__init__(*args, **kwargs)
        # Ensure self.instance is available before accessing it
        if self.instance.pk:
            # Set the queryset for the admins field to only include relevant accounts
            self.fields["admins"].queryset = self.instance.admins.all()


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    form = PotForm
    list_display = ("id", "pot_factory", "deployer", "deployed_at", "name")
    search_fields = ("id", "name", "deployer__id")
    list_filter = ("deployed_at",)

    def get_form(self, request, obj=None, **kwargs):
        form = super(PotAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            form.base_fields["admins"].queryset = obj.admins.all()
        return form


@admin.register(PotApplication)
class PotApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "pot", "applicant", "status", "submitted_at")
    search_fields = ("pot__id", "applicant__id")
    list_filter = ("status", "submitted_at")


@admin.register(PotApplicationReview)
class PotApplicationReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "reviewer",
        "notes",
        "status",
        "reviewed_at",
        "tx_hash",
    )
    search_fields = ("application__id", "reviewer__id")
    list_filter = ("status", "reviewed_at")


@admin.register(PotPayout)
class PotPayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "pot", "recipient", "amount", "paid_at")
    search_fields = ("pot__id", "recipient__id")
    list_filter = ("paid_at",)


@admin.register(PotPayoutChallenge)
class PotPayoutChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "challenger", "pot", "created_at")
    search_fields = ("challenger__id", "pot__id")
    list_filter = ("created_at",)


@admin.register(PotPayoutChallengeAdminResponse)
class PotPayoutChallengeAdminResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "pot", "admin", "created_at", "resolved")
    search_fields = ("admin__id", "challenge__id")
    list_filter = ("created_at", "resolved")
