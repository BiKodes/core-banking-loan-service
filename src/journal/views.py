"""Views for journal app."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import JournalEntry, JournalEntryLine
from .serializers import (
    JournalEntryCreateSerializer,
    JournalEntryLineSerializer,
    JournalEntryReverseSerializer,
    JournalEntrySerializer,
)


class JournalEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for JournalEntry management."""

    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['description', 'idempotency_key']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return JournalEntryCreateSerializer
        elif self.action == 'reverse':
            return JournalEntryReverseSerializer
        return JournalEntrySerializer

    def create(self, request, *args, **kwargs):
        """Create a new journal entry."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        journal_entry = serializer.save()

        response_serializer = JournalEntrySerializer(journal_entry)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a journal entry."""
        journal_entry = self.get_object()

        serializer = self.get_serializer(
            data=request.data, context={'journal_entry': journal_entry}
        )
        serializer.is_valid(raise_exception=True)
        reversed_entry = serializer.save()

        response_serializer = JournalEntrySerializer(reversed_entry)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def lines(self, request, pk=None):
        """Get all lines for a journal entry."""
        journal_entry = self.get_object()
        lines = journal_entry.lines.all()
        serializer = JournalEntryLineSerializer(lines, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get journal entries by status."""
        status_filter = request.query_params.get('status')
        if not status_filter:
            return Response(
                {'error': 'status parameter required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entries = JournalEntry.objects.filter(status=status_filter)
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)


class JournalEntryLineViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for JournalEntryLine (read-only)."""

    queryset = JournalEntryLine.objects.all()
    serializer_class = JournalEntryLineSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['journal_entry', 'account', 'entry_type']
    ordering_fields = ['created_at', 'account']
    ordering = ['journal_entry', 'created_at']
