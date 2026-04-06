"""
apps.audit.services.trace_service
────────────────────────────────
Utilitário para rastreamento de execução em tempo real.
"""
import time
import uuid
import logging
from typing import Any, Optional
from django.utils import timezone
from apps.audit.models import ExecutionTrace

logger = logging.getLogger(__name__)

class TraceService:
    def __init__(self, trace_id: Optional[uuid.UUID] = None, job_type: str = "GENERIC"):
        self.trace_id = trace_id or uuid.uuid4()
        self.job_type = job_type
        self._start_times = {}

    def start_step(self, step_name: str):
        """Inicia a cronometragem de um passo."""
        self._start_times[step_name] = time.perf_counter()
        logger.debug(f"[Tracer] Inciando: {step_name} (Trace: {self.trace_id})")

    def end_step(
        self, 
        step_name: str, 
        message: str = "", 
        status: str = "SUCCESS", 
        metadata: dict = None,
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """Finaliza um passo, calcula a duração e persiste o log."""
        start_time = self._start_times.pop(step_name, time.perf_counter())
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        try:
            ExecutionTrace.objects.create(
                trace_id=self.trace_id,
                job_type=self.job_type,
                step_name=step_name,
                message=message,
                duration_ms=duration_ms,
                status=status,
                metadata=metadata or {},
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            logger.info(f"[Tracer] Concluido: {step_name} em {duration_ms}ms")
        except Exception as e:
            logger.error(f"[Tracer] Erro ao salvar trace: {e}")

    @classmethod
    def quick_log(cls, trace_id: uuid.UUID, job_type: str, step_name: str, message: str, **kwargs):
        """Log direto sem cronometragem (para eventos pontuais)."""
        ExecutionTrace.objects.create(
            trace_id=trace_id,
            job_type=job_type,
            step_name=step_name,
            message=message,
            **kwargs
        )
