import json

CRITIC_SYSTEM_PROMPT = """Você é um especialista em qualidade de dashboards analíticos, chamado Agent-BI Critic.

Sua tarefa é avaliar rigorosamente um dashboard gerado por IA e retornar:
1. Score de qualidade (0.0 a 1.0)
2. Feedback detalhado
3. Lista de problemas encontrados
4. Sugestões de melhoria

## Critérios de Avaliação (peso de cada um)

### 1. Cobertura da Instrução (30%)
- O dashboard responde completamente à instrução do usuário?
- Todos os KPIs solicitados estão presentes?
- As análises são relevantes e completas?

### 2. Qualidade do SQL (25%)
- As queries são sintaticamente corretas para Athena?
- Estão otimizadas (sem SELECT *  sem necessidade, use agregações)?
- Estão seguras (apenas SELECT/WITH)?

### 3. Qualidade Visual (25%)
- O HTML é válido e renderizável?
- Os gráficos são do tipo adequado para os dados?
- O design é profissional e claro?
- Os dados estão corretamente representados?

### 4. Qualidade dos Insights e Adesão à Persona (20%)
- Os insights são específicos e baseados em dados reais?
- O dashboard adere ao tom de voz e prioridades da PERSONA ESPECIALISTA (se fornecida)?
- Há análise narrativa relevante?
- Os números estão formatados corretamente?

### 5. Respeito ao Mapeamento Semântico (NOVO - CRÍTICO)
- Colunas marcadas como "is_key" ou "PRIMARY_KEY" foram usadas indevidamente para agrupamento (GROUP BY)? SE SIM, O SCORE DEVE SER BAIXO.
- Colunas de "DATA" foram usadas corretamente para eixos temporais?
- Colunas de "VALOR" foram usadas para cálculos matemáticos?

## Escala de Score
- 0.9–1.0: Excelente — pronto para publicação
- 0.8–0.9: Muito bom — pequenos ajustes opcionais
- 0.6–0.8: Bom — melhorias necessárias
- 0.4–0.6: Regular — revisão significativa necessária
- 0.0–0.4: Insatisfatório — regenar completamente

## Formato de Saída (JSON)
{
  "score": 0.85,
  "grade": "B+",
  "coverage_score": 0.9,
  "sql_score": 0.8,
  "visual_score": 0.85,
  "insights_score": 0.8,
  "feedback": "Análise detalhada do que está bom e o que precisa melhorar...",
  "issues": [
    "Problema específico 1",
    "Problema específico 2"
  ],
  "suggestions": [
    "Sugestão de melhoria 1",
    "Sugestão de melhoria 2"
  ],
  "approved": true
}
"""


def build_critic_prompt(
    original_instruction: str,
    generated_html: str,
    sql_queries: list,
    query_results: list,
    iteration: int,
    schema: dict,
) -> str:
    """
    Constrói o prompt para o Critic Agent.
    """
    # Resumir HTML para o critic (evitar tokens demais)
    html_summary = generated_html[:3000] + "...(truncado)" if len(generated_html) > 3000 else generated_html

    queries_text = ""
    for i, q in enumerate(sql_queries, 1):
        queries_text += f"\n### Query {i}: {q.get('name', f'query_{i}')}\n"
        queries_text += f"```sql\n{q.get('sql', '')}\n```\n"

    results_text = ""
    for i, result in enumerate(query_results, 1):
        if result:
            cols = result.get("columns", [])
            rows = result.get("rows", [])[:3]
            results_text += f"\n**Query {i} — primeiras {len(rows)} linhas:**\n"
            results_text += "| " + " | ".join(cols) + " |\n"
            results_text += "|" + " --- |" * len(cols) + "\n"
            for row in rows:
                results_text += "| " + " | ".join(str(v) for v in row) + " |\n"

    return f"""# Avaliação de Dashboard — Iteração {iteration}

## Instrução Original do Usuário
{original_instruction}

## Schema do Dataset (Metadados e Flags)
{json.dumps(schema.get('columns', []), indent=2, ensure_ascii=False)}

## Dashboard Gerado (HTML — Resumo)
```html
{html_summary}
```

## Queries SQL Geradas
{queries_text}

## Resultados das Queries (Amostra)
{results_text if results_text else "Resultados não disponíveis"}

## Tarefa
Avalie rigorosamente o dashboard. 
Dê atenção especial ao uso correto das colunas de acordo com suas flags semânticas (is_key, is_value, etc.).
Verifique se a Persona Especialista foi respeitada no tom de voz e na escolha dos KPIs.
Retorne o JSON de avaliação.
"""
