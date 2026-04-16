"use client";

import Link from "next/link";

interface EventCardProps {
  event: {
    event_id: string;
    title: string | null;
    summary?: string | null;
    content_zh?: string | null;
    source: string;
    entity_id?: string;
    published_at: string;
    alert_level: string;
    score?: number;
    targets?: string[];
  };
  compact?: boolean;
}

const alertStyles: Record<string, { pill: string; border: string; glow: string }> = {
  S: {
    pill: "bg-red-500/20 text-red-200 ring-1 ring-red-400/30",
    border: "border-red-500/40",
    glow: "from-red-500/12 via-transparent to-transparent",
  },
  A: {
    pill: "bg-orange-500/20 text-orange-200 ring-1 ring-orange-400/30",
    border: "border-orange-500/30",
    glow: "from-orange-500/12 via-transparent to-transparent",
  },
  B: {
    pill: "bg-blue-500/20 text-blue-200 ring-1 ring-blue-400/30",
    border: "border-blue-500/30",
    glow: "from-blue-500/12 via-transparent to-transparent",
  },
  C: {
    pill: "bg-slate-700/70 text-slate-200 ring-1 ring-slate-500/40",
    border: "border-slate-700",
    glow: "from-slate-500/10 via-transparent to-transparent",
  },
};

export function EventCard({ event, compact }: EventCardProps) {
  const summary = event.summary || event.content_zh || "";
  const displaySummary = summary.length > 120 ? summary.slice(0, 120) + "..." : summary;
  
  const timeAgo = getTimeAgo(new Date(event.published_at));
  const style = alertStyles[event.alert_level] || alertStyles.C;
  
  return (
    <Link href={`/dashboard/events/${event.event_id}`} className="block">
      <div
        className={`group relative overflow-hidden rounded-2xl border ${style.border} bg-[#11131a] p-4 transition duration-200 hover:-translate-y-0.5 hover:border-slate-500/60 hover:bg-[#171a24]`}
      >
        <div className={`pointer-events-none absolute inset-0 bg-gradient-to-r ${style.glow}`} />
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${style.pill}`}>
                {event.alert_level}
              </span>
              <span className="rounded-full bg-slate-800/80 px-2.5 py-1 text-[11px] text-gray-300">
                {event.source}
              </span>
              {event.entity_id && (
                <span className="rounded-full bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-400">
                  {event.entity_id}
                </span>
              )}
              <span className="text-xs text-gray-500">{timeAgo}</span>
              {event.score !== undefined && event.score > 0 && (
                <span className="rounded-full bg-yellow-500/12 px-2.5 py-1 text-[11px] font-medium text-yellow-300 ring-1 ring-yellow-500/20">
                  {event.score.toFixed(1)}分
                </span>
              )}
            </div>
            
            <h3 className="mb-1 line-clamp-2 text-sm font-medium text-white">
              {event.title || "无标题"}
            </h3>
            
            {!compact && (
              <p className="line-clamp-2 text-xs leading-5 text-gray-400">
                {displaySummary || "暂无摘要"}
              </p>
            )}
            
            {event.targets && event.targets.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {event.targets.slice(0, 3).map((t) => (
                  <span key={t} className="rounded-full bg-blue-500/10 px-2 py-1 text-[11px] text-blue-300 ring-1 ring-blue-500/20">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="pt-1 text-slate-600 transition group-hover:text-slate-300">↗</div>
        </div>
      </div>
    </Link>
  );
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
