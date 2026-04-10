"use client";

import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Database, Shield } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 md:p-8 relative overflow-hidden bg-lux-bg">
      {/* Elementos abstratos de fundo (Ambient lights) */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-lux-card rounded-full mix-blend-multiply blur-3xl opacity-60"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-lux-border rounded-full mix-blend-multiply blur-3xl opacity-40"></div>
      </div>

      <motion.main 
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel w-full max-w-6xl z-10 p-8 md:p-16 text-center"
      >
        <motion.div
           initial={false}
           animate={{ scale: 1, opacity: 1 }}
           transition={{ delay: 0.4, duration: 0.6 }}
           className="mb-8 inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-lux-muted/20 bg-lux-bg/40 backdrop-blur-sm text-sm font-medium text-lux-muted"
        >
          <span className="w-2 h-2 rounded-full bg-lux-text animate-pulse"></span>
          Enterprise Intelligence Engine
        </motion.div>

        <h1 className="font-serif text-5xl md:text-8xl font-bold tracking-tight text-lux-text mb-6">
          Agent<span className="opacity-80 mix-blend-multiply">-BI</span>
        </h1>
        
        <p className="text-lg md:text-2xl text-lux-muted max-w-2xl mx-auto mb-12 font-light leading-relaxed">
          Decisões estratégicas guiadas por Inteligência Artificial autônoma. 
          A arquitetura high-end dos seus dados corporativos.
        </p>

        <motion.div 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex justify-center mb-24"
        >
          <Link href="/projects" className="glass-button flex items-center justify-center gap-3 text-lg px-8 py-4 tracking-wide shadow-xl">
            Acessar Plataforma <ArrowRight size={20} className="opacity-80" />
          </Link>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left mt-12 border-t border-lux-border/30 pt-16">
          <motion.div whileHover={{ y: -5 }} className="glass-panel p-8 bg-lux-bg/40 border-lux-border/20 transition-all hover:bg-lux-bg/70 shadow-none">
            <div className="w-12 h-12 bg-lux-text rounded-xl flex items-center justify-center mb-6 shadow-md">
              <Database className="text-lux-bg" size={22} strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-bold mb-3 font-serif text-lux-text">Data Lake Nativo</h3>
            <p className="text-lux-muted text-sm leading-relaxed">Conecte seus dados em escala na AWS com Athena e Glue.</p>
          </motion.div>

          <motion.div whileHover={{ y: -5 }} className="glass-panel p-8 bg-lux-bg/40 border-lux-border/20 transition-all hover:bg-lux-bg/70 shadow-none">
            <div className="w-12 h-12 bg-lux-text rounded-xl flex items-center justify-center mb-6 shadow-md">
              <BarChart3 className="text-lux-bg" size={22} strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-bold mb-3 font-serif text-lux-text">Auto-Dashboards</h3>
            <p className="text-lux-muted text-sm leading-relaxed">Geração de visões complexas em segundos, através de linguagem natural.</p>
          </motion.div>

          <motion.div whileHover={{ y: -5 }} className="glass-panel p-8 bg-lux-bg/40 border-lux-border/20 transition-all hover:bg-lux-bg/70 shadow-none">
            <div className="w-12 h-12 bg-lux-text rounded-xl flex items-center justify-center mb-6 shadow-md">
              <Shield className="text-lux-bg" size={22} strokeWidth={1.5} />
            </div>
            <h3 className="text-xl font-bold mb-3 font-serif text-lux-text">Governança Auditável</h3>
            <p className="text-lux-muted text-sm leading-relaxed">Audit-trails imutáveis e checkpoints de aprovação humana para publicações.</p>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
