from django.urls import path

from accounts.api import AccountsAPI, DonorsAPI

urlpatterns = [
    path("v1/accounts", AccountsAPI.as_view(), name="accounts_api"),
    path(
        "v1/accounts/<str:account_id>", AccountsAPI.as_view(), name="accounts_api_by_id"
    ),
    path(
        "accounts/<int:account_id>/<str:action>",  # e.g. /accounts/lachlan.near/active_pots - consider putting this under /pots instead of /accounts since Pots are the resource being fetched, even though the action is being performed on an Account
        AccountsAPI.as_view(),
        name="accounts_api_by_id_with_action",
    ),
    path("v1/donors", DonorsAPI.as_view(), name="donors_api"),
]
