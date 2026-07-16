from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from events.models import Event, Participation, Announcement

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
        url_punch = reverse('punch_in', kwargs={'event_id': event_id})
        response = self.client.post(url_punch)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Participation
        part = Participation.objects.get(event_id=event_id, volunteer=self.volunteer)
        self.assertIsNotNone(part.punch_in)

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
        from django.utils import timezone
        Participation.objects.create(
            event=event, volunteer=self.volunteer, punch_in=timezone.now()
        )

        self.client.force_authenticate(user=self.volunteer)
        url_report = reverse('volunteer_report', kwargs={'pk': self.volunteer.id})
        response = self.client.get(url_report)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        self.assertEqual(response.data[0]['event_title'], "Report Event")

    def test_announcement_lifecycle(self):
        # 1. Non-admin user (volunteer) tries to create announcement -> Denied
        self.client.force_authenticate(user=self.volunteer)
        url_announcements = '/api/announcements/'
        announcement_data = {
            'title': 'Volunteer Title',
            'content': 'Volunteer Content'
        }
        response = self.client.post(url_announcements, announcement_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Admin creates announcement -> Success
        self.client.force_authenticate(user=self.admin)
        announcement_data = {
            'title': 'System Maintenance',
            'content': 'We are performing system maintenance tonight.'
        }
        response = self.client.post(url_announcements, announcement_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'System Maintenance')
        self.assertEqual(response.data['content'], 'We are performing system maintenance tonight.')
        announcement_id = response.data['id']

        # Verify that a notification was sent to the volunteer
        self.client.force_authenticate(user=self.volunteer)
        response_notif = self.client.get('/api/notifications/')
        self.assertEqual(response_notif.status_code, status.HTTP_200_OK)
        # Verify the notification exists and is marked for the volunteer
        self.assertTrue(len(response_notif.data['results']) > 0)
        notif = response_notif.data['results'][0]
        self.assertEqual(notif['verb'], 'New Announcement')
        self.assertEqual(notif['description'], 'We are performing system maintenance tonight.')
        self.assertEqual(notif['target']['type'], 'announcement')
        self.assertEqual(notif['target']['id'], announcement_id)

        # 3. Admin updates announcement -> Success, notifications updated
        self.client.force_authenticate(user=self.admin)
        url_detail = f'/api/announcements/{announcement_id}/'
        update_data = {
            'title': 'System Maintenance UPDATED',
            'content': 'We are performing system maintenance tomorrow morning instead.'
        }
        response = self.client.put(url_detail, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'System Maintenance UPDATED')

        # Verify the notification's description was updated for the volunteer
        self.client.force_authenticate(user=self.volunteer)
        response_notif = self.client.get('/api/notifications/')
        notif = response_notif.data['results'][0]
        self.assertEqual(notif['description'], 'We are performing system maintenance tomorrow morning instead.')

        # 4. Volunteer retrieves announcement list -> Success
        response = self.client.get(url_announcements)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['title'], 'System Maintenance UPDATED')

        # 5. Admin deletes announcement -> Success, and notifications are cleaned up
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(url_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify notifications associated with the announcement are deleted
        self.client.force_authenticate(user=self.volunteer)
        response_notif = self.client.get('/api/notifications/')
        # The list should no longer have the notification since it was deleted
        self.assertEqual(len(response_notif.data['results']), 0)
