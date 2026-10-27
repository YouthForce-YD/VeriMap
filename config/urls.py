from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('api/upozillas/', views.get_upozillas_api, name='api_upozillas'),

    path('receiver/dashboard/', views.receiver_dashboard, name='receiver_dashboard'),
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('donor/payment/<int:demand_id>/', views.payment_view, name='payment'),
    path('donor/receipt/<int:payment_id>/', views.download_donation_receipt, name='download_receipt'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
