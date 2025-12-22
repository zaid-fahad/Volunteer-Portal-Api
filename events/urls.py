from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, ParticipationViewSet, VolunteerReportView

router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'participations', ParticipationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('reports/volunteer/<int:pk>/', VolunteerReportView.as_view(), name='volunteer_report'),
]
