"""Views for accounts app."""

from decimal import Decimal
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import Account, AccountBalance
from .serializers import (
    AccountSerializer, AccountListSerializer, AccountHierarchySerializer,
    AccountBalanceSerializer
)


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Account management."""

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['account_type', 'currency', 'is_active', 'parent']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'account_type', 'created_at']
    ordering = ['code']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AccountListSerializer
        elif self.action == 'hierarchy':
            return AccountHierarchySerializer
        return AccountSerializer

    def create(self, request, *args, **kwargs):
        """Create a new account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get account balance as of a specific date."""
        account = self.get_object()
        as_of_date = request.query_params.get('as_of_date')

        if as_of_date:
            try:
                as_of_date = datetime.fromisoformat(as_of_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            as_of_date = timezone.now()

        balance = account.get_balance(as_of_date)
        return Response({
            'account_code': account.code,
            'account_name': account.name,
            'balance': float(balance),
            'as_of_date': as_of_date.isoformat(),
            'currency': account.currency
        })

    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get account hierarchy for a specific root account."""
        root_code = request.query_params.get('root')
        if not root_code:
            return Response(
                {'error': 'root parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            root_account = Account.objects.get(code=root_code, parent__isnull=True)
        except Account.DoesNotExist:
            return Response(
                {'error': f'Root account {root_code} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AccountHierarchySerializer(root_account)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get accounts by type."""
        account_type = request.query_params.get('type')
        if not account_type:
            return Response(
                {'error': 'type parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        accounts = Account.objects.filter(account_type=account_type)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance_history(self, request, pk=None):
        """Get balance history for an account."""
        account = self.get_object()
        snapshots = account.balance_snapshots.all()

        paginator = self.paginator
        if paginator:
            page = paginator.paginate_queryset(snapshots, request)
            serializer = AccountBalanceSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AccountBalanceSerializer(snapshots, many=True)
        return Response(serializer.data)

