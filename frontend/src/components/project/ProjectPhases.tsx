"use client";
import React from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Database, Shuffle, BrainCircuit, Sparkles, Check } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface Phase {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

export function ProjectPhases({ projectId }: { projectId: string }) {
  const pathname = usePathname();

  const phases: Phase[] = [
    {
      id: "governance",
      label: "Governanca Corporativa",
      icon: <ShieldCheck size={18} />,
      path: "/projects/new",
    },
    {
      id: "sources",
      label: "Ingestao AWS",
      icon: <Database size={18} />,
      path: `/projects/${projectId}/sources`,
    },
    {
      id: "transformation",
      label: "Transformacao",
      icon: <Shuffle size={18} />,
      path: `/projects/${projectId}/sources/preview`,
    },
    {
      id: "semantic",
      label: "Contexto Semantico",
      icon: <BrainCircuit size={18} />,
      path: `/projects/${projectId}/insights`,
    },
    {
      id: "generation",
      label: "Agente BI",
      icon: <Sparkles size={18} />,
      path: `/dashboard/generate`,
    },
  ];

  const getActiveIndex = () => {
    if (pathname.includes("/dashboard/generate")) return 4;
    if (pathname.includes("/insights")) return 3;
    if (pathname.includes("/sources/preview")) return 2;
    if (pathname.includes("/sources")) return 1;
    if (pathname.includes("/projects/new")) return 0;
    if (pathname.includes(`/projects/${projectId}`)) return 0;
    return -1;
  };

  const getPhaseStatus = (index: number) => {
    const activeIndex = getActiveIndex();
    if (activeIndex === -1) return "pending";
    if (index < activeIndex) return "completed";
    if (index === activeIndex) return "active";
    return "pending";
  };

  const activeIndex = getActiveIndex();
  const progressWidth = activeIndex === -1 ? 0 : (activeIndex / (phases.length - 1)) * 100;

  return (
    <div className="w-full pt-1 pb-14 md:pb-12 mb-1">
      <div className="max-w-5xl mx-auto px-2 md:px-4">
        <div className="relative flex items-center justify-between gap-4">
          <div className="absolute top-1/2 left-0 w-full h-[2px] bg-lux-border/45 dark:bg-lux-border/75 -translate-y-1/2 z-0" />

          <motion.div
            className="absolute top-1/2 left-0 h-[3px] bg-lux-text dark:bg-lux-accent -translate-y-1/2 z-0"
            initial={{ width: "0%" }}
            animate={{ width: `${progressWidth}%` }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
          />

          {phases.map((phase, idx) => {
            const status = getPhaseStatus(idx);
            const isActive = status === "active";
            const isCompleted = status === "completed";

            return (
              <div key={phase.id} className="relative z-10 flex flex-col items-center text-center min-w-0 flex-1">
                <Link href={phase.path} className="group">
                  <motion.div
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.95 }}
                    className={`
                      w-11 h-11 md:w-12 md:h-12 rounded-full border-2 flex items-center justify-center transition-all duration-500
                      ${
                        isActive
                          ? "bg-lux-text text-lux-bg border-lux-text shadow-[0_0_20px_rgba(81,56,48,0.3)] dark:border-lux-accent dark:bg-lux-accent"
                          : isCompleted
                            ? "bg-lux-bg/80 text-lux-text border-lux-text dark:text-lux-accent dark:border-lux-accent"
                            : "bg-lux-bg text-lux-muted border-lux-border/60 dark:border-lux-border/90 dark:text-lux-muted hover:border-lux-text/60 dark:hover:border-lux-accent"
                      }
                    `}
                  >
                    {isCompleted ? <Check size={20} strokeWidth={3} /> : phase.icon}
                  </motion.div>
                </Link>

                <span
                  className={`
                    absolute top-full mt-3 text-[9px] md:text-[11px] font-bold uppercase tracking-widest transition-colors duration-500 leading-tight max-w-[110px] md:max-w-[150px]
                    ${isActive ? "text-lux-text dark:text-lux-accent" : "text-lux-muted/75 dark:text-lux-muted"}
                  `}
                >
                  {phase.label}
                </span>

                {isActive && (
                  <motion.div
                    layoutId="phase-indicator"
                    className="absolute -top-2 w-1 h-1 rounded-full bg-lux-text dark:bg-lux-accent"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
