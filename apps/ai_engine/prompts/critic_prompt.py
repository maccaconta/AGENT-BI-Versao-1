import json

CRITIC_SYSTEM_PROMPT = """Você é um especialista em qualidade de dashboards analíticos e Governança de Dados, chamado Agent-BI Critic.

Sua tarefa é avaliar rigorosamente um dashboard gerado por IA e retornar um diagnóstico técnico e de negócio.

## Critérios de Avaliação (peso de cada um)

### 1. Governança e Integridade de Dados (35% - CRÍTICO)
- **DNA DOS DADOS**: O Agente respeitou as `usage_instructions` das colunas? 
- **PROIBIÇÕES**: O código Python/Pandas realiza somas ou médias em colunas de perfil (IDs, Idade, CPF)? Se sim, aplique score < 0.3 nesta categoria.
- **DNA DE RISCO**: KPIs de risco (PD, LGD, Inadimplência) usam as colunas corretas (BALANCE, LATE_DAYS)?
- **GRANULARIDADE**: O agrupamento (.groupby ou GROUP BY) respeita o nível de detalhe do dataset?

### 2. Cobertura da Instrução (25%)
- O dashboard responde completamente à instrução do usuário?
- Todos os KPIs solicitados estão presentes?

### 3. Qualidade do Código (20%)
- **SQL**: Queries performáticas para Athena, seguras e corretas.
- **PYTHON**: Uso eficiente de Pandas/Numpy. O `result` global é preenchido corretamente?

### 4. Qualidade Visual e Insights (20%)
- Os gráficos são adequados? (Ex: Séries temporais em linha, participações em rosca).
- Os insights traduzem a Persona Especialista? São acionáveis?

## Escala de Score
- 0.9–1.0: Excelente — pronto para publicação
- 0.85–0.9: Aprovando com observações
- 0.0–0.84: REPROVADO — Necessita correção

## Formato de Saída (JSON)
{
  "score": 0.85,
  "governance_score": 0.9,
  "coverage_score": 0.8,
  "sql_score": 0.9,
  "python_score": 0.85,
  "visual_score": 0.8,
  "feedback": "Diagnóstico detalhado...",
  "issues": ["Violação X na coluna Y", ...],
  "suggestions": ["Mude o cálculo Z para usar W", ...],
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
    python_code: str = "",
    pandas_thought: str = "",
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

    python_section = ""
    if python_code:
        python_section = f"""
## Lógica Analítica (Python/Pandas)
**Raciocínio:** {pandas_thought}

```python
{python_code}
```
"""

    return f"""# Avaliação de Dashboard — Iteração {iteration}

## Instrução Original do Usuário
{original_instruction}

## Schema do Dataset (Metadados e Flags de Governança)
{json.dumps(schema.get('columns', []), indent=2, ensure_ascii=False)}

{python_section}

## Dashboard Gerado (HTML — Resumo)
```html
{html_summary}
```

## Queries SQL Geradas
{queries_text}

## Resultados das Queries (Amostra)
{results_text if results_text else "Resultados não disponíveis"}

## Tarefa
Avalie rigorosamente o dashboard quanto à acurácia, design e GOVERNANÇA.
Dê atenção especial se o código (SQL ou Python) respeita as `usage_instructions` do schema histórico/snapshot.
Retorne o diagnóstico em JSON.
"""
