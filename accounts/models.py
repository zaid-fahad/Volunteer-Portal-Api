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


    role = models.CharField(max_length=50, choices=Role.choices, default=Role.VOLUNTEER, db_index=True)
    
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


class EmailConfiguration(models.Model):
    email_host = models.CharField(max_length=255, default='smtp.gmail.com')
    email_port = models.IntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=255, blank=True, null=True)
    email_host_password = models.CharField(max_length=255, blank=True, null=True)
    default_from_email = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Email Config ({self.email_host_user})"


class EmailLog(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[('Success', 'Success'), ('Failed', 'Failed')])
    error_message = models.TextField(blank=True, null=True)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Email to {self.recipient} at {self.sent_at} ({self.status})"
