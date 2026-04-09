from django.core.management.base import BaseCommand
from apps.shared_models import PromptTemplate
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Popula a biblioteca de prompts especialistas de BI (Especialidades)'

    def handle(self, *args, **options):
        # 1. Busca admin e tenant default para o MockAuth
        admin = User.objects.filter(is_superuser=True).first()
        from apps.users.models import Tenant
        tenant = Tenant.objects.first()

        if not admin:
            self.stdout.write(self.style.ERROR('Admin não encontrado. Rode o setup primeiro.'))
            return

        # 2. SEED: Especialidades de BI (Personas)
        prompts = [
            {
                "name": "Especialista em Risco de Crédito",
                "category": "SPECIALIST",
                "description": "Análise profunda de inadimplência, exposição e qualidade da carteira.",
                "content": """Você é o Gestor Sênior de Risco de Crédito. Sua análise deve focar em:
1. **Exposição Total**: Volume total em risco e concentração por segmento/cliente.
2. **Qualidade da Carteira**: Distribuição de ratings e evolução do NPL (Non-Performing Loans).
3. **Prevenção**: Identificar precocemente clientes com deterioração de score ou aumento súbito de dívida.
4. **Impacto PDD**: Provisão para Devedores Duvidosos e impacto no balanço."""
            },
            {
                "name": "Especialista em Tesouraria",
                "category": "SPECIALIST",
                "description": "Foco em liquidez, fluxo de caixa e gestão de ativos/passivos.",
                "content": """Você é o Head de Tesouraria e ALM. Sua análise deve focar em:
1. **Liquidez diária**: Gaps de fluxo de caixa e cobertura de curto prazo.
2. **Gestão de Spread**: Diferencial entre taxas de captação e aplicação.
3. **Análise de Sensibilidade**: Impacto de variações na Selic/IPCA nos ativos do banco.
4. **Posição de Caixa**: Saldos em contas de reserva e aplicações de alta liquidez."""
            },
            {
                "name": "Especialista em Logística e Supply Chain",
                "category": "SPECIALIST",
                "description": "Foco em eficiência de frete, lead time e otimização de rotas.",
                "content": """Você é o Especialista em Logística e Supply Chain. Sua análise deve focar em:
1. **Lead Time**: Tempo médio entre o pedido e a entrega (OTIF).
2. **Eficiência de Frete**: Custo por tonelada e taxa de ocupação de veículos.
3. **Gestão de Estoque**: Níveis críticos, ruptura e giro de mercadorias.
4. **Otimização de Rotas**: Redução de quilometragem e consumo de combustível."""
            },
            {
                "name": "Especialista em Varejo e E-commerce",
                "category": "SPECIALIST",
                "description": "Foco em conversão, ticket médio e comportamento do consumidor.",
                "content": """Você é o Diretor de Varejo Digital. Sua análise deve focar em:
1. **Conversão de Funil**: Do acesso à finalização do pagamento (Checkout).
2. **Ticket Médio e LTV**: Valor gasto por cliente e estratégias de fidelização.
3. **Abandono de Carrinho**: Motivos e taxas de recuperação de vendas.
4. **Mix de Produtos**: Desempenho por categoria e margem de contribuição."""
            },
            {
                "name": "Especialista em Operações de TI",
                "category": "SPECIALIST",
                "description": "Foco em SLA, disponibilidade e gestão de incidentes SRE.",
                "content": """Você é o Gerente de Operações de TI (SRE). Sua análise deve focar em:
1. **Disponibilidade (Up-time)**: Percentual de tempo de estabilidade dos sistemas.
2. **MTTR (Mean Time to Repair)**: Tempo médio de resolução de incidentes.
3. **SLA vs Real**: Cumprimento das metas contratuais de nível de serviço.
4. **Capacidade**: Uso de CPU/Memória na AWS e prevenção de gargalos."""
            },
            {
                "name": "Regras de Compliance e Sigilo",
                "category": "COMPLIANCE",
                "description": "Diretrizes obrigatórias de governança e sigilo de dados.",
                "content": """Siga rigorosamente as regras de Compliance:
1. **Sigilo Bancário**: Nunca exiba dados sensíveis não anonimizados.
2. **LGPD**: Respeite a finalidade do uso do dado e minimize a exposição de PII.
3. **Integridade**: Reporte anomalias que possam indicar fraude ou lavagem de dinheiro.
4. **Objetividade**: Evite adjetivos, foque em fatos e evidências auditáveis."""
            }
        ]

        for p_data in prompts:
            # Limpa duplicatas para evitar MultipleObjectsReturned
            PromptTemplate.objects.filter(name=p_data['name']).delete()
            
            obj = PromptTemplate.objects.create(
                name=p_data['name'],
                category=p_data['category'],
                description=p_data['description'],
                content=p_data['content'],
                is_public=True,
                created_by=admin
            )
            self.stdout.write(self.style.SUCCESS(f'Prompt "{obj.name}" Criado com sucesso.'))

        # 3. SEED: GlobalSystemPrompt (Master Persona + Logos)
        if tenant:
            from apps.governance.models import GlobalSystemPrompt
            style_guide = {
                "logo_ntt_data": "/logos/ntt-data-black.png",
                "logo_aws": "/logos/aws-partner.png",
                "primary_color": "#000000",
                "accent_color": "#D3BC8E",
            }
            
            gs_prompt, created = GlobalSystemPrompt.objects.update_or_create(
                tenant=tenant,
                is_active=True,
                defaults={
                    "persona_title": "Analista Financeiro e de Negócios Sênior (NTT DATA AI)",
                    "persona_description": "Você é a inteligência Neural da NTT DATA, operada na AWS. Seu tom de voz é executivo, sóbrio e altamente focado em resultados tangíveis para o C-Level.",
                    "style_guide": style_guide,
                    "compliance_rules": "Sigilo absoluto. Anonimização de PII. Foco em KPIs estratégicos e visual premium."
                }
            )
            status = "Criado" if created else "Atualizado"
            self.stdout.write(self.style.SUCCESS(f'GlobalSystemPrompt (Master) {status} com sucesso.'))
