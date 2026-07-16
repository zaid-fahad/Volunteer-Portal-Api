import logging
from django.db.models import Sum, Count
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import (
    CustomTokenObtainPairSerializer, 
    VolunteerRegistrationSerializer, 
    AdminRegistrationSerializer, 
    UserSerializer,
    UserListSerializer
)

from rest_framework.filters import SearchFilter

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
    queryset = User.objects.filter(role=User.Role.VOLUNTEER).annotate(
        annotated_total_hours=Sum('participations__log_hours'),
        annotated_total_events=Count('participations')
    )
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'department']

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
    queryset = User.objects.filter(role=User.Role.VOLUNTEER).annotate(
        annotated_total_hours=Sum('participations__log_hours'),
        annotated_total_events=Count('participations')
    )
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
        user = User.objects.filter(id=request.user.id).annotate(
            annotated_total_hours=Sum('participations__log_hours'),
            annotated_total_events=Count('participations')
        ).first()
        serializer = UserSerializer(user)
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
            updated_user = serializer.save()
            # Reload with annotations for clean response serialization
            annotated_user = User.objects.filter(id=updated_user.id).annotate(
                annotated_total_hours=Sum('participations__log_hours'),
                annotated_total_events=Count('participations')
            ).first()
            serializer = UserSerializer(annotated_user)
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

        from django.db import transaction

        count = 0
        skipped = 0
        error_count = 0
        
        with transaction.atomic():
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

from django.core.mail import send_mail, get_connection
from django.conf import settings
from .models import EmailConfiguration, EmailLog
from .serializers import EmailConfigurationSerializer, EmailLogSerializer

def get_email_sender_and_connection():
    config = EmailConfiguration.objects.filter(is_active=True).first()
    if config and config.email_host_user:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=config.email_host,
            port=config.email_port,
            username=config.email_host_user,
            password=config.email_host_password or '',
            use_tls=config.email_use_tls,
        )
        from_email = config.default_from_email or config.email_host_user
        return connection, from_email
    return None, getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@iub.edu.bd')

def send_volunteer_email_logged(subject, message, to_email, sender_user=None):
    connection, from_email = get_email_sender_and_connection()
    try:
        if connection:
            send_mail(subject, message, from_email, [to_email], connection=connection, fail_silently=False)
        else:
            send_mail(subject, message, from_email, [to_email], fail_silently=False)
        
        EmailLog.objects.create(
            recipient=to_email,
            subject=subject,
            status='Success',
            sender=sender_user
        )
        return True, None
    except Exception as e:
        error_msg = str(e)
        EmailLog.objects.create(
            recipient=to_email,
            subject=subject,
            status='Failed',
            error_message=error_msg,
            sender=sender_user
        )
        return False, error_msg


class SendVolunteerCredentialsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Only admins can send credential emails.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            volunteer = User.objects.get(id=id, role=User.Role.VOLUNTEER)
        except User.DoesNotExist:
            return Response({'error': 'Volunteer not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not volunteer.initial_password:
            return Response({'error': 'No generated password found for this volunteer.'}, status=status.HTTP_400_BAD_REQUEST)

        to_email = volunteer.email or f"{volunteer.username}@iub.edu.bd"

        subject = "Your DOSA Volunteer Portal Credentials"
        message = (
            f"Hello {volunteer.first_name or 'Volunteer'},\n\n"
            f"Your account has been created on the DOSA Volunteer Portal.\n\n"
            f"Here are your login credentials:\n"
            f"Student ID (Username): {volunteer.username}\n"
            f"Initial Password: {volunteer.initial_password}\n\n"
            f"You can log in at: http://localhost:3000/login\n\n"
            f"Best regards,\n"
            f"DOSA Admin Team"
        )

        success, error_msg = send_volunteer_email_logged(subject, message, to_email, sender_user=request.user)
        if success:
            return Response({'success': f'Credentials email successfully sent to {to_email}'}, status=status.HTTP_200_OK)
        return Response({'error': f'Failed to send email: {error_msg}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        config = EmailConfiguration.objects.first()
        if not config:
            config = EmailConfiguration.objects.create(
                email_host='smtp.gmail.com',
                email_port=587,
                email_use_tls=True,
                email_host_user='your-email@gmail.com',
                email_host_password='',
                default_from_email='your-email@gmail.com',
                is_active=False
            )
        return config

    def get(self, request):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        config = self.get_object()
        serializer = EmailConfigurationSerializer(config)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        
        config = self.get_object()
        
        # Scenario: Sending a test email
        if 'test_recipient' in request.data:
            recipient = request.data.get('test_recipient')
            if not recipient:
                return Response({'error': 'test_recipient email is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Temporary config parameters to test before saving
            test_host = request.data.get('email_host', config.email_host)
            test_port = int(request.data.get('email_port', config.email_port))
            test_use_tls = request.data.get('email_use_tls', config.email_use_tls)
            test_user = request.data.get('email_host_user', config.email_host_user)
            test_password = request.data.get('email_host_password')
            
            # If password is empty in test payload, fall back to already saved password
            if not test_password and test_user == config.email_host_user:
                test_password = config.email_host_password

            subject = "DOSA Volunteer Portal SMTP Connection Test"
            message = "Congratulations! Your volunteer portal SMTP settings are configured correctly and working."
            
            try:
                test_connection = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=test_host,
                    port=test_port,
                    username=test_user,
                    password=test_password or '',
                    use_tls=test_use_tls,
                )
                from_email = request.data.get('default_from_email', test_user)
                send_mail(subject, message, from_email, [recipient], connection=test_connection, fail_silently=False)
                
                # Log success
                EmailLog.objects.create(
                    recipient=recipient,
                    subject=subject,
                    status='Success',
                    sender=request.user
                )
                return Response({'success': f'Test email sent successfully to {recipient}'}, status=status.HTTP_200_OK)
            except Exception as e:
                # Log failure
                EmailLog.objects.create(
                    recipient=recipient,
                    subject=subject,
                    status='Failed',
                    error_message=str(e),
                    sender=request.user
                )
                return Response({'error': f'SMTP Connection Test Failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Standard config save/update
        serializer = EmailConfigurationSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            # If email_host_password is provided in request, write it
            password = request.data.get('email_host_password')
            if password is not None:
                serializer.save(email_host_password=password)
            else:
                serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailLogListView(generics.ListAPIView):
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['recipient', 'subject', 'status']

    def get_queryset(self):
        if self.request.user.role != 'ADMIN':
            return EmailLog.objects.none()
        return EmailLog.objects.all().order_by('-sent_at')
