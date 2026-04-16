"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "首页" },
  { href: "/dashboard/events", label: "事件" },
  { href: "/dashboard/methodology", label: "方法论" },
  { href: "/dashboard/themes", label: "主题" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const today = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  
  return (
    <div className="min-h-screen text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[rgba(5,9,14,0.78)] backdrop-blur-2xl">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-8">
            <Link href="/dashboard" className="flex items-center gap-3 text-white">
              <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-400/25 bg-cyan-400/10 text-sm font-semibold text-cyan-200 shadow-[0_0_30px_rgba(34,211,238,0.14)]">
                <span className="absolute inset-[5px] rounded-[14px] border border-cyan-300/10" />
                <span className="relative">AR</span>
              </div>
              <div>
                <div className="text-sm font-semibold tracking-[0.24em] text-slate-100">AI RADAR</div>
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Signal Desk</div>
              </div>
            </Link>
            <nav className="flex flex-wrap gap-2 rounded-full border border-white/10 bg-white/5 p-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href || 
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`rounded-full px-4 py-2 text-sm transition ${
                      isActive 
                        ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.28)]" 
                        : "text-slate-400 hover:bg-white/8 hover:text-white"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <span className="hidden items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs text-emerald-200 sm:inline-flex">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.9)]" />
              Pipeline Online
            </span>
            <a
              href="/api/docs"
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition hover:border-cyan-400/30 hover:bg-white/10 hover:text-white"
            >
              API Docs
            </a>
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-xs text-cyan-200">
              PROD
            </span>
            <span className="hidden rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-500 xl:inline-flex">
              {today}
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6">
        {children}
      </main>
    </div>
  );
}
