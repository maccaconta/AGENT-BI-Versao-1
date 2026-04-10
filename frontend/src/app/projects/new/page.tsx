"use client";

import { motion } from "framer-motion";
import { Building2, ArrowLeft, Target, Briefcase, FileText, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import WizardStepper from "@/components/layout/WizardStepper";
import { getBackendJsonHeaders } from "@/lib/backendAuth";

const DRAFT_KEY = "agent_bi_project_draft";

type ProjectDraft = {
  projectId: string;
  dashboard: string;
  dataDomain: string;
  domainDataOwner: string;
  confidentiality: string;
  crawlFrequency: string;
  objective: string;
  specialist_prompt_id?: string | null;
};

export default function NewProjectWorkspace() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [form, setForm] = useState<ProjectDraft>({
    projectId: "",
    dashboard: "",
    dataDomain: "",
    domainDataOwner: "",
    confidentiality: "",
    crawlFrequency: "",
    objective: "",
    specialist_prompt_id: null,
  });

  const [specialists, setSpecialists] = useState<any[]>([]);
  const [fetchingSpecialists, setFetchingSpecialists] = useState(false);
  const [domains, setDomains] = useState<any[]>([]);
  const [fetchingDomains, setFetchingDomains] = useState(false);

  useEffect(() => {
    const rawDraft = sessionStorage.getItem(DRAFT_KEY);
    if (!rawDraft) return;

    try {
      const parsed = JSON.parse(rawDraft) as Partial<ProjectDraft>;
      setForm((current) => ({
        ...current,
        ...parsed,
        projectId: parsed.projectId || current.projectId,
      }));
    } catch {
      // Keep defaults if browser draft is invalid.
    }
  }, []);

  useEffect(() => {
    async function fetchSpecs() {
      try {
        setFetchingSpecialists(true);
        // Usando a ponte direta para o backend conforme padrão estabelecido
        const res = await fetch("http://127.0.0.1:8000/api/v1/governance/prompt-templates/?t=" + Date.now(), {
          headers: { "Content-Type": "application/json" } 
        });
        if (res.ok) {
          const data = await res.json();
          const results = Array.isArray(data) ? data : (data.results || []);
          // Filtro flexível para especialistas
          setSpecialists(results.filter((s: any) => 
            s.category?.toUpperCase() === "SPECIALIST" || s.category === "Especialista"
          ));
        }
      } catch (err) {
        console.error("Erro ao buscar especialistas:", err);
      } finally {
        setFetchingSpecialists(false);
      }
    }

    async function fetchDomains() {
      try {
        setFetchingDomains(true);
        const res = await fetch("http://127.0.0.1:8000/api/v1/projects/domains/?t=" + Date.now(), {
          headers: { "Content-Type": "application/json" }
        });
        if (res.ok) {
          const data = await res.json();
          const results = Array.isArray(data) ? data : (data.results || []);
          setDomains(results);
        }
      } catch (err) {
        console.error("Erro ao buscar domínios:", err);
      } finally {
        setFetchingDomains(false);
      }
    }

    fetchSpecs();
    fetchDomains();
  }, []);

  const persistDraft = (draft: ProjectDraft) => {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    sessionStorage.setItem("agent_bi_current_project_id", draft.projectId);
  };

  const updateField = <K extends keyof ProjectDraft>(field: K, value: ProjectDraft[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("🔵 Iniciando persistencia do projeto no backend...");
    setLoading(true);
    setSubmitError(null);

    try {
      const isUpdate = !!form.projectId;
      const url = isUpdate 
        ? `http://127.0.0.1:8000/api/v1/projects/${form.projectId}/`
        : "http://127.0.0.1:8000/api/v1/projects/";
      
      const response = await fetch(url, {
        method: isUpdate ? "PATCH" : "POST",
        headers: getBackendJsonHeaders(),
        body: JSON.stringify({
          dashboard: form.dashboard,
          dataDomain: form.dataDomain,
          domainDataOwner: form.domainDataOwner,
          confidentiality: form.confidentiality,
          crawlFrequency: form.crawlFrequency,
          objective: form.objective,
          specialist_prompt_id: form.specialist_prompt_id,
        }),
      });

      const responseBody = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail =
          (typeof responseBody?.detail === "string" && responseBody.detail) ||
          "Falha ao salvar projeto no backend.";
        throw new Error(detail);
      }

      const backendProjectId = (responseBody?.id || form.projectId) as string | undefined;
      if (!backendProjectId) {
        throw new Error("Backend não retornou o UUID do projeto.");
      }

      const draftWithId = { ...form, projectId: backendProjectId };
      persistDraft(draftWithId);
      sessionStorage.setItem("agent_bi_last_project_create_response", JSON.stringify(responseBody, null, 2));
      router.push(`/projects/${backendProjectId}/sources`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Erro inesperado ao salvar projeto.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div initial={false} animate={{ opacity: 1, scale: 1 }} className="max-w-4xl mx-auto pb-20">
      <Link href="/projects" className="inline-flex items-center gap-2 mb-8 text-lux-muted hover:text-lux-text font-medium text-sm transition-colors">
        <ArrowLeft size={16} /> Meus Projetos de Dados
      </Link>

      <WizardStepper currentStep={1} />

      <div className="mb-10">
        <h1 className="text-4xl font-serif font-bold text-lux-text mb-2">Novo Projeto de Dados</h1>
        <p className="text-lux-muted text-lg">
          Os atributos de seguranca desta pagina guiam a rede da Agent-BI e populam de maneira estrita o catalogo de dados da AWS e os pesos dos agentes semanticos.
        </p>
      </div>

      <form onSubmit={handleSave} className="glass-panel p-8 bg-lux-bg/60 border-lux-border/50 shadow-2xl relative overflow-hidden transition-all hover:border-lux-border/80">
        <div className="space-y-6 relative z-10 flex flex-col">
          {submitError ? (
            <div className="rounded-xl border border-red-400/40 bg-red-100/70 px-4 py-3 text-sm font-semibold text-red-900">
              {submitError}
            </div>
          ) : null}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="md:col-span-1">
              <label className="text-xs font-bold text-lux-text mb-2 flex items-center gap-2">
                <FileText size={14} className="text-lux-muted" /> Dashboard
              </label>
              <input
                required
                type="text"
                value={form.dashboard}
                onChange={(e) => updateField("dashboard", e.target.value)}
                placeholder="Nome do dashboard..."
                className="glass-input w-full p-3 text-sm border border-lux-border/60 bg-lux-card/50 hover:bg-lux-bg transition-colors shadow-inner"
              />
            </div>

            <div className="md:col-span-1">
              <label className="text-xs font-bold text-lux-text mb-2 flex items-center gap-2">
                <Briefcase size={14} className="text-lux-muted" /> Dominio de Dados
              </label>
              <select
                required
                value={form.dataDomain}
                onChange={(e) => updateField("dataDomain", e.target.value)}
                className="glass-input w-full p-3 text-sm border border-lux-border/60 bg-lux-card/50 text-lux-text hover:bg-lux-bg transition-colors shadow-inner cursor-pointer appearance-none"
              >
                <option value="">{fetchingDomains ? "Buscando domínios..." : "Selecione o dominio..."}</option>
                {domains.length > 0 ? domains.map(d => (
                   <option key={d.id} value={d.name}>{d.name}</option>
                )) : (
                  <>
                    <option>Mesa de Operacoes</option>
                    <option>Tesouraria Global</option>
                    <option>Asset Management</option>
                    <option>Controladoria e Risco</option>
                    <option>Varejo e Comercial</option>
                  </>
                )}
              </select>
            </div>

            <div className="md:col-span-1">
              <label className="text-xs font-bold text-lux-text mb-2 flex items-center gap-2">
                <Building2 size={14} className="text-lux-muted" /> Domain Data Owner
              </label>
              <input
                required
                type="text"
                value={form.domainDataOwner}
                onChange={(e) => updateField("domainDataOwner", e.target.value)}
                placeholder="Ex: Gestor do dominio financeiro"
                className="glass-input w-full p-3 text-sm border border-lux-border/60 bg-lux-card/50 hover:bg-lux-bg transition-colors shadow-inner"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 p-5 bg-lux-card/40 border border-lux-border/40 rounded-2xl relative shadow-sm">
            <div className="absolute top-0 left-0 w-1 h-full bg-lux-accent/40 rounded-l-2xl" />

            <div className="md:col-span-2">
              <label className="text-[10px] uppercase tracking-wider font-extrabold text-lux-muted mb-2 flex items-center gap-2">
                Confidencialidade Corporativa
              </label>
              <select
                required
                value={form.confidentiality}
                onChange={(e) => updateField("confidentiality", e.target.value)}
                className="glass-input w-full p-2.5 font-bold text-xs border border-lux-border/60 bg-lux-bg text-lux-text hover:bg-lux-card transition-colors cursor-pointer appearance-none"
              >
                <option value="">Selecione...</option>
                <option>Uso Interno Geral</option>
                <option>Restrito Depto</option>
                <option>Confidencial</option>
              </select>
            </div>

            <div className="md:col-span-2 space-y-3">
              <label className="text-[10px] uppercase tracking-wider font-extrabold text-lux-muted flex items-center gap-2">
                Persona Cognitiva / Especialista de Dominio
              </label>
              <select
                required
                value={form.specialist_prompt_id || ""}
                onChange={(e) => updateField("specialist_prompt_id", e.target.value || null)}
                className="glass-input w-full p-2.5 font-bold text-xs border border-lux-border/60 bg-lux-bg text-lux-text hover:bg-lux-card transition-colors cursor-pointer appearance-none"
              >
                <option value="">Selecione o Especialista (Persona)...</option>
                {specialists.map(spec => (
                  <option key={spec.id} value={spec.id}>{spec.name}</option>
                ))}
              </select>
              
              {form.specialist_prompt_id && (
                <motion.div 
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-5 bg-white border border-lux-border/30 rounded-2xl shadow-sm"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 rounded-full bg-[#D4AF37]/10 flex items-center justify-center">
                      <ShieldCheck size={16} className="text-[#D4AF37]" />
                    </div>
                    <div>
                      <p className="text-[10px] text-[#D4AF37] font-black uppercase tracking-widest leading-none">Persona Corporativa</p>
                      <p className="text-xs text-lux-text font-bold">Capacidades do Especialista</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <p className="text-xs text-lux-text/80 leading-relaxed font-medium italic">
                      {(() => {
                          const desc = specialists.find(s => s.id === form.specialist_prompt_id)?.description || "";
                          return (desc.toLowerCase() === "nan" || !desc) ? "Especialista analítico de domínio com foco em governança de dados e insights executivos." : desc;
                      })()}
                    </p>
                    
                    <div className="pt-4 border-t border-lux-border/20">
                      <p className="text-[9px] text-lux-muted font-bold uppercase tracking-widest mb-2 flex items-center gap-1.5">
                        <Zap size={10} /> Base de Conhecimento do Agente
                      </p>
                      <div className="relative group/preview overflow-hidden bg-slate-50/50 rounded-xl border border-lux-border/10">
                          <div className="max-h-40 overflow-y-auto p-3 text-[11px] text-lux-text/70 font-mono leading-relaxed scrollbar-thin scrollbar-thumb-lux-border/20 scrollbar-track-transparent">
                              {(() => {
                                  const content = specialists.find(s => s.id === form.specialist_prompt_id)?.content || "";
                                  if (content.toLowerCase() === "nan" || !content) return "Carregando instruções nativas...";
                                  return content;
                              })()}
                          </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-[9px] text-lux-muted/60 uppercase font-bold tracking-tighter">
                    <span>Verified Agent Identity</span>
                    <span>Auto-Generated Prompt Sync</span>
                  </div>
                </motion.div>
              )}
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-lux-text mb-2 flex items-center gap-2">
              <Target size={14} className="text-lux-muted" /> Objetivo (Prompt Mestre da IA)
            </label>
            <textarea
              required
              value={form.objective}
              onChange={(e) => updateField("objective", e.target.value)}
              placeholder="Descreva o resultado analitico esperado para orquestracao das views SQL..."
              className="glass-input w-full p-4 text-sm border border-lux-border/60 bg-lux-card/50 h-24 resize-none hover:bg-lux-bg transition-colors shadow-inner leading-relaxed"
            />
          </div>
        </div>

        <div className="mt-12 pt-6 border-t border-lux-border/30 flex justify-end gap-5 relative z-10 items-center">
          <button type="button" onClick={() => router.push("/projects")} className="px-6 py-3 rounded-xl font-bold text-lux-muted hover:bg-lux-border/20 transition-colors">
            Cancelar Rascunho
          </button>
          <button type="submit" disabled={loading} className="flex items-center gap-3 bg-lux-text text-lux-bg px-10 py-5 rounded-2xl font-bold font-serif shadow-xl hover:scale-105 transition-transform disabled:opacity-50 disabled:cursor-wait tracking-wide text-lg">
            {loading ? "Criando Projeto no Backend..." : <>Gravar Metadados Corporativos e Iniciar Ingestao &gt;</>}
          </button>
        </div>
      </form>
    </motion.div>
  );
}
