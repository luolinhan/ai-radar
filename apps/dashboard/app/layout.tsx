import type { Metadata } from "next";
import "./globals.css";
import { Layout as AppLayout } from "@/src/components/Layout";

export const metadata: Metadata = {
  title: {
    default: "AI Radar",
    template: "%s | AI Radar",
  },
  description: "AI产业链事件驱动交易辅助系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-transparent text-slate-50 antialiased">
        <AppLayout>
          {children}
        </AppLayout>
      </body>
    </html>
  );
}
