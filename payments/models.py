import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from projects.models import Demand

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    METHOD_CHOICES = (
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
        ('card', 'Card/bank transfer'),
    )
    demand = models.ForeignKey(Demand, on_delete=models.CASCADE, related_name='payments')
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donations')
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bkash')
    payment_gateway_ref = models.CharField(max_length=100, unique=True, editable=False)
    payment_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']

    def clean(self):
        super().clean()
        if self.amount_paid is not None:
            self.amount_paid = Decimal(str(self.amount_paid)).quantize(Decimal('0.01'))
            if self.amount_paid <= Decimal('0.00'):
                raise ValidationError({'amount_paid': 'Payment amount must be greater than zero.'})
        if not self.payment_gateway_ref:
            self.payment_gateway_ref = f"CB-{uuid.uuid4().hex[:10].upper()}"

    def save(self, *args, **kwargs):
        if self.amount_paid is not None:
            self.amount_paid = Decimal(str(self.amount_paid)).quantize(Decimal('0.01'))
        if not self.payment_gateway_ref:
            self.payment_gateway_ref = f"CB-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor.name} - {self.amount_paid} BDT ({self.payment_status})"
