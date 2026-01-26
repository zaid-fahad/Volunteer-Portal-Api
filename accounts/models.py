from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        VOLUNTEER = "VOLUNTEER", "Volunteer"

    class BloodGroup(models.TextChoices) :
        A_POS = "A+", "A Positive"
        A_NEG = "A-", "A Negative"
        B_POS = "B+", "B Positive"
        B_NEG = "B-", "B Negative"
        AB_POS = "AB+", "AB Positive"
        AB_NEG = "AB-", "AB Negative"
        O_POS = "O+", "O Positive"
        O_NEG = "O-", "O Negative"


    role = models.CharField(max_length=50, choices=Role.choices, default=Role.VOLUNTEER)
    
    # Common fields (from doc: Phone)
    # First_name, Last_name, Email are already in AbstractUser
    phone = models.CharField(max_length=15, blank=True, null=True)
    initial_password = models.CharField(max_length=128, blank=True, null=True, help_text="Stored plain text password for initial login visibility")
    
    # Volunteer specific fields (from doc: Department, BloodGroup)
    # These can be blank for Admins
    alternative_email = models.EmailField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    blood_group = models.CharField(max_length=10, choices=BloodGroup.choices, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}(@{self.username}) - ({self.role})"
