from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Event(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PENDING = 'Pending', 'Pending'
        DONE = 'Done', 'Done'

    class AttendanceStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        ACTIVE = 'Active', 'Active'
        CLOSE = 'Close', 'Close'

    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    participants = models.IntegerField(default=0, help_text="Number of participants needed or registered") # Renamed from 'Participance' for clarity, assuming it means count or limit? If it means ManyToMany users, we should clarify. User likely means count or description based on normal context, but I will assume simple integer or string for now. "Participance" usually means Participation. Given "Participance Log Hour", maybe it's just a text field or int. I will use IntegerField for now as 'capacity' or 'participants count'. 
    # WAIT, 'Participance' might mean the list of users? But usually that's separate. 
    # Re-reading: "Participance Log Hour". Maybe "Participance" is one int field? 
    # I will assume "Participants" is a count for now.
    
    log_hour = models.FloatField(null=True, blank=True, help_text="Hours to be logged for this event. Calculated automatically from start/end time if left blank.")
    venue = models.CharField(max_length=255)
    organizer = models.CharField(max_length=255, null=True, blank=True) # Could be a User ForeignKey, but requirements say "Organizer" field. Using CharField for flexibility as requested.
    remarks = models.TextField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    attendance_status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Participation(models.Model):
    class Type(models.TextChoices):
        WORKING = 'Working', 'Working'
        AUDIENCE = 'Audience', 'Audience'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'

    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participations')
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.WORKING)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    punch_in = models.DateTimeField(null=True, blank=True)
    punch_out = models.DateTimeField(null=True, blank=True)
    log_hours = models.FloatField(default=0.0, help_text="Total hours logged for this session.")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.volunteer.username} - {self.event.title}"
