from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        VOLUNTEER = "VOLUNTEER", "Volunteer"

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.VOLUNTEER)
    
    # Common fields (from doc: Phone)
    # First_name, Last_name, Email are already in AbstractUser
    phone = models.CharField(max_length=15, blank=True, null=True)
    initial_password = models.CharField(max_length=128, blank=True, null=True, help_text="Stored plain text password for initial login visibility")
    
    # Volunteer specific fields (from doc: Department, Gender)
    # These can be blank for Admins
    department = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
