from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from io import BytesIO

User = get_user_model()

class AccountsAutomatedTests(APITestCase):
    
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

    def test_authentication_flow(self):
        url = reverse('token_obtain_pair')
        data = {'username': 'volunteer1', 'password': 'userpass'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_password_management(self):
        # 1. Admin Reset User Password
        self.client.force_authenticate(user=self.admin)
        url = reverse('password_management')
        data = {'user_id': self.volunteer.id, 'new_password': 'newadminpass'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.volunteer.refresh_from_db()
        self.assertTrue(self.volunteer.check_password('newadminpass'))

        # 2. User Changes Own Password
        self.client.force_authenticate(user=self.volunteer)
        data = {'old_password': 'newadminpass', 'new_password': 'selfchangedpass'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.volunteer.refresh_from_db()
        self.assertTrue(self.volunteer.check_password('selfchangedpass'))

    def test_csv_import_export(self):
        self.client.force_authenticate(user=self.admin)
        
        # Test Export
        url_export = reverse('volunteer_export')
        response = self.client.get(url_export)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # Test Import
        url_import = reverse('volunteer_import')
        csv_content = b"Username,Email,First Name,Last Name\nimportuser,imp@test.com,Imp,User"
        file = BytesIO(csv_content)
        file.name = 'test_volunteers.csv'
        response = self.client.post(url_import, {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(username='importuser').exists())
