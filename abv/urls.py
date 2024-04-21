from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name = "index"),
    path("submit/", views.submit, name = "submit"),
    path("data_raw_csv/", views.data_raw_csv, name = "data_raw_csv"),
    path("data_latest_per_user_csv/", views.data_latest_per_user_csv, name = "data_latest_per_user_csv"),
    path("data_majority_vote_csv/", views.data_majority_vote_csv, name = "data_majority_vote_csv"),
    # path("data_raw_html/", views.data_raw_html, name = "data_raw_html"),
    # path("data_voted_html/", views.data_voted_html, name = "data_voted_html"),
]
