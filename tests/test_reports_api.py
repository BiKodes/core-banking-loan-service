"""Tests for reports API endpoints with export functionality."""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from src.accounts.models import Account, JournalEntry, JournalEntryLine
from src.loans_management.models import Loan, Borrower


class ReportsExportAPITestCase(APITestCase):
    """Test cases for reports API with export functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        
        self.cash_account = Account.objects.create(
            code='AC-001',
            name='Cash',
            description='Company cash account',
            account_type='ASSET',
            currency='KES',
            is_active=True,
        )
        
        self.income_account = Account.objects.create(
            code='IN-001',
            name='Sales Revenue',
            description='Income from sales',
            account_type='INCOME',
            currency='KES',
            is_active=True,
        )
    
    def test_account_balance_report_json(self):
        """Test account balance report in JSON format."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(f'{url}?format=json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_id', response.data)
        self.assertEqual(response.data['account_id'], self.cash_account.id)
    
    def test_account_balance_report_excel(self):
        """Test account balance report in Excel format."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(f'{url}?format=xlsx')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('Content-Disposition', response)
    
    def test_account_balance_report_pdf_not_implemented(self):
        """Test account balance report PDF returns 501."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(f'{url}?format=pdf')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', response)
    
    def test_transaction_history_report_json(self):
        """Test transaction history report in JSON format."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/transactions/'
        response = self.client.get(f'{url}?format=json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_transaction_history_report_excel(self):
        """Test transaction history report in Excel format."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/transactions/'
        response = self.client.get(f'{url}?format=xlsx')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def test_transaction_history_report_pdf(self):
        """Test transaction history report in PDF format."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/transactions/'
        response = self.client.get(f'{url}?format=pdf')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', response)
    
    def test_trial_balance_report_json(self):
        """Test trial balance report in JSON format."""
        url = '/api/v1/reports/trial-balance/'
        response = self.client.get(f'{url}?format=json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('lines', response.data)
        self.assertIn('is_balanced', response.data)
    
    def test_trial_balance_report_excel(self):
        """Test trial balance report in Excel format."""
        url = '/api/v1/reports/trial-balance/'
        response = self.client.get(f'{url}?format=xlsx')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def test_trial_balance_report_pdf(self):
        """Test trial balance report in PDF format."""
        url = '/api/v1/reports/trial-balance/'
        response = self.client.get(f'{url}?format=pdf')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', response)
    
    def test_balance_sheet_report_json(self):
        """Test balance sheet report in JSON format."""
        url = '/api/v1/reports/balance-sheet/'
        response = self.client.get(f'{url}?format=json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('assets', response.data)
        self.assertIn('liabilities', response.data)
        self.assertIn('equity', response.data)
    
    def test_balance_sheet_report_excel(self):
        """Test balance sheet report in Excel format."""
        url = '/api/v1/reports/balance-sheet/'
        response = self.client.get(f'{url}?format=xlsx')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def test_balance_sheet_report_pdf(self):
        """Test balance sheet report in PDF format."""
        url = '/api/v1/reports/balance-sheet/'
        response = self.client.get(f'{url}?format=pdf')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', response)
    
    def test_loan_aging_report_json(self):
        """Test loan aging report in JSON format."""
        url = '/api/v1/reports/loan-aging/'
        response = self.client.get(f'{url}?format=json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('buckets', response.data)
    
    def test_loan_aging_report_excel(self):
        """Test loan aging report in Excel format."""
        url = '/api/v1/reports/loan-aging/'
        response = self.client.get(f'{url}?format=xlsx')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def test_loan_aging_report_pdf(self):
        """Test loan aging report in PDF format."""
        url = '/api/v1/reports/loan-aging/'
        response = self.client.get(f'{url}?format=pdf')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', response)
    
    def test_format_parameter_case_insensitive(self):
        """Test that format parameter is case-insensitive."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(f'{url}?format=XLSX')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    def test_default_format_is_json(self):
        """Test that default format is JSON when not specified."""
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('account_id', response.data)
    
    def test_account_not_found(self):
        """Test 404 when account doesn't exist."""
        url = '/api/v1/reports/accounts/99999/balance/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access reports."""
        self.client.force_authenticate(user=None)
        
        url = f'/api/v1/reports/accounts/{self.cash_account.id}/balance/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
