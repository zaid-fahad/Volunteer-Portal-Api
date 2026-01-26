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

class VolunteerListView(generics.ListCreateAPIView):
    queryset = User.objects.filter(role=User.Role.VOLUNTEER)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        from .utils import create_random_password
        
        # Generate random password
        random_password = create_random_password()
        
        # Derive email from username
        username = serializer.validated_data.get('username')
        email = f"{username}@iub.edu.bd"
        
        # Save user with generated fields
        user = serializer.save(
            role=User.Role.VOLUNTEER,
            email=email,
            initial_password=random_password
        )
        user.set_password(random_password)
        user.save()
        
        logger_admin.info(f"Admin {self.request.user.username} added volunteer: {user.username} with generated email and password.")

class VolunteerDetailView(generics.RetrieveUpdateDestroyAPIView):
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

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        data = request.data
        
        # Define allowed fields based on role
        if user.role == User.Role.VOLUNTEER:
            # Volunteers can update name, phone, and department
            allowed_fields = ['first_name', 'last_name', 'phone', 'department']
        else:
            # Admins can update name and phone (department usually not applicable for admin profile UI)
            allowed_fields = ['first_name', 'last_name', 'phone']
            
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
            
        serializer = UserSerializer(user, data=filtered_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import csv
from django.http import HttpResponse

from django.db.models import Sum, Count

class VolunteerCSVExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="volunteers.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Username', 'Full Name', 'Email', 
            'Phone', 'Department', 'Total Events', 'Total Hours'
        ])

        # Fetch volunteers with annotated stats for performance
        volunteers = User.objects.filter(role=User.Role.VOLUNTEER).annotate(
            event_count=Count('participations'),
            hours_sum=Sum('participations__event__log_hour')
        )

        for v in volunteers:
            writer.writerow([
                v.id, 
                v.username, 
                v.first_name,  
                v.email, 
                v.phone, 
                v.department, 
                v.event_count,
                v.hours_sum or 0.0
            ])

        return response

class VolunteerCSVImportView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'File is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not file.name.endswith('.csv'):
             return Response({'error': 'File must be CSV'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = file.read().decode('utf-8-sig') # Handle UTF-8 with BOM
            decoded_file = content.splitlines()
        except UnicodeDecodeError:
            file.seek(0)
            content = file.read().decode('latin-1') 
            decoded_file = content.splitlines()

        reader = csv.DictReader(decoded_file)
        
        # Log headers for debugging
        headers = reader.fieldnames
        logger_admin.info(f"CSV Import attempt. Headers found: {headers}")

        import io
        from .utils import create_random_password, drive_to_img_src

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID (Username)', 'Full Name', 'Email', 'Initial Password', 'Import Status'])
        
        # Map headers to be case-insensitive and stripped
        header_map = {h.strip().lower(): h for h in headers} if headers else {}
        
        def get_row_value(row, *possible_keys):
            for key in possible_keys:
                # Try exact match first
                if key in row:
                    return row[key]
                # Try case-insensitive stripped match
                lower_key = key.strip().lower()
                if lower_key in header_map:
                    return row[header_map[lower_key]]
            return None

        count = 0
        skipped = 0
        error_count = 0
        
        for row in reader:
            username = get_row_value(row, 'IUB ID', 'ID', 'Username', 'Student ID')
            if not username:
                skipped += 1
                continue
            
            username = str(username).strip()
            
            try:
                if User.objects.filter(username=username).exists():
                    writer.writerow([username, '', '', '', 'Skipped: Already exists'])
                    skipped += 1
                    continue

                random_password = create_random_password()
                email = get_row_value(row, 'Email Address', 'IUB email', 'Email') or f"{username}@iub.edu.bd"
                full_name = get_row_value(row, 'Full Name', 'Name') or f"Volunteer({username})"
                last_name = get_row_value(row, 'Last Name') or ""
                phone = get_row_value(row, 'Phone Number', 'Phone')
                
                # Handle scientific notation for phone numbers (common Excel issue)
                if phone and ('E+' in str(phone) or 'e+' in str(phone)):
                    try:
                        phone = str(int(float(phone)))
                    except:
                        pass

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=random_password,
                    first_name=full_name,
                    last_name=last_name,
                    role=User.Role.VOLUNTEER,
                    phone=phone,
                    department=get_row_value(row, 'Majoring Department ', 'Department', 'Major') or "",
                    alternative_email = get_row_value(row, 'Alternative email'),
                    blood_group = get_row_value(row, 'Blood Group'),
                    image_url = drive_to_img_src(get_row_value(row, 'Photo (Please upload a decent photo)', 'Photo', 'Image')),
                )
                
                user.initial_password = random_password
                user.save()
                
                writer.writerow([username, full_name, email, random_password, 'Success'])
                count += 1
            except Exception as e:
                logger.error(f"Error importing volunteer {username}: {str(e)}")
                writer.writerow([username, '', '', '', f'Error: {str(e)}'])
                error_count += 1

        logger_admin.info(f"CSV Import finished. Success: {count}, Skipped (mostly empty rows): {skipped}, Errors: {error_count}")

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="imported_credentials_{count}.csv"'
        return response
