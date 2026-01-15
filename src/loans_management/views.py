"""Viewsets for loan management."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Borrower, Lender, Loan, LoanRepayment, LoanEvent
from .serializers import (
	BorrowerSerializer,
	LenderSerializer,
	LoanSerializer,
	LoanCreateSerializer,
	LoanDisbursementSerializer,
	LoanRepaymentSerializer,
	LoanWriteOffSerializer,
	LoanInterestAccrualSerializer,
	LoanRepaymentListSerializer,
	LoanEventSerializer,
)


class BorrowerViewSet(viewsets.ModelViewSet):
	queryset = Borrower.objects.all()
	serializer_class = BorrowerSerializer
	filter_backends = [SearchFilter, OrderingFilter]
	search_fields = ['full_name', 'phone_number', 'email', 'id_number']
	ordering_fields = ['created_at']
	ordering = ['-created_at']


class LenderViewSet(viewsets.ModelViewSet):
	queryset = Lender.objects.all()
	serializer_class = LenderSerializer
	filter_backends = [SearchFilter, OrderingFilter]
	search_fields = ['name']
	ordering_fields = ['created_at']
	ordering = ['-created_at']


class LoanViewSet(viewsets.ModelViewSet):
	queryset = Loan.objects.all().select_related('borrower', 'lender')
	serializer_class = LoanSerializer
	filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
	filterset_fields = ['status', 'currency', 'lender']
	search_fields = ['id', 'borrower__full_name']
	ordering_fields = ['created_at', 'principal_amount', 'status']
	ordering = ['-created_at']

	def get_serializer_class(self):
		if self.action == 'create':
			return LoanCreateSerializer
		return LoanSerializer

	@action(detail=True, methods=['post'])
	def approve(self, request, pk=None):
		loan = self.get_object()
		if loan.status not in ['PENDING']:
			return Response({'error': 'Loan is not pending.'}, status=status.HTTP_400_BAD_REQUEST)
		loan.status = 'APPROVED'
		loan.save()
		return Response(LoanSerializer(loan).data)

	@action(detail=True, methods=['post'])
	def disburse(self, request, pk=None):
		loan = self.get_object()
		serializer = LoanDisbursementSerializer(data=request.data, context={'loan': loan})
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)

	@action(detail=True, methods=['post'])
	def repay(self, request, pk=None):
		loan = self.get_object()
		serializer = LoanRepaymentSerializer(data=request.data, context={'loan': loan})
		serializer.is_valid(raise_exception=True)
		repayment = serializer.save()
		return Response(LoanRepaymentListSerializer(repayment).data, status=status.HTTP_201_CREATED)

	@action(detail=True, methods=['post'])
	def write_off(self, request, pk=None):
		loan = self.get_object()
		serializer = LoanWriteOffSerializer(data=request.data, context={'loan': loan})
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(LoanSerializer(loan).data)

	@action(detail=True, methods=['post'])
	def accrue_interest(self, request, pk=None):
		loan = self.get_object()
		serializer = LoanInterestAccrualSerializer(data=request.data, context={'loan': loan})
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(LoanSerializer(loan).data)

	@action(detail=True, methods=['get'])
	def repayments(self, request, pk=None):
		loan = self.get_object()
		repayments = loan.repayments.all().order_by('-paid_at')
		page = self.paginate_queryset(repayments)
		if page is not None:
			serializer = LoanRepaymentListSerializer(page, many=True)
			return self.get_paginated_response(serializer.data)
		serializer = LoanRepaymentListSerializer(repayments, many=True)
		return Response(serializer.data)

	@action(detail=True, methods=['get'])
	def events(self, request, pk=None):
		loan = self.get_object()
		events = loan.events.all().order_by('-created_at')
		serializer = LoanEventSerializer(events, many=True)
		return Response(serializer.data)


class LoanRepaymentViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = LoanRepayment.objects.all().select_related('loan')
	serializer_class = LoanRepaymentListSerializer
	filter_backends = [DjangoFilterBackend, OrderingFilter]
	filterset_fields = ['loan', 'status']
	ordering_fields = ['paid_at', 'amount']
	ordering = ['-paid_at']


class LoanEventViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = LoanEvent.objects.all().select_related('loan')
	serializer_class = LoanEventSerializer
	filter_backends = [DjangoFilterBackend, OrderingFilter]
	filterset_fields = ['loan', 'event_type']
	ordering_fields = ['created_at']
	ordering = ['-created_at']
