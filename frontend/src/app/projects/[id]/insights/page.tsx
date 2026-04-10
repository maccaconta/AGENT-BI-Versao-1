"use client";
import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Wand2,
  Link as LinkIcon,
  Workflow,
  ArrowLeft,
  Trash,
  Plus,
  Database,
  Layers,
  Sparkles,
  Table,
  Info,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import {
  getProjectRelationshipsKey,
  readProjectSources,
  type StoredProjectSource,
} from "@/lib/projectSources";
import { ProjectHeaderStandard } from "@/components/project/ProjectHeaderStandard";

interface Relationship {
  id: string;
  source: string;
  target: string;
  sourceKey: string;
  targetKey: string;
  type: "Inner" | "Left";
  confidence: number;
  aiSuggested?: boolean;
}

export default function RelationshipDesigner() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [approving, setApproving] = useState(false);
  const [sources, setSources] = useState<StoredProjectSource[]>([]);
  const [rels, setRels] = useState<Relationship[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newRel, setNewRel] = useState<Partial<Relationship>>({ type: "Inner" });

  useEffect(() => {
    const loadedSources = readProjectSources(projectId);
    setSources(loadedSources);

    const storedRelationships = sessionStorage.getItem(getProjectRelationshipsKey(projectId));
    if (storedRelationships) {
      try {
        setRels(JSON.parse(storedRelationships));
        return;
      } catch {
        return;
      }
    }

    if (loadedSources.length > 1) {
      const first = loadedSources[0];
      const second = loadedSources[1];
      const firstKey = first.selectedCols?.[0] || first.columns?.[0] || "ID";
      const secondKey = second.selectedCols?.[0] || second.columns?.[0] || "ID";
      setRels([
        {
          id: Math.random().toString(36).slice(2, 11),
          source: first.name,
          target: second.name,
          sourceKey: firstKey,
          targetKey: secondKey,
          type: "Inner",
          confidence: 98.4,
          aiSuggested: true,
        },
      ]);
    }
  }, [projectId]);

  useEffect(() => {
    sessionStorage.setItem(getProjectRelationshipsKey(projectId), JSON.stringify(rels));
  }, [projectId, rels]);

  const sourceOptions = useMemo(
    () =>
      sources.map((source) => ({
        ...source,
        availableColumns:
          source.selectedCols && source.selectedCols.length > 0 ? source.selectedCols : source.columns,
      })),
    [sources],
  );

  const handleApprove = () => {
    if (isCartesianRisk || sources.length === 0) return;
    setApproving(true);
    setTimeout(() => {
      router.push(`/dashboard/generate`);
    }, 2800);
  };

  const removeRel = (id: string) => {
    setRels((prev) => prev.filter((rel) => rel.id !== id));
  };

  const addRelationship = () => {
    if (!newRel.source || !newRel.target || !newRel.sourceKey || !newRel.targetKey) return;
    const rel: Relationship = {
      id: Math.random().toString(36).slice(2, 11),
      source: newRel.source as string,
      target: newRel.target as string,
      sourceKey: newRel.sourceKey as string,
      targetKey: newRel.targetKey as string,
      type: (newRel.type as "Inner" | "Left") || "Inner",
      confidence: 100,
    };
    setRels([...rels, rel]);
    setShowAddForm(false);
    setNewRel({ type: "Inner" });
  };

  const isCartesianRisk = rels.length === 0 && sources.length > 1;

  if (approving) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center p-10 bg-lux-bg/5">
        <motion.div animate={{ scale: [1, 1.1, 1], rotate: [0, 5, -5, 0] }} transition={{ duration: 3, repeat: Infinity }}>
          <div className="w-40 h-40 rounded-full border-4 border-lux-text border-t-transparent animate-spin flex items-center justify-center shadow-[0_0_100px_rgba(0,0,0,0.1)]">
            <Database size={64} className="text-lux-text" />
          </div>
        </motion.div>
        <h2 className="text-4xl font-serif font-bold text-lux-text mt-12 mb-6 text-center">Gerando Base Analitica...</h2>
        <p className="text-lux-muted text-xl max-w-2xl text-center leading-relaxed font-light">
          Estamos consolidando o contexto semantico definido e preparando a estrutura final que alimentara o dashboard.
        </p>
      </div>
    );
  }

  return (
    <motion.div initial={false} animate={{ opacity: 1, y: 0 }} className="max-w-[1600px] mx-auto pb-6 px-4">
      <ProjectHeaderStandard 
        projectId={projectId}
        step={4}
        title="Contexto Semântico & Inteligência"
        prevHref={`/projects/${projectId}/sources/preview`}
        prevLabel="Voltar para Transformação"
        onNext={handleApprove}
        nextLabel="Gerar Agente BI"
        nextDisabled={isCartesianRisk || sources.length === 0}
      />

      {sources.length === 0 && (
        <div className="glass-panel rounded-[2rem] border border-lux-border/20 bg-white/60 p-8 text-center text-lux-muted mb-5 mt-6">
          Nenhuma fonte revisada foi encontrada. Volte para as etapas anteriores para carregar e validar os dados.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch mb-6 mt-6">
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h3 className="text-[10px] uppercase font-bold text-lux-muted tracking-[0.2em] flex items-center gap-2">
              <Layers size={14} /> Fontes revisadas ({sources.length})
            </h3>
            <div
              className="inline-flex items-center gap-2 rounded-full border border-lux-border/40 bg-white/70 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-lux-muted"
              title="Conecte as fontes usando as colunas escolhidas para formar o contexto semantico que alimentara o Agente BI."
            >
              <Info size={12} />
              Guia rapido
            </div>
          </div>

          <div className="space-y-3">
            {sources.map((source, index) => (
              <div
                key={index}
                className="p-4 glass-panel bg-white border-lux-border/30 hover:shadow-xl transition-all rounded-[1.25rem] group border-l-4 border-l-lux-text"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-bold text-lux-text truncate max-w-[180px]">{source.name}</p>
                  <span className="text-[9px] bg-lux-bg px-2 py-1 rounded-full border border-lux-border/20 text-lux-muted font-bold uppercase tracking-widest">
                    Revisada
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-lux-muted px-1 font-medium">
                  <span className="flex items-center gap-1.5">
                    <Table size={12} /> {source.rows.toLocaleString()} registros
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Database size={12} /> {(source.selectedCols || source.columns || []).length} campos
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-8">
          <div className="glass-panel p-6 md:p-7 bg-lux-bg/10 border-lux-border/20 relative rounded-[2rem]">
            <div className="flex justify-between items-center mb-6 pb-4 border-b border-lux-border/20">
              <h2 className="text-2xl font-serif font-bold text-lux-text flex items-center gap-4">
                <Workflow size={28} /> Contexto Semantico das Fontes
              </h2>
              <div className="hidden md:flex items-center gap-3 text-[10px] font-bold text-green-700 bg-green-50 px-4 py-2 rounded-full border border-green-200 uppercase tracking-widest">
                <Sparkles size={14} /> Estrutura analitica
              </div>
            </div>

            <div className="space-y-4">
              <AnimatePresence>
                {rels.map((rel) => (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, x: 50 }}
                    key={rel.id}
                    className="relative p-5 bg-white border border-lux-border shadow-sm rounded-[1.5rem] group hover:shadow-2xl hover:scale-[1.01] transition-all"
                  >
                    <button
                      onClick={() => removeRel(rel.id)}
                      className="absolute top-5 right-5 w-10 h-10 rounded-full bg-red-50 text-red-500 border border-red-100 flex items-center justify-center opacity-0 group-hover:opacity-100 shadow-lg hover:bg-red-500 hover:text-white transition-all"
                    >
                      <Trash size={18} />
                    </button>

                    <div className="grid grid-cols-1 md:grid-cols-7 items-center gap-4">
                      <div className="md:col-span-3 bg-lux-bg/5 p-4 rounded-2xl border border-lux-border/10">
                        <p className="text-[9px] uppercase font-bold text-lux-muted mb-2 opacity-60 tracking-widest">Origem</p>
                        <p className="text-xs font-bold text-lux-text truncate mb-4">{rel.source}</p>
                        <div className="text-[11px] font-mono bg-lux-text text-lux-bg px-4 py-2.5 rounded-xl shadow-lg inline-block w-full text-center">
                          {rel.sourceKey}
                        </div>
                      </div>

                      <div className="md:col-span-1 flex flex-col items-center justify-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-lux-bg border border-lux-border flex items-center justify-center text-lux-text shadow-inner group-hover:rotate-180 transition-transform duration-700">
                          <LinkIcon size={20} />
                        </div>
                        <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-lux-muted">
                          {rel.type}
                        </span>
                      </div>

                      <div className="md:col-span-3 bg-lux-bg/5 p-4 rounded-2xl border border-lux-border/10 text-right">
                        <p className="text-[9px] uppercase font-bold text-lux-muted mb-2 opacity-60 tracking-widest">Destino</p>
                        <p className="text-xs font-bold text-lux-text truncate mb-4">{rel.target}</p>
                        <div className="text-[11px] font-mono bg-lux-text text-lux-bg px-4 py-2.5 rounded-xl shadow-lg inline-block w-full text-center">
                          {rel.targetKey}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {showAddForm && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-6 bg-white border-2 border-lux-text border-opacity-10 rounded-[2rem] shadow-2xl space-y-6"
                >
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase text-lux-muted px-2">Fonte A</label>
                      <select
                        className="bg-lux-bg/20 border-lux-border w-full p-4 rounded-2xl text-sm font-bold focus:ring-2 ring-lux-text/10 outline-none"
                        onChange={(event) => setNewRel({ ...newRel, source: event.target.value })}
                      >
                        <option value="">Selecione a tabela...</option>
                        {sourceOptions.map((source) => (
                          <option key={source.id} value={source.name}>
                            {source.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase text-lux-muted px-2">Fonte B</label>
                      <select
                        className="bg-lux-bg/20 border-lux-border w-full p-4 rounded-2xl text-sm font-bold focus:ring-2 ring-lux-text/10 outline-none"
                        onChange={(event) => setNewRel({ ...newRel, target: event.target.value })}
                      >
                        <option value="">Selecione a tabela...</option>
                        {sourceOptions.map((source) => (
                          <option key={source.id} value={source.name}>
                            {source.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase text-lux-muted px-2">Chave A</label>
                      <select
                        disabled={!newRel.source}
                        className="bg-white border-lux-border w-full p-4 rounded-2xl text-sm italic focus:ring-2 ring-lux-text/10 outline-none"
                        onChange={(event) => setNewRel({ ...newRel, sourceKey: event.target.value })}
                      >
                        <option value="">Escolher coluna...</option>
                        {sourceOptions
                          .find((source) => source.name === newRel.source)
                          ?.availableColumns?.map((col: string) => (
                            <option key={col} value={col}>
                              {col}
                            </option>
                          ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase text-lux-muted px-2">Chave B</label>
                      <select
                        disabled={!newRel.target}
                        className="bg-white border-lux-border w-full p-4 rounded-2xl text-sm italic focus:ring-2 ring-lux-text/10 outline-none"
                        onChange={(event) => setNewRel({ ...newRel, targetKey: event.target.value })}
                      >
                        <option value="">Escolher coluna...</option>
                        {sourceOptions
                          .find((source) => source.name === newRel.target)
                          ?.availableColumns?.map((col: string) => (
                            <option key={col} value={col}>
                              {col}
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                    <button
                      onClick={addRelationship}
                      className="bg-lux-text text-lux-bg h-14 rounded-2xl font-bold shadow-2xl hover:scale-[1.02] transition-transform"
                    >
                      Salvar relacionamento
                    </button>
                    <button
                      onClick={() => setShowAddForm(false)}
                      className="h-14 border-lux-border/60 border rounded-2xl font-bold text-lux-muted"
                    >
                      Cancelar
                    </button>
                  </div>
                </motion.div>
              )}

              {!showAddForm && (
                <button
                  onClick={() => setShowAddForm(true)}
                  disabled={sources.length < 2}
                  className="w-full mt-4 flex items-center justify-center gap-3 text-lux-muted font-bold text-sm bg-lux-bg/30 py-4 border-2 border-dashed border-lux-border/40 rounded-[1.5rem] hover:text-lux-text hover:border-lux-text hover:bg-lux-bg/50 transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Plus size={20} className="group-hover:rotate-90 transition-transform" /> Adicionar Relacao Semantica
                </button>
              )}

              {isCartesianRisk && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-6 p-6 bg-red-50 border border-red-200 rounded-[2rem] flex items-center gap-6 shadow-inner"
                >
                  <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center text-red-600 flex-shrink-0">
                    <Database size={28} />
                  </div>
                  <div>
                    <h4 className="font-bold text-red-900 text-lg mb-1">Contexto semantico obrigatorio</h4>
                    <p className="text-red-700 text-sm leading-relaxed font-light">
                      Existem varias fontes carregadas. Defina ao menos uma relacao valida antes de seguir para o
                      Agente BI.
                    </p>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
