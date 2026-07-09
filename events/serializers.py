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
        read_only_fields = ('status', 'volunteer', 'log_hours') # Removed attendance

    def validate(self, attrs):
        event = attrs.get('event')
        if not event:
             # In partial updates, event might not be in attrs, get from instance
             if self.instance:
                 event = self.instance.event
             else:
                 raise serializers.ValidationError("Event is required.")

        # Check if event is full
        current_count = event.participations.count()
        # 'participants' field in Event model is the capacity limit
        limit = event.participants 

        if limit > 0 and current_count >= limit:
             raise serializers.ValidationError(f"Event '{event.title}' is full. Quota filled.")

        return attrs

    def create(self, validated_data):
        # Auto-accept the participation
        validated_data['status'] = Participation.Status.APPROVED # Using APPROVED as 'Accepted'
        return super().create(validated_data)


class EventListSerializer(serializers.ModelSerializer):
    total_participants = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'date', 'start_time', 'end_time', 'venue', 
            'organizer', 'status', 'attendance_status', 'participants', 'total_participants'
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
        fields = ['id', 'title', 'content', 'author', 'author_name', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']
