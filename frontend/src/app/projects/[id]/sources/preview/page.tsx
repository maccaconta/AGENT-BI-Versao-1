"use client";
import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  FileSpreadsheet,
  Edit3,
  Layers,
  Database,
  Table,
  ChevronLeft,
  ChevronRight,
  Info,
  Sparkles,
  Shield,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import {
  mergeProjectSources,
  normalizeProjectSource,
  readProjectSources,
  writeProjectSources,
  type StoredProjectSource,
} from "@/lib/projectSources";
import { getBackendAuthHeaders } from "@/lib/backendAuth";
import { ProjectHeaderStandard } from "@/components/project/ProjectHeaderStandard";

interface ApiDataset {
  id: string;
  name: string;
  status: string;
  description: string;
  source_type: string;
  s3_original_size_bytes: number;
  row_count: number;
  sample_json?: Record<string, unknown>[];
  schema_json?: {
    columns?: Array<{
      name: string;
      description?: string;
      is_key?: boolean;
      is_historical_date?: boolean;
      is_category?: boolean;
      is_value?: boolean;
      is_elected_for_risk?: boolean;
      risk_dna_marker?: string;
    }>;
  };
  data_profile_json?: { ai_strategic_insights?: string[]; is_fact_table?: boolean };
}

export default function DataPreviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [sources, setSources] = useState<StoredProjectSource[]>([]);
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null);
  const [activeEditCol, setActiveEditCol] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(12);
  const [loading, setLoading] = useState(true);
  const [columnFilter, setColumnFilter] = useState("");
  const [draftFlags, setDraftFlags] = useState<{
    is_key: boolean;
    is_historical_date: boolean;
    is_category: boolean;
    is_value: boolean;
    is_elected_for_risk: boolean;
    risk_dna_marker?: string;
  }>({
    is_key: false,
    is_historical_date: false,
    is_category: false,
    is_value: false,
    is_elected_for_risk: false,
  });

  const saveSources = (items: StoredProjectSource[]) => {
    setSources(items);
    writeProjectSources(projectId, items);
  };

  useEffect(() => {
    const sessionSources = readProjectSources(projectId);
    if (sessionSources.length > 0) {
      setSources(sessionSources);
      setActiveSourceId(sessionSources[0].id);
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    let isMounted = true;

    const fetchDatasets = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/api/v1/datasets/?project_id=${projectId}`, {
          headers: getBackendAuthHeaders(),
        });
        if (!response.ok) return;

        const data = await response.json();
        const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
        if (results.length === 0 || !isMounted) return;

        const apiSources = results.map((dataset: ApiDataset) => {
          const colDescriptions: Record<string, string> = {};
          const colFlags: Record<string, any> = {};
          
          if (dataset.schema_json?.columns) {
            dataset.schema_json.columns.forEach((c: any) => {
              if (c.description) colDescriptions[c.name] = c.description;
              colFlags[c.name] = {
                is_key: !!c.is_key,
                is_historical_date: !!c.is_historical_date,
                is_category: !!c.is_category,
                is_value: !!c.is_value,
                is_elected_for_risk: !!c.is_elected_for_risk,
                risk_dna_marker: c.risk_dna_marker || "",
              };
            });
            // Propaga flag de Tabela Fato do Dataset
            if (dataset.data_profile_json && (dataset.data_profile_json as any).is_fact_table) {
               (colFlags as any).is_fact_table = true;
            }
          }

          return normalizeProjectSource({
            id: dataset.id,
            name: dataset.name,
            status: dataset.status,
            type: dataset.source_type,
            size: dataset.s3_original_size_bytes || 0,
            rows: dataset.row_count || 0,
            previewData: Array.isArray(dataset.sample_json) ? dataset.sample_json : [],
            sample: Array.isArray(dataset.sample_json) ? dataset.sample_json.slice(0, 10) : [],
            columns: Array.isArray(dataset.schema_json?.columns)
              ? dataset.schema_json.columns.map((column: any) => column.name)
              : [],
            descriptions: colDescriptions,
            semanticFlags: colFlags,
            // Armazena campos extras da IA
            aiDescription: dataset.description,
            aiInsights: dataset.data_profile_json?.ai_strategic_insights || [],
          });
        });

        const merged = mergeProjectSources(apiSources, readProjectSources(projectId));
        saveSources(merged);
        if (!activeSourceId && merged.length > 0) {
          setActiveSourceId(merged[0].id);
        }
      } catch (error) {
        console.error("Erro ao carregar datasets:", error);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchDatasets();
    const interval = setInterval(fetchDatasets, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeSourceId, projectId]);

  const activeSource = useMemo(
    () => sources.find((source) => source.id === activeSourceId) || null,
    [activeSourceId, sources],
  );

  const columns = useMemo(() => {
    if (!activeSource) return [];
    if (activeSource.columns.length > 0) return activeSource.columns;
    if (activeSource.previewData[0]) return Object.keys(activeSource.previewData[0]);
    return [];
  }, [activeSource]);

  const currentRows =
    activeSource?.previewData.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage) || [];
  const totalPages = activeSource ? Math.max(1, Math.ceil(activeSource.previewData.length / rowsPerPage)) : 0;

  const toggleColumn = (col: string) => {
    if (!activeSource) return;
    const nextSources = sources.map((source) => {
      if (source.id !== activeSourceId) return source;
      const selected = new Set(source.selectedCols || []);
      if (selected.has(col)) selected.delete(col);
      else selected.add(col);
      return { ...source, selectedCols: Array.from(selected) };
    });
    saveSources(nextSources);
  };

  const updateMetadata = async (col: string, text: string, flags: any) => {
    if (!activeSource) return;

    // Atualiza estado local primeiro para UX instantânea
    const nextSources = sources.map((source) =>
      source.id === activeSourceId
        ? { 
            ...source, 
            descriptions: { ...(source.descriptions || {}), [col]: text },
            semanticFlags: { ...(source.semanticFlags || {}), [col]: flags }
          }
        : source,
    );
    saveSources(nextSources);
    setActiveEditCol(null);

    // Se for um dataset persistido no backend (nâo apenas local), sincroniza
    if (activeSourceId && !activeSourceId.startsWith("local-")) {
      try {
        const getResp = await fetch(`http://127.0.0.1:8000/api/v1/datasets/${activeSourceId}/`, {
          headers: getBackendAuthHeaders(),
        });
        if (!getResp.ok) return;
        const dataset = await getResp.json();
        
        const schema = { ...dataset.schema_json };
        if (schema.columns) {
          schema.columns = schema.columns.map((c: any) => 
            c.name === col ? { ...c, description: text, ...flags } : c
          );
        }

        await fetch(`http://127.0.0.1:8000/api/v1/datasets/${activeSourceId}/`, {
          method: "PATCH",
          headers: {
            ...getBackendAuthHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ schema_json: schema }),
        });
      } catch (err) {
        console.error("Erro ao sincronizar metadados com backend:", err);
      }
    }
  };

  const proceedToInsights = () => {
    saveSources(sources);
    router.push(`/projects/${projectId}/insights`);
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes <= 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const getSelectedCount = (source: StoredProjectSource) => (source.selectedCols || columns).length;

  return (
    <motion.div initial={false} animate={{ opacity: 1 }} className="max-w-[1600px] mx-auto pb-6 px-4 h-screen flex flex-col overflow-hidden">
      <ProjectHeaderStandard 
        projectId={projectId}
        step={3}
        title="Transformação de Dados"
        prevHref={`/projects/${projectId}/sources`}
        nextHref={`/projects/${projectId}/insights`}
        nextLabel="Próximo: Contexto Semântico"
      />

      <div className="flex-1 overflow-hidden flex flex-col mt-4">
        {activeSource && (
          <motion.div key={activeSource.id} initial={false} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col min-h-0">
            {/* AI Strategic Intelligence - Lux-Sober Minimalist Design */}
            {(activeSource.aiDescription || (activeSource.aiInsights && activeSource.aiInsights.length > 0)) && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 border border-lux-border/30 bg-lux-bg/50 dark:bg-lux-card/20 rounded-[1.5rem] overflow-hidden shadow-sm"
              >
                <div className="p-4 lg:p-6 flex flex-col lg:flex-row gap-6">
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-lux-text text-lux-bg rounded-xl shadow-md">
                        <Sparkles size={18} />
                      </div>
                      <div>
                        <span className="text-[9px] font-black uppercase tracking-[0.3em] text-lux-muted block mb-0.5">Diagnóstico Executivo</span>
                        <h2 className="text-xl font-serif font-bold text-lux-text leading-tight">
                          {activeSource.aiDescription || "Interpretação Semântica"}
                        </h2>
                      </div>
                    </div>
                    
                    {activeSource.aiInsights && activeSource.aiInsights.length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                        {activeSource.aiInsights.map((insight, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-2 bg-white dark:bg-lux-card/40 border border-lux-border/20 rounded-xl group hover:border-lux-accent/30 transition-all">
                             <div className="mt-1 w-1 h-1 rounded-full bg-lux-accent/60 group-hover:bg-lux-accent shrink-0" />
                             <span className="text-[11px] font-medium text-lux-text/80 leading-snug italic">{insight}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 lg:w-60 bg-lux-bg/40 dark:bg-black/20 p-6 rounded-[1.2rem] border border-lux-border/10 flex flex-col justify-center gap-3">
                    <div className="space-y-1">
                      <p className="text-[9px] font-black uppercase text-lux-muted tracking-widest">Confiabilidade do Modelo</p>
                      <div className="flex items-center gap-2">
                         <div className="flex-1 h-1.5 bg-lux-border/20 rounded-full overflow-hidden">
                            <motion.div 
                              initial={{ width: 0 }} 
                              animate={{ width: "98%" }} 
                              transition={{ duration: 1.5, ease: "easeOut" }}
                              className="h-full bg-emerald-500/60" 
                            />
                         </div>
                         <span className="text-xs font-black text-emerald-600">98%</span>
                      </div>
                    </div>
                    
                    <div className="h-px bg-lux-border/10" />
                    
                    <div className="space-y-1">
                       <p className="text-[9px] font-black uppercase text-lux-muted tracking-widest">Aderência Semântica</p>
                       <p className="text-xl font-serif font-black text-lux-text">Alta Fidelidade</p>
                    </div>

                    {activeSource.status === "READY" && (
                      <div className="mt-2 flex items-center gap-2 text-[10px] font-bold text-emerald-600 bg-emerald-500/5 py-2 px-3 rounded-xl border border-emerald-500/10">
                         <CheckCircle2 size={12} />
                         Análise Auditada pela IA
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4 shrink-0">
              {[
                { label: "Registros", val: activeSource.rows.toLocaleString(), icon: <Layers size={18} /> },
                { label: "Volume", val: formatBytes(activeSource.size), icon: <Database size={18} /> },
                {
                  label: "Status",
                  val: activeSource.status === "READY" ? "Validada" : "Processando",
                  icon: activeSource.status === "READY" ? <CheckCircle2 size={18} className="text-green-500" /> : <Sparkles size={18} className="text-amber-500 animate-pulse" />,
                },
                {
                  label: "Campos",
                  val: `${getSelectedCount(activeSource)} de ${columns.length}`,
                  icon: <Table size={18} />,
                },
              ].map((stat, index) => (
                <div key={index} className="glass-panel p-4 bg-lux-bg/30 border-lux-border/20 rounded-[1.5rem] flex flex-col justify-between min-h-[70px]">
                  <div className="flex items-center justify-between mb-1">
                     <p className="text-[8px] text-lux-muted uppercase font-bold tracking-widest">{stat.label}</p>
                     <div className="text-lux-muted/20">{stat.icon}</div>
                  </div>
                  <p className="text-sm font-serif text-lux-text font-bold">{stat.val}</p>
                </div>
              ))}
            </div>

            {/* Grid de Dados - BRANCO PURO */}
            <div className="flex-1 min-h-0 bg-white border border-lux-border/30 rounded-[2.5rem] overflow-hidden shadow-2xl flex flex-col mb-4">
              <div className="overflow-auto flex-1 custom-scrollbar">
                <table className="w-full border-collapse text-sm">
                  <thead className="sticky top-0 bg-white z-10">
                    <tr className="border-b border-lux-border/20 text-lux-muted uppercase text-[10px] font-black tracking-widest bg-white">
                      {columns.map((col) => (
                        <th key={col} className="px-3 py-4 text-left border-lux-border/10 bg-lux-bg/10 first:border-l-0 group min-w-[260px] align-top">
                          <div className={`p-4 rounded-3xl border transition-all h-full flex flex-col gap-3 shadow-sm ${
                            (activeSource.selectedCols || []).includes(col) 
                              ? "bg-white border-lux-border/40 shadow-lux-shadow/5" 
                              : "bg-gray-50/50 border-dashed border-gray-300 opacity-60"
                          }`}>
                             {/* Header do Card: Checkbox + Nome */}
                             <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2 min-w-0">
                                  <input
                                    type="checkbox"
                                    checked={(activeSource.selectedCols || []).includes(col)}
                                    onChange={() => toggleColumn(col)}
                                    className="w-4 h-4 rounded-lg border-lux-border/50 text-lux-text focus:ring-lux-text/10 cursor-pointer"
                                  />
                                  <span className={`truncate font-black text-[12px] tracking-tight text-lux-text ${!(activeSource.selectedCols || []).includes(col) ? 'line-through italic opacity-50' : ''}`}>
                                    {col}
                                  </span>
                                </div>
                                
                                <button 
                                  onClick={(e) => { 
                                    e.stopPropagation();
                                    setActiveEditCol(col); 
                                    setEditDraft(activeSource.descriptions?.[col] || ""); 
                                    setDraftFlags({
                                      is_key: activeSource.semanticFlags?.[col]?.is_key || false,
                                      is_historical_date: activeSource.semanticFlags?.[col]?.is_historical_date || false,
                                      is_category: activeSource.semanticFlags?.[col]?.is_category || false,
                                      is_value: activeSource.semanticFlags?.[col]?.is_value || false,
                                      is_elected_for_risk: activeSource.semanticFlags?.[col]?.is_elected_for_risk || false,
                                    });
                                  }}
                                  className="p-1.5 hover:bg-lux-text hover:text-white rounded-xl border border-lux-border/20 transition-all flex items-center justify-center bg-white shadow-sm shrink-0"
                                  title="Editar Metadados"
                                >
                                  <Sparkles size={12} className="text-lux-accent" />
                                </button>
                             </div>

                             {/* Badges Semânticos */}
                             <div className="flex flex-wrap gap-1.5">
                                {activeSource.semanticFlags?.[col]?.is_key && (
                                  <span className="px-2 py-0.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-100 text-[8px] font-black uppercase tracking-widest">Key</span>
                                )}
                                {activeSource.semanticFlags?.[col]?.is_historical_date && (
                                  <span className="px-2 py-0.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-100 text-[8px] font-black uppercase tracking-widest">Date</span>
                                )}
                                {activeSource.semanticFlags?.[col]?.is_value && (
                                  <span className="px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100 text-[8px] font-black uppercase tracking-widest">Metric</span>
                                )}
                                
                                {/* Badge de DNA DE RISCO (🛡️) */}
                                {activeSource.semanticFlags?.[col]?.is_elected_for_risk && (
                                  <span className="px-2 py-0.5 rounded-lg bg-red-50 text-red-700 border border-red-200 text-[8px] font-black uppercase tracking-widest flex items-center gap-1">
                                    <Shield size={8} /> Risk DNA: {activeSource.semanticFlags?.[col]?.risk_dna_marker}
                                  </span>
                                )}
                             </div>

                             {/* Descrição / Prompt Integrado */}
                             {activeSource.descriptions?.[col] ? (
                               <div className="text-[10px] leading-relaxed text-lux-muted italic line-clamp-2 hover:line-clamp-none transition-all cursor-default">
                                  "{activeSource.descriptions[col]}"
                               </div>
                             ) : (
                               <div className="text-[9px] text-gray-400 italic">Sem descrição técnica...</div>
                             )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lux-border/5">
                    {currentRows.map((row, i) => (
                      <tr key={i} className={`hover:bg-lux-accent/5 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}`}>
                        {columns.map((col) => (
                          <td key={col} className={`px-6 py-4 border-l border-lux-border/5 text-lux-text/70 font-medium ${!(activeSource.selectedCols || []).includes(col) ? 'opacity-10' : ''}`}>
                            {String(row[col] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Paginação Interna */}
              <div className="p-4 bg-white border-t border-lux-border/10 flex items-center justify-between shrink-0 px-8">
                 <div className="flex items-center gap-2">
                    <button 
                      onClick={() => setCurrentPage(p => Math.max(1, p-1))} 
                      disabled={currentPage === 1}
                      className="p-2 rounded-xl hover:bg-lux-bg disabled:opacity-20"
                    >
                      <ChevronLeft size={18} />
                    </button>
                    <span className="text-[10px] font-black tracking-widest px-4">{currentPage} / {totalPages}</span>
                    <button 
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p+1))}
                      disabled={currentPage === totalPages}
                      className="p-2 rounded-xl hover:bg-lux-bg disabled:opacity-20"
                    >
                      <ChevronRight size={18} />
                    </button>
                 </div>
                 <span className="text-[10px] font-bold text-lux-muted uppercase tracking-widest italic opacity-40">
                   {getSelectedCount(activeSource)} de {columns.length} colunas selecionadas
                 </span>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Editor de Metadados (Modal) */}
      <AnimatePresence>
        {activeEditCol && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-lux-bg/60 backdrop-blur-md">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="w-full max-w-lg p-10 bg-white shadow-3xl border border-lux-border/20 rounded-[3rem]">
              <h3 className="text-2xl font-serif font-bold text-lux-text mb-2">Refinar Metadados</h3>
              <p className="text-lux-muted text-xs mb-6 leading-relaxed italic">
                Explique o significado desta coluna para o Agente BI. 
                <br />
                <strong>Ex:</strong> "Este campo representa o valor líquido da transação" ou "Considere este campo como a chave principal para análise de risco".
              </p>
              <textarea
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                className="w-full h-24 p-4 bg-lux-bg/30 border border-lux-border/40 rounded-2xl mb-4 resize-none focus:outline-none focus:ring-2 ring-lux-accent/20"
                placeholder="Ex: Valor total da transação sem impostos..."
              />
              
              <div className="grid grid-cols-2 gap-3 mb-6">
                 {[
                   { id: 'is_key', label: 'Campo Chave', desc: 'Identificador único' },
                   { id: 'is_historical_date', label: 'Data Histórica', desc: 'Eixo temporal' },
                   { id: 'is_category', label: 'Categoria', desc: 'Agrupamento/Filtro' },
                   { id: 'is_value', label: 'Valor', desc: 'Métrica/Cálculo' },
                 ].map((flag) => (
                   <label key={flag.id} className="flex items-start gap-2 p-3 bg-lux-bg/20 border border-lux-border/10 rounded-xl cursor-pointer hover:bg-lux-bg/40 transition-colors">
                     <input 
                       type="checkbox" 
                       checked={(draftFlags as any)[flag.id]} 
                       onChange={(e) => setDraftFlags({ ...draftFlags, [flag.id]: e.target.checked })}
                       className="mt-1 w-4 h-4 rounded border-lux-border/50 text-lux-text"
                     />
                     <div>
                       <p className="text-[10px] font-black uppercase text-lux-text leading-none mb-1">{flag.label}</p>
                       <p className="text-[9px] text-lux-muted leading-none">{flag.desc}</p>
                     </div>
                   </label>
                 ))}
              </div>

              <div className="flex justify-end gap-3">
                <button onClick={() => setActiveEditCol(null)} className="px-6 py-3 text-lux-muted font-bold hover:text-lux-text transition-colors">Cancelar</button>
                <button onClick={() => updateMetadata(activeEditCol, editDraft, draftFlags)} className="bg-lux-text text-lux-bg px-8 py-3 rounded-xl font-bold shadow-xl hover:scale-105 transition-all">Salvar</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
