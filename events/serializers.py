from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    total_participants = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = '__all__'

    def get_total_participants(self, obj):
        if hasattr(obj, 'annotated_total_participants'):
            return obj.annotated_total_participants
        return obj.participations.count()

from .models import Participation

class ParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participation
        fields = '__all__'
        read_only_fields = ('volunteer',)

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None

        # Prevent volunteers from setting status or log_hours
        if user and user.role == 'VOLUNTEER':
            if 'status' in attrs:
                attrs.pop('status')
            if 'log_hours' in attrs:
                attrs.pop('log_hours')

        event = attrs.get('event')
        if not event:
             # In partial updates, event might not be in attrs, get from instance
             if self.instance:
                 event = self.instance.event
             else:
                 raise serializers.ValidationError("Event is required.")

        # Check if event is full (only when creating new participation)
        if not self.instance:
            current_count = event.participations.count()
            limit = event.participants 

            if limit > 0 and current_count >= limit:
                 raise serializers.ValidationError(f"Event '{event.title}' is full. Quota filled.")

        return attrs

    def create(self, validated_data):
        # Auto-accept the participation for volunteers
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.role == 'VOLUNTEER':
            validated_data['status'] = Participation.Status.APPROVED
        return super().create(validated_data)


class EventListSerializer(serializers.ModelSerializer):
    total_participants = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'date', 'start_time', 'end_time', 'venue', 
            'organizer', 'status', 'attendance_status', 'participants', 'total_participants', 'max_rovers'
        ]

    def get_total_participants(self, obj):
        if hasattr(obj, 'annotated_total_participants'):
            return obj.annotated_total_participants
        return obj.participations.count()


from .models import Announcement

class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'date', 'author', 'author_name', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']
