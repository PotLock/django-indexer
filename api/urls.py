from django.urls import path

from accounts.api import AccountsAPI, DonorsAPI
from base.api import StatsAPI
from lists.api import ListsAPI
from pots.api import PotsAPI

urlpatterns = [
    # accounts
    path("v1/accounts", AccountsAPI.as_view(), name="accounts_api"),
    path(
        "v1/accounts/<str:account_id>", AccountsAPI.as_view(), name="accounts_api_by_id"
    ),
    path(
        "v1/accounts/<str:account_id>/<str:action>",  # e.g. /accounts/lachlan.near/active_pots - consider putting this under /pots instead of /accounts since Pots are the resource being fetched, even though the action is being performed on an Account
        AccountsAPI.as_view(),
        name="accounts_api_by_id_with_action",
    ),
    # donors
    path("v1/donors", DonorsAPI.as_view(), name="donors_api"),
    # lists
    path("v1/lists", ListsAPI.as_view(), name="lists_api"),
    path("v1/lists/<int:list_id>", ListsAPI.as_view(), name="lists_api_by_id"),
    path(
        "v1/lists/<int:list_id>/<str:action>",  # e.g. /lists/1/registrations
        ListsAPI.as_view(),
        name="lists_api_by_id_with_action",
    ),
    # pots
    path("v1/pots", PotsAPI.as_view(), name="pots_api"),
    path("v1/pots/<str:pot_id>/", PotsAPI.as_view(), name="pots_api_by_id"),
    path(
        "v1/pots/<str:pot_id>/<str:action>",
        PotsAPI.as_view(),
        name="pots_api_by_id_with_action",
    ),
    # stats
    path("v1/stats", StatsAPI.as_view(), name="stats_api"),
]
