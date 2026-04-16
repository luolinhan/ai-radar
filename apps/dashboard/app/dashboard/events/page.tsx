"use client";

import { useEffect, useState } from "react";
import { EventCard } from "@/src/components/EventCard";
import { api } from "@/src/lib/api";

const AUTO_REFRESH_MS = 60_000;

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState("");
  const [level, setLevel] = useState("");
  const [keyword, setKeyword] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadEvents(showLoading = false) {
      if (showLoading) {
        setLoading(true);
      }
      setError(null);

      try {
        const data = await api.getEvents({
          ...(source ? { source } : {}),
          ...(level ? { alert_level: level } : {}),
          since_days: 6,
          exclude_retweets: true,
          min_signal: 6,
          suppress_low_signal: true,
          limit: 50,
        });

        if (cancelled) {
          return;
        }

        setEvents(data.items || []);
        setLastUpdated(new Date());
      } catch (e) {
        if (cancelled) {
          return;
        }
        console.error(e);
        setError("事件列表加载失败，请稍后重试。");
      } finally {
        if (!cancelled && showLoading) {
          setLoading(false);
        }
      }
    }

    loadEvents(true);

    const intervalId = window.setInterval(() => {
      loadEvents(false);
    }, AUTO_REFRESH_MS);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        loadEvents(false);
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
  }, [source, level, refreshToken]);

  const filteredEvents = events.filter((event) => {
    if (!keyword.trim()) {
      return true;
    }

    const text = `${event.title || ""} ${event.content_zh || ""}`.toLowerCase();
    return text.includes(keyword.trim().toLowerCase());
  });

  const countsByLevel = filteredEvents.reduce<Record<string, number>>((result, event) => {
    const levelKey = event.alert_level || "C";
    result[levelKey] = (result[levelKey] || 0) + 1;
    return result;
  }, {});
  const latestEventAt = filteredEvents[0]?.published_at ? new Date(filteredEvents[0].published_at) : null;
  const latestEventAgeHours = latestEventAt
    ? (Date.now() - latestEventAt.getTime()) / (1000 * 60 * 60)
    : null;

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[28px] border border-cyan-400/20 bg-[linear-gradient(135deg,rgba(8,20,28,.96),rgba(11,24,31,.94),rgba(10,16,28,.98))] p-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_24%),radial-gradient(circle_at_85%_15%,rgba(16,185,129,0.12),transparent_18%)]" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">Unified Event Tape</div>
            <h1 className="mt-2 text-3xl font-semibold text-white">事件列表</h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-300">
              原始事件流是判断“要不要看详情”的第一道筛选器。先按来源和优先级压缩噪音，再用关键词做临时聚焦。
            </p>
          </div>
          <button
            onClick={() => setRefreshToken((value) => value + 1)}
            className="rounded-full border border-cyan-400/25 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-200 transition hover:border-cyan-300/40 hover:bg-cyan-300/14"
          >
            刷新列表
          </button>
        </div>
        <div className="relative mt-5 flex flex-wrap gap-2">
          <SummaryPill label="当前条数" value={`${filteredEvents.length}`} />
          <SummaryPill label="高优先级" value={`${filteredEvents.filter((item) => ["S", "A"].includes(item.alert_level)).length}`} />
          <SummaryPill label="已筛选来源" value={source || "全部"} />
          <SummaryPill label="关键词" value={keyword.trim() || "未设置"} />
          <SummaryPill label="自动刷新" value="60 秒" />
          <SummaryPill label="页面刷新" value={lastUpdated ? formatTime(lastUpdated) : "加载中"} />
          <SummaryPill label="最新事件" value={latestEventAt ? formatDateTime(latestEventAt) : "暂无"} />
          <SummaryPill label="信号过滤" value="主流高信号" />
        </div>
      </section>

      {latestEventAgeHours !== null && latestEventAgeHours > 6 && (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          近 6 小时内没有通过高信号过滤的新事件。页面已刷新，但低价值 X 噪音已被压掉，因此列表顶部可能不会频繁变化。
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="rounded-[24px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-4">
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto]">
            <input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="搜索标题或摘要"
              className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/40"
            />
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400/40"
            >
              <option value="">全部来源</option>
              <option value="rss">RSS</option>
              <option value="github">GitHub</option>
              <option value="x">X/Twitter</option>
              <option value="web">网页</option>
            </select>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400/40"
            >
              <option value="">全部级别</option>
              <option value="S">S级</option>
              <option value="A">A级</option>
              <option value="B">B级</option>
              <option value="C">C级</option>
            </select>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>筛选会先从服务端拉最近 6 天内的 50 条高时效事件，再在前端做关键词过滤。</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
              共 {filteredEvents.length} 条
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 rounded-[24px] border border-white/10 bg-[rgba(10,16,28,0.84)] p-4">
          {["S", "A", "B", "C"].map((levelKey) => (
            <EventMetric key={levelKey} label={`${levelKey} 级`} value={`${countsByLevel[levelKey] || 0}`} />
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-gray-400">加载中...</div>
      ) : filteredEvents.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-white/10 bg-[rgba(10,16,28,0.84)] p-8 text-center text-slate-500">
          暂无事件
        </div>
      ) : (
        <div className="grid gap-3">
          {filteredEvents.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))}
        </div>
      )}
    </div>
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

function formatDateTime(value: Date) {
  return value.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function SummaryPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
      {label} · {value}
    </span>
  );
}

function EventMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
