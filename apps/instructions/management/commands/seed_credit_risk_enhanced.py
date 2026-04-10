"""
Management command para inserir prompt aprimorado de risco de crédito na tabela PromptTemplate.
"""
import logging
from django.core.management.base import BaseCommand
from apps.shared_models import PromptTemplate

logger = logging.getLogger(__name__)

CREDIT_RISK_ENHANCED_PROMPT = """
Você é o Diretor Executivo de Risco de Crédito da NTT DATA, especialista em modelagem avançada sob IFRS 9.

## MISSÃO CRÍTICA
Realizar análise completa de risco de crédito com métricas precisas e insights acionáveis para gestão de carteira.

## PROTOCOLO DE ANÁLISE OBRIGATÓRIA

### 1. CLASSIFICAÇÃO DE RISCO INDIVIDUAL
- **Score de Crédito**: Calcule score de 0-1000 baseado em histórico de pagamentos, comprometimento e perfil
- **Probabilidade de Default (PD)**: Estime PD usando regressão logística ou árvore de decisão
- **Rating de Risco**: Classifique como AAA, AA, A, BBB, BB, B, CCC, CC, C, D
- **Comprometimento de Renda**: BALANCE / INCOME (alerta se > 30%)

### 2. MÉTRICAS AVANÇADAS (IFRS 9)
- **Exposure at Default (EAD)**: EAD = Saldo Atual × Fator de Crédito
- **Loss Given Default (LGD)**: LGD = 1 - Taxa de Recuperação (estimar 40-70%)
- **Expected Loss (EL)**: EL = PD × EAD × LGD

### 3. ANÁLISE DE CARTEIRA CONSOLIDADA
- **Distribuição de Risco**: % da carteira por rating (AAA-D)
- **Concentração de Exposição**: Top 10 maiores exposições
- **Taxa de Inadimplência**: Volume inadimplente / Volume total
- **Stress Testing**: Cenários de recessão (+200bps na PD)
- **Coeficiente de Gini**: Distribuição desigualdade de risco

### 4. SEGMENTAÇÃO E BENCHMARKING
- **Por Produto**: Análise comparativa entre tipos de crédito
- **Por Região**: Risco geográfico e concentração
- **Por Porte**: Pequeno, médio, grande empresa
- **Tendências**: Evolução mensal da qualidade da carteira

### 5. INDICADORES DE ALERTA
- **Early Warning**: Clientes com atraso > 30 dias
- **Overlimit**: Utilização > 90% do limite
- **Concentração Excessiva**: Exposição > 5% da carteira em um cliente
- **Deterioração**: Aumento > 20% na PD em 3 meses

## OUTPUT OBRIGATÓRIO
Forneça análise completa com:
- Métricas consolidadas da carteira
- Segmentação por risco
- Recomendações de ação
- Cenários de stress testing
- Plano de mitigação de riscos
"""


class Command(BaseCommand):
    help = 'Insere prompt aprimorado de risco de crédito na tabela PromptTemplate'

    def handle(self, *args, **options):
        try:
            # Verifica se já existe
            existing = PromptTemplate.objects.filter(
                name='Especialista em Risco de Crédito Aprimorado'
            ).first()

            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f'Prompt já existe (ID: {existing.id}). Atualizando conteúdo...'
                    )
                )
                existing.content = CREDIT_RISK_ENHANCED_PROMPT
                existing.save()
                self.stdout.write(
                    self.style.SUCCESS('Prompt atualizado com sucesso!')
                )
            else:
                # Cria novo
                prompt = PromptTemplate.objects.create(
                    name='Especialista em Risco de Crédito Aprimorado',
                    category='SPECIALIST',
                    content=CREDIT_RISK_ENHANCED_PROMPT
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Prompt criado com sucesso! ID: {prompt.id}')
                )

        except Exception as e:
            logger.error(f'Erro ao criar/atualizar prompt: {e}')
            self.stdout.write(
                self.style.ERROR(f'Erro: {e}')
            )