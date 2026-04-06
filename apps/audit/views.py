from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.audit.models import ExecutionTrace
from rest_framework import serializers

class ExecutionTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionTrace
        fields = "__all__"

class ExecutionTraceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExecutionTrace.objects.all()
    serializer_class = ExecutionTraceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='by-trace/(?P<trace_id>[^/.]+)')
    def by_trace(self, request, trace_id=None):
        """Retorna todos os passos de um trace_id específico, ordenados por ID para garantir a sequência temporal."""
        traces = self.queryset.filter(trace_id=trace_id).order_by('id')
        serializer = self.get_serializer(traces, many=True)
        return Response(serializer.data)
