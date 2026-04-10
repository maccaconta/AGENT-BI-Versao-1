'use client'

import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  ChevronDown, 
  ChevronUp, 
  Activity, 
  Cpu, 
  Database, 
  Clock, 
  Zap,
  Code,
  Maximize2,
  Minimize2,
  Search,
  BarChart3,
  X
} from 'lucide-react';

interface TraceStep {
  id: number;
  step_name: string;
  message: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  status: string;
  timestamp: string;
  metadata: any;
}

export default function DevHUD() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [traces, setTraces] = useState<TraceStep[]>([]);
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const [selectedMetadata, setSelectedMetadata] = useState<any | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Escutar eventos globais para capturar o trace_id atual (Ingestão ou IA)
  useEffect(() => {
    const handleTraceEvent = (e: any) => {
      if (e.detail?.traceId) {
        setActiveTraceId(e.detail.traceId);
        // Opcional: auto-expandir se quiser que o usuário veja o início
        // setIsOpen(true); 
      }
    };
    window.addEventListener('agent-bi-trace', handleTraceEvent);
    return () => window.removeEventListener('agent-bi-trace', handleTraceEvent);
  }, []);

  // Polling dos logs quando houver um trace ativo
  useEffect(() => {
    if (!activeTraceId) return;

    // Limpar traces anteriores ao iniciar um novo monitoramento
    setTraces([]);
    console.log(`[DevHUD] Novo Monitoramento: ${activeTraceId}`);

    const fetchTraces = async () => {
      try {
        const { getBackendAuthHeaders } = await import('@/lib/backendAuth');
        const response = await fetch(`http://127.0.0.1:8000/api/v1/audit/traces/by-trace/${activeTraceId}/`, {
          headers: getBackendAuthHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          console.log(`[DevHUD] Traces Recebidos (${activeTraceId}):`, data.length);
          // Só atualizar se o ID ainda for o ativo (evitar race conditions)
          setTraces(data || []);
        }
      } catch (err) {
        console.error("Erro HUD Polling:", err);
      }
    };

    const interval = setInterval(fetchTraces, 2000);
    fetchTraces(); // Carga inicial

    return () => clearInterval(interval);
  }, [activeTraceId]);

  // Auto-scroll para o TOPO (onde a novidade agora estabiliza)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [traces]);

  if (!activeTraceId && traces.length === 0) return null;

  const getStepIcon = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('rag') || n.includes('conhecimento') || n.includes('recuperação')) return <Search className="w-3.5 h-3.5 text-amber-500" />;
    if (n.includes('perfil') || n.includes('profiling') || n.includes('análise')) return <BarChart3 className="w-3.5 h-3.5 text-blue-400" />;
    if (n.includes('ia') || n.includes('llm') || n.includes('bedrock')) return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
    if (n.includes('banco') || n.includes('tabela') || n.includes('persis')) return <Database className="w-3.5 h-3.5 text-emerald-400" />;
    return <Activity className="w-3.5 h-3.5 text-zinc-400" />;
  };

  const lastStep = traces.length > 0 ? traces[traces.length - 1] : null;
  const historySteps = traces.length > 1 ? [...traces.slice(0, -1)].reverse() : [];

  return (
    <div className={`fixed bottom-6 right-6 z-[9999] font-mono text-[11px] transition-all duration-500 ease-in-out ${isExpanded && isOpen ? 'w-[450px]' : 'w-80'}`}>
      {!isOpen ? (
        <button 
          onClick={() => setIsOpen(true)}
          className="bg-lux-text border border-lux-accent/20 text-lux-bg p-3 rounded-full shadow-2xl hover:scale-105 transition-all flex items-center gap-2 group overflow-hidden"
        >
          <Activity className="w-4 h-4 animate-pulse text-lux-accent" />
          <span className="hidden group-hover:inline pr-2 font-bold uppercase tracking-widest text-[10px]">Engine Monitor</span>
        </button>
      ) : (
        <div className={`glass-panel border-lux-border/30 rounded-2xl shadow-2xl flex flex-col overflow-hidden bg-lux-card/90 dark:bg-lux-card/95 transition-all duration-500 ${isExpanded ? 'h-[650px]' : 'h-[500px]'}`}>
          {/* Header */}
          <div className="bg-lux-text text-lux-bg p-3 flex items-center justify-between shadow-md shrink-0">
            <div className="flex items-center gap-2 font-bold tracking-wider uppercase text-[10px]">
              <Terminal className="w-4 h-4 text-lux-accent" />
              <span>LOG DE EXECUÇÃO</span>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsExpanded(!isExpanded)} 
                className="text-lux-bg/60 hover:text-lux-accent transition-colors p-1"
                title={isExpanded ? "Reduzir" : "Expandir"}
              >
                {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
              <button 
                onClick={() => setIsOpen(false)} 
                className="text-lux-bg/60 hover:text-lux-accent transition-colors p-1"
                title="Fechar"
              >
                <ChevronDown className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Logs Body */}
          <div className="flex-1 flex flex-col overflow-hidden bg-lux-bg/20">
            {traces.length === 0 && (
              <div className="flex-1 overflow-y-auto p-4 space-y-3 flex flex-col items-center justify-center text-lux-muted italic opacity-50">
                <div className="w-10 h-10 rounded-full border-2 border-lux-accent/30 border-t-lux-accent animate-spin mb-4" />
                <span className="tracking-widest uppercase text-[9px] font-bold">Iniciando Telemetria...</span>
              </div>
            )}
            
            {/* EVENTO ATUAL (FIXO NO TOPO DO CONTEÚDO) */}
            {lastStep && (
              <div className="shrink-0 p-4 border-b border-lux-accent/20 bg-lux-text/5 relative group">
                <div className="absolute top-0 left-0 w-full h-0.5 bg-lux-accent/30 animate-pulse" />
                <div 
                  key={lastStep.id} 
                  className="bg-lux-text border border-lux-accent/40 rounded-xl p-4 space-y-3 shadow-[0_4px_20px_rgba(0,0,0,0.3)] ring-1 ring-lux-accent/10 relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 w-1 h-full bg-lux-accent animate-pulse" />
                  
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-lux-accent/20 border border-lux-accent/30 scale-110">
                        {getStepIcon(lastStep.step_name)}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-black uppercase tracking-[0.15em] text-lux-accent text-[11px] leading-tight">{lastStep.step_name}</span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                           <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                           <span className="text-[9px] text-white/50 font-bold tracking-widest uppercase">Processando Agora</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 bg-white/10 px-2 py-1 rounded-md border border-white/10">
                      <div className="w-1 h-1 rounded-full bg-lux-accent animate-ping" />
                      <span className="font-bold text-lux-accent text-[10px] tabular-nums">{lastStep.duration_ms}ms</span>
                    </div>
                  </div>

                  <p className="text-white leading-relaxed font-sans text-[12px] font-medium tracking-tight">
                    {lastStep.message || 'Processando etapa analítica profunda...'}
                  </p>

                  {(lastStep.input_tokens > 0 || lastStep.output_tokens > 0) && (
                    <div className="flex items-center justify-between pt-2.5 border-t border-white/10">
                      <div className="flex items-center gap-1.5 text-[9px] text-white/40 uppercase font-black tracking-[0.2em]">
                        <Zap className="w-3 h-3 text-lux-accent/50" />
                        <span>TOKENS: {lastStep.input_tokens} <span className="text-lux-accent/30 px-1 opacity-50">/</span> {lastStep.output_tokens}</span>
                      </div>
                      <span className="text-[9px] font-bold text-lux-accent/40 tracking-tighter uppercase">Bedrock Active</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* HISTÓRICO (SCROLL INDEPENDENTE) */}
            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar scroll-smooth"
            >
              {historySteps.length > 0 && (
                <div className="flex items-center gap-3 mb-4 opacity-50">
                  <div className="h-px flex-1 bg-lux-border/20" />
                  <span className="text-[9px] font-black text-lux-muted uppercase tracking-[0.3em] whitespace-nowrap">Histórico de Execução</span>
                  <div className="h-px flex-1 bg-lux-border/20" />
                </div>
              )}

              {historySteps.map((step) => (
                <div 
                  key={step.id} 
                  className="bg-white/5 border border-lux-border/10 rounded-xl p-3.5 space-y-2.5 hover:border-lux-accent/20 transition-all hover:bg-white/10 group opacity-50 hover:opacity-100"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-lux-bg/50 border border-lux-border/10 group-hover:border-lux-accent/30 transition-colors">
                        {getStepIcon(step.step_name)}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-bold uppercase tracking-tight text-lux-text/80 group-hover:text-lux-text transition-colors">{step.step_name}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 text-lux-muted/60 border border-lux-border/10 px-2 py-1 rounded-md text-[10px] font-medium tabular-nums group-hover:text-lux-muted">
                      {step.duration_ms}ms
                    </div>
                  </div>

                  <p className="text-lux-muted/70 leading-relaxed font-sans text-xs group-hover:text-lux-muted transition-colors line-clamp-2 hover:line-clamp-none">
                    {step.message || 'Etapa concluída.'}
                  </p>

                  {step.metadata && Object.keys(step.metadata).length > 0 && (
                    <button 
                      onClick={() => setSelectedMetadata(step.metadata)}
                      className="text-[9px] text-lux-accent/60 hover:text-lux-accent flex items-center gap-1.5 pt-1 uppercase font-bold tracking-widest transition-colors"
                    >
                      <Code className="w-3 h-3" />
                      <span>Inspecionar Contexto</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Modal Overlay para JSON */}
          {selectedMetadata && (
            <div className="absolute inset-0 z-[10000] bg-lux-card/98 backdrop-blur-md flex flex-col animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="p-3 border-b border-lux-border/20 flex justify-between items-center bg-lux-text text-lux-bg">
                <span className="text-[10px] font-bold uppercase tracking-widest">Metadados da Etapa</span>
                <button onClick={() => setSelectedMetadata(null)} className="hover:text-lux-accent transition-colors">
                   <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-auto p-4 custom-scrollbar bg-lux-bg/50">
                <pre className="text-[10px] text-lux-text whitespace-pre-wrap font-mono bg-black/5 dark:bg-white/5 p-3 rounded-lg border border-lux-border/10 leading-relaxed">
                  {JSON.stringify(selectedMetadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Footer Status */}
          <div className="p-2.5 bg-lux-text text-lux-bg/50 text-[9px] flex justify-between border-t border-lux-border/20 items-center">
            <span className="font-bold tracking-widest uppercase">ID: {activeTraceId?.slice(0,8)}...</span>
            <span className="flex items-center gap-2 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 font-bold uppercase tracking-widest">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Sync
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
