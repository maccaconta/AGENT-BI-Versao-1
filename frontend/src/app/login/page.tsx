"use client";
import React, { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Globe, Lock, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = () => {
    setLoading(true);
    // Simulação do túnel do Google OAuth2
    setTimeout(() => {
      router.push("/login/mfa"); // Próximo passo: Desafio TOTP
    }, 1800);
  };

  return (
    <div className="min-h-screen bg-lux-bg flex items-center justify-center p-6 relative overflow-hidden transition-colors duration-500 font-sans">
      
      {/* Elementos Decorativos de Background (Lux) */}
      <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-lux-card/10 rounded-full blur-[120px]" />
      <div className="absolute bottom-[-10%] left-[-5%] w-[400px] h-[400px] bg-lux-text/5 rounded-full blur-[100px]" />

      <motion.div 
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-[480px] z-10"
      >
        <div className="glass-panel p-10 md:p-14 border-lux-border/30 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.15)] flex flex-col items-center">
            
            {/* Branding Core */}
            <div className="mb-12 flex flex-col items-center">
               <motion.img 
                 initial={false}
                 animate={{ scale: 1, opacity: 1 }}
                 src="/logos/ntt-data-black.png" 
                 alt="NTT DATA" 
                 className="h-10 w-auto mb-6 object-contain"
               />
               <div className="h-px w-12 bg-lux-border/40 mb-6" />
               <h1 className="text-3xl font-serif font-bold text-lux-text tracking-tight text-center">Monitor de Acesso</h1>
               <p className="text-lux-muted text-[10px] mt-3 font-black uppercase tracking-[0.4em]">Governança & Auditoria</p>
            </div>

            {/* Login Action Area */}
            <div className="w-full space-y-6">
               <button 
                 onClick={handleGoogleLogin}
                 disabled={loading}
                 className="w-full flex items-center justify-center gap-4 bg-white border border-lux-border/30 p-5 rounded-2xl text-lux-text font-bold shadow-sm hover:shadow-md hover:bg-lux-bg transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-wait group"
               >
                 <div className="p-2 bg-lux-bg/50 rounded-lg group-hover:bg-white transition-colors">
                   <img src="/logos/google-cloud.svg" alt="Google" className="w-5 h-5" /> 
                 </div>
                 <span className="text-md">Autenticar via Google Cloud</span>
                 {loading ? (
                    <div className="w-4 h-4 border-2 border-lux-text border-t-transparent rounded-full animate-spin ml-2" />
                 ) : (
                    <ArrowRight size={18} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                 )}
               </button>

               <div className="relative flex items-center justify-center py-4">
                  <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-lux-border/20"></div></div>
                  <span className="relative px-4 bg-lux-bg text-[10px] uppercase font-bold text-lux-muted tracking-widest">Segurança Bancária</span>
               </div>

               {/* Institutional Credits & AWS */}
               <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-lux-bg/30 rounded-2xl flex flex-col items-center justify-center border border-lux-border/10">
                     <ShieldCheck size={20} className="text-lux-muted mb-2" />
                     <span className="text-[10px] font-bold text-lux-text uppercase">AES-256 Auth</span>
                  </div>
                  <div className="p-4 bg-lux-bg/30 rounded-2xl flex flex-col items-center justify-center border border-lux-border/10">
                     <Lock size={20} className="text-lux-muted mb-2" />
                     <span className="text-[10px] font-bold text-lux-text uppercase">Zero Trust</span>
                  </div>
               </div>
            </div>

            {/* Footer Branding */}
            <div className="mt-14 flex items-center gap-3 opacity-60">
               <span className="text-[10px] font-bold text-lux-muted uppercase tracking-widest">Powered by</span>
               <img src="/logos/aws-partner.png" alt="AWS" className="h-5 w-auto" />
            </div>
        </div>

        {/* Global Compliance Note */}
        <p className="mt-8 text-center text-[10px] text-lux-muted/60 max-w-[300px] mx-auto leading-relaxed">
           Esta plataforma é monitorada por protocolos de **Governança Global**. O acesso requer autenticação multifator obrigatória conforme política NTT DATA.
        </p>
      </motion.div>
    </div>
  );
}
