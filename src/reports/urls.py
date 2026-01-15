"""URL routing for reports app."""

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path(
        'accounts/<int:account_id>/balance/',
        views.account_balance_report,
        name='account-balance'
    ),
    
    path(
        'accounts/<int:account_id>/transactions/',
        views.transaction_history_report,
        name='transaction-history'
    ),
    
    path(
        'trial-balance/',
        views.trial_balance_report,
        name='trial-balance'
    ),
    
    path(
        'balance-sheet/',
        views.balance_sheet_report,
        name='balance-sheet'
    ),
    
    path(
        'loan-aging/',
        views.loan_aging_report,
        name='loan-aging'
    ),
]
