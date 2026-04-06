from django.urls import path

from apps.ai_engine.views import CopilotGenerateAPIView, CopilotSQLPreviewAPIView

urlpatterns = [
    path("generate", CopilotGenerateAPIView.as_view(), name="copilot-generate"),
    path("sql-preview", CopilotSQLPreviewAPIView.as_view(), name="copilot-sql-preview"),
]
