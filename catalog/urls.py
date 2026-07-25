from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("courses/search", views.course_search, name="course-search"),
]
