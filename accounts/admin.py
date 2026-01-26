from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from django.utils.html import format_html

# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'blood_group', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active', 'blood_group']
    # Add custom fields to the admin interface
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone', 'department', 'alternative_email', 'blood_group', 'image_url', 'display_image')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone', 'department', 'alternative_email', 'blood_group', 'image_url', 'display_image')}),
    )

    # user profile image
    readonly_fields=('display_image',)

    def display_image(self, obj) :
        if obj.image_url :
            return format_html('<img src="{}" style="width: 200px; height: 200px; object-fit: cover;" />', obj.image_url)
        return "No Image"
    # Set the column name in the admin table
    display_image.short_description = 'Profile Picture'