from rest_framework import serializers
from notifications.models import Notification
from django.contrib.contenttypes.models import ContentType
from .models import Event
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    timesince = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'actor', 'verb', 'target', 'unread', 'timestamp', 'timesince', 'description'
        ]

    def get_actor(self, obj):
        if obj.actor:
            if isinstance(obj.actor, User):
                return {
                    'type': 'user',
                    'id': obj.actor.id,
                    'username': obj.actor.username,
                    'name': f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.username
                }
            elif isinstance(obj.actor, Event):
                return {
                    'type': 'event',
                    'id': obj.actor.id,
                    'title': obj.actor.title
                }
            return {'type': 'unknown', 'display': str(obj.actor)}
        return None

    def get_target(self, obj):
        if obj.target:
            # Handle Event target specifically
            if isinstance(obj.target, Event):
                return {
                    'type': 'event',
                    'id': obj.target.id,
                    'title': obj.target.title
                }
            return str(obj.target)
        return None

    def get_timesince(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.timestamp)
