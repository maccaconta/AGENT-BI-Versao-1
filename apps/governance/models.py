"""
apps.governance.models
──────────────────────
Modelos para controle de diretrizes globais da IA (System Prompts).
"""
import uuid
from django.db import models
from apps.users.models import TimeStampedModel, Tenant, User


class GlobalSystemPrompt(TimeStampedModel):
    """
    Diretriz mestre que orienta a criação de dashboards por todos os usuários do tenant.
    Define persona, estilo visual (NTT DATA/AWS) e regras de compliance.
    """
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name="system_prompts",
        verbose_name="Tenant"
    )
    
    # Persona Details
    persona_title = models.CharField(
        max_length=255, 
        default="Analista Financeiro Sênior",
        verbose_name="Título da Persona"
    )
    persona_description = models.TextField(
        default="Você é um analista financeiro sênior especializado em identificar relações ocultas em dados e gerar insights estratégicos.",
        verbose_name="Descrição da Persona"
    )
    
    # UI Guidelines (JSON)
    # Ex: {"primary_color": "#D3BC8E", "logo_url": "...", "font_family": "serif"}
    style_guide = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Guia de Estilo (JSON)",
        help_text="Configuração de cores, logos (NTT DATA, AWS) e fontes padrão corporativas."
    )
    
    # Governance & Compliance
    compliance_rules = models.TextField(
        blank=True,
        verbose_name="Regras de Compliance",
        help_text="Políticas de dados e segurança que a LLM deve observar."
    )
    
    # Advanced Data Profiling Toggles
    enable_temporal_profile = models.BooleanField(
        default=True,
        verbose_name="Ativar Perfil Temporal",
        help_text="Gera estatísticas de tendências mensais/semanais na ingestão de dados."
    )
    enable_correlation_profile = models.BooleanField(
        default=False,
        verbose_name="Ativar Perfil de Correlação",
        help_text="Gera estatísticas de correlação entre colunas categóricas e numéricas (Beta)."
    )
    enable_anomaly_detection = models.BooleanField(
        default=False,
        verbose_name="Ativar Detecção de Anomalias",
        help_text="Identifica e sinaliza outliers e picos no dataset (Beta)."
    )

    # Future & Advanced Statistics (Placeholders)
    enable_clustering_profile = models.BooleanField(
        default=False,
        verbose_name="Ativar Clustering",
        help_text="Agrupamento automático de perfis segmentados (Em breve)."
    )
    enable_forecasting_profile = models.BooleanField(
        default=False,
        verbose_name="Ativar Forecasting",
        help_text="Previsão preditiva baseada em séries temporais (Em breve)."
    )

    # Resource Management
    max_tokens_limit = models.IntegerField(
        default=32000,
        verbose_name="Limite de Tokens Master",
        help_text="Cota máxima de tokens para respostas da IA (Claude 3.5 Sonnet)."
    )

    ingestion_row_limit = models.IntegerField(
        default=5000,
        verbose_name="Limite de Linhas para Ingestão",
        help_text="Número máximo de linhas processadas pelo Agent-BI durante a ingestão (Governança)."
    )
    
    language = models.CharField(
        max_length=10, 
        default="pt-BR",
        verbose_name="Idioma Principal"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_prompts"
    )

    class Meta:
        db_table = "governance_system_prompts"
        verbose_name = "System Prompt Global"
        verbose_name_plural = "System Prompts Globais"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.persona_title} ({self.tenant.name})"

    def generate_full_system_prompt(self):
        """Constrói o prompt final concatenado para a LLM."""
        prompt = f"VOCÊ É: {self.persona_title}. {self.persona_description}\n\n"
        prompt += f"IDIOMA: RESPONDA SEMPRE EM {self.language.upper()}.\n\n"
        
        if self.style_guide:
            prompt += "DIRETRIZES DE DESIGN:\n"
            for key, val in self.style_guide.items():
                prompt += f"- {key}: {val}\n"
            prompt += "\n"
            
        if self.compliance_rules:
            prompt += f"REGRAS DE COMPLIANCE:\n{self.compliance_rules}\n"
            
        return prompt


class AgentSystemPrompt(TimeStampedModel):
    """
    Prompts de sistema específicos para cada agente técnico (Supervisor, Pandas, NL2SQL, etc).
    Permite governança granular sobre o comportamento de cada componente da IA.
    """
    agent_key = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Chave do Agente",
        help_text="Ex: supervisor_agent, pandas_agent, nl2sql_agent"
    )
    name = models.CharField(max_length=255, verbose_name="Nome do Agente")
    description = models.TextField(blank=True, verbose_name="Descrição/Objetivo")
    content = models.TextField(verbose_name="System Prompt")
    
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    version = models.CharField(max_length=20, default="1.0.0", verbose_name="Versão")

    class Meta:
        db_table = "governance_agent_prompts"
        verbose_name = "System Prompt de Agente"
        verbose_name_plural = "System Prompts de Agentes"
        ordering = ["agent_key"]

    def __str__(self):
        return f"{self.name} ({self.agent_key})"
