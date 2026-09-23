from django.urls import path

from .views import HealthLiveView, HealthReadyView, MetaView

urlpatterns = [
    path("health/live/", HealthLiveView.as_view(), name="health-live"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready"),
    path("meta/", MetaView.as_view(), name="meta"),
]
