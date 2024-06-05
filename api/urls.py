from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts.api import (
    AccountActivePotsAPI,
    AccountDetailAPI,
    AccountsListAPI,
    DonorsAPI,
)
from base.api import StatsAPI
from lists.api import ListDetailAPI, ListRegistrationsAPI, ListsListAPI
from pots.api import (
    PotApplicationsAPI,
    PotDetailAPI,
    PotDonationsAPI,
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
    # stats
    path("v1/stats", StatsAPI.as_view(), name="stats_api"),
]
