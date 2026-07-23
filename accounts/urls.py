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
    VolunteerCSVImportView,
    ProfileView,
    SendVolunteerCredentialsView,
    EmailConfigurationView,
    EmailLogListView,
    RequestPasswordResetLinkView,
    ConfirmPasswordResetLinkView
)

urlpatterns = [
    path('auth/login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/password-reset/', PasswordManagementView.as_view(), name='password_management'),
    path('auth/forgot-password/', RequestPasswordResetLinkView.as_view(), name='forgot_password'),
    path('auth/confirm-password-reset/', ConfirmPasswordResetLinkView.as_view(), name='confirm_password_reset'),
    path('auth/register/volunteer/', VolunteerSignupView.as_view(), name='volunteer_signup'),
    path('auth/register/admin/', AdminSignupView.as_view(), name='admin_signup'),
    # Volunteer management
    path('volunteers/', VolunteerListView.as_view(), name='volunteer_list'),
    path('volunteers/<int:id>/', VolunteerDetailView.as_view(), name='volunteer_detail'),
    path('volunteers/<int:id>/send-credentials/', SendVolunteerCredentialsView.as_view(), name='send_volunteer_credentials'),
    path('volunteers/export/', VolunteerCSVExportView.as_view(), name='volunteer_export'),
    path('volunteers/import/', VolunteerCSVImportView.as_view(), name='volunteer_import'),
    # Email settings
    path('email-config/', EmailConfigurationView.as_view(), name='email_config'),
    path('email-logs/', EmailLogListView.as_view(), name='email_logs'),
]
