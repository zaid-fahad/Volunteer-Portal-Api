from django.db import models

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
    
    log_hour = models.FloatField(help_text="Hours to be logged for this event")
    venue = models.CharField(max_length=255)
    organizer = models.CharField(max_length=255) # Could be a User ForeignKey, but requirements say "Organizer" field. Using CharField for flexibility as requested.
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

from django.contrib.auth import get_user_model
User = get_user_model()

class Participation(models.Model):
    class Type(models.TextChoices):
        WORKING = 'Working', 'Working'
        AUDIENCE = 'Audience', 'Audience'

    class Attendance(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        YES = 'Yes', 'Yes'
        NO = 'No', 'No'
    
    # Assuming 'Status' field here refers to the status of the request (e.g., Requested, Approved)
    # Since it wasn't strictly defined in values, I'll add a generic one or assume it might be 'Active'/'Pending' like Event.
    # I will use a simple CharField for now or Pending/Approved options.
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
    
    attendance = models.CharField(
        max_length=20,
        choices=Attendance.choices,
        default=Attendance.PENDING
    )
    
    attendance_at = models.DateTimeField(null=True, blank=True, help_text="Punch In Time")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.volunteer.username} - {self.event.title}"
