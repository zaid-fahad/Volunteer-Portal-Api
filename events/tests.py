from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from events.models import Event, Participation

User = get_user_model()

class EventsAutomatedTests(APITestCase):
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', 
            email='admin@test.com', 
            password='adminpass',
            role=User.Role.ADMIN
        )
        self.volunteer = User.objects.create_user(
            username='volunteer1', 
            email='vol1@test.com', 
            password='userpass',
            role=User.Role.VOLUNTEER
        )

    def test_event_lifecycle_and_check_in(self):
        self.client.force_authenticate(user=self.admin)
        
        # Create Event
        # NOTE: Using list-create url from router
        url_events = '/api/events/' 
        data = {
            'title': 'Test Event',
            'date': '2025-12-12',
            'start_time': '10:00:00',
            'end_time': '12:00:00',
            'participants': 10,
            'log_hour': 2,
            'venue': 'Test Venue',
            'organizer': 'AdminOrg',
            'status': 'Active'
        }
        response = self.client.post(url_events, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event_id = response.data['id']

        # Volunteer Join/Punch-In
        self.client.force_authenticate(user=self.volunteer)
        # Using custom action url format for routers
        url_punch = f'/api/events/{event_id}/punch-in/'
        response = self.client.post(url_punch)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Participation
        part = Participation.objects.get(event_id=event_id, volunteer=self.volunteer)
        self.assertEqual(part.attendance, 'Yes')
        self.assertIsNotNone(part.attendance_at)

        # Admin Complete Event
        self.client.force_authenticate(user=self.admin)
        url_complete = f'/api/events/{event_id}/complete/'
        response = self.client.put(url_complete)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        event = Event.objects.get(id=event_id)
        self.assertEqual(event.status, 'Done')

    def test_reports(self):
        # Create Event and Participation first
        event = Event.objects.create(
            title="Report Event", date="2025-01-01", start_time="10:00", end_time="11:00", 
            participants=5, log_hour=1, venue="Home", organizer="Me", status="Done"
        )
        Participation.objects.create(
            event=event, volunteer=self.volunteer, attendance="Yes"
        )

        self.client.force_authenticate(user=self.volunteer)
        url_report = reverse('volunteer_report', kwargs={'pk': self.volunteer.id})
        response = self.client.get(url_report)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        self.assertEqual(response.data[0]['event_title'], "Report Event")
