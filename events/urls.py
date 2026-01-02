from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, ParticipationViewSet, VolunteerReportView, PunchInView, PunchOutView, NotificationViewSet

router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'participations', ParticipationViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('punch-in/<int:event_id>/', PunchInView.as_view(), name='punch_in'),
    path('punch-out/<int:event_id>/', PunchOutView.as_view(), name='punch_out'),
    path('reports/volunteer/<int:pk>/', VolunteerReportView.as_view(), name='volunteer_report'),
]
