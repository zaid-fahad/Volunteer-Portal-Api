import logging
from django.shortcuts import render
from datetime import date, datetime, timedelta
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Event, Participation
from .serializers import EventSerializer, ParticipationSerializer, EventListSerializer
from .notifications_serializers import NotificationSerializer
from notifications.models import Notification
from accounts.permissions import IsAdminUser

from rest_framework.filters import SearchFilter

logger = logging.getLogger('events')
logger_participation = logging.getLogger('events.participation')

# Create your views here.

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().annotate(
        annotated_total_participants=Count('participations')
    )
    serializer_class = EventSerializer
    filter_backends = [SearchFilter]
    search_fields = ['title', 'venue', 'organizer']

    def get_serializer_class(self):
        if self.action in ['list', 'active']:
            return EventListSerializer
        return EventSerializer

    def _calculate_log_hour(self, instance):
        if instance.start_time and instance.end_time:
            dummy_date = date.today()
            start = datetime.combine(dummy_date, instance.start_time)
            end = datetime.combine(dummy_date, instance.end_time)
            
            # Handle cases where end time is after midnight
            if end <= start:
                end += timedelta(days=1)
                
            delta = end - start
            instance.log_hour = round(delta.total_seconds() / 3600, 2)
            instance.save()

    def perform_create(self, serializer):
        event = serializer.save()
        self._calculate_log_hour(event)
        logger.info(f"Event created: {event.title} (Auto-calculated hours: {event.log_hour}) by {self.request.user.username}")

    def perform_update(self, serializer):
        event = serializer.save()
        self._calculate_log_hour(event)
        logger.info(f"Event updated: {event.title} (Recalculated hours: {event.log_hour}) by {self.request.user.username}")

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            # list and retrieve can be accessed by any authenticated user (or allowany if public)
            permission_classes = [IsAuthenticated] 
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['put', 'patch'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        event = self.get_object()
        event.status = Event.Status.DONE
        event.save()
        logger.info(f"Event marked complete: {event.title} (ID: {event.id})")
        return Response({'status': 'Event marked as done', 'id': event.id})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def active(self, request):
        user = request.user
        queryset = self.queryset
        
        if user.role == 'ADMIN':
             # Admin sees all active events
             events = queryset.filter(status=Event.Status.ACTIVE)
        else:
             # Volunteer sees active (and pending if needed, but request said 'only active')
             # "pending and done for volunteer only active". Uh, request said: 
             # "/events/active(for admin all active, pending and done for volunteer only active)"
             # Actually "for admin all active, pending and done" means admin sees everything? 
             # Or means Admin sees "Active" list which includes PENDING/DONE? 
             # "for admin all active" likely means Admin endpoint can see all statii, or specific list.
             # Let's follow filtered logic:
             # Logic: Volunteer -> ACTIVE only.
             # Admin -> ACTIVE (Request says "all active"). 
             # Wait, usually /events/active implies "List of active events".
             # If admin wants to see "Current active events", it's status=ACTIVE.
             # If admin wants see ALL, they use basic LIST.
             # So I will make /events/active/ return status=ACTIVE for everyone, or specifically what user asked.
             # User said: "for admin all active, pending and done for volunteer only active"
             # This means Admin response should include Active, Pending, Done (basically everything?)
             # Volunteer response: Active only.
             
            events = queryset.filter(status=Event.Status.ACTIVE)
            if user.role == 'ADMIN':
                # Actually if Admin sees "Pending, Active, Done", isn't that just EVERYTHING?
                # Maybe "Cancelled" is rejected?
                # I will just return all for Admin if that's what he meant, or filters Active/Pending/Done explicitly.
                # Assuming "All" for now as standard list does that.
                # But since this is a specific endpoint 'active', maybe it implies "Not Cancelled"?
                # I will filter by [ACTIVE, PENDING, DONE]
                events = queryset.filter(status__in=[Event.Status.ACTIVE, Event.Status.PENDING, Event.Status.DONE])
        
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)


from rest_framework.views import APIView

class PunchInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        from django.db import transaction
        from django.utils import timezone

        user = request.user

        # Fetch participation first, pre-fetching event details
        try:
            participation = Participation.objects.filter(event_id=event_id, volunteer=user).select_related('event').first()
        except ValueError:
            return Response({'error': 'Invalid Event ID'}, status=404)

        if participation:
            if participation.punch_in and not participation.punch_out:
                 return Response({'message': 'Already punched in.'}, status=200)

            participation.punch_in = timezone.now()
            participation.punch_out = None 
            participation.save()
            logger_participation.info(f"Volunteer {user.username} PUNCHED IN to event {participation.event.title}")
            return Response({'status': 'Punched in successfully', 'participation_id': participation.id})

        # If NOT exists, Join & Punch In within a transaction to guarantee quota checks
        try:
            with transaction.atomic():
                try:
                    event_locked = Event.objects.select_for_update().get(pk=event_id)
                except Event.DoesNotExist:
                    return Response({'error': 'Event not found'}, status=404)

                current_count = event_locked.participations.count()
                if event_locked.participants > 0 and current_count >= event_locked.participants:
                    logger_participation.warning(f"Quota filled for event {event_locked.title}. User {user.username} rejected.")
                    return Response({'error': f"Event '{event_locked.title}' is full. Quota filled."}, status=400)

                participation = Participation.objects.create(
                    volunteer=user,
                    event=event_locked,
                    punch_in=timezone.now(),
                    status=Participation.Status.APPROVED
                )
                logger_participation.info(f"Volunteer {user.username} JOINED and PUNCHED IN to event {event_locked.title}")
                return Response({'status': 'Punched in successfully (joined event)', 'participation_id': participation.id})

        except Exception as e:
            return Response({'error': str(e)}, status=500)

class PunchOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        from django.utils import timezone
        user = request.user
        
        try:
            participation = Participation.objects.filter(event_id=event_id, volunteer=user).select_related('event').first()
        except ValueError:
            return Response({'error': 'Invalid Event ID'}, status=404)
            
        if not participation:
            return Response({'error': 'Participation not found'}, status=404)
        
        if not participation.punch_in:
            return Response({'error': 'You must punch in before punching out'}, status=400)
            
        now = timezone.now()
        participation.punch_out = now
        
        # Calculate Logged Hours
        if participation.punch_in:
            duration = now - participation.punch_in
            delta_hours = duration.total_seconds() / 3600.0
            participation.log_hours = round(delta_hours, 2)
            
        participation.save()
        
        logger_participation.info(f"Volunteer {user.username} PUNCHED OUT from event {participation.event.title} (Logged: {participation.log_hours} hrs)")
        return Response({
            'status': 'Punched out successfully', 
            'participation_id': participation.id,
            'log_hours': participation.log_hours
        })


class ParticipationViewSet(viewsets.ModelViewSet):
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='types')
    def get_types(self, request):
        types = Participation.Type.choices
        # Format as list of labels/values for the frontend
        data = [{'value': v, 'label': l} for v, l in types]
        return Response(data)

    def get_queryset(self):
        # Volunteers see only their own participations, Admins see all
        user = self.request.user
        if user.role == 'ADMIN':
            queryset = Participation.objects.all()
        else:
            queryset = Participation.objects.filter(volunteer=user)

        # Optimize: Support filtering by event directly at database level
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)

        return queryset

    def perform_create(self, serializer):
        from django.db import transaction
        from rest_framework.exceptions import ValidationError

        event = serializer.validated_data['event']

        # Atomic transaction to ensure quota safety during registration
        with transaction.atomic():
            # Lock the Event row
            event_locked = Event.objects.select_for_update().get(id=event.id)
            
            # Check Quota
            if event_locked.participants > 0:
                current_count = event_locked.participations.count()
                if current_count >= event_locked.participants:
                     raise ValidationError({'error': f"Event '{event_locked.title}' is full. Quota filled."})
            
            # Save Participation
            if self.request.user.role == 'VOLUNTEER':
                 instance = serializer.save(volunteer=self.request.user)
            else:
                 instance = serializer.save(volunteer=self.request.user)
            
            logger_participation.info(f"Participation created for event {event_locked.title} by {self.request.user.username}")


from rest_framework.views import APIView

class VolunteerReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Admin can view anyone, Volunteer can view self
        if request.user.role != 'ADMIN' and request.user.id != pk:
            return Response({'error': 'Permission denied'}, status=403)
        
        # Get participations, prefetching the related event details
        participations = Participation.objects.filter(volunteer_id=pk).select_related('event')
        
        data = []
        for p in participations:
            data.append({
                'participation_id': p.id,
                'event_title': p.event.title,
                'event_date': p.event.date,
                'event_status': p.event.status,
                'type': p.type,
                'status': p.status,
                'punch_in': p.punch_in,
                'punch_out': p.punch_out,
                'log_hours': p.log_hours
            })
            
        return Response(data)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = self.request.user.notifications.all().prefetch_related('actor', 'target')
        unread = self.request.query_params.get('unread')
        if unread == 'true':
            qs = qs.unread()
        return qs

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.request.user.notifications.mark_all_as_read()
        return Response({'status': 'all marked as read'})


from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
User = get_user_model()

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if user.role == 'ADMIN':
            total_events = Event.objects.count()
            total_volunteers = User.objects.filter(role=User.Role.VOLUNTEER).count()
            total_hours = Participation.objects.aggregate(Sum('log_hours'))['log_hours__sum'] or 0.0
            
            # Active events with count
            active_events = Event.objects.filter(status=Event.Status.ACTIVE).annotate(
                annotated_total_participants=Count('participations')
            )
            
            events_data = []
            for e in active_events:
                events_data.append({
                    'id': e.id,
                    'title': e.title,
                    'date': e.date,
                    'start_time': e.start_time,
                    'end_time': e.end_time,
                    'venue': e.venue,
                    'organizer': e.organizer,
                    'status': e.status,
                    'attendance_status': e.attendance_status,
                    'participants': e.participants,
                    'participantCount': e.annotated_total_participants
                })

            return Response({
                'totalEvents': total_events,
                'totalVolunteers': total_volunteers,
                'totalHours': round(total_hours, 2),
                'activeEvents': events_data
            })
            
        else:
            active_events = Event.objects.filter(status=Event.Status.ACTIVE).annotate(
                annotated_total_participants=Count('participations')
            )
            
            events_data = []
            for e in active_events:
                events_data.append({
                    'id': e.id,
                    'title': e.title,
                    'date': e.date,
                    'start_time': e.start_time,
                    'end_time': e.end_time,
                    'venue': e.venue,
                    'organizer': e.organizer,
                    'status': e.status,
                    'attendance_status': e.attendance_status,
                    'participants': e.participants,
                    'participantCount': e.annotated_total_participants
                })
            
            my_participations = Participation.objects.filter(volunteer=user).select_related('event')
            
            registered_events_data = []
            in_progress_event = None
            
            for p in my_participations:
                if p.event.status != Event.Status.DONE:
                    registered_events_data.append({
                        'id': p.event.id,
                        'title': p.event.title,
                        'date': p.event.date,
                        'start_time': p.event.start_time,
                        'end_time': p.event.end_time,
                        'venue': p.event.venue,
                        'organizer': p.event.organizer,
                        'status': p.event.status,
                        'attendance_status': p.event.attendance_status,
                        'participants': p.event.participants
                    })
                
                if p.punch_in and not p.punch_out:
                    in_progress_event = {
                        'id': p.event.id,
                        'title': p.event.title,
                        'date': p.event.date,
                        'start_time': p.event.start_time,
                        'end_time': p.event.end_time,
                        'venue': p.event.venue,
                        'organizer': p.event.organizer,
                        'status': p.event.status,
                        'attendance_status': p.event.attendance_status,
                        'participants': p.event.participants
                    }
            
            notifications = user.notifications.all().prefetch_related('actor', 'target')[:10]
            from .notifications_serializers import NotificationSerializer
            notifications_data = NotificationSerializer(notifications, many=True).data

            return Response({
                'events': events_data,
                'registeredEvents': registered_events_data,
                'inProgressEvent': in_progress_event,
                'notifications': notifications_data
            })
