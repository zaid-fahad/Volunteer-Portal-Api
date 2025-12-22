from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Allocates access only to Admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')

class IsVolunteerUser(BasePermission):
    """
    Allocates access only to Volunteer users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'VOLUNTEER')
