"""
apps.ai_engine.services.prompt_service
───────────────────────────────────────
Serviço para gestão dinâmica de prompts via Banco de Dados.
Permite alterar o comportamento dos agentes sem deploy de código.
"""
import logging
from typing import Optional
from django.core.cache import cache
from apps.governance.models import AgentSystemPrompt

logger = logging.getLogger(__name__)

class PromptService:
    """
    Centraliza o carregamento de System Prompts.
    Prioridade:
    1. Banco de Dados (PromptTemplate com categoria 'SYSTEM_PROMPT')
    2. Cache (para performance)
    3. Fallback (String hardcoded no código)
    """
    
    CACHE_TIMEOUT = 60 * 5  # 5 minutos
    
    @classmethod
    def get_system_prompt(cls, agent_name: str, default_content: str) -> str:
        """
        Recupera o prompt de sistema para um agente específico.
        """
        # Normaliza a chave: "SupervisorAgent" -> "supervisor_agent"
        # Isso garante compatibilidade com o que os agentes já passam hoje
        agent_key = agent_name.replace("Agent", "").lower() + "_agent"
        if "data_interpreter" in agent_name.lower():
            agent_key = "data_interpreter_agent" # Caso especial

        cache_key = f"system_prompt_{agent_key}"
        cached_prompt = cache.get(cache_key)
        
        if cached_prompt:
            return cached_prompt
            
        try:
            # Busca no banco pela nova tabela técnica
            template = AgentSystemPrompt.objects.filter(
                agent_key=agent_key,
                is_active=True
            ).first()
            
            if template:
                content = template.content
                cache.set(cache_key, content, cls.CACHE_TIMEOUT)
                logger.info(f"[PromptService] Prompt técnico '{agent_key}' carregado do Banco de Dados.")
                return content
                
        except Exception as e:
            logger.warning(f"[PromptService] Falha ao acessar AgentSystemPrompt no DB: {e}")
            
        # Fallback para o default hardcoded
        logger.debug(f"[PromptService] Usando fallback local para o agente: {agent_key}")
        return default_content

    @classmethod
    def invalidate_cache(cls, agent_name: str):
        """Invalida o cache quando um prompt é atualizado via Admin."""
        cache_key = f"system_prompt_{agent_name.lower()}"
        cache.delete(cache_key)
