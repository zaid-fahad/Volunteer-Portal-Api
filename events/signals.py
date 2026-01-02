from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.signals import notify
from .models import Event, Participation
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=Event)
def event_notifications(sender, instance, created, **kwargs):
    print(f"DEBUG: Signal fired for event {instance.title}, created={created}")
    if created:
        # 1. New Event Notification
        # Target: All Volunteers
        volunteers = User.objects.filter(role='VOLUNTEER')
        notify.send(
            instance, # Actor (The event itself or we could pass the admin if we knew who it was)
            recipient=volunteers,
            verb='New Event Created',
            target=instance,
            description=f"A new event '{instance.title}' is available for registration."
        )
    else:
        # 2. Existing Event Status Changes
        # We need to know what changed. Since Django signals don't easily provide 'old' values
        # without custom logic, we check the current state.
        
        # Determine notification content based on current status
        notify_msg = None
        verb = None
        
        if instance.status == Event.Status.ACTIVE:
            verb = 'Event Started'
            notify_msg = f"The event '{instance.title}' has officially started!"
        elif instance.status == Event.Status.DONE:
            verb = 'Event Completed'
            notify_msg = f"Good workload! The event '{instance.title}' is now marked as completed."
            
        if instance.attendance_status == Event.AttendanceStatus.ACTIVE:
             verb = 'Attendance Open'
             notify_msg = f"Attendance for '{instance.title}' is now OPEN. You can start your session!"
        
        if instance.attendance_status == Event.AttendanceStatus.CLOSE:
             verb = 'Attendance Closed'
             notify_msg = f"Attendance for '{instance.title}' is now CLOSED. You can't start your session!"

        if notify_msg:
            # Target: Only registered volunteers for this specific event
            participants = User.objects.filter(participations__event=instance).distinct()
            if participants.exists():
                notify.send(
                    instance,
                    recipient=participants,
                    verb=verb,
                    target=instance,
                    description=notify_msg
                )

# @receiver(post_save, sender=Participation)
# def participation_notifications(sender, instance, created, **kwargs):
#     if created:
#         # Notify Admin about new registration (optional but useful)
#         admins = User.objects.filter(role='ADMIN')
#         notify.send(
#             instance.volunteer,
#             recipient=admins,
#             verb='Registered for Event',
#             target=instance.event,
#             description=f"{instance.volunteer.username} joined '{instance.event.title}'"
#         )