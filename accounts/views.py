import logging
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import (
    CustomTokenObtainPairSerializer, 
    VolunteerRegistrationSerializer, 
    AdminRegistrationSerializer, 
    UserSerializer
)

logger = logging.getLogger('accounts')
logger_admin = logging.getLogger('accounts.admin')
logger_volunteer = logging.getLogger('accounts.volunteer')

User = get_user_model()

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
             logger.info(f"User logged in: {request.data.get('username')}")
        else:
             logger.warning(f"Failed login attempt: {request.data.get('username')}")
        return response

class VolunteerSignupView(generics.CreateAPIView):
    serializer_class = VolunteerRegistrationSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        user = serializer.save()
        logger_volunteer.info(f"New Volunteer registered: {user.username}")

class AdminSignupView(generics.CreateAPIView):
    serializer_class = AdminRegistrationSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        user = serializer.save()
        logger_admin.info(f"New Admin registered: {user.username}")

class VolunteerListView(generics.ListAPIView):
    queryset = User.objects.filter(role=User.Role.VOLUNTEER)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class VolunteerDetailView(generics.RetrieveAPIView):
    queryset = User.objects.filter(role=User.Role.VOLUNTEER)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAdminUser

class PasswordManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data
        
        # Scenario 1: Admin resetting someone else's password
        if user.role == 'ADMIN' and 'user_id' in data:
            target_user_id = data.get('user_id')
            new_password = data.get('new_password')
            
            if not new_password:
                 return Response({'error': 'new_password is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                target_user = User.objects.get(id=target_user_id)
                target_user.set_password(new_password)
                target_user.save()
                logger_admin.info(f"Admin {user.username} reset password for user {target_user.username}")
                return Response({'success': True, 'message': f'Password for {target_user.username} has been reset by Admin.'})
            except User.DoesNotExist:
                logger_admin.warning(f"Admin {user.username} tried to reset password for invalid user_id {target_user_id}")
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Scenario 2: User changing their own password (Admin or Volunteer)
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
             return Response({'error': 'old_password and new_password are required for self-change'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(old_password):
             return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        return Response({'success': True, 'message': 'Your password has been changed successfully.'})

import csv
from django.http import HttpResponse

class VolunteerCSVExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="volunteers.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Username', 'First Name', 'Last Name', 'Email', 'Phone', 'Department', 'Gender'])

        volunteers = User.objects.filter(role=User.Role.VOLUNTEER)
        for v in volunteers:
            writer.writerow([v.id, v.username, v.first_name, v.last_name, v.email, v.phone, v.department, v.gender])

        return response

class VolunteerCSVImportView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'File is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith('.csv'):
             return Response({'error': 'File must be CSV'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        count = 0
        errors = []
        
        for row in reader:
            try:
                # Basic check for required
                username = row.get('Username') or row.get('username')
                email = row.get('Email') or row.get('email')
                password = "DefaultPassword123!" # Hardcoded default for import, admin should force reset or include in CSV

                if not username:
                    continue
                
                if User.objects.filter(username=username).exists():
                    errors.append(f"Skipped {username}: already exists")
                    continue

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=row.get('First Name', ''),
                    last_name=row.get('Last Name', ''),
                    role=User.Role.VOLUNTEER,
                    phone=row.get('Phone', ''),
                    department=row.get('Department', ''),
                    gender=row.get('Gender', '')
                )
                count += 1
            except Exception as e:
                errors.append(f"Error importing row {row}: {str(e)}")

        return Response({'success': True, 'imported': count, 'errors': errors})
