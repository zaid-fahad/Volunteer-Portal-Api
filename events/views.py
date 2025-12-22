import logging
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer
from accounts.permissions import IsAdminUser

logger = logging.getLogger('events')
logger_participation = logging.getLogger('events.participation')

# Create your views here.

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def perform_create(self, serializer):
        event = serializer.save()
        logger.info(f"Event created: {event.title} by {self.request.user.username}")

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
        
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='punch-in')
    def punch_in(self, request, pk=None):
        from django.db import transaction
        from django.utils import timezone

        user = request.user
        if user.role != 'VOLUNTEER':
             return Response({'error': 'Only volunteers can punch in.'}, status=403)

        # 1. Try to find existing participation (No Lock)
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=404)

        participation = Participation.objects.filter(event=event, volunteer=user).first()

        # 2. If exists, just update (No Atomic needed for this specific user's row update)
        if participation:
            if participation.attendance == Participation.Attendance.YES:
                 return Response({'message': 'Already punched in.'}, status=200)

            participation.attendance = Participation.Attendance.YES
            participation.attendance_at = timezone.now()
            participation.save()
            logger_participation.info(f"Volunteer {user.username} PUNCHED IN to event {event.title}")
            return Response({'status': 'Punched in successfully', 'participation_id': participation.id})

        # 3. If NOT exists, we are "Joining". This needs Lock.
        try:
            with transaction.atomic():
                # Re-fetch event with lock to ensure quota safety
                event_locked = Event.objects.select_for_update().get(pk=pk)
                
                # Check Quota
                current_count = event_locked.participations.count()
                if event_locked.participants > 0 and current_count >= event_locked.participants:
                    logger_participation.warning(f"Quota filled for event {event_locked.title}. User {user.username} rejected.")
                    return Response({'error': f"Event '{event_locked.title}' is full. Quota filled."}, status=400)

                # Create
                participation = Participation.objects.create(
                    volunteer=user,
                    event=event_locked,
                    attendance=Participation.Attendance.YES,
                    attendance_at=timezone.now(),
                    status=Participation.Status.APPROVED
                )
                logger_participation.info(f"Volunteer {user.username} JOINED and PUNCHED IN to event {event_locked.title}")
                return Response({'status': 'Punched in successfully (joined event)', 'participation_id': participation.id})

        except Exception as e:
            return Response({'error': str(e)}, status=500)

from .models import Participation
from .serializers import ParticipationSerializer

class ParticipationViewSet(viewsets.ModelViewSet):
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Volunteers see only their own participations, Admins see all
        user = self.request.user
        if user.role == 'ADMIN':
            return Participation.objects.all()
        return Participation.objects.filter(volunteer=user)

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
        
        # Get participations
        participations = Participation.objects.filter(volunteer_id=pk)
        
        data = []
        for p in participations:
            data.append({
                'participation_id': p.id,
                'event_title': p.event.title,
                'event_date': p.event.date,
                'event_status': p.event.status,
                'type': p.type,
                'status': p.status,
                'attendance': p.attendance,
                'attendance_at': p.attendance_at
            })
            
        return Response(data)
