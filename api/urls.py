from django.urls import path

from accounts.api import DonorsAPI

urlpatterns = [
    path("v1/donors", DonorsAPI.as_view(), name="donors-api"),
]
