from django.contrib import admin
from .models import Event, Participation

# Register your models here.

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'start_time', 'venue', 'organizer', 'status', 'attendance_status')
    list_filter = ('status', 'attendance_status', 'date')
    search_fields = ('title', 'venue', 'organizer')
    ordering = ('-date',)

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'event', 'type', 'status', 'punch_in', 'punch_out')
    list_filter = ('type', 'status')
    search_fields = ('volunteer__username', 'event__title')
