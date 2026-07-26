from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("webhooks/stripe/", views.stripe_webhook, name="stripe-webhook"),
]