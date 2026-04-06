"""
apps.ai_engine.services.html_renderer_service
Camada de renderizacao HTML do dashboard.
"""
from __future__ import annotations

import json
from typing import Any

from django.utils import timezone


class DashboardHtmlRendererService:
    OPERATIONAL_MARKER = 'data-agent-bi-operational-dashboard="true"'

    def build_html(self, context: dict, footer_insights: list[str], sql_proposal: dict | None = None) -> str:
        """
        Mantem compatibilidade com chamadas existentes.
        """
        return self.build_operational_html(
            context=context,
            footer_insights=footer_insights,
            sql_proposal=sql_proposal or {},
        )

    def is_operational_dashboard_html(self, html: str) -> bool:
        content = (html or "")
        if not content:
            return False
        required_markers = [
            self.OPERATIONAL_MARKER,
            "fetch(",
            "/api/v1/copilot/sql-preview",
            "id=\"agent-bi-insights\"",
        ]
        return all(marker in content for marker in required_markers)

    def build_operational_html(self, context: dict, footer_insights: list[str], sql_proposal: dict | None = None) -> str:
        title = self._escape_html(context.get("reportTitle") or context.get("dashboardName") or "Dashboard Corporativo")
        description = self._escape_html(context.get("reportDescription") or "Dashboard incremental corporativo.")

        sql_text = ""
        if isinstance(sql_proposal, dict):
            sql_text = str(sql_proposal.get("sql") or "").strip()

        api_base_url = self._resolve_api_base_url(context)
        api_url = f"{api_base_url.rstrip('/')}/api/v1/copilot/sql-preview"

        fetch_payload = {
            "sql": sql_text,
            "datasets": context.get("datasets") or [],
            "limit": 300,
        }
        insights = self._normalize_insights(footer_insights)

        fetch_payload_json = json.dumps(fetch_payload, ensure_ascii=False)
        insights_json = json.dumps(insights, ensure_ascii=False)

        generated_at = timezone.now().strftime("%d/%m/%Y %H:%M")

        return f"""<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5efe8;
      --card: #ffffff;
      --text: #2f211d;
      --muted: #7b675d;
      --border: #ddcfc4;
      --accent: #805f4f;
      --accent-soft: #ecd9cc;
      --good: #1f7a4f;
      --warn: #9a5b13;
      --bad: #9d2f2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: linear-gradient(135deg, #f6efe8 0%, #f2e7dd 100%); color: var(--text); }}
    .container {{ max-width: 1280px; margin: 0 auto; padding: 28px 22px 34px 22px; }}
    .header {{ margin-bottom: 18px; }}
    .header p {{ margin: 0; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); font-weight: 700; }}
    .header h1 {{ margin: 7px 0 8px 0; font-size: 30px; line-height: 1.2; color: var(--text); }}
    .header .desc {{ margin: 0; color: #5b4a42; line-height: 1.55; max-width: 900px; }}
    .status {{ margin-top: 8px; font-size: 12px; color: var(--muted); }}

    .kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }}
    .kpi .label {{ font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
    .kpi .value {{ font-size: 26px; font-weight: 700; color: var(--text); }}

    .grid {{ display: grid; grid-template-columns: 1.2fr .8fr; gap: 12px; margin-top: 12px; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }}
    .card h3 {{ margin: 0 0 12px 0; font-size: 16px; color: var(--text); }}

    .bars {{ display: flex; flex-direction: column; gap: 9px; }}
    .bar-row {{ display: grid; grid-template-columns: 160px 1fr 70px; gap: 8px; align-items: center; }}
    .bar-label {{ font-size: 12px; color: #594941; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{ height: 12px; border-radius: 99px; background: #f0e4da; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: linear-gradient(90deg, #9f7b68, #7d5c4e); }}
    .bar-val {{ font-size: 11px; color: #5f4f47; text-align: right; }}

    .donut-wrap {{ display: flex; align-items: center; gap: 16px; }}
    .donut {{ width: 170px; height: 170px; border-radius: 999px; border: 1px solid var(--border); }}
    .legend {{ flex: 1; display: flex; flex-direction: column; gap: 8px; }}
    .legend-item {{ display: grid; grid-template-columns: 12px 1fr auto; gap: 8px; align-items: center; font-size: 12px; color: #594941; }}
    .dot {{ width: 12px; height: 12px; border-radius: 999px; }}

    .table-card {{ margin-top: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid var(--border); text-align: left; padding: 8px 6px; }}
    th {{ background: #f7f0ea; color: #594941; font-weight: 700; }}

    .insights {{ margin-top: 12px; }}
    .insights ol {{ margin: 0; padding-left: 20px; }}
    .insights li {{ margin: 8px 0; line-height: 1.45; color: #4d3d36; }}

    .sql {{ margin-top: 12px; font-family: Consolas, monospace; font-size: 11px; background: #1f1a18; color: #f5e6dc; border-radius: 10px; padding: 10px; white-space: pre-wrap; }}
    .footer {{ margin-top: 16px; padding-top: 10px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted); }}

    @media (max-width: 1024px) {{
      .kpis {{ grid-template-columns: 1fr; }}
      .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 100px 1fr 56px; }}
      .donut-wrap {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body {self.OPERATIONAL_MARKER}>
  <div class=\"container\">
    <header class=\"header\">
      <p>Dashboard Corporativo Operacional</p>
      <h1>{title}</h1>
      <p class=\"desc\">{description}</p>
      <p class=\"status\" id=\"agent-bi-status\">Consultando dados via NL2SQL...</p>
    </header>

    <section class=\"kpis\" id=\"agent-bi-kpis\"></section>

    <section class=\"grid\">
      <article class=\"card\">
        <h3>Distribuicao por Dimensao</h3>
        <div id=\"agent-bi-bars\" class=\"bars\"></div>
      </article>
      <article class=\"card\">
        <h3>Participacao Relativa</h3>
        <div id=\"agent-bi-donut\" class=\"donut-wrap\"></div>
      </article>
    </section>

    <article class=\"card table-card\">
      <h3>Tabela Analitica</h3>
      <div id=\"agent-bi-table\"></div>
    </article>

    <article class=\"card insights\">
      <h3>Seis Insights Objetivos</h3>
      <ol id=\"agent-bi-insights\"></ol>
    </article>

    <article class=\"sql\" id=\"agent-bi-sql\"></article>

    <footer class=\"footer\">
      Versao gerada em {generated_at}. Status: DRAFT. Fonte de consulta: endpoint NL2SQL via fetch.
    </footer>
  </div>

  <script>
    (function () {{
      const apiUrl = {json.dumps(api_url)};
      const payload = {fetch_payload_json};
      const baseInsights = {insights_json};

      const statusEl = document.getElementById('agent-bi-status');
      const kpisEl = document.getElementById('agent-bi-kpis');
      const barsEl = document.getElementById('agent-bi-bars');
      const donutEl = document.getElementById('agent-bi-donut');
      const tableEl = document.getElementById('agent-bi-table');
      const insightsEl = document.getElementById('agent-bi-insights');
      const sqlEl = document.getElementById('agent-bi-sql');

      function fmt(n) {{
        if (typeof n !== 'number' || Number.isNaN(n)) return '-';
        return new Intl.NumberFormat('pt-BR').format(n);
      }}

      function pickColumns(rows) {{
        if (!rows.length) return {{ numeric: [], text: [] }};
        const sample = rows[0];
        const keys = Object.keys(sample);
        const numeric = keys.filter((k) => typeof sample[k] === 'number');
        const text = keys.filter((k) => typeof sample[k] !== 'number');
        return {{ numeric, text }};
      }}

      function safeTopRows(rows, size) {{
        return rows.slice(0, size);
      }}

      function renderKpis(data, rows, measureKey) {{
        const sum = rows.reduce((acc, row) => acc + (Number(row[measureKey]) || 0), 0);
        const cards = [
          {{ label: 'Linhas retornadas', value: data.row_count || rows.length }},
          {{ label: 'Colunas retornadas', value: (data.columns || []).length }},
          {{ label: measureKey ? `Soma de ${{measureKey}}` : 'Soma de valores', value: sum }},
        ];
        kpisEl.innerHTML = cards.map((card) => `\n          <div class="kpi">\n            <div class="label">${{card.label}}</div>\n            <div class="value">${{fmt(Number(card.value) || 0)}}</div>\n          </div>\n        `).join('');
      }}

      function renderBars(rows, dimensionKey, measureKey) {{
        if (!rows.length || !dimensionKey || !measureKey) {{
          barsEl.innerHTML = '<p>Nao ha dados suficientes para grafico de barras.</p>';
          return;
        }}
        const top = safeTopRows(rows, 8);
        const maxVal = Math.max(...top.map((row) => Number(row[measureKey]) || 0), 1);
        barsEl.innerHTML = top.map((row) => {{
          const label = String(row[dimensionKey] ?? '-');
          const val = Number(row[measureKey]) || 0;
          const width = Math.max(2, Math.round((val / maxVal) * 100));
          return `\n            <div class="bar-row">\n              <div class="bar-label" title="${{label}}">${{label}}</div>\n              <div class="bar-track"><div class="bar-fill" style="width:${{width}}%"></div></div>\n              <div class="bar-val">${{fmt(val)}}</div>\n            </div>\n          `;
        }}).join('');
      }}

      function renderDonut(rows, dimensionKey, measureKey) {{
        if (!rows.length || !dimensionKey || !measureKey) {{
          donutEl.innerHTML = '<p>Nao ha dados suficientes para grafico de participacao.</p>';
          return;
        }}
        const top = safeTopRows(rows, 5);
        const palette = ['#7b5f52', '#9e7e6d', '#c09e87', '#d6b9a2', '#ebd6c4'];
        const total = top.reduce((acc, row) => acc + (Number(row[measureKey]) || 0), 0) || 1;

        let start = 0;
        const segments = top.map((row, idx) => {{
          const val = Number(row[measureKey]) || 0;
          const pct = (val / total) * 100;
          const end = start + pct;
          const item = {{
            label: String(row[dimensionKey] ?? '-'),
            val,
            pct,
            color: palette[idx % palette.length],
            from: start,
            to: end,
          }};
          start = end;
          return item;
        }});

        const gradient = segments
          .map((s) => `${{s.color}} ${{s.from.toFixed(2)}}% ${{s.to.toFixed(2)}}%`)
          .join(', ');

        const legend = segments
          .map((s) => `\n            <div class="legend-item">\n              <span class="dot" style="background:${{s.color}}"></span>\n              <span>${{s.label}}</span>\n              <span>${{s.pct.toFixed(1)}}%</span>\n            </div>\n          `)
          .join('');

        donutEl.innerHTML = `\n          <div class="donut" style="background: conic-gradient(${{gradient}})"></div>\n          <div class="legend">${{legend}}</div>\n        `;
      }}

      function renderTable(data, rows) {{
        const columns = data.columns || [];
        if (!rows.length || !columns.length) {{
          tableEl.innerHTML = '<p>Nao ha dados para tabela.</p>';
          return;
        }}
        const head = columns.map((c) => `<th>${{c}}</th>`).join('');
        const body = safeTopRows(rows, 20)
          .map((row) => `<tr>${{columns.map((c) => `<td>${{row[c] ?? ''}}</td>`).join('')}}</tr>`)
          .join('');
        tableEl.innerHTML = `<table><thead><tr>${{head}}</tr></thead><tbody>${{body}}</tbody></table>`;
      }}

      function buildInsights(rows, dimensionKey, measureKey) {{
        const insights = [];
        const top = safeTopRows(rows, 6);

        if (top.length && dimensionKey && measureKey) {{
          const first = top[0];
          insights.push(`A maior contribuicao observada foi em \"${{first[dimensionKey]}}\" com ${{fmt(Number(first[measureKey]) || 0)}} registros/valor.`);
        }}

        if (top.length >= 2 && measureKey) {{
          const diff = (Number(top[0][measureKey]) || 0) - (Number(top[1][measureKey]) || 0);
          insights.push(`A diferenca entre o primeiro e o segundo item e de ${{fmt(Math.abs(diff))}}.`);
        }}

        if (rows.length) {{
          insights.push(`A consulta NL2SQL retornou ${{fmt(rows.length)}} linhas nesta amostra operacional.`);
        }}

        if (dimensionKey) {{
          const distinct = new Set(rows.map((r) => String(r[dimensionKey]))).size;
          insights.push(`Foram identificadas ${{fmt(distinct)}} categorias distintas para \"${{dimensionKey}}\".`);
        }}

        if (measureKey) {{
          const values = rows.map((r) => Number(r[measureKey]) || 0);
          const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
          insights.push(`A media de \"${{measureKey}}\" no resultado e ${{fmt(Math.round(avg))}}.`);
        }}

        while (insights.length < 6 && baseInsights.length > insights.length) {{
          insights.push(baseInsights[insights.length]);
        }}
        while (insights.length < 6) {{
          insights.push('Nao ha evidencias adicionais suficientes para ampliar os insights sem extrapolar os dados retornados.');
        }}

        return insights.slice(0, 6);
      }}

      async function run() {{
        sqlEl.textContent = payload.sql || 'SQL nao informada.';

        if (!payload.sql || !Array.isArray(payload.datasets) || !payload.datasets.length) {{
          statusEl.textContent = 'Nao foi possivel consultar: SQL ou datasets ausentes no payload.';
          const fallback = baseInsights.slice(0, 6);
          insightsEl.innerHTML = fallback.map((item) => `<li>${{item}}</li>`).join('');
          return;
        }}

        try {{
          const res = await fetch(apiUrl, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload),
          }});

          if (!res.ok) {{
            const err = await res.json().catch(() => ({{ detail: 'Erro desconhecido ao consultar dados.' }}));
            throw new Error(err.detail || `Erro HTTP ${{res.status}}`);
          }}

          const data = await res.json();
          const rows = Array.isArray(data.rows) ? data.rows : [];
          const columns = pickColumns(rows);
          const dimensionKey = columns.text[0] || (data.columns || [])[0] || null;
          const measureKey = columns.numeric[0] || (data.columns || []).find((c) => c !== dimensionKey) || null;

          renderKpis(data, rows, measureKey);
          renderBars(rows, dimensionKey, measureKey);
          renderDonut(rows, dimensionKey, measureKey);
          renderTable(data, rows);

          const insights = buildInsights(rows, dimensionKey, measureKey);
          insightsEl.innerHTML = insights.map((item) => `<li>${{item}}</li>`).join('');

          statusEl.textContent = `Consulta operacional concluida com sucesso (${{rows.length}} linhas).`;
        }} catch (error) {{
          statusEl.textContent = `Falha na consulta operacional: ${{error.message}}`;
          kpisEl.innerHTML = '';
          barsEl.innerHTML = '<p>Falha ao carregar grafico de barras.</p>';
          donutEl.innerHTML = '<p>Falha ao carregar grafico de participacao.</p>';
          tableEl.innerHTML = '<p>Falha ao carregar tabela analitica.</p>';
          const fallback = baseInsights.slice(0, 6);
          insightsEl.innerHTML = fallback.map((item) => `<li>${{item}}</li>`).join('');
        }}
      }}

      run();
    }})();
  </script>
</body>
</html>"""

    def _resolve_api_base_url(self, context: dict) -> str:
        metadata = context.get("reportMetadata") or {}
        if isinstance(metadata, dict):
            api_base_url = str(metadata.get("apiBaseUrl") or "").strip()
            if api_base_url:
                return api_base_url
        return "http://127.0.0.1:8000"

    def _normalize_insights(self, footer_insights: list[str]) -> list[str]:
        insights = [str(item).strip() for item in (footer_insights or []) if str(item).strip()]
        while len(insights) < 6:
            insights.append("Insight adicional indisponivel sem novos dados ou filtros complementares.")
        return insights[:6]

    def _escape_html(self, value: Any) -> str:
        text = str(value or "")
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
