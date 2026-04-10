"use client";

import React, { useState, useEffect } from "react";
import { 
  MessageSquareQuote, 
  Palette, 
  ShieldAlert, 
  Save, 
  RefreshCw, 
  Globe,
  Sparkles,
  Info,
  CheckCircle2,
  Cpu,
  BarChart3,
  Zap,
  Activity,
  ChevronRight,
  ShieldCheck
} from "lucide-react";

/**
 * AdminPromptsPage
 * ───────────────
 * Central de Governança de IA. Permite configurar o GlobalSystemPrompt do Tenant.
 * Estética: Ultra-Modern Luxury (Gradients, high-end typography).
 * Atualizado com terminologia corporativa e cores de status nos switches.
 */
export default function AdminPromptsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [activeTab, setActiveTab] = useState<"MASTER" | "SPECIALISTS">("MASTER");
  const [specialists, setSpecialists] = useState<any[]>([]);
  const [selectedSpecialist, setSelectedSpecialist] = useState<any>(null);

  // Ponte direta para o backend no modo Local Fast
  const BACKEND_URL = "http://127.0.0.1:8000";

  const [prompt, setPrompt] = useState({
    id: null as string | null,
    persona_title: "Analista Financeiro Sênior",
    persona_description: "Você é um analista financeiro sênior especializado em identificar relações ocultas em dados e gerar insights estratégicos.",
    style_guide: {
      primary_color: "#D4AF37",
      secondary_color: "#1A1A1A",
      logo_url: "",
      font_family: "Inter"
    } as any,
    compliance_rules: "",
    language: "pt-BR",
    enable_temporal_profile: true,
    enable_correlation_profile: false,
    enable_anomaly_detection: false,
    enable_clustering_profile: false,
    enable_forecasting_profile: false,
    max_tokens_limit: 32000,
    ingestion_row_limit: 5000,
    is_active: true
  });

  const getHeaders = () => ({
    "Content-Type": "application/json",
    "X-Tenant-Slug": "default" // Identificação obrigatória para o backend Django
  });

  useEffect(() => {
    fetchGlobalPrompt();
    fetchSpecialists();
  }, []);

  async function fetchSpecialists() {
    const timestamp = new Date().getTime();
    const url = `${BACKEND_URL}/api/v1/governance/prompt-templates/?_t=${timestamp}`;
    
    try {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        cache: 'no-store'
      });
      
      if (res.ok) {
        const data = await res.json();
        // Como desativamos a paginação no backend, 'data' agora deve ser um array direto
        const rawResults = Array.isArray(data) ? data : (data.results || []);
        
        // Filtra especialistas de forma robusta
        const filtered = rawResults.filter((s: any) => 
            s.category?.toUpperCase() === "SPECIALIST" || s.category === "Especialista"
        );
        
        console.log("🔍 Especialistas carregados:", filtered.length);
        setSpecialists(filtered);
        if (filtered.length > 0 && (!selectedSpecialist || !filtered.find((f: any) => f.id === selectedSpecialist.id))) {
            setSelectedSpecialist(filtered[0]);
        }
      }
    } catch (err: any) {
      console.error("Erro ao carregar especialistas:", err);
    }
  }

  async function fetchGlobalPrompt() {
    try {
      setLoading(true);
      const res = await fetch(`${BACKEND_URL}/api/v1/governance/system-prompts/`, {
        headers: getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        if (data.results && data.results.length > 0) {
          const p = data.results[0];
          setPrompt({
            id: p.id,
            persona_title: p.persona_title,
            persona_description: p.persona_description,
            style_guide: p.style_guide || {},
            compliance_rules: p.compliance_rules || "",
            language: p.language || "pt-BR",
            enable_temporal_profile: p.enable_temporal_profile ?? true,
            enable_correlation_profile: p.enable_correlation_profile ?? false,
            enable_anomaly_detection: p.enable_anomaly_detection ?? false,
            enable_clustering_profile: p.enable_clustering_profile ?? false,
            enable_forecasting_profile: p.enable_forecasting_profile ?? false,
            max_tokens_limit: p.max_tokens_limit ?? 32000,
            ingestion_row_limit: p.ingestion_row_limit ?? 5000,
            is_active: p.is_active
          });
        }
      }
    } catch (err) {
      console.error("Erro ao carregar governança:", err);
      setError("Não foi possível carregar as políticas globais.");
    } finally {
      setLoading(false);
    }
  }

  const handleSave = async () => {
    setSaving(true);
    setSuccess(false);
    setError(null);
    
    try {
      if (activeTab === "MASTER") {
          const isUpdate = !!prompt.id;
          const url = isUpdate 
            ? `${BACKEND_URL}/api/v1/governance/system-prompts/${prompt.id}/` 
            : `${BACKEND_URL}/api/v1/governance/system-prompts/`;
          
          const method = isUpdate ? "PATCH" : "POST";

          const res = await fetch(url, {
            method,
            headers: getHeaders(),
            body: JSON.stringify(prompt)
          });

          if (!res.ok) {
            const errDetail = await res.json().catch(() => ({}));
            throw new Error(errDetail.detail || "Erro ao salvar diretrizes.");
          }
      } else if (activeTab === "SPECIALISTS" && selectedSpecialist) {
          const res = await fetch(`${BACKEND_URL}/api/v1/governance/prompt-templates/${selectedSpecialist.id}/`, {
            method: "PATCH",
            headers: getHeaders(),
            body: JSON.stringify({
                content: selectedSpecialist.content,
                description: selectedSpecialist.description
            })
          });
          if (!res.ok) throw new Error("Erro ao salvar especialista.");
          fetchSpecialists();
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || "Falha ao salvar as diretrizes. Verifique sua conexão.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="h-[60vh] flex flex-col items-center justify-center gap-4 text-[#D4AF37]">
       <RefreshCw className="animate-spin" size={32} />
       <p className="text-xs font-bold tracking-widest uppercase animate-pulse">Sincronizando com a Governança...</p>
    </div>
  );

  return (
    <div className="space-y-10 animate-in fade-in duration-700 max-w-7xl mx-auto pb-20 px-4">
      {/* Cabeçalho de Governança */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="text-4xl font-black tracking-tighter text-[#1A1A1A] font-serif">Centro de Governança de IA</h1>
            <p className="text-[#8C8C8C] mt-2 max-w-xl text-md leading-relaxed tracking-tight border-l-2 border-[#D4AF37] pl-4">
              Defina a persona cognitiva, os especialistas de domínio e as diretrizes de compliance bancário.
            </p>
          </div>
          
          <div className="flex gap-2 p-1 bg-[#F9F9F9] border border-[#F1E9DB] rounded-2xl w-fit">
             <button 
                onClick={() => setActiveTab("MASTER")}
                className={`px-6 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === "MASTER" ? "bg-[#1A1A1A] text-white shadow-lg" : "text-[#8C8C8C] hover:bg-white"}`}>
                Identidade Master
             </button>
             <button 
                onClick={() => setActiveTab("SPECIALISTS")}
                className={`px-6 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === "SPECIALISTS" ? "bg-[#1A1A1A] text-white shadow-lg" : "text-[#8C8C8C] hover:bg-white"}`}>
                Biblioteca de Especialistas
             </button>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-3 shrink-0">
          {success && (
            <div className="flex items-center gap-2 text-emerald-600 text-xs font-black uppercase tracking-widest animate-in slide-in-from-right-4">
               <CheckCircle2 size={14} /> Diretrizes Publicadas com Sucesso
            </div>
          )}
          {error && (
            <div className="bg-red-50 text-red-500 text-[10px] font-black uppercase px-4 py-2 border border-red-100 rounded-full animate-pulse">{error}</div>
          )}
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-3 px-10 py-5 bg-[#1A1A1A] text-white rounded-[2rem] font-black text-sm hover:scale-[1.02] hover:shadow-[0_20px_40px_rgba(212,175,55,0.2)] transition-all disabled:opacity-50 active:scale-95 group shadow-xl"
          >
            {saving ? <RefreshCw className="animate-spin" size={18} /> : <Zap size={18} className="text-[#D4AF37] group-hover:animate-pulse" />}
            {saving ? "Sincronizando..." : `Salvar Configurações de ${activeTab === "MASTER" ? "Persona" : "Especialista"}`}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-8 space-y-10">
          {activeTab === "MASTER" ? (
            <>
              {/* Persona Master */}
              <section className="bg-white border border-[#F1E9DB] p-10 rounded-[3rem] shadow-[0_10px_30px_rgba(0,0,0,0.02)] hover:shadow-[0_20px_60px_rgba(212,175,55,0.05)] transition-all duration-700 relative group">
                <div className="flex items-center gap-4 mb-10">
                  <div className="p-4 bg-[#FDF9F0] text-[#D4AF37] rounded-3xl group-hover:rotate-6 transition-transform shadow-sm">
                    <MessageSquareQuote size={28} />
                  </div>
                  <div>
                    <h2 className="text-2xl font-black tracking-tight text-[#1A1A1A]">Identidade & Persona da IA</h2>
                    <p className="text-[10px] text-[#8C8C8C] font-black tracking-[0.2em] uppercase">Configurações Globais de Persona</p>
                  </div>
                </div>
                
                <div className="space-y-10">
                  <div className="relative group/input">
                    <label className="text-[10px] uppercase tracking-[0.25em] font-black text-[#D4AF37] mb-4 block">Título da Persona Master</label>
                    <input 
                      type="text" 
                      value={prompt.persona_title}
                      onChange={(e) => setPrompt({...prompt, persona_title: e.target.value})}
                      className="w-full p-6 bg-[#F9F9F9] border-2 border-transparent focus:border-[#F1E9DB] focus:bg-white rounded-[1.75rem] text-md font-bold transition-all outline-none shadow-inner"
                      placeholder="Ex: Consultor Estratégico de Negócios"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] uppercase tracking-[0.25em] font-black text-[#D4AF37] mb-4 block">Essência Cognitiva (Lógica & Comportamento)</label>
                    <textarea 
                      rows={6}
                      value={prompt.persona_description}
                      onChange={(e) => setPrompt({...prompt, persona_description: e.target.value})}
                      className="w-full p-8 bg-[#F9F9F9] border-2 border-transparent focus:border-[#F1E9DB] focus:bg-white rounded-[2rem] text-sm leading-relaxed transition-all outline-none resize-none font-serif text-[#333] shadow-inner"
                      placeholder="Descreva detalhadamente como o Agente de IA deve raciocinar e interagir..."
                    />
                  </div>
                </div>
              </section>

              {/* Data Intelligence & AI Performance */}
              <section className="bg-white border border-[#F1E9DB] p-10 rounded-[3rem] shadow-[0_10px_30px_rgba(0,0,0,0.02)] relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                   <Cpu size={120} />
                </div>

                <div className="flex items-center gap-4 mb-12">
                  <div className="p-4 bg-[#1A1A1A] text-[#D4AF37] rounded-3xl shadow-lg">
                    <Activity size={28} />
                  </div>
                  <div>
                    <h2 className="text-2xl font-black tracking-tight text-[#1A1A1A]">Inteligência de Dados & Performance</h2>
                    <p className="text-[10px] text-[#D4AF37] font-black tracking-[0.2em] uppercase">Motor de Processamento "Nova Amazonas"</p>
                  </div>
                </div>

                <div className="space-y-16">
                  {/* Token Limit Control */}
                  <div className="space-y-8 bg-[#FDF9F0]/30 p-8 rounded-[2.5rem] border border-[#F1E9DB]/50">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                      <div>
                        <label className="text-xs uppercase tracking-[0.2em] font-black text-[#1A1A1A] block mb-2 flex items-center gap-2">
                           Limite Mestre de Tokens <Info size={14} className="text-[#D4AF37]" />
                        </label>
                        <p className="text-xs text-[#8C8C8C] leading-relaxed max-w-md italic">
                          Define a profundidade da análise. Valores entre **16k e 32k** são o equilíbrio ideal entre custo e precisão para auditorias de dados.
                        </p>
                      </div>
                      <div className="flex items-center gap-4 bg-white border border-[#F1E9DB] p-4 px-6 rounded-2xl shadow-sm text-[#1A1A1A]">
                        <Zap size={20} className="text-[#D4AF37]" />
                        <span className="text-lg font-mono font-black tracking-tighter">
                          {prompt.max_tokens_limit.toLocaleString()} <span className="text-[#8C8C8C] text-xs">Tokens</span>
                        </span>
                      </div>
                    </div>
                    
                    <div className="relative pt-4">
                      <input 
                        type="range" 
                        min="4000" 
                        max="200000" 
                        step="4000"
                        value={prompt.max_tokens_limit}
                        onChange={(e) => setPrompt({...prompt, max_tokens_limit: parseInt(e.target.value)})}
                        className="w-full h-3 bg-white border border-[#F1E9DB] rounded-full appearance-none cursor-pointer accent-[#D4AF37] hover:scale-[1.01] transition-transform"
                      />
                      <div className="flex justify-between mt-4 text-[9px] text-[#8C8C8C] font-black uppercase tracking-[0.2em]">
                        <span className="opacity-50">Econômico (4k)</span>
                        <span className="text-[#D4AF37] font-black border-b-2 border-[#D4AF37]">Sugestão Ideal (32k)</span>
                        <span className="opacity-50">Contexto Infinito (200k)</span>
                      </div>
                    </div>
                  </div>

                  {/* Statistical Switches */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[
                      { id: 'temporal', label: 'Perfil Temporal', key: 'enable_temporal_profile', icon: <Activity size={20} />, desc: 'Mapeia ciclos sazonais e tendências históricas em datas.' },
                      { id: 'correlation', label: 'Correlação', key: 'enable_correlation_profile', icon: <BarChart3 size={20} />, desc: 'Descobre relações matemáticas ocultas entre colunas.' },
                      { id: 'anomaly', label: 'Anomalias', key: 'enable_anomaly_detection', icon: <ShieldAlert size={20} />, desc: 'Identifica automaticamente outliers e desvios críticos.' }
                    ].map(stat => (
                      <div key={stat.id} className="p-8 bg-[#F9F9F9] border border-transparent hover:border-[#F1E9DB] rounded-[2rem] transition-all group/stat flex flex-col justify-between h-full relative">
                        <div>
                          <div className="flex items-center justify-between mb-4">
                            <div className={`p-3 rounded-2xl shadow-sm group-hover/stat:scale-110 transition-transform ${(prompt as any)[stat.key] ? 'bg-[#1A1A1A] text-[#D4AF37]' : 'bg-white text-[#8C8C8C]'}`}>
                              {stat.icon}
                            </div>
                            <div className="relative inline-flex items-center gap-2">
                               <span className={`text-[9px] font-black uppercase tracking-tighter transition-colors ${(prompt as any)[stat.key] ? 'text-emerald-500' : 'text-slate-400'}`}>
                                  {(prompt as any)[stat.key] ? 'LIGADO' : 'DESLIGADO'}
                               </span>
                               <label className="relative inline-flex items-center cursor-pointer">
                                <input 
                                  type="checkbox" 
                                  checked={(prompt as any)[stat.key]}
                                  onChange={(e) => setPrompt({...prompt, [stat.key]: e.target.checked})}
                                  className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                              </label>
                            </div>
                          </div>
                          <span className="text-sm font-black uppercase tracking-tight block mb-2">
                            {stat.label}
                          </span>
                        </div>
                        <p className="text-xs text-[#8C8C8C] leading-snug italic font-serif">{stat.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              {/* Compliance & Data Guardrails */}
              <section className="bg-white border border-[#F1E9DB] p-10 rounded-[3rem] shadow-[0_10px_30px_rgba(0,0,0,0.02)] relative overflow-hidden group">
                <div className="flex items-center gap-4 mb-6 relative z-10">
                    <div className="p-4 bg-[#FDF9F0] text-[#D4AF37] rounded-3xl border border-[#F1E9DB] shadow-sm">
                      <Zap size={28} />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black tracking-tight text-[#1A1A1A]">Controle de Escala (Ingestão)</h2>
                      <p className="text-[10px] text-[#D4AF37] font-black tracking-[0.25em] uppercase">Limitação de Processamento</p>
                    </div>
                </div>
                
                <div className="relative group/input mb-6">
                  <label className="text-[10px] uppercase tracking-[0.15em] font-black text-[#8C8C8C] mb-2 block">Limite de Linhas para Ingestão (Global)</label>
                  <input 
                    type="number" 
                    value={prompt.ingestion_row_limit || 5000}
                    onChange={(e) => setPrompt({...prompt, ingestion_row_limit: parseInt(e.target.value) || 0})}
                    className="w-full md:w-1/3 p-4 bg-[#F9F9F9] border-2 border-transparent focus:border-[#F1E9DB] focus:bg-white rounded-2xl text-md font-bold transition-all outline-none shadow-sm"
                    placeholder="Ex: 5000"
                  />
                  <p className="text-[9px] text-[#8C8C8C] mt-2 italic">* Este parâmetro define o teto de processamento para novos datasets do Tenant.</p>
                </div>

                <div className="border-t border-[#F1E9DB] pt-8">
                  <label className="text-[10px] uppercase tracking-[0.25em] font-black text-[#D4AF37] mb-4 block">Diretrizes de Compliance Bancário</label>
                  <textarea 
                    rows={5}
                    value={prompt.compliance_rules}
                    onChange={(e) => setPrompt({...prompt, compliance_rules: e.target.value})}
                    className="w-full p-8 bg-[#F9F9F9] border-2 border-transparent rounded-[2rem] text-sm leading-relaxed font-serif focus:border-[#F1E9DB] focus:bg-white outline-none text-[#1A1A1A] placeholder:text-[#8C8C8C]/40 resize-none transition-all shadow-inner relative z-10"
                    placeholder="Ex: 1. Proteger PII (Nomes, CPFs)...\n2. Manter tom de voz institucional...\n3. Não alucinar datas futuras..."
                  />
                </div>
              </section>
            </>
          ) : (
            <>
              {/* Specialist Library */}
              <div className="flex flex-col lg:flex-row gap-10">
                {/* Lista Lateral - Aumentada para ocupar mais espaço se necessário */}
                <div className="w-full lg:w-1/3 space-y-4">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-[10px] font-black uppercase tracking-widest text-[#D4AF37]">Capacidades de Domínio</h3>
                    <span className="px-3 py-1 bg-[#FDF9F0] text-[#D4AF37] text-[8px] font-black rounded-full border border-[#F1E9DB]">
                      {specialists.length} TOTAL
                    </span>
                  </div>
                  
                  <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
                    {specialists.length > 0 ? (
                      specialists.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => setSelectedSpecialist(s)}
                          className={`w-full p-6 rounded-[1.5rem] text-left border-2 transition-all flex items-center justify-between group shadow-sm ${selectedSpecialist?.id === s.id ? "bg-[#1A1A1A] border-[#D4AF37] text-white ring-4 ring-[#D4AF37]/5" : "bg-white border-[#F1E9DB] text-[#1A1A1A] hover:border-[#D4AF37]/50 hover:bg-[#FDF9F0]/30"}`}
                        >
                          <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-xl ${selectedSpecialist?.id === s.id ? "bg-[#D4AF37] text-[#1A1A1A]" : "bg-[#F9F9F9] text-[#8C8C8C]"}`}>
                               <Cpu size={16} />
                            </div>
                            <div>
                              <p className="font-black text-xs uppercase tracking-tight">{s.name}</p>
                              <p className={`text-[9px] font-medium mt-0.5 opacity-60`}>{s.category}</p>
                            </div>
                          </div>
                          <ChevronRight size={14} className={`group-hover:translate-x-1 transition-transform ${selectedSpecialist?.id === s.id ? "text-[#D4AF37]" : "text-[#F1E9DB]"}`} />
                        </button>
                      ))
                    ) : (
                      <div className="p-10 text-center border-2 border-dashed border-[#F1E9DB] rounded-[2rem] bg-[#FDF9F0]/10">
                         <p className="text-[10px] font-black text-[#8C8C8C] uppercase tracking-widest">Nenhum Especialista Disponível</p>
                         <p className="text-[10px] text-[#D4AF37] mt-2 italic font-serif">Selecione um módulo na biblioteca</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Área de Edição - Agora mais robusta e isolada */}
                <div className="w-full lg:w-2/3">
                  {selectedSpecialist ? (
                    <section className="bg-white border border-[#F1E9DB] p-10 rounded-[3rem] shadow-[0_30px_60px_rgba(0,0,0,0.03)] animate-in fade-in zoom-in-95 duration-500 relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-8 opacity-[0.03] rotate-12">
                         <Sparkles size={180} />
                      </div>

                      <div className="flex items-center gap-4 mb-10 relative z-10">
                        <div className="p-4 bg-[#1A1A1A] text-[#D4AF37] rounded-3xl shadow-lg ring-4 ring-[#D4AF37]/10">
                          <Sparkles size={28} />
                        </div>
                        <div>
                          <h2 className="text-2xl font-black tracking-tighter text-[#1A1A1A] uppercase">{selectedSpecialist.name}</h2>
                          <div className="flex items-center gap-2 mt-1">
                             <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                             <p className="text-[9px] text-[#8C8C8C] font-black tracking-[0.2em] uppercase">Módulo de Especialidade Ativo</p>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-10 relative z-10">
                        <div className="group/field">
                          <label className="text-[10px] uppercase tracking-[0.25em] font-black text-[#D4AF37] mb-4 block">Definição do Especialista</label>
                          <input 
                            type="text" 
                            value={selectedSpecialist.description}
                            onChange={(e) => setSelectedSpecialist({...selectedSpecialist, description: e.target.value})}
                            className="w-full p-6 bg-[#F9F9F9] border-2 border-transparent focus:border-[#F1E9DB] focus:bg-white rounded-[1.5rem] text-sm font-bold transition-all outline-none shadow-sm"
                          />
                        </div>

                        <div>
                          <label className="text-[10px] uppercase tracking-[0.25em] font-black text-[#D4AF37] mb-4 block">Lógica de Raciocínio (Prompt Context)</label>
                          <textarea 
                            rows={12}
                            value={selectedSpecialist.content}
                            onChange={(e) => setSelectedSpecialist({...selectedSpecialist, content: e.target.value})}
                            className="w-full p-8 bg-[#F9F9F9] border-2 border-transparent focus:border-[#F1E9DB] focus:bg-white rounded-[2.5rem] text-sm leading-relaxed font-serif text-[#333] shadow-inner outline-none transition-all resize-none"
                            placeholder="Descreva as regras que este especialista deve seguir..."
                          />
                        </div>
                      </div>
                    </section>
                  ) : (
                    <div className="h-[500px] flex flex-col items-center justify-center border-4 border-dashed border-[#F1E9DB] rounded-[4rem] text-[#8C8C8C] p-10 bg-[#FDF9F0]/5">
                        <div className="p-6 bg-white rounded-full shadow-lg mb-6 text-[#D4AF37] animate-bounce">
                           <ChevronRight size={32} />
                        </div>
                        <p className="font-black uppercase tracking-[0.2em] text-xs">Selecione um módulo na biblioteca</p>
                        <p className="text-[10px] mt-2 italic">A configuração será injetada no motor de BI.</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Painel Lateral de Preview */}
        <div className="lg:col-span-4 space-y-8 h-fit lg:sticky lg:top-28">
           <div className="bg-white border-2 border-[#F1E9DB] p-8 rounded-[3rem] shadow-xl relative overflow-hidden group/preview">
              <div className="absolute top-0 right-0 p-6">
                 <Sparkles className="text-[#D4AF37] opacity-40 group-hover/preview:scale-125 transition-transform duration-500" size={24} />
              </div>

              <h3 className="text-xs uppercase tracking-[0.2em] font-black text-[#D4AF37] mb-10">Preview em Tempo Real</h3>
              
              <div className="space-y-6">
                 {activeTab === "MASTER" ? (
                   <>
                     <div className="p-5 bg-[#F9F9F9] rounded-2xl border-l-[6px] border-l-[#D4AF37] shadow-sm">
                        <span className="text-[#8C8C8C] block mb-2 font-black uppercase text-[9px] tracking-widest">Identidade Master</span>
                        <p className="font-black text-[#1A1A1A] text-lg">{prompt.persona_title || "Sem Título"}</p>
                     </div>

                     <div className="p-6 bg-[#FDF9F0] rounded-2xl shadow-inner border border-[#F1E9DB]/40">
                        <span className="text-[#8C8C8C] block mb-3 font-black uppercase text-[9px] tracking-widest">Contexto Master</span>
                        <p className="text-[12px] leading-relaxed text-[#444] italic line-clamp-6 font-serif">
                          "{prompt.persona_description || "Aguardando definição..."}"
                        </p>
                     </div>
                   </>
                 ) : (
                    <>
                     <div className="p-5 bg-[#F9F9F9] rounded-2xl border-l-[6px] border-l-[#D4AF37] shadow-sm">
                        <span className="text-[#8C8C8C] block mb-2 font-black uppercase text-[9px] tracking-widest">Especialista Selecionado</span>
                        <p className="font-black text-[#1A1A1A] text-lg">{selectedSpecialist?.name || "Nenhum"}</p>
                     </div>

                     <div className="p-6 bg-[#FDF9F0] rounded-2xl shadow-inner border border-[#F1E9DB]/40">
                        <span className="text-[#8C8C8C] block mb-3 font-black uppercase text-[9px] tracking-widest">Visão do Domínio</span>
                        <p className="text-[12px] leading-relaxed text-[#444] italic line-clamp-6 font-serif">
                          "{selectedSpecialist?.description || "Selecione uma persona para visualizar..."}"
                        </p>
                     </div>
                    </>
                 )}

                <div className="mt-10 pt-8 border-t-2 border-[#FDF9F0] flex items-center justify-between">
                   <div className="flex -space-x-3">
                      <div className="w-10 h-10 rounded-full border-4 border-white bg-[#1A1A1A] text-white flex items-center justify-center text-[10px] font-black shadow-lg">NTT</div>
                      <div className="w-10 h-10 rounded-full border-4 border-white bg-[#D4AF37] text-white flex items-center justify-center text-[10px] font-black shadow-lg">A-BI</div>
                   </div>
                   <span className="text-[9px] font-black text-[#8C8C8C] uppercase tracking-[0.2em] animate-pulse">Pronto para Injeção</span>
                </div>
              </div>
           </div>

           <div className="bg-[#1A1A1A] p-8 rounded-[2.5rem] shadow-2xl border-t border-white/10 group overflow-hidden">
              <div className="flex items-center gap-3 text-[#D4AF37] mb-6">
                <Info size={18} strokeWidth={3} className="group-hover:rotate-12 transition-transform" />
                <span className="text-[10px] uppercase font-black tracking-[0.25em]">Nota de Autoridade</span>
              </div>
              <p className="text-[12px] text-white/70 leading-relaxed font-serif italic mb-6">
                "Estas diretrizes formam a camada fundamental (Master Prompt) que rege todas as células de IA deste tenant."
              </p>
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                 <div className="w-1/3 h-full bg-[#D4AF37] opacity-50" />
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
