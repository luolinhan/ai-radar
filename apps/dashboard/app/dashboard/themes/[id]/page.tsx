"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/src/lib/api";
import { EventCard } from "@/src/components/EventCard";

interface ThemeDetail {
  id: string;
  name_en: string;
  name_zh?: string | null;
  description?: string | null;
  related_symbols?: string[];
  event_count_7d: number;
  event_count_30d: number;
  avg_score: number;
  hit_rate?: number | null;
  heat_trend?: string | null;
  recent_events?: any[];
}

export default function ThemeDetailPage() {
  const params = useParams();
  const [theme, setTheme] = useState<ThemeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTheme() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getTheme(String(params.id));
        setTheme(result);
      } catch (err) {
        console.error(err);
        setError("主题详情加载失败。");
      } finally {
        setLoading(false);
      }
    }

    loadTheme();
  }, [params.id]);

  if (loading) {
    return <div className="p-8 text-gray-400">加载中...</div>;
  }

  if (error) {
    return <div className="p-8 text-red-200">{error}</div>;
  }

  if (!theme) {
    return <div className="p-8 text-gray-400">主题不存在</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/dashboard/themes" className="text-sm text-blue-400">
        返回主题列表
      </Link>

      <section className="rounded-2xl border border-violet-500/20 bg-[linear-gradient(135deg,rgba(25,20,45,.95),rgba(16,20,31,.98))] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.25em] text-slate-500">{theme.name_en}</div>
            <h1 className="mt-2 text-3xl font-bold text-white">{theme.name_zh || theme.name_en}</h1>
            {theme.description && (
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">{theme.description}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <ThemeMetric label="7天事件" value={String(theme.event_count_7d || 0)} />
            <ThemeMetric label="30天事件" value={String(theme.event_count_30d || 0)} />
            <ThemeMetric label="平均评分" value={String(theme.avg_score || 0)} />
            <ThemeMetric
              label="命中率"
              value={theme.hit_rate !== null && theme.hit_rate !== undefined ? `${theme.hit_rate}%` : "-"}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {(theme.related_symbols || []).map((symbol) => (
            <span key={symbol} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              {symbol}
            </span>
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <section>
          <h2 className="mb-3 text-lg font-semibold text-white">相关事件</h2>
          {theme.recent_events && theme.recent_events.length > 0 ? (
            <div className="grid gap-3">
              {theme.recent_events.map((event) => (
                <EventCard key={event.event_id} event={event} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-800 bg-[#11131a] p-8 text-center text-gray-500">
              暂无相关事件。
            </div>
          )}
        </section>

        <aside className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
            <h2 className="mb-3 text-lg font-semibold text-white">主题解读</h2>
            <p className="text-sm leading-7 text-slate-300">
              这个主题页用于快速观察事件堆积、评分质量和关联标的集中度。优先关注 7 天事件密度高、平均评分高、并且关联标的明确的主题。
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
            <h2 className="mb-3 text-lg font-semibold text-white">观察重点</h2>
            <ul className="space-y-2 text-sm text-slate-300">
              <li>热度是否在持续提升</li>
              <li>高分事件是否集中在少数龙头标的</li>
              <li>主题内事件是否存在一致方向</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

function ThemeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0f1117] p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
