from django.contrib import admin
from .models import PotFactory, Pot, PotApplication, PotPayout, PotPayoutChallenge, PotPayoutChallengeAdminResponse

@admin.register(PotFactory)
class PotFactoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'deployed_at')
    search_fields = ('id', 'owner__id')

@admin.register(Pot)
class PotAdmin(admin.ModelAdmin):
    list_display = ('id', 'pot_factory', 'deployer', 'deployed_at', 'name')
    search_fields = ('id', 'name', 'deployer__id')
    list_filter = ('deployed_at',)

@admin.register(PotApplication)
class PotApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'pot', 'applicant', 'status', 'submitted_at')
    search_fields = ('pot__id', 'applicant__id')
    list_filter = ('status', 'submitted_at')

@admin.register(PotPayout)
class PotPayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'pot', 'recipient', 'amount', 'paid_at')
    search_fields = ('pot__id', 'recipient__id')
    list_filter = ('paid_at',)

@admin.register(PotPayoutChallenge)
class PotPayoutChallengeAdmin(admin.ModelAdmin):
    list_display = ('id', 'challenger', 'pot', 'created_at')
    search_fields = ('challenger__id', 'pot__id')
    list_filter = ('created_at',)

@admin.register(PotPayoutChallengeAdminResponse)
class PotPayoutChallengeAdminResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'challenge', 'admin', 'created_at', 'resolved')
    search_fields = ('admin__id', 'challenge__id')
    list_filter = ('created_at', 'resolved')
