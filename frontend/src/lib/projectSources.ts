export interface StoredProjectSource {
  id: string;
  name: string;
  type: string;
  size: number;
  rows: number;
  columns: string[];
  previewData: Record<string, unknown>[];
  sample: Record<string, unknown>[];
  selectedCols?: string[];
  descriptions?: Record<string, string>;
  semanticFlags?: Record<string, {
    is_key?: boolean;
    is_historical_date?: boolean;
    is_category?: boolean;
    is_value?: boolean;
    is_elected_for_risk?: boolean;
    risk_dna_marker?: string;
  }>;
  status?: string;
  aiDescription?: string;
  aiInsights?: string[];
}

const LEGACY_KEY = "agent_bi_multi_sources";

export function getProjectSourcesKey(projectId: string) {
  return `agent_bi_sources_${projectId}`;
}

export function getProjectRelationshipsKey(projectId: string) {
  return `agent_bi_relationships_${projectId}`;
}

export function normalizeProjectSource(source: Partial<StoredProjectSource>): StoredProjectSource {
  const previewData = Array.isArray(source.previewData) ? source.previewData : [];
  const sample = Array.isArray(source.sample)
    ? source.sample
    : previewData.slice(0, 10);
  const columns =
    Array.isArray(source.columns) && source.columns.length > 0
      ? source.columns
      : previewData[0]
        ? Object.keys(previewData[0])
        : [];

  return {
    id: source.id || Math.random().toString(36).slice(2, 11),
    name: source.name || "Fonte sem nome",
    type: source.type || "FILE",
    size: typeof source.size === "number" ? source.size : 0,
    rows: typeof source.rows === "number" ? source.rows : previewData.length,
    columns,
    previewData,
    sample,
    selectedCols: Array.isArray(source.selectedCols) ? source.selectedCols : columns,
    descriptions: source.descriptions || {},
    semanticFlags: source.semanticFlags || {},
    status: source.status || "READY",
    aiDescription: source.aiDescription || "",
    aiInsights: Array.isArray(source.aiInsights) ? source.aiInsights : [],
  };
}

export function readProjectSources(projectId: string): StoredProjectSource[] {
  if (typeof window === "undefined") return [];

  const raw =
    sessionStorage.getItem(getProjectSourcesKey(projectId)) ||
    sessionStorage.getItem(LEGACY_KEY);

  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalizeProjectSource);
  } catch {
    return [];
  }
}

export function writeProjectSources(projectId: string, sources: StoredProjectSource[]) {
  if (typeof window === "undefined") return;
  const normalized = sources.map(normalizeProjectSource);
  const payload = JSON.stringify(normalized);
  sessionStorage.setItem(getProjectSourcesKey(projectId), payload);
  sessionStorage.setItem(LEGACY_KEY, payload);
}

export function mergeProjectSources(
  apiSources: StoredProjectSource[],
  sessionSources: StoredProjectSource[],
): StoredProjectSource[] {
  const byName = new Map<string, StoredProjectSource>();

  // 1. Processamos as fontes da sessão primeiro (contêm edições de colunas/descrições do usuário)
  sessionSources.forEach((source) => {
    if (source.name) {
      byName.set(source.name, normalizeProjectSource(source));
    }
  });

  // 2. Mesclamos com as fontes da API (contêm os IDs reais do backend e metadados oficiais)
  apiSources.forEach((apiSource) => {
    const existing = byName.get(apiSource.name);
    const normalizedApi = normalizeProjectSource(apiSource);

    if (!existing) {
      byName.set(normalizedApi.name, normalizedApi);
      return;
    }

    // Se já existe, mesclamos mantendo as customizações do usuário (descrições, colunas selecionadas)
    // mas priorizamos o ID e status da API (backend).
    // IMPORTANTE: Se as descrições ou flags locais estiverem vazias, aceitamos o preenchimento automático da IA.
    const mergedDescriptions = { ...(normalizedApi.descriptions || {}) };
    Object.keys(existing.descriptions || {}).forEach(col => {
      // Se o usuário já escreveu algo, mantemos a escrita dele
      if (existing.descriptions?.[col]) mergedDescriptions[col] = existing.descriptions[col];
    });

    const mergedFlags = { ...(normalizedApi.semanticFlags || {}) };
    Object.keys(existing.semanticFlags || {}).forEach(col => {
       const hasLocalFlag = Object.values(existing.semanticFlags?.[col] || {}).some(v => v === true);
       if (hasLocalFlag) mergedFlags[col] = existing.semanticFlags?.[col] || {};
    });

    byName.set(normalizedApi.name, {
      ...existing,
      id: normalizedApi.id, // O ID do backend sempre vence
      status: normalizedApi.status,
      rows: normalizedApi.rows || existing.rows,
      size: normalizedApi.size || existing.size,
      previewData: normalizedApi.previewData.length > 0 ? normalizedApi.previewData : existing.previewData,
      sample: normalizedApi.sample.length > 0 ? normalizedApi.sample : existing.sample,
      columns: normalizedApi.columns.length > 0 ? normalizedApi.columns : existing.columns,
      descriptions: mergedDescriptions,
      semanticFlags: mergedFlags,
      aiDescription: normalizedApi.aiDescription || existing.aiDescription,
      aiInsights: normalizedApi.aiInsights || existing.aiInsights,
    });
  });

  return Array.from(byName.values());
}
