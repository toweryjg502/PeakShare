from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Campus info', {'fields': ('is_verified', 'phone_number')}),
    )
    list_display = ('username', 'email', 'is_verified', 'is_staff')
    list_filter = UserAdmin.list_filter + ('is_verified',)
