"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/src/lib/api";

interface Theme {
  id: string;
  name_en: string;
  name_zh: string | null;
  description: string | null;
  related_symbols: string[];
  event_count_7d: number;
  avg_score: number;
}

export default function ThemesPage() {
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadThemes() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getThemes();
        setThemes(result.items || []);
      } catch (err) {
        console.error(err);
        setError("主题列表加载失败，请稍后重试。");
      } finally {
        setLoading(false);
      }
    }

    loadThemes();
  }, []);

  if (loading) {
    return <div className="p-8 text-gray-400">加载中...</div>;
  }

  const activeThemes = themes.filter((theme) => theme.event_count_7d > 0).length;
  const tradableThemes = themes.filter((theme) => theme.related_symbols?.length > 0).length;
  const topTheme = themes.reduce<Theme | null>((best, theme) => {
    if (!best) {
      return theme;
    }
    return theme.avg_score > best.avg_score ? theme : best;
  }, null);

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[28px] border border-amber-400/18 bg-[linear-gradient(135deg,rgba(24,18,11,.96),rgba(16,22,34,.94),rgba(10,16,28,.98))] p-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.16),transparent_24%),radial-gradient(circle_at_80%_20%,rgba(34,211,238,0.12),transparent_18%)]" />
        <div className="relative grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <div className="text-xs uppercase tracking-[0.28em] text-amber-200/80">Theme Clusters</div>
            <h1 className="mt-2 text-3xl font-semibold text-white">主题热度</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
              主题页负责把零散事件重新组织成可跟踪的交易叙事。优先关注事件密度、平均评分和标的集中度同时抬升的主题。
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <ThemePill label="主题总数" value={`${themes.length}`} />
              <ThemePill label="近 7 天活跃" value={`${activeThemes}`} />
              <ThemePill label="有标的映射" value={`${tradableThemes}`} />
            </div>
          </div>

          <div className="rounded-[24px] border border-white/10 bg-[rgba(8,12,18,0.72)] p-5 backdrop-blur-xl">
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Theme Snapshot</div>
            <div className="mt-3 text-lg font-semibold text-white">
              {topTheme?.name_zh || topTheme?.name_en || "暂无高分主题"}
            </div>
            <div className="mt-2 text-sm text-slate-400">
              {topTheme?.description || "当前主题更多承担分组和追踪作用，待后续评分样本继续累积。"}
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <ThemeMetric label="最高均分" value={topTheme ? topTheme.avg_score.toFixed(1) : "-"} />
              <ThemeMetric label="近 7 天事件" value={topTheme ? String(topTheme.event_count_7d) : "-"} />
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {themes.map((theme) => (
          <Link
            key={theme.id}
            href={`/dashboard/themes/${theme.id}`}
            className="group rounded-[24px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 transition hover:-translate-y-0.5 hover:border-amber-400/25 hover:bg-[rgba(14,22,36,0.92)]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{theme.name_en}</div>
                <h3 className="mt-2 text-lg font-semibold text-white">
                  {theme.name_zh || theme.name_en}
                </h3>
              </div>
              <span className="rounded-full border border-amber-400/18 bg-amber-400/10 px-2.5 py-1 text-sm font-medium text-amber-200">
                {theme.avg_score > 0 ? theme.avg_score.toFixed(1) : "-"}
              </span>
            </div>
            
            {theme.description && (
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-400">{theme.description}</p>
            )}
            
            <div className="mt-5 grid grid-cols-2 gap-3">
              <ThemeMetric label="近 7 天事件" value={String(theme.event_count_7d)} />
              <ThemeMetric label="平均评分" value={theme.avg_score > 0 ? theme.avg_score.toFixed(1) : "-"} />
            </div>

            <div className="mt-4 flex items-center justify-between gap-3">
              <div className="text-sm text-slate-500">
                关联标的 <span className="text-white">{theme.related_symbols?.length || 0}</span> 个
              </div>
              {theme.related_symbols && theme.related_symbols.length > 0 && (
                <div className="flex flex-wrap justify-end gap-1">
                  {theme.related_symbols.slice(0, 4).map((symbol) => (
                    <span key={symbol} className="rounded-full border border-cyan-400/18 bg-cyan-400/10 px-2.5 py-1 text-[11px] text-cyan-200">
                      {symbol}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>

      {!themes.length && !error && (
        <div className="rounded-[24px] border border-dashed border-white/10 bg-[rgba(10,16,28,0.84)] p-8 text-center text-slate-500">
          暂无主题数据。
        </div>
      )}
    </div>
  );
}

function ThemeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}

function ThemePill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
      {label} · {value}
    </span>
  );
}
