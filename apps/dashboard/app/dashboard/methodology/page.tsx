"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/src/lib/api";

const AUTO_REFRESH_MS = 60_000;

interface MethodologyItem {
  event_id: string;
  title: string | null;
  summary_zh: string | null;
  source: string;
  entity_id: string;
  topics: string[];
  target_symbols: string[];
  published_at: string | null;
  methodology_score: number;
}

export default function MethodologyPage() {
  const [items, setItems] = useState<MethodologyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadMethodology(showLoading = false) {
      if (showLoading) {
        setLoading(true);
      }
      setError(null);

      try {
        const result = await api.getMethodology(24);
        if (cancelled) {
          return;
        }
        setItems(result.items || []);
        setLastUpdated(new Date());
      } catch (err) {
        if (cancelled) {
          return;
        }
        console.error(err);
        setError("方法论流加载失败，请稍后重试。");
      } finally {
        if (!cancelled && showLoading) {
          setLoading(false);
        }
      }
    }

    loadMethodology(true);

    const intervalId = window.setInterval(() => {
      loadMethodology(false);
    }, AUTO_REFRESH_MS);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        loadMethodology(false);
      }
    };

    window.addEventListener("focus", handleVisibilityChange);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      window.removeEventListener("focus", handleVisibilityChange);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refreshToken]);

  if (loading) {
    return <div className="p-8 text-gray-400">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[28px] border border-emerald-400/18 bg-[linear-gradient(135deg,rgba(10,21,20,.96),rgba(10,16,28,.94),rgba(14,28,28,.96))] p-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(52,211,153,0.18),transparent_24%),radial-gradient(circle_at_85%_15%,rgba(34,211,238,0.1),transparent_18%)]" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.28em] text-emerald-200/80">Method Feed</div>
            <h1 className="mt-2 text-3xl font-semibold text-white">方法论流</h1>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
              单独跟踪“大模型怎么用出优势”的内容，优先收录工作流、提示词、自动化、agent 实战和前沿工具玩法。
            </p>
          </div>
          <button
            onClick={() => setRefreshToken((value) => value + 1)}
            className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200 transition hover:border-emerald-300/40 hover:bg-emerald-300/14"
          >
            刷新列表
          </button>
        </div>
        <div className="relative mt-5 flex flex-wrap gap-2">
          <Pill label="当前条数" value={`${items.length}`} />
          <Pill label="自动刷新" value="60 秒" />
          <Pill label="最近更新" value={lastUpdated ? formatTime(lastUpdated) : "加载中"} />
          <Pill label="适用场景" value="提示词 / 工作流 / 自动化" />
        </div>
      </section>

      {error && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      )}

      {!items.length && !error ? (
        <div className="rounded-[24px] border border-dashed border-white/10 bg-[rgba(10,16,28,0.84)] p-8 text-center text-slate-500">
          暂无方法论内容。
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {items.map((item) => (
            <Link
              key={item.event_id}
              href={`/dashboard/events/${item.event_id}`}
              className="group rounded-[24px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 transition hover:-translate-y-0.5 hover:border-emerald-400/25 hover:bg-[rgba(14,22,36,0.92)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                    <span className="rounded-full border border-emerald-400/16 bg-emerald-400/10 px-2.5 py-1 text-emerald-200">
                      方法分 {item.methodology_score.toFixed(1)}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                      {item.source}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                      {item.entity_id}
                    </span>
                    <span>{item.published_at ? getTimeAgo(new Date(item.published_at)) : "-"}</span>
                  </div>
                  <h3 className="mt-3 line-clamp-2 text-lg font-semibold text-white">
                    {item.title || "无标题"}
                  </h3>
                </div>
              </div>

              <p className="mt-3 line-clamp-4 text-sm leading-7 text-slate-300">
                {item.summary_zh || "暂无摘要"}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {item.topics?.slice(0, 3).map((topic) => (
                  <span key={topic} className="rounded-full border border-cyan-400/16 bg-cyan-400/10 px-2.5 py-1 text-[11px] text-cyan-200">
                    {topic}
                  </span>
                ))}
                {item.target_symbols?.slice(0, 3).map((symbol) => (
                  <span key={symbol} className="rounded-full border border-amber-400/16 bg-amber-400/10 px-2.5 py-1 text-[11px] text-amber-200">
                    {symbol}
                  </span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
      {label} · {value}
    </span>
  );
}

function formatTime(value: Date) {
  return value.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function getTimeAgo(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}天前`;
  if (hours > 0) return `${hours}小时前`;
  if (minutes > 0) return `${minutes}分钟前`;
  return "刚刚";
}
