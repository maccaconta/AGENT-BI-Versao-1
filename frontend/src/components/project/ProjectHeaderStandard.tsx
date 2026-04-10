"use client";

import React from "react";
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar, 
  Layers, 
  Database, 
  Sparkles, 
  Terminal,
  Activity
} from "lucide-react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

interface ProjectHeaderStandardProps {
  projectId: string;
  step: number;
  totalSteps?: number;
  title: string;
  nextHref?: string;
  prevHref?: string;
  nextLabel?: string;
  prevLabel?: string;
  onNext?: () => void;
  onPrev?: () => void;
  nextDisabled?: boolean;
}

/**
 * ProjectHeaderStandard
 * ────────────────────
 * Cabeçalho unificado e elegante para as etapas do projeto (1 a 5).
 * Foco: Simetria, Centralização e Estética Clean Luxury.
 */
export function ProjectHeaderStandard({
  projectId,
  step,
  totalSteps = 5,
  title,
  nextHref,
  prevHref,
  nextLabel = "Avançar",
  prevLabel = "Voltar",
  onNext,
  onPrev,
  nextDisabled
}: ProjectHeaderStandardProps) {
  const router = useRouter();
  const currentDate = "06/04/2026";

  const handleNext = () => {
    if (onNext) {
      onNext();
    } else if (nextHref) {
      router.push(nextHref);
    }
  };

  const handlePrev = () => {
    if (onPrev) {
      onPrev();
    } else if (prevHref) {
      router.push(prevHref);
    }
  };

  const getStepIcon = (s: number) => {
    switch (s) {
      case 1: return <Activity size={16} />;
      case 2: return <Database size={16} />;
      case 3: return <Layers size={16} />;
      case 4: return <Sparkles size={16} />;
      case 5: return <Terminal size={16} />;
      default: return <Activity size={16} />;
    }
  };

  return (
    <header className="w-full -mt-2 pb-6 px-10 flex flex-col items-center">
      {/* Main Nav Cluster (Centralized) */}
      <div className="w-full max-w-5xl flex items-center justify-between gap-8 py-4 px-8 bg-white/40 dark:bg-lux-card/40 border border-lux-border/20 backdrop-blur-3xl rounded-[2.5rem] shadow-sm relative group overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-lux-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

        {/* Action: Back */}
        <div className="flex-1 flex justify-start">
          {prevHref || onPrev ? (
            <button
              onClick={handlePrev}
              className="flex items-center gap-3 px-6 py-3 rounded-2xl text-[11px] font-black text-lux-muted uppercase tracking-widest hover:text-lux-text hover:bg-lux-border/10 transition-all active:scale-95"
            >
              <ChevronLeft size={16} /> {prevLabel}
            </button>
          ) : (
            <div className="px-10" /> // Placeholder to keep symmetry
          )}
        </div>

        {/* Center Cluster: Step & Title */}
        <div className="flex flex-col items-center text-center gap-2">
           <div className="flex items-center gap-3 px-4 py-1.5 bg-lux-text dark:bg-lux-accent text-white dark:text-black rounded-full shadow-lg scale-110">
              <span className="text-[9px] font-black uppercase tracking-[0.25em]">Etapa {step} de {totalSteps}</span>
              <div className="w-1 h-3 bg-white/20 dark:bg-black/20 rounded-full" />
              {getStepIcon(step)}
           </div>
           
           <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-lux-text/60 dark:text-lux-accent/60 mt-2">
             {title}
           </h2>
        </div>

        {/* Action: Next */}
        <div className="flex-1 flex justify-end">
          {nextHref || onNext ? (
            <button
              onClick={handleNext}
              disabled={nextDisabled}
              className={`flex items-center gap-3 px-8 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest shadow-xl transition-all ${
                nextDisabled 
                  ? "bg-lux-border/20 text-lux-muted/40 cursor-not-allowed" 
                  : "bg-lux-text dark:bg-lux-accent text-white dark:text-black shadow-lux-text/10 hover:scale-105 active:scale-95"
              }`}
            >
              {nextLabel} <ChevronRight size={16} />
            </button>
          ) : (
            <div className="px-10" /> // Placeholder
          )}
        </div>
      </div>
      
      {/* Decorative Phase Indicator */}
      <div className="mt-6 flex gap-4">
         {[1,2,3,4,5].map(s => (
           <div 
             key={s} 
             className={`h-1.5 rounded-full transition-all duration-700 ${
               s === step ? 'w-12 bg-lux-accent shadow-[0_0_10px_rgba(212,175,55,0.4)]' : 
               s < step ? 'w-3 bg-lux-text opacity-40' : 'w-3 bg-lux-border/30'
             }`}
           />
         ))}
      </div>
    </header>
  );
}
