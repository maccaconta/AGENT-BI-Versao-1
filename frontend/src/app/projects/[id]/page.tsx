"use client";
import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Plus, 
  Database, 
  Wand2, 
  BarChart3, 
  MoreVertical, 
  LayoutGrid, 
  Star, 
  ShieldCheck, 
  ArrowUpCircle, 
  Search,
  AlertCircle
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ProjectHeaderStandard } from "@/components/project/ProjectHeaderStandard";

export default function ProjectWorkspace() {
  const params = useParams();
  const projectId = params.id as string;
  const [showDictionaryModal, setShowDictionaryModal] = useState(false);
  const [selectedSource, setSelectedSource] = useState<any>(null);

  // Mocks Inteligentes de Metadados de Versões
  const oficialDash = { 
    id: "dash-1", 
    name: "Cockpit Executivo Financeiro", 
    author: "Diretoria LATAM", 
    version: "v2.5 (Oficial)", 
    date: "Hoje, 09:12" 
  };

  const drafts = [
    { id: "dash-2", name: "Heatmap Regional de Margens", author: "Agente BI", version: "Rascunho-v1.0", date: "Ontem, 18:40" },
    { id: "dash-3", name: "Testes Anomalias Logísticas", author: "Marcio L.", version: "Rascunho-v1.2", date: "02/Abr, 14:20" },
  ];

  // Mocks para demonstração do Dicionário (Em produção viriam da API enriquecida)
  const sources = [
    { 
      name: "fato_mensal_credito.csv", 
      status: "Validado IA", 
      size: "1.2M",
      granularity: "HISTORICAL",
      keys: ["ID_CLIENTE", "DATA_REF"],
      columns: [
        { name: "ID_CLIENTE", desc: "Identificador único do cliente", instr: "Chave primária; não somar." },
        { name: "VL_EXPOSICAO", desc: "Valor total da exposição financeira", instr: "Campo de cálculo (MEASURE); usar para soma total." },
        { name: "VL_INADIMPLENCIA", desc: "Valor em atraso", instr: "Indicador de risco; base para cálculo de PD." }
      ]
    }
  ];

  const openDictionary = (src: any) => {
    setSelectedSource(src);
    setShowDictionaryModal(true);
  };

  return (
    <motion.div initial={false} animate={{ opacity: 1, y: 0 }} className="w-full relative px-4 pb-20">
      <ProjectHeaderStandard 
        projectId={projectId}
        step={1}
        title="Governança & Workspace"
        prevHref={`/projects`}
        prevLabel="Voltar para Projetos"
        nextHref={`/projects/${projectId}/sources`}
        nextLabel="Ir para Ingestão"
      />

      {/* Background Neural Glows Agenticos (Mantendo o Pantone Nude/Luxo) */}
      <div className="absolute top-[-100px] left-1/4 w-[550px] h-[550px] bg-lux-text/5 rounded-full blur-[120px] -z-10 pointer-events-none"></div>
      <div className="absolute top-[200px] right-[-100px] w-[400px] h-[400px] bg-lux-card/50 rounded-full blur-[100px] -z-10 pointer-events-none"></div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-10 relative z-10 mt-10">
        {/* Sidebar Vertical com Data Sources (Semantic Layer) */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-panel p-6 bg-lux-bg/40 backdrop-blur-xl border border-lux-border/40 shadow-sm relative overflow-hidden group rounded-[2rem]">
             {/* Sútil feixe reflexivo rotativo */}
             <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] bg-gradient-to-r from-transparent via-lux-text/5 to-transparent rotate-45 transform -translate-x-[100%] transition-transform duration-1000 group-hover:translate-x-[100%] pointer-events-none"></div>

             <h3 className="font-serif font-bold text-lux-text mb-4 text-xl border-b border-lux-border/30 pb-3 relative z-10">Fontes Mapeadas</h3>
             
             {sources.length === 0 ? (
                <p className="text-sm text-lux-muted my-6 relative z-10">Nenhuma origem conectada ainda.</p>
             ) : (
                <div className="space-y-4 relative z-10">
                  {sources.map((src, i) => (
                    <div key={i} className="p-4 bg-lux-card/60 rounded-lg border border-lux-border/30 shadow-inner group/card">
                      <p className="text-sm font-bold text-lux-text truncate mb-2" title={src.name}>{src.name}</p>
                      <div className="flex items-center justify-between text-xs text-lux-muted mb-3">
                        <span className="text-green-700 font-bold bg-green-50/50 px-2 flex items-center gap-1 rounded py-0.5"><Database size={10}/> {src.status}</span>
                        <span className="font-mono">{src.size} lin.</span>
                      </div>
                      <button 
                        onClick={() => openDictionary(src)}
                        className="w-full py-2 bg-lux-text text-lux-bg text-[10px] font-black uppercase tracking-widest rounded-lg opacity-0 group-hover/card:opacity-100 transition-all hover:bg-lux-accent hover:text-lux-text shadow-lg"
                      >
                        Dicionário de Negócio
                      </button>
                    </div>
                  ))}
                </div>
             )}
             
             <Link href={`/projects/${projectId}/sources`} className="block w-full mt-6 py-3 text-center text-xs uppercase tracking-widest font-bold text-lux-text border border-dashed border-lux-border/60 rounded-lg hover:bg-lux-border/20 transition-all shadow-sm bg-lux-bg/20 relative z-10">
               + Conectar Nova
             </Link>
          </div>
        </div>

        {/* Córtex Central de Dashboards */}
        <div className="lg:col-span-3 space-y-12">
          
          {/* Sessão Blueprint (Oficial Premium) */}
          <section>
            <h2 className="text-sm uppercase tracking-widest font-bold text-lux-text flex items-center gap-2 mb-4 opacity-80">
               <ShieldCheck size={18} className="text-lux-muted"/> Painel Oficial de Produção (Público)
            </h2>
            <div className="glass-panel relative p-6 bg-lux-bg hover:bg-lux-card/40 border border-[#b29a8a]/40 shadow-[0_10px_35px_rgba(81,56,48,0.12)] flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-500 overflow-hidden group hover:-translate-y-1 rounded-[2rem]">
               {/* Glow interno vivo do blueprint */}
               <div className="absolute top-0 right-0 w-80 h-full bg-gradient-to-l from-lux-text/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000 blur-xl pointer-events-none"></div>

               <div className="flex items-center gap-5 relative z-10">
                  <div className="w-16 h-16 rounded-xl bg-lux-text text-lux-bg flex items-center justify-center shadow-xl transform group-hover:scale-105 transition-transform duration-500">
                    <Star size={28} className="fill-current opacity-80" />
                  </div>
                  <div>
                    <h3 className="font-serif font-bold text-lux-text text-2xl flex items-center gap-3">
                       {oficialDash.name}
                       <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded shadow-sm border bg-lux-text text-lux-bg border-lux-text">
                         Blueprint Ativo
                       </span>
                    </h3>
                    <p className="text-sm text-lux-muted flex items-center gap-2 mt-2">
                      Aprovação C-Level: <strong className="text-lux-text">{oficialDash.author}</strong> <span className="opacity-50">•</span> {oficialDash.date}
                    </p>
                  </div>
               </div>
               
               <div className="flex flex-col items-end gap-3 relative z-10">
                  <span className="font-mono text-xs bg-transparent px-3 py-1 rounded text-lux-muted font-bold border border-solid border-lux-border/50 shadow-sm">
                    {oficialDash.version}
                  </span>
                  <div className="flex gap-2">
                    <button className="text-lux-muted hover:text-lux-text p-2 hover:bg-lux-border/20 rounded-lg transition-colors">
                      <MoreVertical size={20} />
                    </button>
                    <button className="bg-lux-text text-lux-bg px-6 py-2 rounded-lg text-sm font-bold shadow-xl hover:scale-105 transition-transform">
                      Analisar Dashboard
                    </button>
                  </div>
               </div>
            </div>
          </section>

          {/* Sessão Rascunhos (Draft) */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm uppercase tracking-widest font-bold text-lux-text flex items-center gap-2 opacity-80">
                 <LayoutGrid size={18} className="text-lux-muted"/> Zona de Rascunhos da IA Gen
              </h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-lux-muted/70" size={14} />
                <input type="text" placeholder="Filtrar rascunhos..." className="glass-input pl-9 h-9 w-56 text-xs bg-lux-bg/50 border-lux-border/40 focus:border-lux-border transition-colors outline-none" />
              </div>
            </div>

            <div className="space-y-4">
              {drafts.map((dash, idx) => (
                <div key={idx} className="glass-panel p-5 bg-lux-bg/20 backdrop-blur-md hover:bg-lux-card/40 border border-lux-border/30 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer transition-colors group rounded-[1.5rem]">
                   <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-lux-bg border border-lux-border/50 flex flex-shrink-0 items-center justify-center text-lux-muted group-hover:text-lux-text group-hover:border-lux-border transition-all shadow-sm">
                        <BarChart3 size={20} />
                      </div>
                      <div>
                        <h3 className="font-bold text-lux-text text-lg flex items-center gap-3">
                           {dash.name}
                        </h3>
                        <p className="text-xs text-lux-muted flex items-center gap-2 mt-1">
                          Desenvolvido por {dash.author} <span className="opacity-50">•</span> Última iteração: {dash.date}
                        </p>
                      </div>
                   </div>
                   
                   <div className="flex items-center gap-4">
                      <span className="font-mono text-[11px] bg-lux-border/10 px-2 py-1 rounded text-lux-muted/70 font-bold border border-dashed border-lux-border/40">
                        {dash.version}
                      </span>
                      {/* Botão de Promover a Oficial com ícone explicativo */}
                      <button className="text-lux-text bg-lux-border/10 hover:bg-lux-border/30 border border-lux-border/20 px-3 py-1.5 rounded flex items-center gap-2 text-xs font-bold transition-colors opacity-0 group-hover:opacity-100" title="Promover a Oficial">
                        <ArrowUpCircle size={14}/> Tornar Público
                      </button>
                      <button className="text-lux-muted hover:text-lux-text p-2 hover:bg-lux-border/20 rounded-full transition-colors opacity-0 group-hover:opacity-100">
                        <MoreVertical size={18} />
                      </button>
                   </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>

      {/* Modal: Dicionário de Negócio (Camada Semântica Enriquecida) */}
      <AnimatePresence>
        {showDictionaryModal && selectedSource && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-6"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="w-full max-w-4xl max-h-[90vh] bg-lux-bg border border-lux-border/40 rounded-[3rem] shadow-2xl overflow-hidden flex flex-col"
            >
              <div className="p-8 border-b border-lux-border/20 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-lux-text text-white flex items-center justify-center shadow-xl">
                    <Database size={28} />
                  </div>
                  <div>
                    <h2 className="text-2xl font-serif font-bold text-lux-text">Dicionário de Negócio</h2>
                    <p className="text-xs text-lux-muted uppercase tracking-widest font-black mt-1">Semântica de Dados • {selectedSource.name}</p>
                  </div>
                </div>
                <button 
                  onClick={() => setShowDictionaryModal(false)}
                  className="w-12 h-12 rounded-full border border-lux-border/20 flex items-center justify-center text-lux-muted hover:bg-lux-text hover:text-white transition-all"
                >
                  <Plus className="rotate-45" size={24} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-10 space-y-8 custom-scrollbar">
                {/* Granularidade */}
                <div className="flex items-center gap-6 p-6 bg-lux-card/40 border border-lux-border/20 rounded-2xl shadow-inner">
                   <div className="w-14 h-14 rounded-full bg-lux-text text-white flex items-center justify-center shadow-lg">
                      <LayoutGrid size={24} />
                   </div>
                   <div>
                      <p className="text-[10px] font-black uppercase tracking-widest text-lux-muted mb-1">Granularidade Detectada</p>
                      <h4 className="text-xl font-bold text-lux-text">
                        {selectedSource.granularity === "HISTORICAL" ? "Histórico Temporal (Snapshot Mensal)" : "Registro Único (Snapshot Atual)"}
                      </h4>
                      <p className="text-xs text-lux-muted mt-1 leading-relaxed italic">
                        "As chaves {selectedSource.keys.join(', ')} identificam a menor unidade de análise neste dataset."
                      </p>
                   </div>
                </div>

                {/* Tabela de Dicionário */}
                <div>
                  <h3 className="text-xs font-black uppercase tracking-[0.2em] text-lux-text mb-4">Campos e Instruções Analíticas</h3>
                  <div className="border border-lux-border/20 rounded-2xl overflow-hidden">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-lux-bg/50 border-b border-lux-border/20 text-lux-muted uppercase tracking-widest">
                          <th className="p-4 font-black">Coluna</th>
                          <th className="p-4 font-black">Conceito de Negócio</th>
                          <th className="p-4 font-black">Instrução de Uso (IA)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-lux-border/10">
                        {selectedSource.columns.map((col: any, idx: number) => (
                          <tr key={idx} className="hover:bg-lux-card/30 transition-colors">
                            <td className="p-4 font-mono font-bold text-lux-text">{col.name}</td>
                            <td className="p-4 text-lux-muted leading-relaxed">{col.desc}</td>
                            <td className="p-4">
                              <span className="px-3 py-1 bg-lux-text text-lux-bg rounded-lg font-bold text-[10px] shadow-sm">
                                {col.instr}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-lux-bg/50 border-t border-lux-border/20 flex justify-end shrink-0">
                <button 
                  onClick={() => setShowDictionaryModal(false)}
                  className="bg-lux-text text-white px-10 py-3 rounded-2xl text-xs font-bold shadow-xl hover:scale-105 transition-transform"
                >
                  Fechar Dicionário
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
