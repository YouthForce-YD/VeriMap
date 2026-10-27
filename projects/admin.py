from django.contrib import admin
from .models import Demand, ProjectProgress
# Register your models here.

@admin.register(Demand)
class DemandAdmin(admin.ModelAdmin):
    list_display = ('demand_name', 'receiver', 'zilla', 'upozilla', 'requested_amount', 'donor_amount', 'collected_amount', 'status', 'created_at')
    list_filter = ('status', 'zilla')
    search_fields = ('demand_name', 'receiver__name', 'zilla', 'upozilla')

@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    list_display = ('demand', 'progress_percent', 'last_updated')
    list_filter = ('progress_percent',)

