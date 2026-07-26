from django.urls import path

from . import views

app_name = "tutor"

urlpatterns = [
    path("courses/<int:course_id>/ask/", views.ask_tutor_view, name="ask"),
]