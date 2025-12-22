from django.urls import path
from .views import (
    CustomLoginView, 
    VolunteerSignupView, 
    AdminSignupView, 
    VolunteerListView, 
    VolunteerListView, 
    VolunteerDetailView,
    PasswordManagementView,
    VolunteerCSVExportView,
    VolunteerCSVImportView
)

urlpatterns = [
    path('auth/login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('auth/password-reset/', PasswordManagementView.as_view(), name='password_management'),
    path('auth/register/volunteer/', VolunteerSignupView.as_view(), name='volunteer_signup'),
    path('auth/register/admin/', AdminSignupView.as_view(), name='admin_signup'),
    # Volunteer management
    path('volunteers/', VolunteerListView.as_view(), name='volunteer_list'),
    path('volunteers/<int:id>/', VolunteerDetailView.as_view(), name='volunteer_detail'),
    path('volunteers/export/', VolunteerCSVExportView.as_view(), name='volunteer_export'),
    path('volunteers/import/', VolunteerCSVImportView.as_view(), name='volunteer_import'),
]
