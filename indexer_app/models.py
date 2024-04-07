from django.db import models
from django.utils.translation import gettext_lazy as _


class Account(models.Model):
    id = models.CharField(
        _("address"),
        primary_key=True,
        max_length=64,
        db_index=True,
        validators=[],
        help_text=_("On-chain account address."),
    )
    total_donations_received_usd = models.DecimalField(
        _("total donations received in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donations received in USD."),
    )
    total_donated_usd = models.DecimalField(
        _("total donated in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total donated in USD."),
    )
    total_matching_pool_allocations_usd = models.DecimalField(
        _("total matching pool allocations in USD"),
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total matching pool allocations in USD."),
    )
    donors_count = models.PositiveIntegerField(
        _("donors count"),
        default=0,
        help_text=_("Number of donors."),
    )

    # add Meta, properties & methods as necessary


class ListRegistrationStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    GRAYLISTED = "Graylisted", "Graylisted"
    BLACKLISTED = "Blacklisted", "Blacklisted"


class List(models.Model):
    id = models.AutoField(
        _("list id"),
        primary_key=True,
        help_text=_("List id."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="lists",
        null=False,
        help_text=_("List owner."),
    )
    name = models.CharField(
        _("name"),
        max_length=64,
        null=False,
        help_text=_("List name."),
    )
    description = models.TextField(
        _("description"),
        max_length=256,
        null=True,
        help_text=_("List description."),
    )
    cover_image_url = models.URLField(
        _("cover image url"),
        null=True,
        help_text=_("Cover image url."),
    )
    admin_only_registrations = models.BooleanField(
        _("admin only registrations"),
        null=False,
        help_text=_("Admin only registrations."),
    )
    default_registration_status = models.CharField(
        _("default registration status"),
        max_length=32,
        null=False,
        choices=ListRegistrationStatus.choices,
        help_text=_("Default registration status."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("List creation date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("List last update date."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_lists",
        help_text=_("List admins."),
    )

    class Meta:
        indexes = [
            models.Index(fields=["created_at", "updated_at"], name="idx_list_stamps")
        ]


class ListUpvote(models.Model):
    id = models.AutoField(
        _("upvote id"),
        primary_key=True,
        help_text=_("Upvote id."),
    )
    list = models.ForeignKey(
        List,
        on_delete=models.CASCADE,
        related_name="upvotes",
        null=False,
        help_text=_("List upvoted."),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="upvoted_lists",
        null=False,
        help_text=_("Account that upvoted the list."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Upvote creation date."),
    )


class ListRegistration(models.Model):
    id = models.AutoField(
        _("registration id"),
        primary_key=True,
        help_text=_("Registration id."),
    )
    list = models.ForeignKey(
        List,
        on_delete=models.CASCADE,
        related_name="registrations",
        null=False,
        help_text=_("List registered."),
    )
    registrant = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="registered_lists",
        null=False,
        help_text=_("Account that registered on the list."),
    )
    status = models.CharField(
        _("registration status"),
        max_length=32,
        null=False,
        choices=ListRegistrationStatus.choices,
        help_text=_("Registration status."),
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=False,
        help_text=_("Registration submission date."),
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("Registration last update date."),
    )
    registrant_notes = models.TextField(
        _("registrant notes"),
        max_length=1024,
        null=True,
        help_text=_("Registrant notes."),
    )
    admin_notes = models.TextField(
        _("admin notes"),
        max_length=1024,
        null=True,
        help_text=_("Admin notes."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=True,
        help_text=_("Transaction hash."),
    )

    class Meta:
        indexes = [models.Index(fields=["id", "status"], name="idx_list_id_status")]


class PotFactory(models.Model):
    id = models.OneToOneField(
        Account,
        primary_key=True,
        related_name="pot_factory",
        on_delete=models.CASCADE,
        help_text=_("Pot factory account ID."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_pot_factories",
        null=False,
        help_text=_("Pot factory owner."),
    )
    admins = models.ManyToManyField(
        Account,
        related_name="admin_pot_factories",
        help_text=_("Pot factory admins."),
    )
    whitelisted_deployers = models.ManyToManyField(
        Account,
        related_name="whitelisted_pot_factories",
        help_text=_("Pot factory whitelisted deployers."),
    )
    deployed_at = models.DateTimeField(
        _("deployed at"),
        null=False,
        help_text=_("Pot factory deployment date."),
    )
    source_metadata = models.JSONField(
        _("source metadata"),
        null=True,
        help_text=_("Pot factory source metadata."),
    )
    protocol_fee_basis_points = models.PositiveIntegerField(
        _("protocol fee basis points"),
        null=False,
        help_text=_("Pot factory protocol fee basis points."),
    )
    protocol_fee_recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_factories_protocol_fee_recipient",
        null=False,
        help_text=_("Pot factory protocol fee recipient."),
    )
    require_whitelist = models.BooleanField(
        _("require whitelist"),
        null=False,
        help_text=_("Require whitelist."),
    )


class Pot(models.Model):
    id = models.OneToOneField(
        Account,
        primary_key=True,
        related_name="pot",
        on_delete=models.CASCADE,
        help_text=_("Pot account ID."),
    )
    pot_factory = models.ForeignKey(
        PotFactory,
        on_delete=models.CASCADE,
        related_name="pots",
        null=False,
        help_text=_("Pot factory."),
    )
    deployer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="deployed_pots",
        null=False,
        help_text=_("Pot deployer."),
        db_index=True,
    )
    deployed_at = models.DateTimeField(
        _("deployed at"),
        null=False,
        help_text=_("Pot deployment date."),
        db_index=True,
    )
    source_metadata = models.JSONField(
        _("source metadata"),
        null=False,
        help_text=_("Pot source metadata."),
    )
    owner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="owned_pots",
        null=False,
        help_text=_("Pot owner."),
    )
    chef = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="chef_pots",
        null=True,
        help_text=_("Pot chef."),
    )
    name = models.TextField(
        _("name"),
        null=False,
        help_text=_("Pot name."),
    )
    description = models.TextField(
        _("description"),
        null=False,
        help_text=_("Pot description."),
    )
    max_approved_applicants = models.PositiveIntegerField(
        _("max approved applicants"),
        null=False,
        help_text=_("Max approved applicants."),
    )
    base_currency = models.CharField(
        _("base currency"),
        max_length=64,
        null=True,
        help_text=_("Base currency."),
    )
    application_start = models.DateTimeField(
        _("application start"),
        null=False,
        help_text=_("Pot application start date."),
    )
    application_end = models.DateTimeField(
        _("application end"),
        null=False,
        help_text=_("Pot application end date."),
    )
    matching_round_start = models.DateTimeField(
        _("matching round start"),
        null=False,
        help_text=_("Pot matching round start date."),
    )
    matching_round_end = models.DateTimeField(
        _("matching round end"),
        null=False,
        help_text=_("Pot matching round end date."),
    )
    registry_provider = models.CharField(
        _("registry provider"),
        max_length=64,
        null=True,
        help_text=_("Registry provider."),
    )
    min_matching_pool_donation_amount = models.CharField(
        _("min matching pool donation amount"),
        max_length=64,
        null=False,
        help_text=_("Min matching pool donation amount."),
    )
    sybil_wrapper_provider = models.CharField(
        _("sybil wrapper provider"),
        max_length=64,
        null=True,
        help_text=_("Sybil wrapper provider."),
    )
    custom_sybil_checks = models.CharField(
        _("custom sybil checks"),
        max_length=64,
        null=True,
        help_text=_("Custom sybil checks."),
    )
    custom_min_threshold_score = models.PositiveIntegerField(
        _("custom min threshold score"),
        null=True,
        help_text=_("Custom min threshold score."),
    )
    referral_fee_matching_pool_basis_points = models.PositiveIntegerField(
        _("referral fee matching pool basis points"),
        null=False,
        help_text=_("Referral fee matching pool basis points."),
    )
    referral_fee_public_round_basis_points = models.PositiveIntegerField(
        _("referral fee public round basis points"),
        null=False,
        help_text=_("Referral fee public round basis points."),
    )
    chef_fee_basis_points = models.PositiveIntegerField(
        _("chef fee basis points"),
        null=False,
        help_text=_("Chef fee basis points."),
    )
    total_matching_pool = models.CharField(
        _("total matching pool"),
        max_length=64,
        null=False,
        help_text=_("Total matching pool."),
    )
    total_matching_pool_usd = models.DecimalField(
        _("total matching pool in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Total matching pool in USD."),
    )
    matching_pool_balance = models.CharField(
        _("matching pool balance"),
        max_length=64,
        null=False,
        help_text=_("Matching pool balance."),
    )
    matching_pool_donations_count = models.PositiveIntegerField(
        _("matching pool donations count"),
        null=False,
        help_text=_("Matching pool donations count."),
    )
    total_public_donations = models.CharField(
        _("total public donations"),
        max_length=64,
        null=False,
        help_text=_("Total public donations."),
    )
    total_public_donations_usd = models.DecimalField(
        _("total public donations in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Total public donations in USD."),
    )
    public_donations_count = models.PositiveIntegerField(
        _("public donations count"),
        null=False,
        help_text=_("Public donations count."),
    )
    cooldown_end = models.DateTimeField(
        _("cooldown end"),
        null=True,
        help_text=_("Pot cooldown end date."),
    )
    cooldown_period_ms = models.PositiveIntegerField(
        _("cooldown period in ms"),
        null=False,
        help_text=_("Pot cooldown period in ms."),
    )
    all_paid_out = models.BooleanField(
        _("all paid out"),
        null=False,
        help_text=_("All paid out."),
    )
    protocol_config_provider = models.CharField(
        _("protocol config provider"),
        max_length=64,
        null=True,
        help_text=_("Protocol config provider."),
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["application_start", "application_end"],
                name="idx_application_period",
            ),
            models.Index(
                fields=["matching_round_start", "matching_round_end"],
                name="idx_matching_period",
            ),
        ]


class PotApplicationStatus(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    INREVIEW = "InReview", "InReview"


class PotApplication(models.Model):
    id = models.AutoField(
        _("application id"),
        primary_key=True,
        help_text=_("Application id."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="applications",
        null=False,
        help_text=_("Pot applied to."),
        db_index=True,
    )
    applicant = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_applications",
        null=False,
        help_text=_("Account that applied to the pot."),
        db_index=True,
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=True,
        help_text=_("Application message."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        null=False,
        choices=PotApplicationStatus.choices,
        help_text=_("Application status."),
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=False,
        help_text=_("Application submission date."),
        db_index=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        help_text=_("Application last update date."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )


class PotApplicationReview(models.Model):
    id = models.AutoField(
        _("review id"),
        primary_key=True,
        help_text=_("Review id."),
    )
    application = models.ForeignKey(
        PotApplication,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=False,
        help_text=_("Application reviewed."),
    )
    reviewer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_application_reviews",
        null=False,
        help_text=_("Account that reviewed the application."),
    )
    notes = models.TextField(
        _("notes"),
        max_length=1024,
        null=True,
        help_text=_("Review notes."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        null=False,
        choices=PotApplicationStatus.choices,
        help_text=_("Application status for this review."),
    )
    reviewed_at = models.DateTimeField(
        _("reviewed at"),
        null=False,
        help_text=_("Review date."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )


class PotPayout(models.Model):
    id = models.AutoField(
        _("payout id"),
        primary_key=True,
        help_text=_("Payout id."),
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payouts",
        null=False,
        help_text=_("Payout recipient."),
        db_index=True,
    )
    amount = models.CharField(
        _("amount"),
        max_length=64,
        null=False,
        help_text=_("Payout amount."),
    )
    amount_paid_usd = models.DecimalField(
        _("amount paid in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Payout amount in USD."),
    )
    ft = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="ft_pot_payouts",
        null=False,
        help_text=_("Payout FT."),
        db_index=True,
    )
    paid_at = models.DateTimeField(
        _("paid at"),
        null=False,
        help_text=_("Payout date."),
        db_index=True,
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )


class PotPayoutChallenge(models.Model):
    id = models.AutoField(
        _("challenge id"),
        primary_key=True,
        help_text=_("Challenge id."),
    )
    challenger = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payout_challenges",
        null=False,
        help_text=_("Payout challenger."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="challenges",
        null=False,
        help_text=_("Pot challenged."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Challenge creation date."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=False,
        help_text=_("Challenge message."),
    )


class PotPayoutChallengeAdminResponse(models.Model):
    id = models.AutoField(
        _("Admin response id"),
        primary_key=True,
        help_text=_("Admin response id."),
    )
    challenge = models.ForeignKey(
        PotPayoutChallenge,
        on_delete=models.CASCADE,
        related_name="admin_responses",
        null=False,
        help_text=_("Challenge responded to."),
    )
    admin = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="pot_payout_challenge_admin_responses",
        null=False,
        help_text=_("Admin that responded to the challenge."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        null=False,
        help_text=_("Admin response creation date."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=False,
        help_text=_("Admin response message."),
    )
    resolved = models.BooleanField(
        _("resolved"),
        null=False,
        help_text=_("Admin response resolution status."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )


class Donation(models.Model):
    id = models.AutoField(
        _("donation id"),
        primary_key=True,
        help_text=_("Donation id."),
    )
    donor = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="donations",
        null=False,
        help_text=_("Donor."),
        db_index=True,
    )
    total_amount = models.CharField(
        _("total amount"),
        max_length=64,
        null=False,
        help_text=_("Total amount."),
    )
    total_amount_usd = models.DecimalField(
        _("total amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Total amount in USD."),
    )
    net_amount = models.CharField(
        _("net amount"),
        max_length=64,
        null=False,
        help_text=_("Net amount."),
    )
    net_amount_usd = models.DecimalField(
        _("net amount in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Net amount in USD."),
    )
    ft = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="ft_donations",
        null=False,
        help_text=_("Donation FT."),
    )
    pot = models.ForeignKey(
        Pot,
        on_delete=models.CASCADE,
        related_name="donations",
        null=True,
        help_text=_("Donation pot."),
        db_index=True,
    )
    matching_pool = models.BooleanField(
        _("matching pool"),
        null=False,
        help_text=_("Matching pool."),
    )
    message = models.TextField(
        _("message"),
        max_length=1024,
        null=True,
        help_text=_("Donation message."),
    )
    donated_at = models.DateTimeField(
        _("donated at"),
        null=False,
        help_text=_("Donation date."),
        db_index=True,
    )
    recipient = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="received_donations",
        null=True,
        help_text=_("Donation recipient."),
    )
    protocol_fee = models.CharField(
        _("protocol fee"),
        max_length=64,
        null=False,
        help_text=_("Protocol fee."),
    )
    protocol_fee_usd = models.DecimalField(
        _("protocol fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Protocol fee in USD."),
    )
    referrer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="referral_donations",
        null=True,
        help_text=_("Donation referrer."),
    )
    referrer_fee = models.CharField(
        _("referrer fee"),
        max_length=64,
        null=False,
        help_text=_("Referrer fee."),
    )
    referrer_fee_usd = models.DecimalField(
        _("referrer fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Referrer fee in USD."),
    )
    chef = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="chef_donations",
        null=True,
        help_text=_("Donation chef."),
    )
    chef_fee = models.CharField(
        _("chef fee"),
        max_length=64,
        null=False,
        help_text=_("Chef fee."),
    )
    chef_fee_usd = models.DecimalField(
        _("chef fee in USD"),
        max_digits=20,
        decimal_places=2,
        null=True,
        help_text=_("Chef fee in USD."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )


class ActivityType(models.TextChoices):
    DONATE_DIRECT = "Donate_Direct", "Donate Direct"
    DONATE_POT_PUBLIC = "Donate_Pot_Public", "Donate Pot Public"
    DONATE_POT_MATCHING_POOL = "Donate_Pot_Matching_Pool", "Donate Pot Matching Pool"
    REGISTER = "Register", "Register"
    REGISTER_BATCH = "Register_Batch", "Register Batch"
    DEPLOY_POT = "Deploy_Pot", "Deploy Pot"
    PROCESS_PAYOUTS = "Process_Payouts", "Process Payouts"
    CHALLENGE_PAYOUT = "Challenge_Payout", "Challenge Payout"
    SUBMIT_APPLICATION = "Submit_Application", "Submit Application"
    UPDATE_POT_CONFIG = "Update_Pot_Config", "Update Pot Config"
    ADD_LIST_ADMIN = "Add_List_Admin", "Add List Admin"
    REMOVE_LIST_ADMIN = "Remove_List_Admin", "Remove List Admin"


class Activity(models.Model):
    id = models.AutoField(
        _("activity id"),
        primary_key=True,
        help_text=_("Activity id."),
    )
    signer = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="signed_activities",
        null=False,
        help_text=_("Signer."),
    )
    receiver = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="received_activities",
        null=False,
        help_text=_("Receiver."),
    )
    timestamp = models.DateTimeField(
        _("timestamp"),
        null=False,
        help_text=_("Activity timestamp."),
        db_index=True,
    )
    action_result = models.JSONField(
        _("action result"),
        null=True,
        help_text=_("Activity action result."),
    )
    tx_hash = models.CharField(
        _("transaction hash"),
        max_length=64,
        null=False,
        help_text=_("Transaction hash."),
    )
    type = models.CharField(
        _("type"),
        max_length=32,
        null=False,
        choices=ActivityType.choices,
        help_text=_("Activity type."),
    )


class TokenHistoricalData(models.Model):
    token_id = models.CharField(
        _("token id"),
        primary_key=True,
        max_length=64,
        db_index=True,
        help_text=_("Token id."),
    )
    last_updated = models.DateTimeField(
        _("last updated"),
        null=False,
        help_text=_("Last updated date."),
        db_index=True,
    )
    historical_price_usd = models.DecimalField(
        _("historical price USD"),
        max_digits=20,
        decimal_places=2,
        null=False,
        help_text=_("Historical price."),
    )
