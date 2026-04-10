"use client";
import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, QrCode, Smartphone, CheckCircle2, ArrowRight, RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";

export default function MFAPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [isFirstAccess, setIsFirstAccess] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length < 6) return;
    
    setLoading(true);
    // Simulação da validação do TOTP via AWS Cognito SDK
    setTimeout(() => {
        // BYPASS DE HOMOLOGAÇÃO: Aceita qualquer código de 6 dígitos
        if (code.length === 6) {
            // GRAVAR COOKIE DE SESSÃO PARA O MIDDLEWARE RECONHECER
            document.cookie = "session_token=valid_mock_token; path=/; max-age=3600";
            sessionStorage.setItem("agent_bi_access_token", "valid_mock_token");
            sessionStorage.setItem("agent_bi_tenant_slug", "default");
            router.push("/projects");
        } else {
            setError(true);
            setLoading(false);
        }
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-lux-bg flex items-center justify-center p-6 relative font-sans transition-colors duration-500 overflow-hidden">
      
      <motion.div 
        initial={false}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-[500px] z-10"
      >
        <div className="glass-panel p-10 md:p-14 border-lux-border/40 shadow-2xl relative">
            
            {/* Header / Security Context */}
            <div className="mb-10 text-center">
               <div className="w-16 h-16 rounded-3xl bg-lux-text text-lux-bg mx-auto flex items-center justify-center mb-6 shadow-xl">
                  <ShieldAlert size={32} />
               </div>
               <h1 className="text-3xl font-serif font-bold text-lux-text tracking-tight mb-2">Monitor de Identidade</h1>
               <p className="text-lux-muted text-sm px-4 underline underline-offset-4 decoration-lux-accent/30 tracking-tight">
                  Acesso de Homologação: Digite **qualquer código de 6 dígitos** para autenticar seu dispositivo.
               </p>
            </div>

            <form onSubmit={handleVerify} className="space-y-8">
               
               {/* First Access Flow (QR Code) Placeholder Sóbrio */}
               <AnimatePresence>
                  {isFirstAccess && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-lux-card/40 rounded-3xl p-8 border border-lux-border/20 text-center relative overflow-hidden"
                    >
                        <div className="absolute top-0 left-0 w-full h-1 bg-lux-accent" />
                        <div className="flex flex-col items-center gap-4">
                           <div className="bg-white p-6 rounded-2xl shadow-inner mb-2 border border-lux-border/10 opacity-70">
                              <QrCode size={160} className="text-lux-text" />
                           </div>
                           <p className="text-[10px] uppercase font-bold text-lux-muted tracking-widest flex items-center gap-2">
                             <Smartphone size={14}/> Sincronização via Celular
                           </p>
                           <button 
                             type="button"
                             onClick={() => setIsFirstAccess(false)}
                             className="text-[10px] font-black text-lux-accent uppercase tracking-widest hover:opacity-70 transition-opacity"
                           >
                             Prosseguir para Digitação
                           </button>
                        </div>
                    </motion.div>
                  )}
               </AnimatePresence>

               {/* TOTP Input Section */}
               <div className="flex flex-col items-center gap-6">
                  <label className="text-[10px] uppercase font-bold text-lux-muted tracking-[0.2em]">Verificação Multifator (MFA)</label>
                  <div className="relative w-full">
                     <input 
                       required
                       type="text" 
                       maxLength={6}
                       placeholder="000000"
                       value={code}
                       onChange={(e) => { 
                          setError(false);
                          setCode(e.target.value.replace(/[^0-9]/g, ''));
                       }}
                       className={`w-full bg-white border h-16 text-center text-4xl font-serif tracking-[0.4em] rounded-2xl shadow-inner outline-none transition-all ${error ? 'border-red-500 bg-red-50 text-red-700' : 'border-lux-border/40 focus:border-lux-text focus:shadow-xl'}`}
                     />
                     {error && (
                        <p className="absolute -bottom-6 left-0 w-full text-center text-[10px] font-bold text-red-600 uppercase tracking-widest">Código incorreto ou expirado</p>
                     )}
                  </div>
               </div>

               <button 
                 type="submit"
                 disabled={loading || code.length < 6}
                 className="w-full flex items-center justify-center gap-3 bg-lux-text text-lux-bg p-5 rounded-2xl font-bold shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 disabled:grayscale disabled:scale-100 group text-lg tracking-tight font-serif"
               >
                 {loading ? "Processando Auditoria..." : "Autenticar Acesso Seguro"}
                 {!loading && <CheckCircle2 size={22} className="opacity-0 group-hover:opacity-100 transition-all text-lux-accent" />}
               </button>
            </form>

            <div className="mt-12 flex justify-center">
               <button className="flex items-center gap-2 text-xs font-bold text-lux-muted hover:text-lux-text transition-colors">
                  <RefreshCcw size={14} /> Solicitar Nova Chave Digital
               </button>
            </div>
        </div>

        {/* Bottom Section: Branding e Segurança */}
        <div className="mt-8 flex items-center justify-center gap-6">
           <img src="/logos/ntt-data-black.png" alt="NTT DATA" className="h-4 opacity-70" />
           <div className="w-px h-3 bg-lux-border/30" />
           <img src="/logos/aws-partner.png" alt="AWS" className="h-4 opacity-70" />
           <div className="w-px h-3 bg-lux-border/30" />
           <span className="text-[9px] uppercase font-bold text-lux-muted tracking-widest">Certificado NIST</span>
        </div>
      </motion.div>
    </div>
  );
}
