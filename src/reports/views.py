"""Financial reporting views."""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Q, F, Sum, Case, When, DecimalField, Count, Value, CharField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from src.accounts.models import Account, JournalEntry, JournalEntryLine
from src.loans_management.models import Loan
from .serializers import (
    AccountBalanceReportSerializer,
    TransactionHistorySerializer,
    TrialBalanceSerializer,
    BalanceSheetSerializer,
    LoanAgingReportSerializer,
)
from .export import (
    export_account_balance_report,
    export_transaction_history_report,
    export_trial_balance_report,
    export_balance_sheet_report,
    export_loan_aging_report,
    export_account_balance_pdf,
    export_transaction_history_pdf,
    export_trial_balance_pdf,
    export_balance_sheet_pdf,
    export_loan_aging_pdf,
    get_excel_response,
    get_pdf_response,
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for reports."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_balance_report(request, account_id):
    """
    Get account balance (current or historical).
    """
    as_of_date_str = request.query_params.get('as_of_date')
    
    if as_of_date_str:
        try:
            as_of_date = datetime.fromisoformat(as_of_date_str.replace('Z', '+00:00'))
        except ValueError:
            return Response(
                {"error": "Invalid as_of_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        as_of_date = timezone.now()
    
    try:
        account = Account.objects.get(pk=account_id)
    except Account.DoesNotExist:
        return Response(
            {"error": "Account not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    lines = JournalEntryLine.objects.filter(
        account=account,
        journal_entry__posted_at__lte=as_of_date,
        journal_entry__status='POSTED'
    ).aggregate(
        debit_sum=Coalesce(Sum('debit'), Decimal('0.00')),
        credit_sum=Coalesce(Sum('credit'), Decimal('0.00'))
    )
    
    debit_total = lines['debit_sum']
    credit_total = lines['credit_sum']
    
    if account.account_type in ['ASSET', 'EXPENSE']:
        balance = debit_total - credit_total
    else:
        balance = credit_total - debit_total
    
    export_format = request.query_params.get('format', 'json').lower()
    
    if export_format == 'xlsx':
        account_data = {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'balance': balance,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'as_of_date': as_of_date,
        }
        wb = export_account_balance_report(account_data)
        return get_excel_response(f'account_balance_{account.code}_{as_of_date.date()}', wb)
    
    elif export_format == 'pdf':
        account_data = {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'balance': balance,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'as_of_date': as_of_date,
        }
        pdf_bytes = export_account_balance_pdf(account_data)
        return get_pdf_response(f'account_balance_{account.code}_{as_of_date.date()}', pdf_bytes)
    
    data = {
        'account_id': account.id,
        'account_code': account.code,
        'account_name': account.name,
        'account_type': account.account_type,
        'currency': account.currency,
        'balance': balance,
        'debit_total': debit_total,
        'credit_total': credit_total,
        'as_of_date': as_of_date,
    }
    
    serializer = AccountBalanceReportSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history_report(request, account_id):
    """
    Get paginated transaction history for an account with running balance.
    """
    try:
        account = Account.objects.get(pk=account_id)
    except Account.DoesNotExist:
        return Response(
            {"error": "Account not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    lines_qs = JournalEntryLine.objects.filter(
        account=account,
        journal_entry__status='POSTED'
    ).select_related('journal_entry').order_by('journal_entry__posted_at', 'id')
    
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            lines_qs = lines_qs.filter(journal_entry__posted_at__gte=start_date)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            lines_qs = lines_qs.filter(journal_entry__posted_at__lte=end_date)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    export_format = request.query_params.get('format', 'json').lower()
    
    if export_format == 'xlsx':
        all_lines = lines_qs[:5000]
    else:
        all_lines = lines_qs
    
    transactions = []
    running_balance = Decimal('0.00')
    
    for line in all_lines:
        entry = line.journal_entry
        
        if account.account_type in ['ASSET', 'EXPENSE']:
            running_balance += line.debit - line.credit
        else:
            running_balance += line.credit - line.debit
        
        transactions.append({
            'transaction_id': entry.id,
            'date': entry.posted_at,
            'idempotency_key': entry.idempotency_key,
            'description': entry.description,
            'entry_type': line.entry_type,
            'debit': line.debit,
            'credit': line.credit,
            'running_balance': running_balance,
            'status': entry.status,
        })
    
    if export_format == 'xlsx':
        export_data = {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'transactions': transactions,
        }
        wb = export_transaction_history_report(export_data)
        return get_excel_response(f'transaction_history_{account.code}_{datetime.now().date()}', wb)
    
    elif export_format == 'pdf':
        export_data = {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'transactions': transactions,
        }
        pdf_bytes = export_transaction_history_pdf(export_data)
        return get_pdf_response(f'transaction_history_{account.code}_{datetime.now().date()}', pdf_bytes)
    
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(transactions, request)
    
    serializer = TransactionHistorySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trial_balance_report(request):
    """
    Generate trial balance report.
    """
    as_of_date_str = request.query_params.get('as_of_date')
    currency = request.query_params.get('currency')
    
    if as_of_date_str:
        try:
            as_of_date = datetime.fromisoformat(as_of_date_str.replace('Z', '+00:00'))
        except ValueError:
            return Response(
                {"error": "Invalid as_of_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        as_of_date = timezone.now()
    
    accounts_qs = Account.objects.filter(is_active=True)
    if currency:
        accounts_qs = accounts_qs.filter(currency=currency)
    
    accounts = accounts_qs.order_by('account_type', 'code')
    
    lines = []
    total_debits = Decimal('0.00')
    total_credits = Decimal('0.00')
    
    for account in accounts:
        aggregates = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__posted_at__lte=as_of_date,
            journal_entry__status='POSTED'
        ).aggregate(
            debit_sum=Coalesce(Sum('debit'), Decimal('0.00')),
            credit_sum=Coalesce(Sum('credit'), Decimal('0.00'))
        )
        
        debit_total = aggregates['debit_sum']
        credit_total = aggregates['credit_sum']
        
        if account.account_type in ['ASSET', 'EXPENSE']:
            net_balance = debit_total - credit_total
            if net_balance > 0:
                debit_balance = net_balance
                credit_balance = Decimal('0.00')
            else:
                debit_balance = Decimal('0.00')
                credit_balance = abs(net_balance)
        else:
            net_balance = credit_total - debit_total
            if net_balance > 0:
                credit_balance = net_balance
                debit_balance = Decimal('0.00')
            else:
                credit_balance = Decimal('0.00')
                debit_balance = abs(net_balance)
        
        if debit_balance > 0 or credit_balance > 0:
            lines.append({
                'account_type': account.account_type,
                'account_code': account.code,
                'account_name': account.name,
                'debit_balance': debit_balance,
                'credit_balance': credit_balance,
            })
            
            total_debits += debit_balance
            total_credits += credit_balance
    
    data = {
        'as_of_date': as_of_date,
        'currency': currency,
        'lines': lines,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'is_balanced': abs(total_debits - total_credits) < Decimal('0.01'),
    }
    
    export_format = request.query_params.get('format', 'json').lower()
    
    if export_format == 'xlsx':
        export_data = {
            'accounts': lines,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': data['is_balanced'],
            'as_of_date': as_of_date,
        }
        wb = export_trial_balance_report(export_data)
        return get_excel_response(f'trial_balance_{as_of_date.date()}', wb)
    
    elif export_format == 'pdf':
        export_data = {
            'accounts': lines,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': data['is_balanced'],
            'as_of_date': as_of_date,
        }
        pdf_bytes = export_trial_balance_pdf(export_data)
        return get_pdf_response(f'trial_balance_{as_of_date.date()}', pdf_bytes)
    
    serializer = TrialBalanceSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def balance_sheet_report(request):
    """
    Generate balance sheet report.
    """
    as_of_date_str = request.query_params.get('as_of_date')
    currency = request.query_params.get('currency')
    
    if as_of_date_str:
        try:
            as_of_date = datetime.fromisoformat(as_of_date_str.replace('Z', '+00:00'))
        except ValueError:
            return Response(
                {"error": "Invalid as_of_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        as_of_date = timezone.now()
    
    def get_account_balances(account_type):
        accounts_qs = Account.objects.filter(is_active=True, account_type=account_type)
        if currency:
            accounts_qs = accounts_qs.filter(currency=currency)
        
        accounts = accounts_qs.order_by('code')
        section_accounts = []
        section_total = Decimal('0.00')
        
        for account in accounts:
            aggregates = JournalEntryLine.objects.filter(
                account=account,
                journal_entry__posted_at__lte=as_of_date,
                journal_entry__status='POSTED'
            ).aggregate(
                debit_sum=Coalesce(Sum('debit'), Decimal('0.00')),
                credit_sum=Coalesce(Sum('credit'), Decimal('0.00'))
            )
            
            debit_total = aggregates['debit_sum']
            credit_total = aggregates['credit_sum']
            
            if account_type in ['ASSET']:
                balance = debit_total - credit_total
            else:
                balance = credit_total - debit_total
            
            if balance != 0:
                section_accounts.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'balance': balance,
                })
                section_total += balance
        
        return section_accounts, section_total
    
    asset_accounts, total_assets = get_account_balances('ASSET')
    liability_accounts, total_liabilities = get_account_balances('LIABILITY')
    equity_accounts, total_equity = get_account_balances('EQUITY')
    
    total_liabilities_and_equity = total_liabilities + total_equity
    
    data = {
        'as_of_date': as_of_date,
        'currency': currency,
        'assets': {
            'section_name': 'Assets',
            'accounts': asset_accounts,
            'total': total_assets,
        },
        'liabilities': {
            'section_name': 'Liabilities',
            'accounts': liability_accounts,
            'total': total_liabilities,
        },
        'equity': {
            'section_name': 'Equity',
            'accounts': equity_accounts,
            'total': total_equity,
        },
        'total_assets': total_assets,
        'total_liabilities_and_equity': total_liabilities_and_equity,
        'is_balanced': abs(total_assets - total_liabilities_and_equity) < Decimal('0.01'),
    }
    
    export_format = request.query_params.get('format', 'json').lower()
    
    if export_format == 'xlsx':
        export_data = {
            'assets': asset_accounts,
            'liabilities': liability_accounts,
            'equity': equity_accounts,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'is_balanced': data['is_balanced'],
            'as_of_date': as_of_date,
        }
        wb = export_balance_sheet_report(export_data)
        return get_excel_response(f'balance_sheet_{as_of_date.date()}', wb)
    
    elif export_format == 'pdf':
        export_data = {
            'assets': asset_accounts,
            'liabilities': liability_accounts,
            'equity': equity_accounts,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'is_balanced': data['is_balanced'],
            'as_of_date': as_of_date,
        }
        pdf_bytes = export_balance_sheet_pdf(export_data)
        return get_pdf_response(f'balance_sheet_{as_of_date.date()}', pdf_bytes)
    
    serializer = BalanceSheetSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_aging_report(request):
    """
    Generate loan aging report.
    """
    as_of_date_str = request.query_params.get('as_of_date')
    currency = request.query_params.get('currency')
    include_detail = request.query_params.get('include_detail', 'false').lower() == 'true'
    
    if as_of_date_str:
        try:
            as_of_date = datetime.fromisoformat(as_of_date_str.replace('Z', '+00:00'))
        except ValueError:
            return Response(
                {"error": "Invalid as_of_date format. Use ISO 8601 format."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        as_of_date = timezone.now()
    
    loans_qs = Loan.objects.filter(
        status__in=['ACTIVE', 'DEFAULTED'],
        outstanding_principal__gt=0
    ).select_related('borrower')
    
    if currency:
        loans_qs = loans_qs.filter(currency=currency)
    
    buckets = {
        'current': {'name': 'Current', 'range': '0-29 days', 'min': 0, 'max': 29, 'loans': []},
        '30_59': {'name': '30-59 Days', 'range': '30-59 days', 'min': 30, 'max': 59, 'loans': []},
        '60_89': {'name': '60-89 Days', 'range': '60-89 days', 'min': 60, 'max': 89, 'loans': []},
        '90_plus': {'name': '90+ Days', 'range': '90+ days', 'min': 90, 'max': 999999, 'loans': []},
    }
    
    total_loans = 0
    total_outstanding = Decimal('0.00')
    
    for loan in loans_qs:
        if not loan.due_date:
            continue
        
        days_overdue = (as_of_date.date() - loan.due_date).days
        
        bucket_key = None
        if 0 <= days_overdue <= 29:
            bucket_key = 'current'
        elif 30 <= days_overdue <= 59:
            bucket_key = '30_59'
        elif 60 <= days_overdue <= 89:
            bucket_key = '60_89'
        elif days_overdue >= 90:
            bucket_key = '90_plus'
        
        if bucket_key:
            loan_data = {
                'loan_id': loan.id,
                'borrower_name': loan.borrower.full_name,
                'principal_amount': loan.principal_amount,
                'outstanding_principal': loan.outstanding_principal,
                'accrued_interest': loan.accrued_interest,
                'disbursed_at': loan.disbursed_at,
                'due_date': loan.due_date,
                'days_overdue': days_overdue,
                'status': loan.status,
            }
            buckets[bucket_key]['loans'].append(loan_data)
            total_loans += 1
            total_outstanding += loan.outstanding_principal + loan.accrued_interest
    
    bucket_summaries = []
    for key, bucket in buckets.items():
        loan_count = len(bucket['loans'])
        total_principal = sum(loan['outstanding_principal'] for loan in bucket['loans'])
        total_interest = sum(loan['accrued_interest'] for loan in bucket['loans'])
        total = total_principal + total_interest
        
        bucket_summaries.append({
            'bucket_name': bucket['name'],
            'days_range': bucket['range'],
            'loan_count': loan_count,
            'total_outstanding': total,
            'total_principal': total_principal,
            'total_interest': total_interest,
        })
    
    loans_detail = []
    if include_detail:
        for bucket in buckets.values():
            loans_detail.extend(bucket['loans'])
    
    data = {
        'as_of_date': as_of_date,
        'currency': currency,
        'buckets': bucket_summaries,
        'total_loans': total_loans,
        'total_outstanding': total_outstanding,
        'loans_detail': loans_detail if include_detail else [],
    }
    
    export_format = request.query_params.get('format', 'json').lower()
    
    if export_format == 'xlsx':
        export_data = {
            'summary': bucket_summaries,
            'total_outstanding': total_outstanding,
            'loan_details': loans_detail if include_detail else [],
            'as_of_date': as_of_date,
        }
        wb = export_loan_aging_report(export_data)
        return get_excel_response(f'loan_aging_{as_of_date.date()}', wb)
    
    elif export_format == 'pdf':
        export_data = {
            'summary': bucket_summaries,
            'total_outstanding': total_outstanding,
            'loan_details': loans_detail if include_detail else [],
            'as_of_date': as_of_date,
        }
        pdf_bytes = export_loan_aging_pdf(export_data)
        return get_pdf_response(f'loan_aging_{as_of_date.date()}', pdf_bytes)
    
    serializer = LoanAgingReportSerializer(data)
    return Response(serializer.data)
