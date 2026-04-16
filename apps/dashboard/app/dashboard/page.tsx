"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EventCard } from "@/src/components/EventCard";
import { api } from "@/src/lib/api";

interface DashboardData {
  top_events: any[];
  top_events_count: number;
  alert_stats: Record<string, number>;
  recent_alerts: any[];
  hot_themes: any[];
  backtest_summary: {
    total_count: number;
    hit_count: number;
    hit_rate: number;
    avg_return_1d: number;
  };
  watching_events: any[];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, recommendationResult] = await Promise.all([
        api.getDashboardOverview(),
        api.getRecommendations(4),
      ]);
      setData(overview);
      setRecommendations(recommendationResult.items || []);
    } catch (e) {
      console.error(e);
      setError("总览数据加载失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-gray-400">加载中...</div>;
  }

  const totalAlerts = Object.values(data?.alert_stats || {}).reduce((sum, count) => sum + count, 0);
  const priorityLevel = ["S", "A", "B", "C"].find((level) => (data?.alert_stats?.[level] || 0) > 0) || "C";
  const strongestRecommendation = recommendations.reduce((max, item) => {
    const score = Number(item.final_score || 0);
    return score > max ? score : max;
  }, 0);
  const strongestTheme = (data?.hot_themes || []).reduce((best: any, theme: any) => {
    if (!best) {
      return theme;
    }
    return Number(theme.avg_score || 0) > Number(best.avg_score || 0) ? theme : best;
  }, null);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[32px] border border-cyan-400/20 bg-[linear-gradient(135deg,rgba(9,15,26,.96),rgba(12,28,36,.92),rgba(15,23,42,.94))] p-6 shadow-[0_30px_120px_rgba(2,12,27,0.45)] sm:p-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_26%),radial-gradient(circle_at_82%_18%,rgba(245,158,11,0.14),transparent_18%),linear-gradient(120deg,transparent,rgba(255,255,255,0.03),transparent)]" />
        <div className="relative grid gap-8 xl:grid-cols-[1.25fr_0.75fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.34em] text-cyan-200/80">Live Radar Console</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              把事件流、主题热度和交易线索压缩进一个可执行界面。
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">
              首页优先展示今天值得处理的内容，而不是把你埋进原始数据里。先看高优先级事件，再看主题聚集度，最后决定是否进入详情研判。
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <HeroPill label="推荐跟踪" value={`${recommendations.length} 条`} />
              <HeroPill label="观察队列" value={`${data?.watching_events?.length || 0} 条`} />
              <HeroPill label="活跃主题" value={`${(data?.hot_themes || []).filter((theme: any) => theme.event_count_7d > 0).length} 个`} />
              <HeroPill label="最高优先级" value={`${priorityLevel} 级`} />
            </div>
          </div>

          <aside className="rounded-[28px] border border-white/10 bg-[rgba(8,12,18,0.72)] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Session Brief</div>
                <div className="mt-1 text-lg font-semibold text-white">今日操作摘要</div>
              </div>
              <button
                onClick={loadDashboard}
                className="rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1.5 text-xs text-cyan-200 transition hover:border-cyan-300/40 hover:bg-cyan-300/14"
              >
                刷新
              </button>
            </div>
            <div className="mt-5 space-y-4">
              <SnapshotRow
                label="最高优先级"
                value={`${priorityLevel} 级`}
                detail={`24h ${data?.alert_stats?.[priorityLevel] || 0} 条`}
              />
              <SnapshotRow
                label="最佳推荐分"
                value={strongestRecommendation ? strongestRecommendation.toFixed(1) : "-"}
                detail={recommendations[0]?.title || "暂无推荐事件"}
              />
              <SnapshotRow
                label="最热主题"
                value={strongestTheme?.name_zh || strongestTheme?.name_en || "-"}
                detail={strongestTheme ? `均分 ${Number(strongestTheme.avg_score || 0).toFixed(1)}` : "等待主题聚类"}
              />
              <SnapshotRow
                label="最新关注"
                value={data?.top_events?.[0]?.source || "-"}
                detail={data?.top_events?.[0]?.title || "暂无重点事件"}
              />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/dashboard/events"
                className="rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-100"
              >
                查看事件流
              </Link>
              <Link
                href="/dashboard/themes"
                className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-400/30 hover:bg-white/10"
              >
                浏览主题簇
              </Link>
              <Link
                href="/dashboard/methodology"
                className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200 transition hover:border-emerald-300/40 hover:bg-emerald-300/14"
              >
                查看方法论流
              </Link>
            </div>
          </aside>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="24h 重点事件"
          value={String(data?.top_events_count || 0)}
          detail="按评分与时间排序"
          accent="cyan"
        />
        <StatCard
          label="24h 告警总数"
          value={String(totalAlerts)}
          detail="含 S / A / B / C 级别"
          accent="amber"
        />
        <StatCard
          label="7d 回测命中率"
          value={`${data?.backtest_summary?.hit_rate || 0}%`}
          detail={`${data?.backtest_summary?.hit_count || 0}/${data?.backtest_summary?.total_count || 0} 命中`}
          accent="emerald"
        />
        <StatCard
          label="7d 平均 1D 收益"
          value={`${data?.backtest_summary?.avg_return_1d || 0}%`}
          detail="事件后 1 天收益表现"
          accent="violet"
        />
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.18fr_0.82fr]">
        <section className="space-y-6">
          <div className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">今日重点事件</h2>
                <p className="mt-1 text-sm text-slate-400">优先阅读评分靠前且刚进入观察窗口的事件。</p>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-400">过去 24 小时</span>
            </div>
            {data?.top_events?.length > 0 ? (
              <div className="grid gap-3">
                {data.top_events.map((event: any) => (
                  <EventCard key={event.event_id} event={event} />
                ))}
              </div>
            ) : (
              <EmptyPanel message="暂无重点事件" />
            )}
          </div>

          <div className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">最近告警</h2>
                <p className="mt-1 text-sm text-slate-400">便于回看最近已经触达过的提醒，防止重复处理。</p>
              </div>
              <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Alert Feed</span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {data?.recent_alerts?.length ? (
                data.recent_alerts.map((alert: any) => (
                  <div key={alert.event_id} className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 transition hover:border-cyan-400/20 hover:bg-white/[0.05]">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="line-clamp-2 text-sm font-medium text-white">{alert.title}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-400">
                          <span className="rounded-full bg-slate-900/80 px-2.5 py-1">{alert.source}</span>
                          <span>{new Date(alert.sent_at).toLocaleString("zh-CN")}</span>
                        </div>
                      </div>
                      <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-200">
                        {alert.alert_level}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="md:col-span-2">
                  <EmptyPanel message="暂无已发送告警。" />
                </div>
              )}
            </div>
          </div>

          <section className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <h2 className="mb-4 text-lg font-semibold text-white">观察中事件</h2>
            {data?.watching_events?.length > 0 ? (
              <div className="grid gap-2">
                {data.watching_events.map((event: any) => (
                  <EventCard key={event.event_id} event={event} compact />
                ))}
              </div>
            ) : (
              <EmptyPanel message="暂无观察中事件" />
            )}
          </section>
        </section>

        <section className="space-y-6">
          <div className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">行动清单</h2>
              <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Action Queue</span>
            </div>
            <div className="space-y-3">
              {recommendations.length ? (
                recommendations.map((item) => (
                  <Link
                    key={item.event_id}
                    href={`/dashboard/events/${item.event_id}`}
                    className="block rounded-2xl border border-white/8 bg-white/[0.03] p-4 transition hover:-translate-y-0.5 hover:border-cyan-400/20 hover:bg-white/[0.05]"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="line-clamp-2 text-sm font-medium text-white">{item.title || "无标题"}</div>
                        <div className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">
                          {item.summary_zh || "暂无摘要"}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
                          <span className="rounded-full bg-slate-900/80 px-2.5 py-1">{item.direction || "neutral"}</span>
                          <span className="rounded-full bg-slate-900/80 px-2.5 py-1">{item.action_suggestion}</span>
                          <span className="rounded-full bg-slate-900/80 px-2.5 py-1">{item.risk_level}</span>
                        </div>
                      </div>
                      <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-1 text-xs text-amber-200">
                        {item.final_score?.toFixed?.(1) || item.final_score}
                      </span>
                    </div>
                  </Link>
                ))
              ) : (
                <EmptyPanel message="暂无推荐事件。" />
              )}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">告警分布</h2>
              <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Severity Mix</span>
            </div>
            <div className="grid gap-3">
              {["S", "A", "B", "C"].map((level) => (
                <LevelRow
                  key={level}
                  level={level}
                  count={data?.alert_stats?.[level] || 0}
                  total={totalAlerts}
                />
              ))}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">热门主题</h2>
              <Link href="/dashboard/themes" className="text-sm text-cyan-300 transition hover:text-cyan-200">
                查看全部
              </Link>
            </div>
            <div className="grid gap-3">
              {data?.hot_themes?.length ? (
                data.hot_themes.map((theme: any) => (
                  <Link
                    key={theme.id || theme.name_en}
                    href={`/dashboard/themes/${theme.id}`}
                    className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 transition hover:border-cyan-400/20 hover:bg-white/[0.05]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-medium text-white">{theme.name_zh || theme.name_en}</div>
                        <div className="mt-1 text-xs text-slate-400">
                          7天 {theme.event_count_7d || 0} 条
                        </div>
                      </div>
                      <span className="rounded-full border border-white/10 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300">
                        {theme.heat_trend || "steady"}
                      </span>
                    </div>
                    <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                      <span>均分 {Number(theme.avg_score || 0).toFixed(1)}</span>
                      <span>{(theme.related_symbols || []).slice(0, 3).join(" / ") || "无标的"}</span>
                    </div>
                  </Link>
                ))
              ) : (
                <EmptyPanel message="主题聚类数据尚未生成。" />
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function HeroPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
      {label} · {value}
    </span>
  );
}

function SnapshotRow({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-white">{value}</div>
      <div className="mt-2 line-clamp-2 text-sm text-slate-400">{detail}</div>
    </div>
  );
}

function StatCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: string;
  detail: string;
  accent: "cyan" | "amber" | "emerald" | "violet";
}) {
  const accentStyles = {
    cyan: "from-cyan-400/22 to-blue-500/12",
    amber: "from-amber-400/22 to-orange-500/12",
    emerald: "from-emerald-400/22 to-cyan-400/10",
    violet: "from-violet-400/20 to-fuchsia-500/10",
  };

  return (
    <div className="overflow-hidden rounded-[24px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-5">
      <div className={`mb-4 h-1.5 rounded-full bg-gradient-to-r ${accentStyles[accent]}`} />
      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
      <div className="mt-2 text-sm text-slate-400">{detail}</div>
    </div>
  );
}

function LevelRow({
  level,
  count,
  total,
}: {
  level: string;
  count: number;
  total: number;
}) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
  const colors: Record<string, string> = {
    S: "from-red-400 to-red-600",
    A: "from-orange-400 to-amber-500",
    B: "from-cyan-400 to-blue-500",
    C: "from-slate-400 to-slate-600",
  };

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className="flex items-center justify-between text-sm">
        <div className="font-medium text-white">{level} 级事件</div>
        <div className="text-slate-400">
          {count} 条 / {percentage}%
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-950/80">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colors[level] || colors.C}`}
          style={{ width: `${Math.max(percentage, count > 0 ? 8 : 0)}%` }}
        />
      </div>
    </div>
  );
}

function EmptyPanel({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-8 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}
