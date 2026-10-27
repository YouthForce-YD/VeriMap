from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

bd_phone_validator = RegexValidator(
    regex=r'^01[3-9]\d{8}$',
    message="Enter a valid Bangladeshi phone number (like: 017XXXXXXXX) ."
)

nid_validator = RegexValidator(
    regex=r'^(\d{10}|\d{13}|\d{17})$',
    message="Enter a valid NID number (10, 13, or 17 digits)."
)

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('donor', 'Donor'),
        ('receiver', 'Receiver'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, validators=[bd_phone_validator], unique=True)
    national_id = models.CharField(max_length=20, validators=[nid_validator], unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES, default='donor')
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    @property
    def phone(self):
        return self.phone_number

    @phone.setter
    def phone(self, value):
        self.phone_number = value

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.user_type = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_user_type_display()})"
