from django.urls import path

from accounts.api import AccountsAPI, DonorsAPI

urlpatterns = [
    path("v1/accounts", AccountsAPI.as_view(), name="accounts-api"),
    path("v1/donors", DonorsAPI.as_view(), name="donors-api"),
]
