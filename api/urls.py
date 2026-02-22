from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts.api import (
    AccountActivePotsAPI,
    AccountDetailAPI,
    AccountDonationsReceivedAPI,
    AccountDonationsSentAPI,
    AccountListRegistrationsAPI,
    AccountPayoutsReceivedAPI,
    AccountPotApplicationsAPI,
    AccountUpvotedListsAPI,
    AccountsListAPI,
    DonorsAPI,
)
from api.sync import (
    AccountSyncAPI,
    ListSyncAPI,
    ListRegistrationsSyncAPI,
    SingleRegistrationSyncAPI,
    ListDeleteSyncAPI,
    ListUpvoteSyncAPI,
    ListRemoveUpvoteSyncAPI,
    PotSyncAPI,
    PotDonationsSyncAPI,
    PotApplicationsSyncAPI,
    PotPayoutsSyncAPI,
    PotPayoutChallengesSyncAPI,
)
from base.api import StatsAPI, ReclaimProofRequestView
from campaigns.api import (
    AllCampaignDonationsAPI,
    CampaignContractConfigAPI,
    CampaignDetailAPI,
    CampaignDonationsAPI,
    CampaignsAPI,
)
from campaigns.sync import (
    CampaignSyncAPI,
    CampaignDonationSyncAPI,
    CampaignDeleteSyncAPI,
    CampaignRefundSyncAPI,
    CampaignUnescrowSyncAPI,
)
from donations.api import DonationContractConfigAPI
from donations.sync import DirectDonationSyncAPI
from grantpicks.api import AccountProjectListAPI, ProjectListAPI, ProjectRoundVotesAPI, ProjectStatsAPI, RoundApplicationsAPI, RoundDetailAPI, RoundsListAPI
from lists.api import (
    ListDetailAPI,
    ListRandomRegistrationAPI,
    ListRegistrationsAPI,
    ListsListAPI,
)
from pots.api import (
    MpdaoVotersListAPI,
    MpdaoVoterDetailAPI,
    PotApplicationsAPI,
    PotDetailAPI,
    PotDonationsAPI,
    PotFactoriesAPI,
    PotPayoutsAPI,
    PotsListAPI,
    PotSponsorsAPI,
)

urlpatterns = [
    # schema
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
    ),
    # accounts
    path("v1/accounts", AccountsListAPI.as_view(), name="accounts_api"),
    path(
        "v1/accounts/<str:account_id>",
        AccountDetailAPI.as_view(),
        name="accounts_api_by_id",
    ),
    path(
        "v1/accounts/<str:account_id>/active_pots",
        AccountActivePotsAPI.as_view(),
        name="accounts_api_by_id_active_pots",
    ),
    path(
        "v1/accounts/<str:account_id>/pot_applications",
        AccountPotApplicationsAPI.as_view(),
        name="accounts_api_by_id_pot_applications",
    ),
    path(
        "v1/accounts/<str:account_id>/donations_received",
        AccountDonationsReceivedAPI.as_view(),
        name="accounts_api_by_id_donations_received",
    ),
    path(
        "v1/accounts/<str:account_id>/donations_sent",
        AccountDonationsSentAPI.as_view(),
        name="accounts_api_by_id_donations_sent",
    ),
    path(
        "v1/accounts/<str:account_id>/payouts_received",
        AccountPayoutsReceivedAPI.as_view(),
        name="accounts_api_by_id_payouts_received",
    ),
    path(
        "v1/accounts/<str:account_id>/list-registrations",
        AccountListRegistrationsAPI.as_view(),
        name="accounts_api_by_id_registrations",
    ),
    path(
        "v1/accounts/<str:account_id>/upvoted-lists",
        AccountUpvotedListsAPI.as_view(),
        name="accounts_api_upvoted_lists",
    ),
    path(
        "v1/accounts/<str:account_id>/rounds",
        RoundsListAPI.as_view(),
        name="accounts_api_rounds",
    ),
    # donate contract config
    path(
        "v1/donate_contract_config",
        DonationContractConfigAPI.as_view(),
        name="donate_contract_config_api",
    ),
    # direct donation sync
    path(
        "v1/donations/sync",
        DirectDonationSyncAPI.as_view(),
        name="direct_donation_sync_api",
    ),
    # campaigns
    path("v1/campaigns", CampaignsAPI.as_view(), name="campaigns_api"),
    path(
        "v1/campaigns/<int:campaign_id>",
        CampaignDetailAPI.as_view(),
        name="campaigns_api_by_id",
    ),
    path(
        "v1/campaigns/<int:campaign_id>/donations",
        CampaignDonationsAPI.as_view(),
        name="campaigns_donations_api",
    ),
    path(
        "v1/campaign_donations",
        AllCampaignDonationsAPI.as_view(),
        name="all_campaign_donations_api",
    ),
    path(
        "v1/campaign_contract_config",
        CampaignContractConfigAPI.as_view(),
        name="campaign_contract_config_api",
    ),
    # campaign sync endpoints
    path(
        "v1/campaigns/<int:campaign_id>/sync",
        CampaignSyncAPI.as_view(),
        name="campaign_sync_api",
    ),
    path(
        "v1/campaigns/<int:campaign_id>/donations/sync",
        CampaignDonationSyncAPI.as_view(),
        name="campaign_donation_sync_api",
    ),
    path(
        "v1/campaigns/<int:campaign_id>/delete/sync",
        CampaignDeleteSyncAPI.as_view(),
        name="campaign_delete_sync_api",
    ),
    path(
        "v1/campaigns/<int:campaign_id>/refunds/sync",
        CampaignRefundSyncAPI.as_view(),
        name="campaign_refund_sync_api",
    ),
    path(
        "v1/campaigns/<int:campaign_id>/unescrow/sync",
        CampaignUnescrowSyncAPI.as_view(),
        name="campaign_unescrow_sync_api",
    ),
    # donors
    path("v1/donors", DonorsAPI.as_view(), name="donors_api"),
    # lists
    path("v1/lists", ListsListAPI.as_view(), name="lists_api"),
    path("v1/lists/<int:list_id>", ListDetailAPI.as_view(), name="lists_api_by_id"),
    path(
        "v1/lists/<int:list_id>/registrations",
        ListRegistrationsAPI.as_view(),
        name="lists_api_by_id_registrations",
    ),
    path(
        "v1/lists/<int:list_id>/random_registration",
        ListRandomRegistrationAPI.as_view(),
        name="lists_api_by_id_registrations",
    ),
    # pots
    path("v1/pots", PotsListAPI.as_view(), name="pots_api"),
    path("v1/pots/<str:pot_id>/", PotDetailAPI.as_view(), name="pots_api_by_id"),
    path(
        "v1/pots/<str:pot_id>/applications",
        PotApplicationsAPI.as_view(),
        name="pots_applications_api",
    ),
    path(
        "v1/pots/<str:pot_id>/donations",
        PotDonationsAPI.as_view(),
        name="pots_donations_api",
    ),
    path(
        "v1/pots/<str:pot_id>/sponsors",
        PotSponsorsAPI.as_view(),
        name="pots_sponsors_api",
    ),
    path(
        "v1/pots/<str:pot_id>/payouts", PotPayoutsAPI.as_view(), name="pots_payouts_api"
    ),
    path(
        "v1/potfactories", PotFactoriesAPI.as_view(), name="pot_factories_api"
    ),
    # stats
    path("v1/stats", StatsAPI.as_view(), name="stats_api"),
    path("v1/reclaim/generate-request", ReclaimProofRequestView.as_view(), name="stats_api"),

    # grantpicks
    path("v1/rounds", RoundsListAPI.as_view(), name="rounds_api"),
    path("v1/round/<int:round_id>/", RoundDetailAPI.as_view(), name="rounds_api_by_id"),
    path("v1/round/<int:round_id>/<str:project_id>/votes", ProjectRoundVotesAPI.as_view(), name="project_round_votes_api_by_id"),
    path("v1/projects", ProjectListAPI.as_view(), name="projects_api"),
    path(
        "v1/rounds/<str:round_id>/applications",
        RoundApplicationsAPI.as_view(),
        name="rounds_applications_api",
    ),
    path("v1/<str:account_id>/projects", AccountProjectListAPI.as_view(), name="user_projects_api"),
    path("v1/<str:account_id>/project-stats", ProjectStatsAPI.as_view(), name="projects_stat__api"),

    path(
        "v1/mpdao/voters",
        MpdaoVotersListAPI.as_view(),
        name="mpdao_voters_list",
    ),
    path(
        "v1/mpdao/voters/<str:voter_id>",
        MpdaoVoterDetailAPI.as_view(),
        name="mpdao_voter_detail",
    ),
    # sync endpoints (for on-demand data fetching from blockchain)
    path(
        "v1/lists/<int:list_id>/sync",
        ListSyncAPI.as_view(),
        name="list_sync_api",
    ),
    path(
        "v1/lists/<int:list_id>/registrations/sync",
        ListRegistrationsSyncAPI.as_view(),
        name="list_registrations_sync_api",
    ),
    path(
        "v1/lists/<int:list_id>/registrations/<str:registrant_id>/sync",
        SingleRegistrationSyncAPI.as_view(),
        name="single_registration_sync_api",
    ),
    # pot sync endpoints
    path(
        "v1/pots/<str:pot_id>/sync",
        PotSyncAPI.as_view(),
        name="pot_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/donations/sync",
        PotDonationsSyncAPI.as_view(),
        name="pot_donations_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/applications/sync",
        PotApplicationsSyncAPI.as_view(),
        name="pot_applications_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/payouts/sync",
        PotPayoutsSyncAPI.as_view(),
        name="pot_payouts_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/challenges/sync",
        PotPayoutChallengesSyncAPI.as_view(),
        name="pot_challenges_sync_api",
    ),
    path(
        "v1/lists/<int:list_id>/delete/sync",
        ListDeleteSyncAPI.as_view(),
        name="list_delete_sync_api",
    ),
    path(
        "v1/lists/<int:list_id>/upvote/sync",
        ListUpvoteSyncAPI.as_view(),
        name="list_upvote_sync_api",
    ),
    path(
        "v1/lists/<int:list_id>/remove-upvote/sync",
        ListRemoveUpvoteSyncAPI.as_view(),
        name="list_remove_upvote_sync_api",
    ),
    # pot sync endpoints
    path(
        "v1/pots/<str:pot_id>/sync",
        PotSyncAPI.as_view(),
        name="pot_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/donations/sync",
        PotDonationsSyncAPI.as_view(),
        name="pot_donations_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/applications/sync",
        PotApplicationsSyncAPI.as_view(),
        name="pot_applications_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/payouts/sync",
        PotPayoutsSyncAPI.as_view(),
        name="pot_payouts_sync_api",
    ),
    path(
        "v1/pots/<str:pot_id>/challenges/sync",
        PotPayoutChallengesSyncAPI.as_view(),
        name="pot_challenges_sync_api",
    ),
    # account sync
    path(
        "v1/accounts/<str:account_id>/sync",
        AccountSyncAPI.as_view(),
        name="account_sync_api",
    ),
]
