"""
apps.ai_engine.prompts.generator_prompt
─────────────────────────────────────────
Prompts do Generator Agent para geração de SQL + HTML de dashboards.
"""

GENERATOR_SYSTEM_PROMPT = """Você é um especialista em análise de dados e visualização, chamado Agent-BI Generator.

Sua tarefa é:
1. Analisar a instrução do usuário
2. Gerar queries SQL otimizadas para Amazon Athena
3. Executar análise dos dados
4. Gerar um dashboard HTML completo e profissional

## Regras Obrigatórias

### SQL
- Use apenas SELECT e WITH (CTEs)
- Nunca use DROP, DELETE, INSERT, UPDATE, CREATE
- Otimize para Athena: use partições, LIMIT quando adequado
- Use backticks para nomes de tabelas/colunas: `database`.`table`
- Sempre filtre por partições quando disponíveis
- Agrupe dados adequadamente para visualização

### HTML
- HTML5 standalone e completo (inclua <!DOCTYPE html>)
- Inclua Chart.js via CDN: https://cdn.jsdelivr.net/npm/chart.js
- Design moderno com CSS inline (dark mode, cores vibrantes)
- Layout responsivo com CSS Grid/Flexbox
- KPIs grandes e destacados no topo
- Gráficos relevantes para os dados (bar, line, pie, doughnut, scatter)
- Tabela de dados com paginação simples
- Seção de insights narrativos
- Rodapé com metadata (data de geração, dataset, queries usadas)
- Não insira os dados estáticos no HTML. O HTML deve ser dinâmico.
- Busque os dados no backend usando `fetch('/api/v1/datasets/{{dataset_id}}/query/', {method: 'POST', body: JSON.stringify({sql: window.AGENT_BI_SQL})})`.
- Considere que a constante global `window.AGENT_BI_SQL` já estará injetada no script.
- Trate erros de requisição e mostre placeholders visuais enquanto carrega (loading state).

### Qualidade
- Insights devem ser específicos e baseados nos dados
- Use números formatados (K, M, %)
- Escolha o tipo de gráfico mais adequado para cada métrica
- Cores consistentes e acessíveis

## Formato de Saída (JSON)
{
  "sql_queries": [
    {
      "name": "query_1_nome_descritivo",
      "description": "O que esta query retorna",
      "sql": "SELECT ... FROM ..."
    }
  ],
  "insights": "Análise narrativa dos dados em português...",
  "html": "<!DOCTYPE html>..."
}
"""


def build_generator_prompt(
    instruction: str,
    schema: dict,
    sample_data: dict,
    dataset_name: str,
    database: str,
    table: str,
    template_hints: str = "",
    previous_feedback: str = "",
    iteration: int = 1,
) -> str:
    """
    Constrói o prompt para o Generator Agent.

    Args:
        instruction: Instrução do usuário em linguagem natural
        schema: Schema do dataset {columns: [...]}
        sample_data: Amostra de dados {columns: [...], rows: [[...]]}
        dataset_name: Nome do dataset
        database: Glue database
        table: Glue table
        template_hints: Dicas do template selecionado
        previous_feedback: Feedback da iteração anterior (Critic)
        iteration: Número da iteração atual
    """
    columns_desc = "\n".join([
        f"  - `{col['name']}` ({col['type']})"
        + (f" — Ex: {', '.join(col.get('sample_values', []))}" if col.get('sample_values') else "")
        for col in schema.get("columns", [])
    ])

    sample_rows = ""
    if sample_data and sample_data.get("rows"):
        cols = sample_data.get("columns", [])
        rows = sample_data.get("rows", [])[:5]
        sample_rows = "| " + " | ".join(cols) + " |\n"
        sample_rows += "|" + " --- |" * len(cols) + "\n"
        for row in rows:
            sample_rows += "| " + " | ".join(str(v) for v in row) + " |\n"

    feedback_section = ""
    if previous_feedback and iteration > 1:
        feedback_section = f"""
## ⚠️ Iteração {iteration} — Feedback da Revisão Anterior
{previous_feedback}

Corrija os problemas apontados e melhore o dashboard com base neste feedback.
"""

    template_section = ""
    if template_hints:
        template_section = f"""
## Template Aplicado
{template_hints}
"""

    return f"""# Geração de Dashboard — Iteração {iteration}

## Instrução do Usuário
{instruction}

## Dataset
- **Nome:** {dataset_name}
- **Referência Athena:** `{database}`.`{table}`
- **Total de colunas:** {schema.get('column_count', len(schema.get('columns', [])))}
- **Total de linhas:** {schema.get('row_count', 'Desconhecido')}

## Schema das Colunas
{columns_desc}

## Amostra de Dados (primeiras 5 linhas)
{sample_rows if sample_rows else "Amostra não disponível"}

{template_section}
{feedback_section}

## Tarefa
1. Analise o schema e a amostra de dados
2. Gere queries SQL otimizadas para Athena que respondam à instrução
3. Analise os dados como se você os tivesse executado
4. Gere um dashboard HTML profissional e bonito

Responda no formato JSON especificado no sistema prompt.
"""
