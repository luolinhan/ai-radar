"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/src/lib/api";

interface RecommendationItem {
  event_id: string;
  title: string | null;
  summary_zh: string | null;
  why_it_matters_zh: string | null;
  source: string;
  entity_id: string;
  topics: string[];
  target_symbols: string[];
  direction: string;
  risk_level: string;
  action_suggestion: string;
  signal_score: number;
  final_score: number;
  published_at: string | null;
  url: string | null;
}

const directionConfig: Record<string, { label: string; color: string; bg: string }> = {
  bullish: { label: "利好", color: "text-green-700", bg: "bg-green-100" },
  bearish: { label: "利空", color: "text-red-700", bg: "bg-red-100" },
  neutral: { label: "中性", color: "text-gray-700", bg: "bg-gray-100" },
};

export default function RecommendationsPage() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const result = await api.getRecommendations(50);
        if (cancelled) return;
        setItems(result.items || []);
        setLastUpdated(new Date());
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setError("推荐事件加载失败，请稍后重试。");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">推荐事件</h1>
          <p className="text-sm text-gray-500 mt-1">
            经信号评分过滤的高价值事件，按优先级排序
            {lastUpdated && (
              <span className="ml-2">· 更新于 {lastUpdated.toLocaleTimeString("zh-CN")}</span>
            )}
          </p>
        </div>
        <Link
          href="/dashboard"
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          返回总览
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {items.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          暂无推荐事件，可能当前没有高信号事件
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const dir = directionConfig[item.direction?.toLowerCase()] || directionConfig.neutral;
            const scoreColor =
              item.final_score >= 7
                ? "text-red-600"
                : item.final_score >= 5
                ? "text-orange-600"
                : "text-gray-600";

            return (
              <div
                key={item.event_id}
                className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${dir.bg} ${dir.color}`}>
                        {dir.label}
                      </span>
                      <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-50 text-blue-700">
                        评分 {item.final_score ?? 0}/10
                      </span>
                      {item.topics?.slice(0, 3).map((t) => (
                        <span key={t} className="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">
                          {t}
                        </span>
                      ))}
                    </div>
                    <h3 className="text-base font-semibold text-gray-900 truncate">
                      {item.title || "无标题"}
                    </h3>
                    {item.why_it_matters_zh && (
                      <p className="mt-2 text-sm text-gray-700 line-clamp-3">
                        {item.why_it_matters_zh}
                      </p>
                    )}
                    {item.target_symbols && item.target_symbols.length > 0 && (
                      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs text-gray-500">关联标的:</span>
                        {item.target_symbols.map((s) => (
                          <span key={s} className="px-1.5 py-0.5 text-xs font-mono bg-gray-50 rounded">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                    {item.action_suggestion && (
                      <p className="mt-2 text-xs text-gray-500">建议: {item.action_suggestion}</p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-xs text-gray-400">
                      {item.source} · {item.entity_id}
                    </span>
                    {item.published_at && (
                      <span className="text-xs text-gray-400">
                        {new Date(item.published_at).toLocaleDateString("zh-CN")}
                      </span>
                    )}
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        原文
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
