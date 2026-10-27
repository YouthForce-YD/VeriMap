from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email','name','user_type','phone_number','national_id','is_staff')
    list_filter = ('user_type','is_staff','is_active')
    search_fields = ('email','name','phone_number','national_id')
    ordering = ('created_at',)
    fieldsets = UserAdmin.fieldsets + (
        ('CommunityBridge Profile', {'fields':('name','phone_number','national_id','address','user_type') }),
    )
