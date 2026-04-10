"use client";
import { motion } from "framer-motion";
import { FolderKanban, Plus, Clock, Search, Workflow } from "lucide-react";
import Link from "next/link";

export default function ProjectsList() {

  const projects = [
    { id: "proj-1", name: "Análise Comercial Q3", status: "Ativo", dashboards: 4, date: "Hoje", domain: "Vendas", domainColor: "border-green-500" },
    { id: "proj-2", name: "Operações Logísticas", status: "Em Revisão", dashboards: 2, date: "Ontem", domain: "Operações", domainColor: "border-orange-500" },
    { id: "proj-3", name: "Finanças - Modelo Cx.", status: "Ativo", dashboards: 8, date: "01/Abr", domain: "Financeiro", domainColor: "border-blue-500" },
  ];

  return (
    <motion.div initial={false} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="w-full">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
        <div>
          <h1 className="text-4xl font-serif font-bold text-lux-text mb-2 transition-colors">Projetos de Dados Corporativos</h1>
          <p className="text-lux-muted text-lg">Área master de análise: Selecione um modelo já estruturado do catálogo ou desenhe um novo projeto Neural.</p>
        </div>
        <Link href="/projects/new" className="flex items-center gap-2 bg-lux-text text-lux-bg px-6 py-3 rounded-xl text-sm font-bold shadow-lg hover:scale-105 transition-transform">
          <Plus size={18} /> Cadastrar Um Projeto Novo
        </Link>
      </div>

      <div className="mb-8 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-lux-muted/70" size={18} />
          <input type="text" placeholder="Buscar projetos..." className="glass-input pl-12 h-12 w-full text-lg shadow-sm" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((p, i) => (
          <Link href={`/projects/${p.id}/sources`} key={p.id}>
            <motion.div 
              whileHover={{ y: -6, scale: 1.01 }}
              transition={{ duration: 0.2 }}
              className={`glass-panel p-8 cursor-pointer border-l-4 ${p.domainColor} hover:border-lux-text/30 hover:shadow-xl transition-all h-full flex flex-col group bg-lux-bg/40`}
            >
              <div className="flex justify-between items-start mb-6">
                <div className="w-12 h-12 rounded-xl bg-lux-bg/80 border border-lux-border/40 flex items-center justify-center text-lux-text shadow-sm group-hover:bg-lux-text group-hover:text-lux-bg transition-colors">
                  <FolderKanban size={24} />
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-lux-muted">
                    {p.domain}
                  </span>
                  <span className="text-xs font-medium px-3 py-1.5 rounded-full border border-lux-border/40 bg-lux-bg/60 text-lux-text shadow-sm">
                    {p.status}
                  </span>
                </div>
              </div>
              
              <h3 className="text-2xl font-bold text-lux-text mb-2 font-serif group-hover:underline underline-offset-4 decoration-lux-border">{p.name}</h3>
              <p className="text-sm text-lux-muted flex items-center gap-2 mb-8 font-medium">
                <Clock size={16} /> Atualizado {p.date}
              </p>
              
              <div className="mt-auto border-t border-lux-border/40 pt-5 flex items-center justify-between">
                <span className="text-sm text-lux-muted font-medium flex items-center gap-2">
                  <Workflow size={16} /> {p.dashboards} Dashboards
                </span>
                <span className="text-lux-text opacity-0 group-hover:opacity-100 transition-opacity text-sm font-bold tracking-wide">
                  Gerenciar →
                </span>
              </div>
            </motion.div>
          </Link>
        ))}
      </div>
    </motion.div>
  );
}
