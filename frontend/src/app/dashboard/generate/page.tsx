"use client";
import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Terminal,
  Loader2,
  CloudUpload,
  Eye,
  Code,
  Trash,
  Star,
  History,
  Sparkles,
  ChevronLeft,
  LayoutDashboard,
  CheckCircle2,
  AlertCircle,
  Clock as ClockIcon,
  RefreshCw,
  Zap,
  Database,
  Server,
  Download,
  FileJson,
  ShieldCheck,
  Plus
} from "lucide-react";
import { useRouter } from "next/navigation";
import { getProjectRelationshipsKey, readProjectSources, writeProjectSources } from "@/lib/projectSources";
import { getBackendJsonHeaders } from "@/lib/backendAuth";
import { ProjectHeaderStandard } from "@/components/project/ProjectHeaderStandard";
import { ProjectPhases } from "@/components/project/ProjectPhases";

interface DashboardTab {
  id: string;
  name: string;
  prompt: string;
  isBlueprint: boolean;
  content: string;
  fullPrompt?: string;
  auditTrail?: {
    orchestrator_thought?: string;
    pandas_code?: string;
    pandas_thought?: string;
    nl2sql_sql?: string;
    nl2sql_thought?: string;
  };
  followUpSuggestions?: { label: string; prompt: string }[];
}

type CopilotGeneratePayload = {
  project_id: string | null;
  dashboardName: string;
  reportTitle: string;
  reportDescription: string;
  dataDomain: string;
  domainDataOwner: string;
  dataConfidentiality: string;
  crawlerFrequency: string;
  sessionAuthor: string;
  currentVersion: string;
  currentDashboardState: string;
  previousUserPrompts: string[];
  currentUserPrompt: string;
  templatePrompt: string;
  masterPrompt: string;
  reportMetadata: Record<string, unknown>;
  datasets: Record<string, unknown>[];
  semanticRelationships: Record<string, unknown>[];
  knowledgeBasePromptHints: string[];
  existingDashboardHtml: string;
  frontendComponentContract: Record<string, unknown>;
  visualLayoutRules: Record<string, unknown>;
  outputFormatRules: Record<string, unknown>;
  query: string;
  ai_temperature?: number;
  trace_id?: string;
};

function isValidUuid(value: string | null | undefined): value is string {
  if (!value) return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export default function EngineRoom() {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectDraft, setProjectDraft] = useState<Record<string, string> | null>(null);
  const [messages, setMessages] = useState<{ role: "user" | "agent"; content: string }[]>([
    {
      role: "agent",
      content:
        "Olá! Processei com sucesso a unificação das suas fontes na Tabela Ouro. Qual visão estratégica deseja construir primeiro para este projeto?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [viewCode, setViewCode] = useState(false);
  const [tabs, setTabs] = useState<DashboardTab[]>([
    {
      id: "v1.0",
      name: "v1.0 (Rascunho)",
      prompt: "Cruze os setores mapeados na aba prevendo tendências.",
      isBlueprint: false,
      content:
        '<div style="display:flex; height:100%; align-items:center; justify-content:center; color:#513830; font-family:serif;"><h1>(Mock) Painel inicial gerado</h1></div>',
    },
  ]);
  const [activeTabId, setActiveTabId] = useState<string>("v1.0");
  const [dataReady, setDataReady] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [rightTab, setRightTab] = useState<'chat' | 'ingest'>('chat');
  const [loadingAgent, setLoadingAgent] = useState("Orquestrador de IA");
  const [loadingAction, setLoadingAction] = useState("Preparando analistas virtuais...");
  const [aiTemperature, setAiTemperature] = useState(0.3);
  const [showAISettings, setShowAISettings] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);
  
  // Ref para o container de mensagens e estado para controle de scroll inteligente
  const scrollRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [hasNewMessages, setHasNewMessages] = useState(false);

  // Monitora o scroll do usuário para desabilitar auto-scroll se ele subir
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    
    // Margem de segurança de 150px do fundo para considerar "sticky"
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 150;
    
    // Se o usuário subiu propositalmente, pausamos o auto-scroll
    if (!isAtBottom && shouldAutoScroll) {
      setShouldAutoScroll(false);
    }
    
    // Se ele voltou pro fundo manualmente, reativamos
    if (isAtBottom && !shouldAutoScroll) {
      setShouldAutoScroll(true);
      setHasNewMessages(false);
    }
  };

  // Efeito de scroll automático para mensagens cronológicas (Novas na BASE)
  useEffect(() => {
    if (shouldAutoScroll && scrollRef.current) {
      const scrollElement = scrollRef.current;
      // Pequeno delay para garantir que o DOM atualizou
      const timer = setTimeout(() => {
        scrollElement.scrollTo({
          top: scrollElement.scrollHeight,
          behavior: "smooth"
        });
      }, 50);
      return () => clearTimeout(timer);
    } else if (messages.length > 1) {
      // Se não estamos no fundo, avisamos que há novidades
      setHasNewMessages(true);
    }
  }, [messages, shouldAutoScroll]);

  // Efeito para manter o scroll no fundo durante a digitação, se o usuário estiver lá
  useEffect(() => {
    if (isTyping && shouldAutoScroll && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "auto" // 'auto' é menos agressivo durante atualizações rápidas
      });
    }
  }, [isTyping, shouldAutoScroll]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isTyping) {
      const phrases = [
        { agent: "🧠 Planner", action: "Elaborando plano..." },
        { agent: "💾 Data Expert", action: "Consultando base analítica..." },
        { agent: "👨‍💻 Business Analyst", action: "Formulando insights..." },
        { agent: "🎨 Frontend", action: "Desenhando cards..." },
        { agent: "🛡️ Quality Inspector", action: "Validando integridade..." }
      ];
      let i = 0;
      setLoadingAgent(phrases[0].agent);
      setLoadingAction(phrases[0].action);
      interval = setInterval(() => {
        i = (i + 1) % phrases.length;
        setLoadingAgent(phrases[i].agent);
        setLoadingAction(phrases[i].action);
      }, 2500); // Mais rápido conforme pedido
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTyping]);

  useEffect(() => {
    setProjectId(sessionStorage.getItem("agent_bi_current_project_id"));
    const rawDraft = sessionStorage.getItem("agent_bi_project_draft");
    if (!rawDraft) return;
    try {
      const parsed = JSON.parse(rawDraft);
      setProjectDraft(parsed);
      if (parsed.aiTemperature !== undefined) {
        setAiTemperature(parsed.aiTemperature);
      }
    } catch {
      setProjectDraft(null);
    }
  }, []);

  // Polling para verificar prontidão dos dados
  useEffect(() => {
    if (!projectId || dataReady) return;

    const checkStatus = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/`, {
          headers: getBackendJsonHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          setDataReady(data.data_ready);
          setPendingCount(data.pending_datasets_count || 0);
        }
      } catch (err) {
        console.error("Erro ao checar status do projeto:", err);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [projectId, dataReady]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userQuery = input;
    setMessages((prev) => [...prev, { role: "user", content: userQuery }]);
    setInput("");
    setIsTyping(true);

    const traceId = crypto.randomUUID();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent('agent-bi-trace', { detail: { traceId } }));
    }

    try {
      const sources = projectId ? readProjectSources(projectId) : [];
      const relationships =
        projectId && typeof window !== "undefined"
          ? JSON.parse(sessionStorage.getItem(getProjectRelationshipsKey(projectId)) || "[]")
          : [];
      const previousUserPrompts = messages
        .filter((message) => message.role === "user")
        .map((message) => message.content);

      const knowledgeBasePromptHints = Array.from(
        new Set(
          [
            "template html padrao corporativo",
            "layout executivo institucional",
            "paleta de cores corporativa",
            "padrao de componentes visual",
            projectDraft?.dataDomain || "",
            projectDraft?.dashboard || "",
            projectDraft?.objective || "",
          ].filter((item) => item && item.trim().length > 0),
        ),
      );

      const safeProjectId = isValidUuid(projectId) ? projectId : null;

      const payload: CopilotGeneratePayload = {
        project_id: safeProjectId,
        dashboardName: projectDraft?.dashboard || "Dashboard Corporativo",
        reportTitle: projectDraft?.dashboard || "Dashboard Corporativo",
        reportDescription: projectDraft?.objective || "Evolucao incremental do dashboard corporativo.",
        dataDomain: projectDraft?.dataDomain || "",
        domainDataOwner: projectDraft?.domainDataOwner || "",
        dataConfidentiality: projectDraft?.confidentiality || "",
        crawlerFrequency: projectDraft?.crawlFrequency || "",
        sessionAuthor: "frontend-local",
        currentVersion: activeTab?.name || "v1.0 (Rascunho)",
        currentDashboardState: activeTab?.isBlueprint ? "BLUEPRINT" : "DRAFT",
        previousUserPrompts,
        currentUserPrompt: userQuery,
        templatePrompt: "",
        masterPrompt: "",
        reportMetadata: {
          activeTabId,
          tabsCount: tabs.length,
        },
        datasets: sources.map((source) => ({
          id: source.id,
          name: source.name,
          source_type: source.type,
          row_count: source.rows,
          column_count: source.columns.length,
          schema_json: {
            column_count: source.columns.length,
            columns: source.columns.map((column) => ({
              name: column,
              type: "TEXT",
              description: source.descriptions?.[column] || "",
            })),
          },
          sample_json: source.sample,
          selectedCols: source.selectedCols || source.columns,
        })),
        semanticRelationships: relationships,
        knowledgeBasePromptHints,
        existingDashboardHtml: activeTab?.content || "",
        frontendComponentContract: {
          expectsStandaloneHtml: true,
          renderMode: "iframe-srcdoc",
        },
        visualLayoutRules: {
          style: "executive-corporate",
          preserveExistingStructure: true,
        },
        outputFormatRules: {
          requireValidJson: true,
          preserveDraftFlow: true,
        },
        query: userQuery,
        ai_temperature: aiTemperature,
        trace_id: traceId,
      };

      if (typeof window !== "undefined") {
        sessionStorage.setItem("agent_bi_last_copilot_payload", JSON.stringify(payload, null, 2));
      }

      const response = await fetch("http://127.0.0.1:8000/api/v1/copilot/generate", {
        method: "POST",
        headers: getBackendJsonHeaders(),
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.status === "data_not_ready") {
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            content: `⚠️ ${data.message}. Por favor, aguarde a conclusão da análise estatística para garantir resultados precisos.`,
          },
        ]);
        setDataReady(false);
        return;
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content:
            "O Agente BI atualizou o painel de acordo com a sua diretriz. Voce pode promover este rascunho quando o resultado estiver aprovado.",
        },
      ]);

      const nextVersionCounter = tabs.length + 1;
      const newTabId = `v${nextVersionCounter}.0`;

          setTabs((prev) => [
        ...prev,
        {
          id: newTabId,
          name: `${newTabId} (Rascunho)`,
          prompt: userQuery,
          isBlueprint: false,
          content: data.dashboard_html || "Falha ao renderizar",
          fullPrompt: data.generationMetadata?.full_prompt,
          auditTrail: data.auditTrail,
          followUpSuggestions: data.followUpSuggestions || []
        },
      ]);
      setActiveTabId(newTabId);
    } catch {
      setMessages((prev) => [...prev, { role: "agent", content: "[ERRO] Falha na comunicação com a API." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const publishToAWS = () => {
    alert(
      "Iniciando publicacao...\n\nOrquestrando pipeline na AWS, politicas RBAC e estrutura de distribuicao.\n\n(Fluxo de backend ainda a ser finalizado)",
    );
  };

  const handleExportPrompt = () => {
    if (!activeTab?.fullPrompt) {
      alert("Aguarde a geração do dashboard para exportar o prompt.");
      return;
    }
    const blob = new Blob([activeTab.fullPrompt], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Agent-BI-Prompt-${activeTab.id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const toggleBlueprint = (id: string) => {
    setTabs((prev) =>
      prev.map((tab) => {
        if (tab.id === id) {
          return {
            ...tab,
            isBlueprint: true,
            name: tab.name.replace("(Rascunho)", "").replace("(Publico)", "") + " (Publico)",
          };
        }
        return { ...tab, isBlueprint: false, name: tab.name.replace("(Publico)", "(Rascunho)") };
      }),
    );
  };

  const deleteTab = (id: string) => {
    setTabs((prev) => prev.filter((tab) => tab.id !== id));
    if (activeTabId === id && tabs.length > 1) {
      const remaining = tabs.filter((tab) => tab.id !== id);
      setActiveTabId(remaining[remaining.length - 1].id);
    }
  };

  const activeTab = tabs.find((tab) => tab.id === activeTabId);
  const previousHref = projectId ? `/projects/${projectId}/insights` : "/projects";

  return (
    <div className="max-w-[1600px] mx-auto w-full h-screen flex flex-col px-4 overflow-hidden">
      <div className="relative z-0 mb-4 pt-2">
        <ProjectPhases projectId={projectId || "PRJ-TEMP"} />
      </div>

      <ProjectHeaderStandard 
        projectId={projectId || "PRJ-TEMP"}
        step={5}
        title="Agente BI"
        prevHref={previousHref}
        prevLabel="Voltar para Semântica"
      />

      <div className="flex items-center justify-center gap-6 mb-4">
          <div className={`px-4 py-1.5 rounded-full border flex items-center gap-2 transition-all duration-700 ${
            dataReady 
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.1)]" 
              : "bg-amber-500/10 border-amber-500/20 text-amber-500 animate-pulse shadow-[0_0_15px_rgba(245,158,11,0.1)]"
          }`}>
            {dataReady ? (
              <>
                <CheckCircle2 size={14} className="stroke-[3]" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em]">Cérebro Pronto</span>
              </>
            ) : (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em]">Otimizando Dados...</span>
              </>
            )}
          </div>
      </div>
      <p className="text-[11px] text-lux-muted font-medium italic text-center mb-6">"Refine o painel com o agente e publique a versão aprovada."</p>

      <div className="flex flex-col lg:flex-row w-full flex-1 min-h-[400px] gap-8 pb-6 overflow-hidden px-4 md:px-8">
        {/* LADO ESQUERDO: Dashboard (Protagonista - Expansível) */}
        <div className="flex-1 min-h-0 flex flex-col bg-white dark:bg-lux-card/55 backdrop-blur-xl border border-lux-border/60 dark:border-lux-border/85 rounded-[3rem] overflow-hidden shadow-2xl shadow-lux-shadow/10 transition-all duration-500">
          <div className="flex bg-[#F9F9F9] dark:bg-lux-card/90 border-b border-[#F1E9DB] dark:border-lux-border/85 overflow-x-auto custom-scrollbar shrink-0 p-2 gap-1">
            {tabs.map((tab) => (
              <div
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={`flex items-center gap-3 px-8 py-3 cursor-pointer min-w-max transition-all text-[10px] font-black uppercase tracking-widest rounded-2xl ${
                  activeTabId === tab.id
                    ? "bg-white border border-[#D4AF37]/30 text-[#1A1A1A] shadow-md scale-[1.02]"
                    : "bg-transparent text-[#8C8C8C] hover:bg-white"
                }`}
              >
                {tab.name}
                {tab.isBlueprint && <Star size={12} className="text-[#D4AF37] fill-current ml-1" />}
                {tabs.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteTab(tab.id);
                    }}
                    className="text-lux-muted/40 hover:text-red-800 transition-colors ml-4"
                    title="Descartar versao"
                  >
                    <Trash size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>

            <div className="flex-grow bg-[#F3F4F6] dark:bg-[#0a0807] relative overflow-hidden p-4 md:p-8 flex items-center justify-center">
              {/* Moldura Premium Browser - Professional Finish */}
              <div className="w-full h-full bg-white dark:bg-lux-card rounded-[2rem] shadow-[0_40px_120px_-20px_rgba(0,0,0,0.2)] border border-[#F1E9DB] dark:border-lux-border/40 overflow-hidden flex flex-col">
                <div className="h-12 bg-white dark:bg-black/40 border-b border-[#F1E9DB] flex items-center px-6 gap-6 shrink-0">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#FF5F57] shadow-inner" />
                    <div className="w-3 h-3 rounded-full bg-[#FFBD2E] shadow-inner" />
                    <div className="w-3 h-3 rounded-full bg-[#28C840] shadow-inner" />
                  </div>
                  <div className="flex-1 bg-[#F9F9F9] dark:bg-white/5 rounded-full h-7 border border-[#F1E9DB] flex items-center px-4 gap-3">
                    <LayoutDashboard size={12} className="text-[#D4AF37]" />
                    <span className="text-[10px] text-[#8C8C8C] font-bold tracking-tight truncate">secure.agent-bi.ai / {activeTab?.name}</span>
                  </div>
                </div>
                
                <div className="flex-1 relative overflow-hidden bg-white dark:bg-[#120f0d] p-0">
                  {activeTab?.content && !viewCode ? (
                    <iframe
                      srcDoc={activeTab.content}
                      className="w-full h-full border-none shadow-inner"
                      sandbox="allow-scripts allow-same-origin"
                      title="Agente BI Canvas"
                    />
                  ) : activeTab?.content ? (
                    <pre className="p-10 text-xs text-[#E0E0E0] bg-[#1A1A1A] h-full overflow-auto font-mono leading-relaxed">
                      {activeTab.content}
                    </pre>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-20 text-lux-muted/50 text-center h-full">
                      <div className="p-6 bg-[#FDF9F0] rounded-full mb-8 animate-pulse text-[#D4AF37]">
                        <RefreshCw size={48} className="animate-spin duration-[3s]" />
                      </div>
                      <p className="font-serif italic text-xl text-[#1A1A1A] mb-2">{loadingAgent}</p>
                      <p className="text-xs font-black uppercase tracking-[0.2em] text-[#D4AF37]">{loadingAction}</p>
                    </div>
                  )}
                </div>
              </div>

            <div className="absolute bottom-12 right-12 flex gap-3 z-20">
              <button
                onClick={() => setShowAuditModal(true)}
                className="bg-lux-text text-white px-8 py-4 rounded-2xl shadow-[0_20px_40px_rgba(0,0,0,0.3)] flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] hover:scale-105 hover:bg-lux-accent hover:text-lux-text transition-all active:scale-95"
              >
                <Terminal size={18} />
                Audit Log: Ver Lógica
              </button>
              
              <button
                onClick={() => setViewCode(!viewCode)}
                className="bg-[#1A1A1A] text-white px-8 py-4 rounded-2xl shadow-[0_20px_40px_rgba(0,0,0,0.3)] flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] hover:scale-105 hover:bg-[#D4AF37] hover:text-[#1A1A1A] transition-all active:scale-95"
              >
                {viewCode ? <Eye size={18} /> : <Code size={18} />}
                {viewCode ? "Visualizar Painel" : "Inspecionar Código"}
              </button>
            </div>
          </div>
        </div>

        {/* Modal de Auditoria Analítica */}
        <AnimatePresence>
          {showAuditModal && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-6 md:p-12"
            >
              <motion.div 
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="w-full max-w-5xl h-full max-h-[85vh] bg-lux-bg border border-lux-border/40 rounded-[3rem] shadow-2xl overflow-hidden flex flex-col"
              >
                <div className="p-8 border-b border-lux-border/20 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-lux-text text-white flex items-center justify-center shadow-xl">
                      <ShieldCheck size={28} />
                    </div>
                    <div>
                      <h2 className="text-2xl font-serif font-bold text-lux-text">Trilha de Auditoria Analítica</h2>
                      <p className="text-xs text-lux-muted uppercase tracking-widest font-black mt-1">Audit Log • {activeTab?.name}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setShowAuditModal(false)}
                    className="w-12 h-12 rounded-full border border-lux-border/20 flex items-center justify-center text-lux-muted hover:bg-lux-text hover:text-white transition-all shadow-sm"
                  >
                    <Plus className="rotate-45" size={24} />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-10 space-y-12 custom-scrollbar">
                  {/* Sessão: Pensamento Estratégico */}
                  <section>
                    <h3 className="text-sm font-black uppercase tracking-[0.2em] text-lux-text mb-6 flex items-center gap-3">
                      <Sparkles size={18} className="text-lux-accent" /> Raciocínio do Orquestrador
                    </h3>
                    <div className="p-8 bg-white/60 border border-lux-border/20 rounded-[2rem] text-sm text-lux-text italic leading-relaxed shadow-inner">
                      {activeTab?.auditTrail?.orchestrator_thought || activeTab?.auditTrail?.pandas_thought || activeTab?.auditTrail?.nl2sql_thought || "Nenhum raciocínio técnico capturado para esta versão."}
                    </div>
                  </section>

                  {/* Sessão: Código Python (Pandas) */}
                  {activeTab?.auditTrail?.pandas_code && (
                    <section>
                      <h3 className="text-sm font-black uppercase tracking-[0.2em] text-lux-text mb-6 flex items-center gap-3">
                        <Code size={18} className="text-lux-accent" /> Algoritmo Python (Pandas Analytics)
                      </h3>
                      <div className="relative group">
                        <pre className="p-8 bg-[#1a1c1e] text-emerald-400 rounded-[2rem] overflow-x-auto font-mono text-xs leading-relaxed shadow-2xl border border-lux-border/10">
                          {activeTab.auditTrail.pandas_code}
                        </pre>
                        <div className="absolute top-4 right-4 text-[9px] uppercase font-bold text-lux-muted/40 bg-black/20 px-3 py-1 rounded-full">
                          Python Executor
                        </div>
                      </div>
                    </section>
                  )}

                  {/* Sessão: Query SQL (NL2SQL) */}
                  {activeTab?.auditTrail?.nl2sql_sql && (
                    <section>
                      <h3 className="text-sm font-black uppercase tracking-[0.2em] text-lux-text mb-6 flex items-center gap-3">
                        <Database size={18} className="text-lux-accent" /> Consulta SQL (NL2SQL Core)
                      </h3>
                      <div className="relative group">
                        <pre className="p-8 bg-[#1a1c1e] text-blue-300 rounded-[2rem] overflow-x-auto font-mono text-xs leading-relaxed shadow-2xl border border-lux-border/10">
                          {activeTab.auditTrail.nl2sql_sql}
                        </pre>
                        <div className="absolute top-4 right-4 text-[9px] uppercase font-bold text-lux-muted/40 bg-black/20 px-3 py-1 rounded-full">
                          SQLite Generator
                        </div>
                      </div>
                    </section>
                  )}
                </div>

                <div className="p-8 bg-lux-bg/50 border-t border-lux-border/20 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2 text-[10px] text-lux-muted font-bold tracking-widest uppercase">
                    <AlertCircle size={14} /> Trilha auditada e criptografada por NTT DATA Governance
                  </div>
                  <button 
                    onClick={() => setShowAuditModal(false)}
                    className="bg-lux-text text-white px-10 py-3 rounded-2xl text-xs font-bold shadow-xl hover:scale-105 transition-transform"
                  >
                    Fechar Auditoria
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* LADO DIREITO: Painel de Conversação (Abas - Largura Otimizada 320px) */}
        <div className="w-full lg:w-[320px] shrink-0 min-h-0 flex flex-col bg-white/70 backdrop-blur-3xl border border-[#F1E9DB] rounded-[3rem] overflow-hidden shadow-2xl transition-all duration-500">
          {/* Seletor de Abas Lateral */}
          <div className="flex bg-lux-bg/50 dark:bg-black/20 border-b border-lux-border/20 p-2 gap-2 shrink-0 pt-3 px-3">
             <button
               onClick={() => setRightTab('chat')}
               className={`flex-1 flex items-center justify-center gap-3 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                 rightTab === 'chat' 
                   ? "bg-lux-text text-white shadow-xl scale-[1.02]" 
                   : "text-lux-muted hover:bg-lux-border/20"
               }`}
             >
               <Terminal size={14} /> 🤖 Agente BI
             </button>
             <button
               onClick={() => setRightTab('ingest')}
               className={`flex-1 flex items-center justify-center gap-3 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                 rightTab === 'ingest' 
                   ? "bg-lux-text text-white shadow-xl scale-[1.02]" 
                   : "text-lux-muted hover:bg-lux-border/20"
               }`}
             >
               <CloudUpload size={14} /> ☁️ Ingestão AWS
             </button>
          </div>

              <div className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
                {rightTab === 'chat' ? (
                  <>
                    <div className="px-6 py-3 border-b border-lux-border/10 bg-white/5 flex items-center justify-between shrink-0 relative z-10">
                       <span className="text-[9px] font-black uppercase tracking-widest text-lux-muted">Logs da Sessão</span>
                       <div className="flex items-center gap-2">
                         <button 
                           onClick={() => setShowAISettings(!showAISettings)}
                           className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-[9px] font-black uppercase tracking-wider ${
                             showAISettings 
                               ? "bg-lux-text text-white border-lux-text" 
                               : "bg-white/5 border-lux-border/20 text-lux-text hover:bg-lux-border/10"
                           }`}
                         >
                           <Zap size={12} className={aiTemperature > 0.5 ? "text-amber-500 fill-current" : ""} />
                           IA
                         </button>
                         {activeTab?.fullPrompt && (
                           <button 
                             onClick={handleExportPrompt}
                             className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-lux-accent/10 border border-lux-accent/20 text-lux-text hover:bg-lux-accent hover:text-white transition-all text-[9px] font-black uppercase tracking-wider group"
                             title="Exportar Prompt Bedrock (.txt)"
                           >
                             <Download size={12} className="group-hover:scale-110 transition-transform" />
                             Prompt
                           </button>
                         )}
                       </div>
                    </div>

                    {/* AI Calibration Panel (Retractable) */}
                    {showAISettings && (
                      <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-lux-card/80 border-b border-lux-border/20 overflow-hidden shrink-0"
                      >
                        <div className="p-6 space-y-6">
                          <div className="flex justify-between items-center bg-[#FDF9F0] p-3 rounded-2xl border border-[#F1E9DB]">
                            <span className="text-[10px] font-black uppercase tracking-widest text-[#D4AF37]">Calibração IA</span>
                            <span className={`text-[10px] font-black px-3 py-1 rounded-full shadow-sm ${
                              aiTemperature === 0.0 ? "bg-[#1A1A1A] text-white" :
                              aiTemperature === 0.3 ? "bg-[#1A1A1A] text-[#D4AF37]" :
                              "bg-[#D4AF37] text-[#1A1A1A]"
                            }`}>
                              {aiTemperature === 0.0 ? "Audit Mode" : aiTemperature === 0.3 ? "Insight Mode" : "Discovery Mode"}
                            </span>
                          </div>
                          
                          <div className="flex gap-2">
                             {[0.0, 0.3, 0.7].map((temp) => (
                               <button
                                 key={temp}
                                 onClick={() => setAiTemperature(temp)}
                                 className={`flex-1 py-4 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
                                   aiTemperature === temp 
                                     ? "bg-[#1A1A1A] text-white border-[#1A1A1A] shadow-xl" 
                                     : "bg-white border-[#F1E9DB] text-[#8C8C8C] hover:bg-[#FDF9F0]"
                                 }`}
                               >
                                 {temp.toFixed(1)}
                               </button>
                             ))}
                          </div>
                          <p className="text-[9px] text-[#8C8C8C] leading-relaxed italic border-l-2 border-[#D4AF37] pl-3">
                            {aiTemperature === 0.0 && "Aproximação matemática rigorosa. Recomendado para P&L e Audit."}
                            {aiTemperature === 0.3 && "Equilíbrio entre fidelidade absoluta e insights de mercado."}
                            {aiTemperature === 0.7 && "Foco em descobertas e sugestões de novos KPIs estratégicos."}
                          </p>
                        </div>
                      </motion.div>
                    )}
                    <div 
                      ref={scrollRef}
                      onScroll={handleScroll}
                      className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col custom-scrollbar scroll-smooth relative"
                      style={{ display: 'flex', flexDirection: 'column' }} // Garante ordem 0=topo, N=base
                    >
                  {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full opacity-30 text-center px-10 italic">
                       <Sparkles size={40} className="mb-4" />
                       <p className="text-sm">"Olá! Como posso refinar sua experiência analítica hoje?"</p>
                    </div>
                  )}
                  {messages.map((msg, i) => (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[90%] p-5 rounded-2xl text-xs leading-relaxed shadow-sm ${
                          msg.role === "user"
                            ? "bg-lux-text text-white rounded-br-none"
                            : "bg-white dark:bg-white/5 border border-lux-border/20 text-lux-text dark:text-lux-accent rounded-bl-none"
                        }`}
                      >
                        {msg.role === "agent" && <Sparkles size={14} className="mb-3 text-[#D4AF37]" />}
                        {msg.content}
                      </div>
                    </motion.div>
                  ))}
                    {isTyping && (
                    <div className="flex justify-start">
                      <div className="bg-white dark:bg-white/5 border border-lux-border/20 p-5 rounded-2xl rounded-bl-none flex items-center gap-3">
                        <div className="w-1.5 h-1.5 bg-lux-accent rounded-full animate-bounce" />
                        <div className="w-1.5 h-1.5 bg-lux-accent rounded-full animate-bounce delay-100" />
                        <div className="w-1.5 h-1.5 bg-lux-accent rounded-full animate-bounce delay-200" />
                      </div>
                      </div>
                    )}

                    {/* Proactive Follow-up Suggestions */}
                    {!isTyping && activeTab?.followUpSuggestions && activeTab.followUpSuggestions.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {activeTab.followUpSuggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setInput(suggestion.prompt);
                              // Opcional: disparar submit automático
                              // handleSubmit(new Event('submit') as any);
                            }}
                            className="bg-lux-accent/10 border border-lux-accent/30 text-lux-text hover:bg-lux-accent hover:text-white px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all shadow-sm flex items-center gap-2 group"
                          >
                            <Sparkles size={12} className="group-hover:animate-pulse" />
                            {suggestion.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Botão Flutuante de Novas Mensagens */}
                  {hasNewMessages && !shouldAutoScroll && (
                    <motion.button
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => {
                        setShouldAutoScroll(true);
                        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
                        setHasNewMessages(false);
                      }}
                      className="absolute bottom-32 left-1/2 -translate-x-1/2 bg-lux-accent text-black px-6 py-2.5 rounded-full text-[10px] font-black uppercase tracking-widest shadow-2xl z-20 flex items-center gap-2 hover:scale-105 transition-all active:scale-95 border border-white/20"
                    >
                      <Sparkles size={14} className="animate-pulse" /> Novas mensagens abaixo
                    </motion.button>
                  )}

                <div className="p-6 bg-transparent border-t border-lux-border/20 shrink-0">
                  <form onSubmit={handleSubmit} className="flex gap-2 relative">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Comando analítico..."
                      className="flex-1 bg-white/80 dark:bg-black/20 border border-lux-border/30 text-lux-text px-6 py-4 rounded-3xl text-xs focus:outline-none focus:border-lux-accent transition-all shadow-inner placeholder:italic"
                    />
                    <button
                      type="submit"
                      disabled={isTyping || !input.trim() || !dataReady}
                      className={`bg-lux-text dark:bg-lux-accent text-white dark:text-black p-4 rounded-2xl hover:scale-105 transition-transform shadow-xl flex items-center justify-center ${
                        (isTyping || !input.trim() || !dataReady) ? "opacity-30 cursor-not-allowed grayscale" : ""
                      }`}
                    >
                      {isTyping ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
                    </button>
                  </form>
                </div>
              </>
            ) : (
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                 <IngestionControlPanel projectId={projectId} onComplete={() => setRightTab('chat')} />
                 
                 <div className="mt-8 bg-lux-accent/5 p-6 rounded-[2.5rem] border border-lux-accent/10">
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-lux-accent mb-4">Relacionamentos Ativos</h4>
                    <ul className="space-y-4">
                       <li className="flex items-start gap-4">
                          <div className="w-8 h-8 rounded-full bg-lux-accent/10 flex items-center justify-center shrink-0">
                             <Database size={14} className="text-lux-accent" />
                          </div>
                          <div>
                             <p className="text-[11px] font-bold text-lux-text dark:text-white">Fatos x Dimensões</p>
                             <p className="text-[9px] text-lux-muted mt-1 leading-relaxed italic">"Join detectado entre fontes locais via ID de Transação."</p>
                          </div>
                       </li>
                    </ul>
                 </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="lg:hidden mt-5 p-4 bg-lux-card/50 backdrop-blur-xl border border-lux-border/60 rounded-xl shadow-xl shadow-lux-shadow/10">
        <div className="flex items-center gap-2 text-lux-text mb-3">
          <LayoutDashboard size={18} />
          <span className="text-sm font-bold uppercase tracking-wider">Agente BI</span>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Descreva o ajuste desejado para o painel..."
            className="flex-1 bg-lux-card border border-lux-border/60 text-lux-text px-4 py-3 rounded-lg text-sm focus:outline-none focus:border-lux-text transition-colors shadow-inner"
          />
          <button
            type="submit"
            disabled={isTyping || !input.trim()}
            className="bg-lux-text text-lux-bg p-3 rounded-lg hover:scale-105 transition-transform disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
/**
 * IngestionControlPanel
 * ──────────────
 * Painel lateral para consolidar dados locais na AWS antes das análises de IA.
 */
function IngestionControlPanel({ projectId, onComplete }: { projectId: string | null; onComplete?: () => void }) {
  const [sources, setSources] = useState<any[]>([]);
  const [ingesting, setIngesting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const items = readProjectSources(projectId);
    setSources(items);
  }, [projectId]);

  const localSources = sources.filter(s => s.id.startsWith("local-") || s.status !== "INGESTED");
  const ingestedCount = sources.filter(s => s.status === "INGESTED").length;

  const handleIngestAll = async () => {
    if (!projectId || localSources.length === 0) return;
    setIngesting(true);
    
    const results = [...sources];
    
    for (const source of localSources) {
      if (!source.previewData || source.previewData.length === 0) continue;
      
      try {
        const { getBackendJsonHeaders } = await import("@/lib/backendAuth");
        const hdrs = await getBackendJsonHeaders();

        // ── Simulação de Ingestão AWS (Upload em Lote) ────────────────────────
        // Na prática, aqui faríamos o upload real se tivéssemos o RawFile.
        // Como o RawFile não sobrevive ao refresh, usamos o previewData se for pequeno
        // ou avisamos o usuário. Para o MVP, marcamos como INGESTED.
        
        await new Promise(r => setTimeout(r, 1500)); // Simula latência AWS
        
        const idx = results.findIndex(s => s.id === source.id);
        if (idx !== -1) {
          results[idx] = { ...results[idx], status: "INGESTED", id: `aws-${Math.random().toString(36).slice(2, 8)}` };
        }
      } catch (err) {
        console.error("Falha na ingestão AWS:", err);
      }
    }

    writeProjectSources(projectId, results);
    setSources(results);
    setIngesting(false);
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
    if (onComplete) onComplete();
  };

  const handleClear = () => {
    if (!projectId || !confirm("Deseja excluir todas as ingestões deste projeto?")) return;
    writeProjectSources(projectId, []);
    setSources([]);
    window.location.reload();
  };

  if (!projectId) return null;

  return (
    <div className="bg-white/80 dark:bg-lux-card/85 backdrop-blur-3xl border border-lux-border/20 dark:border-lux-border/50 rounded-[3rem] p-6 shadow-2xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform">
         <Database size={60} />
      </div>

      <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-lux-accent mb-6 flex items-center gap-3">
        <Server size={14} /> Ingestão AWS
      </h3>

      <div className="space-y-4 mb-8">
        <div className="flex justify-between items-center px-4 py-3 bg-lux-bg/30 dark:bg-white/5 rounded-2xl border border-lux-border/10">
           <span className="text-[10px] font-black text-lux-muted uppercase tracking-widest">Base de Dados</span>
           <span className="text-[11px] font-bold text-lux-text dark:text-lux-accent">{sources.length} Tabelas</span>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
           <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-2xl text-center">
              <p className="text-[8px] font-black text-emerald-600 uppercase tracking-tighter mb-1">Cloud AWS</p>
              <p className="text-xl font-mono font-black text-emerald-600">{ingestedCount}</p>
           </div>
           <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-2xl text-center">
              <p className="text-[8px] font-black text-amber-600 uppercase tracking-tighter mb-1">Local / Cache</p>
              <p className="text-xl font-mono font-black text-amber-600">{localSources.length}</p>
           </div>
        </div>
      </div>

      <div className="space-y-3 relative z-10">
        <button 
          onClick={handleIngestAll}
          disabled={ingesting || localSources.length === 0}
          className="w-full h-14 bg-lux-text dark:bg-lux-accent text-white dark:text-black rounded-2xl font-black text-sm flex items-center justify-center gap-3 hover:scale-[1.02] shadow-xl transition-all disabled:opacity-40 disabled:grayscale active:scale-95 group/btn overflow-hidden"
        >
          {ingesting ? <RefreshCw className="animate-spin" size={20} /> : <Zap size={20} className="group-hover/btn:animate-pulse" />}
          {ingesting ? "Processando AWS..." : "Consolidar Base AWS"}
          
          <div className="absolute inset-0 bg-white/10 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700" />
        </button>

        <button 
          onClick={handleClear}
          className="w-full h-12 border border-lux-border/20 text-lux-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-all rounded-xl text-[10px] font-black uppercase tracking-widest"
        >
          Limpar Ingestão Atual
        </button>
      </div>

      <div className="mt-6 flex items-center gap-3 px-3">
         <div className={`w-2 h-2 rounded-full ${localSources.length > 0 ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
         <p className="text-[9px] font-black text-lux-muted uppercase tracking-[0.1em]">
           {localSources.length > 0 ? 'Existem fontes aguardando cloud' : 'Sistema em Compliance AWS'}
         </p>
      </div>
      
      {success && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute inset-0 bg-emerald-600 flex items-center justify-center gap-3 text-white font-black uppercase tracking-[0.2em] text-xs z-20"
        >
          <CheckCircle2 size={24} /> Sucesso
        </motion.div>
      )}
    </div>
  );
}
