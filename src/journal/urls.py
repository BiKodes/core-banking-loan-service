"""URL configuration for journal app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JournalEntryViewSet, JournalEntryLineViewSet

app_name = 'journal'

router = DefaultRouter()
router.register(r'entries', JournalEntryViewSet, basename='entry')
router.register(r'lines', JournalEntryLineViewSet, basename='line')

urlpatterns = [
    path('', include(router.urls)),
]
