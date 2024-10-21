from django.db import models

from django.utils.translation import gettext_lazy as _

from datetime import datetime

from base.logging import logger

from accounts.models import Account
from pots.models import PotApplication
from tokens.models import Token

# Create your models here.


class ProjectStatus(models.TextChoices):
    NEW = "NEW", _("New")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    COMPLETED = "COMPLETED", _("Completed")


class ProjectContact(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

class ProjectContract(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    contract_address = models.CharField(max_length=255)

class ProjectRepository(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=255)
    url = models.URLField(max_length=200)


class ProjectFundingHistory(models.Model):
    id = models.AutoField(primary_key=True)
    source = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    denomination = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    

class Project(models.Model):
    id = models.AutoField(primary_key=True)
    on_chain_id =models.IntegerField(
        _("contract project id"),
        null=False,
        unique=True,
        help_text=_("Project id in contract"),
    )
    image_url = models.URLField(max_length=200)
    video_url = models.URLField(max_length=200)
    name = models.CharField(max_length=255)
    overview = models.TextField()
    owner = models.ForeignKey(Account, related_name='owned_projects', on_delete=models.CASCADE)
    payout_address = models.ForeignKey(Account, related_name='payout_projects', on_delete=models.CASCADE)
    contacts = models.ManyToManyField(
        ProjectContact,
        related_name="contact_lists",
        help_text=_("project contacts."),
    )
    contracts = models.ManyToManyField(
        ProjectContract,
        related_name="contract_list",
        help_text=_("project contracts."),
    )
    team_members = models.ManyToManyField(
        Account,
        related_name="team_members",
        help_text=_("Project Team Member"),
    )
    repositories = models.ManyToManyField(
        ProjectRepository,
        related_name="repository_list",
        help_text=_("project repositories."),
    )
    status = models.CharField(max_length=50, choices=ProjectStatus.choices)
    submited_ms = models.BigIntegerField()
    updated_ms = models.BigIntegerField(null=True, blank=True)
    admins = models.ManyToManyField(
        Account,
        related_name="admin_projects",
        help_text=_("Project Admin"),
    )




class Round(models.Model):
    id = models.AutoField(
        _("round id"),
        primary_key=True,
        help_text=_("Round ID in DB (does not necessarily correspond to on-chain ID)."),
    )
    on_chain_id = models.IntegerField(
        _("contract round ID"),
        null=False,
        unique=True,
        help_text=_("Round ID in contract"),
    )
    factory_contract = models.ForeignKey(
        Account,
        related_name="spawned_rounds",
        on_delete=models.CASCADE,
        help_text=_("Round factory account ID."),
    )
    deployed_at = models.DateTimeField(
        _("deployed at"),
        null=False,
        help_text=_("Round deployment date."),
        db_index=True,
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_rounds",
        null=False,
        help_text=_("Round owner."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_rounds",
        help_text=_("Round admins."),
    )
    name = models.TextField(
        _("name"),
        null=False,
        help_text=_("Round name."),
    )
    description = models.TextField(
        _("description"),
        null=False,
        help_text=_("Round description."),
    )
    contacts = models.ManyToManyField(
        ProjectContact,
        related_name="round_contacts",
        help_text=_("Round contacts."),
    )
    expected_amount = models.CharField(
        _("expected amount"),
        null=False,
        help_text=_("Expected amount."),
    )
    
    base_currency = models.CharField(
        _("base currency"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Base currency."),
    )
    application_start = models.DateTimeField(
        _("application start"),
        null=True,
        help_text=_("Round application start date."),
    )
    application_end = models.DateTimeField(
        _("application end"),
        null=True,
        help_text=_("Round application end date."),
    )
    voting_start = models.DateTimeField(
        _("voting start"),
        null=False,
        help_text=_("Round voting start date."),
    )
    voting_end = models.DateTimeField(
        _("voting end"),
        null=False,
        help_text=_("Round voting end date."),
    )
    use_whitelist = models.BooleanField(
        _("use whitelist"),
        null=False,
        help_text=_("Use whitelist."),
    )
    use_vault = models.BooleanField(
        _("use vault"),
        null=False,
        help_text=_("Use vault."),
    )
    num_picks_per_voter = models.PositiveIntegerField(
        _("num picks per voter"),
        null=True,
        blank=True,
        help_text=_("Number of picks per voter."),
    )
    max_participants = models.PositiveIntegerField(
        _("max participants"),
        null=True,
        blank=True,
        help_text=_("Max participants."),
    )
    approved_projects = models.ManyToManyField(
        Project,
        related_name="rounds_approved_in",
        help_text=_("Projects Approved for round."),
    )
    allow_applications = models.BooleanField(
        _("allow applications"),
        null=False,
        help_text=_("Allow applications."),
    )
    is_video_required = models.BooleanField(
        _("is video required"),
        null=False,
        help_text=_("Is video required."),
    )
    cooldown_end = models.DateTimeField(
        _("cooldown end"),
        null=True,
        blank=True,
        help_text=_("Round cooldown end date."),
    )
    cooldown_period_ms = models.PositiveIntegerField(
        _("cooldown period in ms"),
        null=True,
        blank=True,
        help_text=_("Round cooldown period in ms."),
    )
    compliance_req_desc = models.TextField(
        _("compliance req desc"),
        null=False,
        help_text=_("Compliance req desc."),
    )
    compliance_period_ms = models.PositiveIntegerField(
        _("compliance period in ms"),
        null=True,
        blank=True,
        help_text=_("Compliance period in ms."),
    )
    compliance_end = models.DateTimeField(
        _("compliance end"),
        null=True,
        blank=True,
        help_text=_("Compliance end date."),
    )
    allow_remaining_dist = models.BooleanField(
        _("allow remaining dist"),
        null=False,
        help_text=_("Allow remaining dist."),
    )
    remaining_dist_address = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rounds_with_remaining_dist",
        help_text=_("Remaining dist address."),
    )
    remaining_dist_memo = models.CharField(
        _("remaining dist memo"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Remaining dist memo."),
    )
    remaining_dist_at_ms = models.BigIntegerField(
        _("remaining dist at ms"),
        null=True,
        blank=True,
        help_text=_("Remaining dist at ms."),
    )
    current_vault_balance = models.CharField(
        _("current vault balance"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Current vault balance."),
    )
    current_vault_balance_usd = models.DecimalField(
        _("current vault balance in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Current vault balance in USD."),
    )
    remaining_dist_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="remaining_dist_rounds",
        help_text=_("Account responsible for remaining distribution."),
    )
    referrer_fee_basis_points = models.PositiveIntegerField(
        _("referrer fee basis points"),
        null=True,
        blank=True,
        help_text=_("Referrer fee basis points."),
    )
    vault_total_deposits = models.CharField(
        _("vault total deposits"),
        null=True,
        help_text=_("Vault total deposits."),
    )
    vault_total_deposits_usd = models.DecimalField(
        _("vault total deposits in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Vault total deposits in USD."),
    )
    round_complete = models.DateTimeField(
        _("round complete"),
        null=True,
        blank=True,
        help_text=_("Round complete date."),
    )




    def update_vault_usd_equivalent(self):
        # first, see if there is a TokenHistoricalPrice within 1 day (or HISTORICAL_PRICE_QUERY_HOURS) of self.paid_at
        try:
            token = Token.objects.get(account_id="stellar")
            price_usd = token.fetch_usd_prices_common(datetime.now())
            if not price_usd:
                logger.info(
                    f"No USD price found for token {token.symbol} at {datetime.now()}"
                )
                return
            self.vault_total_deposits_usd = token.format_price(self.vault_total_deposits) * price_usd
            self.current_vault_balance_usd = token.format_price(self.current_vault_balance) * price_usd
            self.save()
            logger.info(
                f"Saved USD prices for round vault for round id: {self.id}"
            )
        except Exception as e:
            logger.error(f"Failed to calculate and  stellar vault USD prices: {e}")


class RoundDeposit(models.Model):
    id = models.AutoField(
        _("deposit id"),
        primary_key=True,
        help_text=_("Deposit id."),
    )
    on_chain_id = models.IntegerField(
        _("contract deposit ID"),
        null=False,
        unique=True,
        help_text=_("Deposit ID in contract"),
    )
    round = models.ForeignKey(
        Round,
        on_delete=models.CASCADE,
        related_name="deposits",
        null=False,
        help_text=_("Round that this deposit is for."),
        db_index=True,
    )
    depositor = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="round_deposits",
        null=False,
        help_text=_("Deposit maker."),
        db_index=True,
    )
    amount = models.CharField(
        _("amount"),
        null=False,
        help_text=_("Deposit amount."),
    )
    amount_in_usd = models.DecimalField(
        _("amount deposited in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Deposit amount in USD."),
    )
    protocol_fee = models.CharField(
        _("protocol_fee"),
        null=True,
        help_text=_("protocol fee amount."),
    )
    referrer_fee = models.CharField(
        _("referrer_fee"),
        null=True,
        help_text=_("referrer fee amount."),
    )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        related_name="round_deposits",
        null=True,
        help_text=_("Deposit token."),
    )
    deposit_at = models.DateTimeField(
        _("deposit at"),
        null=True,
        blank=True,
        help_text=_("Deposit date."),
        db_index=True,
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )

class Vote(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='votes')
    tx_hash = models.CharField(
        _("transaction hash"),
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )
    voted_at = models.DateTimeField()

    class Meta:
        unique_together = ('round', 'voter', 'voted_at')



class VotePair(models.Model):
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, related_name='pairs')
    pair_id = models.PositiveIntegerField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='vote_pairs')

    class Meta:
        unique_together = ('vote', 'pair_id')


class StellarEvent(models.Model):
    ledger_sequence = models.BigIntegerField()
    event_type = models.CharField(max_length=100)
    contract_id = models.CharField(max_length=56, null=True)
    data = models.JSONField()
    ingested_at = models.DateTimeField()
    transaction_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("Transaction hash."),
    )
    processed = models.BooleanField(default=False)