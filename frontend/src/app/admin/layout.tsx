"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  ShieldCheck, 
  Settings, 
  Users, 
  MessageSquareQuote, 
  ChevronRight,
  Database,
  LayoutDashboard
} from "lucide-react";

/**
 * AdminLayout
 * ───────────
 * Shell administrativo com Sidebar de Governança.
 * Estética: Clean Luxury (Fundo suave, Glassmorphism, Micro-interações).
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isDarkMode, setIsDarkMode] = React.useState(false);

  // Sincronizar tema com localStorage e documentElement
  React.useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") {
      setIsDarkMode(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleDarkMode = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    if (newMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  };

  const menuItems = [
    { name: "Dashboard Admin", icon: LayoutDashboard, href: "/admin" },
    { name: "Global System Prompts", icon: MessageSquareQuote, href: "/admin/prompts" },
    { name: "Gestão de Usuários", icon: Users, href: "/admin/users" },
    { name: "Domínios de Dados", icon: Database, href: "/admin/domains" },
    { name: "Configurações", icon: Settings, href: "/admin/settings" },
  ];

  return (
    <div className="flex h-screen bg-lux-bg text-lux-text transition-colors duration-500">
      {/* Sidebar Corporativa */}
      <aside className="w-72 border-r border-lux-border/30 bg-lux-bg/50 backdrop-blur-xl flex flex-col p-6">
        <div className="mb-10 pl-2">
          <h2 className="text-sm font-bold tracking-widest text-[#D4AF37] dark:text-lux-accent uppercase tracking-widest">Painel de Controle</h2>
          <p className="text-[10px] text-lux-muted mt-1 italic tracking-tighter uppercase font-black">Governança de IA Corporativa</p>
        </div>

        <nav className="flex-1 space-y-2">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link 
                key={item.href} 
                href={item.href}
                className={`
                  flex items-center justify-between p-3 rounded-xl transition-all duration-300
                  ${isActive 
                    ? "bg-lux-card/50 text-lux-text shadow-sm border border-lux-border/40 dark:border-lux-accent/30 dark:text-lux-accent" 
                    : "text-lux-muted hover:bg-lux-card/30 hover:text-lux-text"
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <item.icon size={18} strokeWidth={isActive ? 2.5 : 2} />
                  <span className="text-sm font-semibold tracking-tight">{item.name}</span>
                </div>
                {isActive && <div className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] dark:bg-lux-accent" />}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto p-4 rounded-2xl bg-gradient-to-br from-[#1A1A1A] to-[#333333] dark:from-lux-card dark:to-lux-bg text-white overflow-hidden relative group">
          <div className="relative z-10 transition-transform duration-500 group-hover:scale-105">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase font-black tracking-widest text-lux-accent bg-lux-accent/10 px-2 py-0.5 rounded shadow-sm">
                Espaço de Inteligência
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-lux-text tracking-tight flex items-center gap-3">
              Projeto: <span className="opacity-60">ADMIN</span>
            </h1>
          </div>
          <div className="absolute -right-4 -bottom-4 w-16 h-16 bg-[#D4AF37]/20 dark:bg-lux-accent/20 blur-2xl rounded-full" />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto bg-lux-bg/20">
        <header className="h-20 border-b border-lux-border/20 bg-lux-bg/30 backdrop-blur-md flex items-center justify-between px-10 sticky top-0 z-40">
          <div className="flex items-center gap-2 text-sm text-lux-muted">
            <span>Admin</span>
            <ChevronRight size={14} />
            <span className="text-lux-text font-semibold tracking-tight">
              {menuItems.find(i => i.href === pathname)?.name || "Geral"}
            </span>
          </div>

          <div className="flex items-center gap-6">
              {/* Theme Toggle Button */}
              <button 
                onClick={toggleDarkMode}
                className="p-2.5 hover:bg-lux-border/20 rounded-xl text-lux-muted hover:text-lux-text transition-all border border-lux-border/30"
                title="Alternar Modo Onyx"
              >
                {isDarkMode ? "☀️" : "🌙"}
              </button>

             <div className="flex flex-col items-end">
                <span className="text-xs font-bold tracking-tight">Administrador NTT</span>
                <span className="text-[10px] text-[#D4AF37] dark:text-lux-accent uppercase font-bold tracking-widest">Master Tenant</span>
             </div>
             <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#B8860B] dark:from-lux-accent dark:to-lux-border flex items-center justify-center text-white font-bold shadow-lg shadow-[#D4AF37]/20 border-2 border-white dark:border-lux-border">
                AD
             </div>
          </div>
        </header>

        <section className="p-10 max-w-7xl mx-auto">
          {children}
        </section>
      </main>
    </div>
  );
}
