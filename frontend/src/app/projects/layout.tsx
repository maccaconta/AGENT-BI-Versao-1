import { Navbar } from "@/components/layout/Navbar";

export default function ProjectsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-lux-bg">
      <Navbar />
      <main className="pt-28 px-6 md:px-12 max-w-7xl mx-auto pb-12">
        {children}
      </main>
    </div>
  );
}
