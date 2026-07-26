from django.urls import path

from . import views

app_name = "tutor"

urlpatterns = [
    path("courses/<int:course_id>/ask/", views.ask_tutor_view, name="ask"),
    path("courses/<int:course_id>/tutor-token/", views.tutor_token_view, name="tutor-token"),
]