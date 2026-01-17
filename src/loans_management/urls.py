"""URL configuration for loans management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BorrowerViewSet,
    LenderViewSet,
    LoanEventViewSet,
    LoanRepaymentViewSet,
    LoanViewSet,
)

app_name = 'loans_management'

router = DefaultRouter()
router.register(r'borrowers', BorrowerViewSet, basename='borrower')
router.register(r'lenders', LenderViewSet, basename='lender')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'repayments', LoanRepaymentViewSet, basename='repayment')
router.register(r'events', LoanEventViewSet, basename='loan-event')

urlpatterns = [
    path('', include(router.urls)),
]
