from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['id'] = self.user.id
        data['username'] = self.user.username
        data['name'] = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        data['email'] = self.user.email
        return data

class UserSerializer(serializers.ModelSerializer):
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'department', 'gender', 'initial_password', 'total_hours']

    def get_total_hours(self, obj):
        from django.db.models import Sum
        total = obj.participations.aggregate(Sum('log_hours'))['log_hours__sum']
        return round(total, 2) if total else 0.0

    def validate(self, attrs):
        # If first_name is empty during creation, set it to Volunteer(username)
        if not self.instance:
            if not attrs.get('first_name'):
                username = attrs.get('username')
                attrs['first_name'] = f"Volunteer({username})"
        return attrs

class BaseRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'phone']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class VolunteerRegistrationSerializer(BaseRegistrationSerializer):
    department = serializers.CharField(required=True)
    gender = serializers.CharField(required=True)

    class Meta(BaseRegistrationSerializer.Meta):
        fields = BaseRegistrationSerializer.Meta.fields + ['department', 'gender']

    def create(self, validated_data):
        validated_data['role'] = User.Role.VOLUNTEER
        # Volunteers are NOT staff and NOT superusers
        validated_data['is_staff'] = False
        validated_data['is_superuser'] = False
        return super().create(validated_data)

class AdminRegistrationSerializer(BaseRegistrationSerializer):
    class Meta(BaseRegistrationSerializer.Meta):
        fields = BaseRegistrationSerializer.Meta.fields

    def create(self, validated_data):
        validated_data['role'] = User.Role.ADMIN
        # Admins ARE staff and ARE superusers
        validated_data['is_staff'] = True
        validated_data['is_superuser'] = True
        return super().create(validated_data)
