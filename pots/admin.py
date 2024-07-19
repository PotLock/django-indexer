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
        if (
            self.instance.pk
            and "admins" in self.fields
            and "whitelisted_deployers" in self.fields
        ):
            # Set the queryset for the admins field to only include relevant accounts
            self.fields["admins"].queryset = self.instance.admins.all()
            # Set the queryset for the whitelisted_deployers field to only include relevant accounts
            self.fields["whitelisted_deployers"].queryset = (
                self.instance.whitelisted_deployers.all()
            )


@admin.register(PotFactory)
class PotFactoryAdmin(admin.ModelAdmin):
    form = PotFactoryForm
    list_display = ("account", "owner", "deployed_at")
    search_fields = ("account", "owner__id")

    def get_form(self, request, obj=None, **kwargs):
        form = super(PotFactoryAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            try:
                form.base_fields["admins"].queryset = obj.admins.all()
                form.base_fields["whitelisted_deployers"].queryset = (
                    obj.whitelisted_deployers.all()
                )
            except KeyError:
                pass
        return form

    # def has_add_permission(self, request):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


class PotForm(forms.ModelForm):
    class Meta:
        model = Pot
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(PotForm, self).__init__(*args, **kwargs)
        # Ensure self.instance is available before accessing it
        if self.instance.pk and "admins" in self.fields:
            # Set the queryset for the admins field to only include relevant accounts
            self.fields["admins"].queryset = self.instance.admins.all()


@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    form = PotForm
    list_display = ("account", "pot_factory", "deployer", "deployed_at", "name")
    search_fields = ("account", "name", "deployer__id")
    list_filter = ("deployed_at",)

    def get_form(self, request, obj=None, **kwargs):
        form = super(PotAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            try:
                form.base_fields["admins"].queryset = obj.admins.all()
            except KeyError:
                pass
        return form

    # def has_add_permission(self, request):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


class PotApplicationAdminForm(forms.ModelForm):
    class Meta:
        model = PotApplication
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["applicant"].widget.attrs.update(
            {"data-placeholder": "Search by applicant ID..."}
        )


@admin.register(PotApplication)
class PotApplicationAdmin(admin.ModelAdmin):
    form = PotApplicationAdminForm
    list_display = ("id", "pot", "applicant", "status", "submitted_at")
    search_fields = ("pot__account", "applicant__id")
    list_filter = ("status", "submitted_at")
    autocomplete_fields = ["applicant"]

    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super().get_search_results(
    #         request, queryset, search_term
    #     )
    #     try:
    #         queryset |= self.model.objects.filter(applicant__id__icontains=search_term)
    #     except ValueError:
    #         pass
    #     return queryset, use_distinct

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     qs = qs.select_related("applicant")
    #     return qs

    # def get_label(self, obj):
    #     return f"{obj.applicant.id} - {obj.pot}"

    # get_label.short_description = "Application"

    # def has_add_permission(self, request):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(PotApplicationReview)
class PotApplicationReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application_applicant_id",  # Use the custom method here
        "reviewer",
        "notes",
        "status",
        "reviewed_at",
        "tx_hash",
    )
    search_fields = ("application__id", "reviewer__id")
    list_filter = ("status", "reviewed_at")
    autocomplete_fields = [
        "application",
        "reviewer",
    ]  # Enable autocomplete for the application field

    def application_applicant_id(self, obj):
        return obj.application.applicant.id

    application_applicant_id.short_description = "Application Applicant ID"

    # def has_add_permission(self, request):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(PotPayout)
class PotPayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "pot", "recipient", "amount", "amount_paid_usd", "paid_at")
    search_fields = ("pot__account", "recipient__id")
    list_filter = ("paid_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PotPayoutChallenge)
class PotPayoutChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "challenger", "pot", "message", "created_at")
    search_fields = ("challenger__id", "pot__account")
    list_filter = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PotPayoutChallengeAdminResponse)
class PotPayoutChallengeAdminResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "pot", "admin", "message", "created_at", "resolved")
    search_fields = ("admin__id", "challenge__id")
    list_filter = ("created_at", "resolved")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
