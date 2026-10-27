from django.contrib import admin
from .models import Payment

# Register your models here.
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_gateway_ref', 'demand', 'donor', 'amount_paid', 'payment_method', 'payment_status', 'paid_at')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('payment_gateway_ref', 'demand__demand_name', 'donor__name')
