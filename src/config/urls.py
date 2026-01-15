"""core_banking_loan_service URL Configuration"""
from django.contrib import admin
from django.urls import path, include

app_name = "core_banking_loan_service"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('src.accounts.urls')),
    path('api/v1/journal/', include('src.journal.urls')),
]
