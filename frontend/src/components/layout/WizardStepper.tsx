"use client";
import { Check, ShieldCheck, Database, Shuffle, BrainCircuit, Sparkles } from "lucide-react";

type StepStatus = "complete" | "current" | "pending";

export default function WizardStepper({ currentStep }: { currentStep: number }) {
  const steps = [
    { id: 1, name: "Governanca Corporativa", icon: ShieldCheck },
    { id: 2, name: "Ingestao AWS", icon: Database },
    { id: 3, name: "Transformacao", icon: Shuffle },
    { id: 4, name: "Contexto Semantico", icon: BrainCircuit },
    { id: 5, name: "Agente BI", icon: Sparkles },
  ];

  const getStatus = (id: number): StepStatus => {
    if (id < currentStep) return "complete";
    if (id === currentStep) return "current";
    return "pending";
  };

  return (
    <div className="w-full max-w-5xl mx-auto mb-14">
      <div className="relative">
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-lux-border/50 dark:bg-lux-border/80 -translate-y-1/2 z-0" />

        <div
          className="absolute top-1/2 left-0 h-0.5 bg-lux-text dark:bg-lux-accent -translate-y-1/2 z-0 transition-all duration-700 ease-in-out shadow-[0_0_10px_rgba(81,56,48,0.5)]"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        <div className="relative z-10 flex justify-between items-center w-full gap-4">
          {steps.map((step) => {
            const status = getStatus(step.id);
            const Icon = step.icon;

            return (
              <div key={step.id} className="flex flex-col items-center text-center flex-1 min-w-0">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-500 shadow-md ${
                    status === "complete"
                      ? "bg-lux-text text-lux-bg scale-100"
                      : status === "current"
                        ? "bg-lux-card border-2 border-lux-text text-lux-text scale-110 shadow-[0_0_15px_rgba(122,100,91,0.4)]"
                        : "bg-lux-bg border border-lux-border/60 dark:border-lux-border/90 text-lux-muted/50 dark:text-lux-muted scale-90"
                  }`}
                >
                  {status === "complete" ? (
                    <Check size={20} strokeWidth={3} />
                  ) : (
                    <Icon size={18} strokeWidth={status === "current" ? 2.5 : 2} />
                  )}
                </div>

                <span
                  className={`mt-3 text-[10px] md:text-[11px] uppercase tracking-wider font-bold transition-all duration-500 leading-tight max-w-[120px] md:max-w-[160px] ${
                    status === "complete"
                      ? "text-lux-text/80"
                      : status === "current"
                        ? "text-lux-text"
                        : "text-lux-muted/60 dark:text-lux-muted"
                  }`}
                >
                  {step.name}
                </span>

                {status === "current" && (
                  <div className="absolute -z-10 w-24 h-24 bg-lux-text/10 rounded-full blur-xl animate-pulse" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
