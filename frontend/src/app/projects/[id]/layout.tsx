"use client";
import React, { useEffect } from "react";
import { useParams } from "next/navigation";
import { ProjectPhases } from "@/components/project/ProjectPhases";
import { motion } from "framer-motion";

/**
 * ProjectLayout
 * ────────────
 * Layout principal para as etapas do projeto (1 a 4).
 * Fornece o contexto de ID do projeto e o container base com fundo Clean Luxury.
 * O cabeçalho de navegação (Etapa X de 5) é injetado individualmente em cada página.
 * A linha do tempo (ProjectPhases) é preservada como solicitado pelo usuário.
 */
export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const projectId = params.id as string;

  useEffect(() => {
    sessionStorage.setItem("agent_bi_current_project_id", projectId);
  }, [projectId]);

  return (
    <div className="min-h-screen bg-lux-bg transition-colors duration-500 pt-8 overflow-x-hidden">
      <div className="max-w-[1700px] mx-auto px-4 md:px-8">
        
        {/* Linha do Tempo (Preservada) */}
        <div className="relative z-0 mb-8 pt-4">
          <ProjectPhases projectId={projectId} />
        </div>

        <motion.main
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full"
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
