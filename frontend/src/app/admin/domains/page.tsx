"use client";
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Database, 
  Plus, 
  Search, 
  MoreVertical, 
  LayoutGrid, 
  Layers, 
  BarChart3, 
  Shield, 
  Globe,
  Settings2
} from "lucide-react";

interface Domain {
  id: string;
  name: string;
  description: string;
  icon: string;
  project_count: number;
  owner_name: string;
}

export default function DomainsAdminPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    async function fetchDomains() {
      try {
        setIsLoading(true);
        const res = await fetch("http://127.0.0.1:8000/api/v1/projects/domains/?t=" + Date.now(), {
          headers: { "Content-Type": "application/json" }
        });
        if (res.ok) {
          const data = await res.json();
          const results = Array.isArray(data) ? data : (data.results || []);
          const mapped = results.map((d: any) => ({
             id: d.id,
             name: d.name,
             description: d.description || "Área de negócio estratégica.",
             icon: d.icon || "Database",
             project_count: d.project_count || 0,
             owner_name: d.owner?.full_name || d.owner_name || "Data Owner"
          }));
          setDomains(mapped);
        }
      } catch (err) {
        console.error("Erro ao buscar domínios:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchDomains();
  }, []);

  const filteredDomains = domains.filter(d => 
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    d.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Header da Página */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-serif font-bold text-lux-text tracking-tight mb-2">Domínios de Dados</h1>
          <p className="text-lux-muted">Estrutura de Data Mesh: Governança distribuída por áreas de negócio.</p>
        </div>
        
        <button className="flex items-center gap-2 bg-lux-text dark:bg-lux-accent text-lux-bg px-6 py-3 rounded-xl font-bold shadow-lg hover:scale-[1.02] transition-transform">
          <Plus size={20} />
          <span>Novo Domínio</span>
        </button>
      </div>

      {/* Toolbar / Filtros */}
      <div className="flex items-center gap-4 bg-lux-card/30 p-2 rounded-2xl border border-lux-border/20 backdrop-blur-sm">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-lux-muted" size={18} />
          <input 
            type="text" 
            placeholder="Buscar por nome do domínio ou descrição..." 
            className="w-full bg-transparent pl-12 pr-4 py-3 text-sm focus:outline-none text-lux-text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Grid de Domínios */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 rounded-3xl bg-lux-card/20 animate-pulse border border-lux-border/10" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence>
            {filteredDomains.map((domain) => (
              <motion.div
                key={domain.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="group relative glass-panel p-8 hover:bg-lux-card/40 transition-all duration-500 border border-lux-border/30 hover:border-lux-text/30 dark:hover:border-lux-accent/30 flex flex-col h-full"
              >
                <div className="flex justify-between items-start mb-6">
                  <div className="p-4 rounded-2xl bg-lux-text dark:bg-lux-accent text-lux-bg shadow-xl">
                    {domain.icon === "BarChart3" && <BarChart3 size={24} />}
                    {domain.icon === "Layers" && <Layers size={24} />}
                    {domain.icon === "Shield" && <Shield size={24} />}
                  </div>
                  <button className="p-2 text-lux-muted hover:text-lux-text transition-colors">
                    <MoreVertical size={20} />
                  </button>
                </div>

                <div className="flex-1">
                  <h3 className="text-xl font-serif font-bold text-lux-text mb-3">{domain.name}</h3>
                  <p className="text-sm text-lux-muted line-clamp-2 leading-relaxed mb-6">
                    {domain.description}
                  </p>
                </div>

                <div className="pt-6 border-t border-lux-border/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <LayoutGrid size={14} className="text-lux-muted" />
                    <span className="text-xs font-bold text-lux-text">{domain.project_count} Projetos</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-widest text-lux-muted font-bold">Responsável:</span>
                    <span className="text-xs font-bold text-lux-text">{domain.owner_name}</span>
                  </div>
                </div>

                {/* Hover Effect Glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-lux-text/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-[2rem] pointer-events-none" />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Card de Adição Rápida */}
          <motion.button 
            whileHover={{ scale: 1.01 }}
            className="border-2 border-dashed border-lux-border/30 rounded-[2rem] p-8 flex flex-col items-center justify-center gap-4 text-lux-muted hover:text-lux-text hover:border-lux-text/40 dark:hover:border-lux-accent/40 hover:bg-lux-card/10 transition-all duration-300 min-h-[250px]"
          >
            <div className="p-4 rounded-full bg-lux-card/30">
              <Plus size={32} />
            </div>
            <span className="font-bold tracking-tight text-sm uppercase tracking-widest">Adicionar Área de Negócio</span>
          </motion.button>
        </div>
      )}

      {/* Info Data Mesh Section */}
      <div className="mt-12 p-8 rounded-[2rem] bg-gradient-to-br from-lux-text to-[#1a1a1a] dark:from-lux-card dark:to-lux-bg text-lux-bg dark:text-lux-text relative overflow-hidden group shadow-2xl">
         <div className="relative z-10 max-w-2xl">
            <div className="flex items-center gap-3 mb-4">
               <Globe className="text-lux-accent" size={24} />
               <h2 className="text-2xl font-serif font-bold">Filosofia Data Mesh</h2>
            </div>
            <p className="text-lux-bg/70 dark:text-lux-muted leading-relaxed mb-6">
              O Agent-BI opera sob o paradigma de dados como produto. Cada domínio tem autonomia para ingerir, transformar e publicar Dashboards oficiais, mantendo a consistência global através dos Master Prompts injetados no Bedrock.
            </p>
            <div className="flex gap-4">
               <button className="px-6 py-2 bg-lux-accent text-lux-bg rounded-lg font-bold text-sm shadow-lg shadow-lux-accent/20">
                  Documentação de Domínios
               </button>
               <button className="px-6 py-2 border border-lux-accent/30 text-lux-accent rounded-lg font-bold text-sm hover:bg-lux-accent/10 transition-colors">
                  Auditoria de Acesso
               </button>
            </div>
         </div>
         {/* Background Decoration */}
         <div className="absolute right-[-10%] top-[-10%] w-[400px] h-[400px] bg-lux-accent/10 rounded-full blur-[100px]" />
         <div className="absolute right-[5%] bottom-[5%] opacity-20 text-lux-accent transform rotate-12 transition-transform duration-1000 group-hover:rotate-45">
            <Database size={180} strokeWidth={1} />
         </div>
      </div>
    </div>
  );
}
