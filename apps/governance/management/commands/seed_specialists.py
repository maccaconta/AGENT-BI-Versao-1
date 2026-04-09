from django.core.management.base import BaseCommand
from apps.shared_models import PromptTemplate
from apps.users.models import User

class Command(BaseCommand):
    help = "Popula a Biblioteca de Especialistas do Centro de Governança de IA."

    def handle(self, *args, **options):
        self.stdout.write("Semeando especialistas de domínio...")
        
        # Busca um admin para associar
        admin = User.objects.filter(is_superuser=True).first()
        
        specialists = [
            {
                "name": "Especialista em Risco e Compliance",
                "category": "SPECIALIST",
                "description": "Focado em identificar exposições de crédito, riscos de mercado e conformidade regulatória (Basileia III).",
                "content": """VOCÊ É O ESPECIALISTA EM RISCO:
- Analise os dados procurando por sinais de deterioração de crédito.
- Identifique concentrações excessivas em um único cliente ou setor.
- Verifique se os limites de exposição estão sendo respeitados.
- Use terminologia de risco: LGD, PD, Exposure at Default, Stress Test."""
            },
            {
                "name": "CFO / Analista Financeiro Estratégico",
                "category": "SPECIALIST",
                "description": "Focado em rentabilidade (ROE, ROA), eficiência de custos e geração de caixa.",
                "content": """VOCÊ É O CFO ESTRATÉGICO:
- Sua prioridade é a margem financeira e o controle de despesas.
- Identifique variações anormais no Opex e Capex.
- Analise a rentabilidade por produto ou unidade de negócio.
- Foque em métricas de valor: EBITDA, Net Profit, Cash Flow."""
            },
            {
                "name": "Auditor Interno e Fraudes",
                "category": "SPECIALIST",
                "description": "Especialista em detectar anomalias, lançamentos duplicados e padrões suspeitos em transações.",
                "content": """VOCÊ É O AUDITOR DE FRAUDES:
- Busque por transações que fogem da média histórica (Benford's Law).
- Identifique acessos ou movimentações em horários atípicos.
- Verifique a integridade das chaves primárias e duplicidades suspeitas.
- Sua linguagem é de investigação e ceticismo profissional."""
            },
            {
                "name": "Especialista em Supply Chain e Logística",
                "category": "SPECIALIST",
                "description": "Otimização de estoque, lead time e visibilidade de gargalos na cadeia de suprimentos.",
                "content": """VOCÊ É O ESPECIALISTA EM SUPPLY CHAIN:
- Analise o giro de estoque e identifique produtos com baixa liquidez.
- Verifique o cumprimento de SLAs de entrega.
- Identifique custos logísticos que podem ser otimizados.
- Foque em métricas de eficiência: OTIF, Lead Time, Inventory Turnover."""
            }
        ]
        
        for s in specialists:
            obj, created = PromptTemplate.objects.get_or_create(
                name=s["name"],
                defaults={
                    "category": s["category"],
                    "description": s["description"],
                    "content": s["content"],
                    "created_by": admin,
                    "is_public": True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Especialista '{s['name']}' criado."))
            else:
                self.stdout.write(self.style.WARNING(f"Especialista '{s['name']}' já existe."))
        
        self.stdout.write(self.style.SUCCESS("Semeação concluída!"))
